#!/usr/bin/env python3
"""
Collect and filter PRs from strapi and appsmith repositories.
Target: 40+ filtered PRs per repo with strict quality criteria.
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
REPOS = [
    {"owner": "strapi", "repo": "strapi", "name": "strapi"},
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

# Filtering parameters
MAX_CHANGES = 500  # ~5KB
MAX_CODE_FILES = 5
PRS_TO_FETCH = 200  # Fetch this many PRs per repo before filtering


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
            print(f"  Error fetching files for PR #{pr_number}: {response.status_code}")
            return []
    except Exception as e:
        print(f"  Exception fetching files for PR #{pr_number}: {e}")
        return []


def filter_prs(owner: str, repo: str, prs: List[Dict]) -> List[Dict]:
    """Filter PRs based on strict criteria."""
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

    print(f"  Filtering {len(prs)} PRs...")

    for i, pr in enumerate(prs, 1):
        if i % 10 == 0:
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

        # Stop early if we have enough
        if stats['passed'] >= 40:
            print(f"    Reached target of 40 filtered PRs!")
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


def save_results(repo_name: str, filtered_prs: List[Dict]) -> Path:
    """Save filtered PRs to JSON file."""
    output_dir = Path("/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/logs/prs") / repo_name
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "filtered_prs.json"

    with open(output_file, 'w') as f:
        json.dump(filtered_prs, f, indent=2)

    print(f"  Saved to: {output_file}")
    return output_file


def main():
    print("=" * 80)
    print("PR Collection and Filtering for PR Mirroring")
    print("=" * 80)
    print(f"Target: 40+ filtered PRs per repo")
    print(f"Max changes: {MAX_CHANGES}")
    print(f"Max code files: {MAX_CODE_FILES}")
    print("=" * 80)
    print()

    all_results = {}

    for repo_config in REPOS:
        owner = repo_config['owner']
        repo = repo_config['repo']
        name = repo_config['name']

        print(f"\n{'='*80}")
        print(f"Processing: {owner}/{repo}")
        print(f"{'='*80}")

        # Step 1: Fetch PRs
        prs = fetch_prs(owner, repo, max_prs=PRS_TO_FETCH)

        if not prs:
            print(f"  No PRs found for {owner}/{repo}")
            continue

        # Step 2: Filter PRs
        filtered_prs = filter_prs(owner, repo, prs)

        # Step 3: Save results
        output_file = save_results(name, filtered_prs)

        all_results[name] = {
            "repo": f"{owner}/{repo}",
            "total_prs": len(prs),
            "filtered_prs": len(filtered_prs),
            "output_file": str(output_file)
        }

        print()

    # Final summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)

    total_collected = 0
    total_filtered = 0

    for name, results in all_results.items():
        print(f"\n{name}:")
        print(f"  Repository: {results['repo']}")
        print(f"  PRs collected: {results['total_prs']}")
        print(f"  PRs after filtering: {results['filtered_prs']}")
        print(f"  Output file: {results['output_file']}")

        total_collected += results['total_prs']
        total_filtered += results['filtered_prs']

    print(f"\n{'='*80}")
    print(f"Total PRs collected: {total_collected}")
    print(f"Total PRs after filtering: {total_filtered}")
    print(f"{'='*80}")

    if total_filtered < 80:
        print(f"\nWARNING: Only {total_filtered} filtered PRs found (target: 80+)")
        print("Consider increasing PRS_TO_FETCH or relaxing filter criteria")


if __name__ == "__main__":
    main()
