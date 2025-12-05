#!/usr/bin/env python3
"""
Expand strapi collection with slightly relaxed criteria to reach 80+ total.
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

# Configuration
REPO = {"owner": "strapi", "repo": "strapi", "name": "strapi"}

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
MAX_CHANGES = 700  # Increased from 500
MAX_CODE_FILES = 8  # Increased from 5
PRS_TO_FETCH = 400  # Fetch more PRs beyond initial 200


def is_good_pr_candidate(pr: Dict, files: List[Dict]) -> tuple[bool, Dict[str, Any]]:
    """Check if PR is a good candidate for PR Mirroring."""
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

    # Calculate diff size
    total_changes = sum(f.get('additions', 0) + f.get('deletions', 0) for f in files)
    if total_changes > MAX_CHANGES:
        return False, {"reason": "diff_too_large", "changes": total_changes}

    # Focused changes
    if len(code_files) > MAX_CODE_FILES:
        return False, {"reason": "too_many_files", "count": len(code_files)}

    # Don't include merge commits
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


def fetch_prs(owner: str, repo: str, start_page: int = 1, max_prs: int = 200) -> List[Dict]:
    """Fetch merged PRs from GitHub API."""
    prs = []
    page = start_page
    per_page = 100

    print(f"  Fetching PRs starting from page {start_page}...")

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
            print("\n  Rate limit hit. Stopping.")
            break

        if response.status_code != 200:
            print(f"\n  Error: {response.status_code}")
            break

        batch = response.json()
        if not batch:
            print("(no more PRs)")
            break

        merged_prs = [pr for pr in batch if pr.get('merged_at')]
        prs.extend(merged_prs)
        print(f"{len(merged_prs)} merged")

        page += 1
        time.sleep(1)

        if len(batch) < per_page:
            break

    print(f"  Total collected: {len(prs)}")
    return prs[:max_prs]


def fetch_pr_files(owner: str, repo: str, pr_number: int) -> List[Dict]:
    """Fetch files changed in a PR."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/files"

    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []


def filter_prs(owner: str, repo: str, prs: List[Dict], existing_numbers: set) -> List[Dict]:
    """Filter PRs based on relaxed criteria."""
    filtered = []
    stats = {
        "total": len(prs),
        "duplicates": 0,
        "missing_tests_or_code": 0,
        "diff_too_large": 0,
        "too_many_files": 0,
        "passed": 0
    }

    print(f"  Filtering {len(prs)} PRs...")
    print(f"    Max changes: {MAX_CHANGES}, Max files: {MAX_CODE_FILES}")

    for i, pr in enumerate(prs, 1):
        if i % 20 == 0:
            print(f"    Progress: {i}/{len(prs)} ({stats['passed']} new)")

        pr_number = pr['number']

        # Skip duplicates
        if pr_number in existing_numbers:
            stats['duplicates'] += 1
            continue

        files = fetch_pr_files(owner, repo, pr_number)
        if not files:
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

        time.sleep(0.5)

        # Stop if we have enough
        if stats['passed'] >= 30:
            print(f"    Reached 30 new PRs!")
            break

    print(f"\n  Stats: {stats['passed']} new, {stats['duplicates']} duplicates")
    return filtered


def main():
    print("=" * 80)
    print("Expanding Strapi Collection")
    print("=" * 80)

    # Load existing data
    existing_file = Path("/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/logs/prs/strapi/filtered_prs.json")

    with open(existing_file) as f:
        existing_prs = json.load(f)

    print(f"Found {len(existing_prs)} existing strapi PRs")
    existing_numbers = {pr['number'] for pr in existing_prs}

    # Fetch more PRs (pages 5-8)
    owner = REPO['owner']
    repo = REPO['repo']

    new_prs = fetch_prs(owner, repo, start_page=5, max_prs=200)

    if not new_prs:
        print("No new PRs found")
        return

    # Filter
    new_filtered = filter_prs(owner, repo, new_prs, existing_numbers)

    # Combine and save
    all_prs = existing_prs + new_filtered
    all_prs.sort(key=lambda x: x['merged_at'], reverse=True)

    with open(existing_file, 'w') as f:
        json.dump(all_prs, f, indent=2)

    print(f"\n{'='*80}")
    print(f"RESULTS")
    print(f"{'='*80}")
    print(f"Existing: {len(existing_prs)}")
    print(f"New: {len(new_filtered)}")
    print(f"Total: {len(all_prs)}")
    print(f"Saved to: {existing_file}")


if __name__ == "__main__":
    main()
