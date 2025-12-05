#!/usr/bin/env python3
"""
Collect and filter PRs from multiple GitHub repositories for PR Mirroring.
Applies strict filtering to ensure high-quality fail-to-pass candidates.
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import requests
from datetime import datetime

# Read GitHub token from .env
def load_github_token():
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        print(f"ERROR: .env file not found at {env_path}")
        sys.exit(1)

    with open(env_path) as f:
        for line in f:
            if line.startswith("GITHUB_TOKEN="):
                token = line.strip().split("=", 1)[1]
                return token

    print("ERROR: GITHUB_TOKEN not found in .env")
    sys.exit(1)

GITHUB_TOKEN = load_github_token()
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def is_good_pr_candidate(pr: Dict[str, Any], files: List[Dict[str, Any]]) -> tuple[bool, str]:
    """
    Strict filtering for PR candidates.
    Returns (is_good, reason) tuple.
    """
    # Check for real test files (not snapshots)
    test_files = [f for f in files if
        (f['filename'].endswith(('.test.ts', '.test.tsx', '.spec.ts', '.spec.tsx'))
        and '.snap' not in f['filename'])]

    # Check for code files
    code_files = [f for f in files if
        f['filename'].endswith(('.ts', '.tsx', '.js', '.jsx'))
        and '.test.' not in f['filename']
        and '.spec.' not in f['filename']
        and '.snap' not in f['filename']
        and 'node_modules' not in f['filename']
        and '__tests__' not in f['filename']]

    # Must have both test files and code files
    if not test_files:
        return False, "No real test files (only snapshots or no tests)"

    if not code_files:
        return False, "No code files modified"

    # Calculate diff size (additions + deletions)
    total_changes = sum(f.get('additions', 0) + f.get('deletions', 0) for f in files)
    if total_changes > 500:  # ~5KB assuming 10 chars per line
        return False, f"Diff too large ({total_changes} changes)"

    # Focused changes (not too many files)
    if len(code_files) > 10:
        return False, f"Too many code files ({len(code_files)})"

    # Check if it's a merge commit (heuristic: multiple parents or title contains "merge")
    if pr.get('title', '').lower().startswith('merge'):
        return False, "Likely a merge commit"

    return True, "PASS"

def fetch_prs(owner: str, repo: str, max_prs: int = 300) -> List[Dict[str, Any]]:
    """
    Fetch merged PRs from GitHub API with pagination.
    """
    print(f"\n{'='*80}")
    print(f"Fetching PRs from {owner}/{repo}...")
    print(f"{'='*80}")

    all_prs = []
    page = 1
    per_page = 100

    while len(all_prs) < max_prs:
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        params = {
            "state": "closed",
            "sort": "updated",
            "direction": "desc",
            "per_page": per_page,
            "page": page
        }

        print(f"  Fetching page {page} (up to {per_page} PRs)...", end=" ")
        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code != 200:
            print(f"\n  ERROR: GitHub API returned {response.status_code}")
            print(f"  {response.text}")
            break

        prs = response.json()
        if not prs:
            print("No more PRs")
            break

        # Filter for merged PRs only
        merged_prs = [pr for pr in prs if pr.get('merged_at') is not None]
        all_prs.extend(merged_prs)
        print(f"Got {len(merged_prs)} merged PRs (total: {len(all_prs)})")

        if len(prs) < per_page:
            # Last page
            break

        page += 1

    print(f"\n  Total merged PRs collected: {len(all_prs)}")
    return all_prs

def filter_prs(owner: str, repo: str, prs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter PRs based on strict criteria.
    """
    print(f"\n{'='*80}")
    print(f"Filtering PRs for {owner}/{repo}...")
    print(f"{'='*80}")

    filtered_prs = []
    stats = {
        "no_test_files": 0,
        "no_code_files": 0,
        "diff_too_large": 0,
        "too_many_files": 0,
        "merge_commit": 0,
        "api_error": 0,
        "passed": 0
    }

    for i, pr in enumerate(prs):
        pr_number = pr['number']

        # Fetch files for this PR
        files_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        print(f"\r  Checking PR #{pr_number} ({i+1}/{len(prs)})...", end="")

        response = requests.get(files_url, headers=HEADERS)
        if response.status_code != 200:
            print(f"\n  WARNING: Failed to fetch files for PR #{pr_number}")
            stats["api_error"] += 1
            continue

        files = response.json()

        # Apply filters
        is_good, reason = is_good_pr_candidate(pr, files)

        if not is_good:
            # Update stats
            if "snapshot" in reason.lower() or "no test" in reason.lower():
                stats["no_test_files"] += 1
            elif "no code" in reason.lower():
                stats["no_code_files"] += 1
            elif "too large" in reason.lower():
                stats["diff_too_large"] += 1
            elif "too many" in reason.lower():
                stats["too_many_files"] += 1
            elif "merge" in reason.lower():
                stats["merge_commit"] += 1
            continue

        # Extract relevant data
        test_files = [f['filename'] for f in files if
            (f['filename'].endswith(('.test.ts', '.test.tsx', '.spec.ts', '.spec.tsx'))
            and '.snap' not in f['filename'])]

        code_files = [f['filename'] for f in files if
            f['filename'].endswith(('.ts', '.tsx', '.js', '.jsx'))
            and '.test.' not in f['filename']
            and '.spec.' not in f['filename']
            and '.snap' not in f['filename']
            and 'node_modules' not in f['filename']
            and '__tests__' not in f['filename']]

        total_changes = sum(f.get('additions', 0) + f.get('deletions', 0) for f in files)

        filtered_pr = {
            "number": pr_number,
            "title": pr['title'],
            "merged_at": pr['merged_at'],
            "merge_commit_sha": pr['merge_commit_sha'],
            "base_sha": pr['base']['sha'],
            "test_files": test_files,
            "code_files": code_files,
            "total_changes": total_changes,
            "html_url": pr['html_url']
        }

        filtered_prs.append(filtered_pr)
        stats["passed"] += 1

    print(f"\n\n  Filtering Results:")
    print(f"  {'â'*40}")
    print(f"  Total PRs checked:        {len(prs)}")
    print(f"  PASSED all filters:       {stats['passed']}")
    print(f"  â No test files:          {stats['no_test_files']}")
    print(f"  â No code files:          {stats['no_code_files']}")
    print(f"  â Diff too large:         {stats['diff_too_large']}")
    print(f"  â Too many files:         {stats['too_many_files']}")
    print(f"  â Merge commits:          {stats['merge_commit']}")
    print(f"  â API errors:             {stats['api_error']}")

    return filtered_prs

def save_prs(owner: str, repo: str, prs: List[Dict[str, Any]]):
    """
    Save filtered PRs to JSON file.
    """
    # Create directory structure
    output_dir = Path(__file__).parent / "logs" / "prs" / repo
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "filtered_prs.json"

    with open(output_file, 'w') as f:
        json.dump(prs, f, indent=2)

    print(f"\n  Saved {len(prs)} PRs to: {output_file}")
    return output_file

def main():
    repos = [
        {"owner": "excalidraw", "repo": "excalidraw"},
        {"owner": "tldraw", "repo": "tldraw"}
    ]

    print(f"\n{'#'*80}")
    print(f"# PR Collection Script for PR Mirroring")
    print(f"# Target: 40+ filtered PRs per repo (80+ total)")
    print(f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*80}")

    all_results = {}

    for repo_info in repos:
        owner = repo_info["owner"]
        repo = repo_info["repo"]

        # Fetch PRs
        prs = fetch_prs(owner, repo, max_prs=300)

        # Filter PRs
        filtered_prs = filter_prs(owner, repo, prs)

        # Save results
        output_file = save_prs(owner, repo, filtered_prs)

        all_results[f"{owner}/{repo}"] = {
            "total_collected": len(prs),
            "total_filtered": len(filtered_prs),
            "output_file": str(output_file)
        }

    # Print final summary
    print(f"\n{'#'*80}")
    print(f"# FINAL SUMMARY")
    print(f"{'#'*80}")

    total_collected = 0
    total_filtered = 0

    for repo_name, results in all_results.items():
        print(f"\n{repo_name}:")
        print(f"  PRs collected:    {results['total_collected']}")
        print(f"  PRs filtered:     {results['total_filtered']}")
        print(f"  Output file:      {results['output_file']}")

        total_collected += results['total_collected']
        total_filtered += results['total_filtered']

    print(f"\n{'â'*80}")
    print(f"TOTAL COLLECTED:    {total_collected}")
    print(f"TOTAL FILTERED:     {total_filtered}")
    print(f"CONVERSION RATE:    {total_filtered/total_collected*100:.1f}%")
    print(f"{'â'*80}")

    if total_filtered < 40:
        print(f"\nâ ï¸  WARNING: Only {total_filtered} PRs passed filters (target: 80+)")
        print(f"   Consider relaxing filters or collecting more PRs")
    else:
        print(f"\nâ SUCCESS: {total_filtered} PRs passed filters (target: 80+)")

if __name__ == "__main__":
    main()
