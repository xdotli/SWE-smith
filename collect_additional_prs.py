#!/usr/bin/env python3
"""
Collect additional PRs with slightly relaxed criteria to reach 80+ total.
"""

import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration - Focus on appsmith since it had low results
REPOS = [
    {"owner": "appsmithorg", "repo": "appsmith", "name": "appsmith"}
]

# GitHub API configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not found in .env file")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

BASE_URL = "https://api.github.com"

# Slightly relaxed filtering parameters
MAX_CHANGES = 600  # Increased from 500
MAX_CODE_FILES = 8  # Increased from 5
PRS_TO_FETCH = 500  # Fetch more PRs


def is_good_pr_candidate(pr: Dict, files: List[Dict]) -> tuple[bool, Dict[str, Any]]:
    """
    Check if PR is a good candidate for PR Mirroring.
    Returns (is_good, metadata)
    """
    # Check for real test files (not snapshots)
    test_files = [
        f['filename'] for f in files if
        (f['filename'].endswith(('.test.ts', '.test.tsx', '.spec.ts', '.spec.tsx'))
        and '.snap' not in f['filename'])
    ]

    # Check for code files
    code_files = [
        f['filename'] for f in files if
        f['filename'].endswith(('.ts', '.tsx'))
        and '.test.' not in f['filename']
        and '.spec.' not in f['filename']
        and 'node_modules' not in f['filename']
        and '__tests__' not in f['filename']
    ]

    # Must have both test and code files
    if not test_files or not code_files:
        return False, {"reason": "missing_tests_or_code"}

    # Calculate diff size (additions + deletions)
    total_changes = sum(f.get('additions', 0) + f.get('deletions', 0) for f in files)
    if total_changes > MAX_CHANGES:
        return False, {"reason": "diff_too_large", "changes": total_changes}

    # Focused changes (not too many files)
    if len(code_files) > MAX_CODE_FILES:
        return False, {"reason": "too_many_files", "count": len(code_files)}

    # Don't include if it's a merge commit
    if pr.get('merge_commit_sha') and 'merge' in pr.get('title', '').lower():
        return False, {"reason": "merge_commit"}

    # Check for snapshot-only changes
    snapshot_files = [f['filename'] for f in files if '.snap' in f['filename']]
    if snapshot_files and len(snapshot_files) == len(test_files):
        return False, {"reason": "snapshot_only"}

    metadata = {
        "test_files": test_files,
        "code_files": code_files,
        "total_changes": total_changes,
        "snapshot_files": snapshot_files
    }

    return True, metadata


def fetch_prs(owner: str, repo: str, max_prs: int = PRS_TO_FETCH) -> List[Dict]:
    """Fetch merged PRs from GitHub API with pagination."""
    prs = []
    page = 1
    per_page = 100

    print(f"  Fetching merged PRs from {owner}/{repo}...")

    while len(prs) < max_prs:
        url = f"{BASE_URL}/repos/{owner}/{repo}/pulls"
        params = {
            "state": "closed",
            "per_page": per_page,
            "page": page,
            "sort": "updated",
            "direction": "desc"
        }

        print(f"    Page {page}... ", end="", flush=True)
        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code == 403:
            print("\n  Rate limit hit. Waiting 60 seconds...")
            time.sleep(60)
            continue

        if response.status_code != 200:
            print(f"\n  Error: {response.status_code}")
            break

        batch = response.json()
        if not batch:
            print("(no more PRs)")
            break

        # Filter for merged PRs only
        merged_prs = [pr for pr in batch if pr.get('merged_at')]
        prs.extend(merged_prs)
        print(f"{len(merged_prs)} merged")

        page += 1
        time.sleep(1)  # Rate limiting

        if len(batch) < per_page:
            break

    print(f"  Total merged PRs collected: {len(prs)}")
    return prs[:max_prs]


def fetch_pr_files(owner: str, repo: str, pr_number: int) -> List[Dict]:
    """Fetch files changed in a PR."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/files"

    try:
        response = requests.get(url, headers=HEADERS)

        if response.status_code == 403:
            print("\n  Rate limit hit. Waiting 60 seconds...")
            time.sleep(60)
            response = requests.get(url, headers=HEADERS)

        if response.status_code == 200:
            return response.json()
        else:
            return []
    except Exception as e:
        return []


def filter_prs(owner: str, repo: str, prs: List[Dict]) -> List[Dict]:
    """Filter PRs based on relaxed criteria."""
    filtered = []
    stats = {
        "total": len(prs),
        "missing_tests_or_code": 0,
        "diff_too_large": 0,
        "too_many_files": 0,
        "merge_commit": 0,
        "snapshot_only": 0,
        "api_errors": 0,
        "passed": 0
    }

    print(f"  Filtering {len(prs)} PRs with relaxed criteria...")
    print(f"    Max changes: {MAX_CHANGES}")
    print(f"    Max code files: {MAX_CODE_FILES}")

    for i, pr in enumerate(prs, 1):
        if i % 20 == 0:
            print(f"    Progress: {i}/{len(prs)} ({stats['passed']} passed so far)")

        pr_number = pr['number']
        files = fetch_pr_files(owner, repo, pr_number)

        if not files:
            stats['api_errors'] += 1
            time.sleep(1)
            continue

        is_good, metadata = is_good_pr_candidate(pr, files)

        if is_good:
            filtered_pr = {
                "number": pr_number,
                "title": pr['title'],
                "merged_at": pr['merged_at'],
                "merge_commit_sha": pr['merge_commit_sha'],
                "base_sha": pr['base']['sha'],
                "html_url": pr['html_url'],
                "test_files": metadata['test_files'],
                "code_files": metadata['code_files'],
                "total_changes": metadata['total_changes'],
                "snapshot_files": metadata.get('snapshot_files', [])
            }
            filtered.append(filtered_pr)
            stats['passed'] += 1
        else:
            reason = metadata.get('reason', 'unknown')
            stats[reason] = stats.get(reason, 0) + 1

        time.sleep(0.5)  # Rate limiting

        # Stop if we have enough new PRs
        if stats['passed'] >= 40:
            print(f"    Reached target of 40 additional PRs!")
            break

    print(f"\n  Filtering Stats:")
    print(f"    Total PRs: {stats['total']}")
    print(f"    Passed: {stats['passed']}")
    print(f"    Missing tests/code: {stats['missing_tests_or_code']}")
    print(f"    Diff too large: {stats['diff_too_large']}")
    print(f"    Too many files: {stats['too_many_files']}")
    print(f"    Merge commits: {stats['merge_commit']}")
    print(f"    Snapshot only: {stats['snapshot_only']}")
    print(f"    API errors: {stats['api_errors']}")

    return filtered


def main():
    print("=" * 80)
    print("Additional PR Collection with Relaxed Criteria")
    print("=" * 80)
    print()

    # Load existing appsmith data
    existing_file = Path("/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/logs/prs/appsmith/filtered_prs.json")

    if existing_file.exists():
        with open(existing_file) as f:
            existing_prs = json.load(f)
        print(f"Found {len(existing_prs)} existing appsmith PRs")
        existing_pr_numbers = {pr['number'] for pr in existing_prs}
    else:
        existing_prs = []
        existing_pr_numbers = set()

    # Fetch and filter new PRs
    owner = "appsmithorg"
    repo = "appsmith"

    print(f"\nFetching additional PRs from {owner}/{repo}...")
    prs = fetch_prs(owner, repo, max_prs=PRS_TO_FETCH)

    if not prs:
        print("No PRs found")
        return

    # Filter PRs
    new_filtered = filter_prs(owner, repo, prs)

    # Remove duplicates
    unique_new = [pr for pr in new_filtered if pr['number'] not in existing_pr_numbers]

    print(f"\n  Found {len(unique_new)} new unique PRs")

    # Combine with existing
    all_prs = existing_prs + unique_new
    all_prs.sort(key=lambda x: x['merged_at'], reverse=True)

    # Save combined results
    output_file = Path("/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/logs/prs/appsmith/filtered_prs.json")
    with open(output_file, 'w') as f:
        json.dump(all_prs, f, indent=2)

    print(f"\n{'='*80}")
    print(f"RESULTS")
    print(f"{'='*80}")
    print(f"Existing PRs: {len(existing_prs)}")
    print(f"New PRs added: {len(unique_new)}")
    print(f"Total PRs: {len(all_prs)}")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()
