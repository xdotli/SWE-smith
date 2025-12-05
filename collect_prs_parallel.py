#!/usr/bin/env python3
"""
Collect and filter PRs from PostHog and ToolJet repositories.
Applies strict filtering to ensure high-quality fail-to-pass candidates.
"""

import os
import json
import requests
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not found in .env file")

HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

REPOS = [
    {
        'owner': 'PostHog',
        'repo': 'posthog',
        'name': 'posthog',
        'target_prs': 40
    },
    {
        'owner': 'ToolJet',
        'repo': 'ToolJet',
        'name': 'tooljet',
        'target_prs': 40
    }
]


def is_good_pr_candidate(pr: Dict[str, Any], files: List[Dict[str, Any]]) -> tuple[bool, str]:
    """
    Apply strict filtering to determine if PR is a good candidate.
    Returns (is_good, reason)
    """
    # Skip merge commits
    if pr.get('merge_commit_sha') and 'Merge' in pr.get('title', ''):
        return False, "merge_commit"

    # Check for real test files (not snapshots)
    test_files = [f for f in files if
        (f['filename'].endswith(('.test.ts', '.test.tsx', '.spec.ts', '.spec.tsx'))
        and '.snap' not in f['filename'])]

    # Check for code files
    code_files = [f for f in files if
        f['filename'].endswith(('.ts', '.tsx'))
        and '.test.' not in f['filename']
        and '.spec.' not in f['filename']
        and 'node_modules' not in f['filename']
        and '__snapshots__' not in f['filename']]

    # Must have both test and code files
    if not test_files:
        return False, "no_test_files"
    if not code_files:
        return False, "no_code_files"

    # Calculate diff size (additions + deletions)
    total_changes = sum(f.get('additions', 0) + f.get('deletions', 0) for f in files)

    # Reject if diff too large (>500 lines ~ 5KB)
    if total_changes > 500:
        return False, f"diff_too_large_{total_changes}"

    # Reject if too small (likely trivial)
    if total_changes < 10:
        return False, f"diff_too_small_{total_changes}"

    # Focused changes (not too many files)
    if len(code_files) > 5:
        return False, f"too_many_files_{len(code_files)}"

    # Check if test files have actual test additions (not just deletions)
    test_additions = sum(f.get('additions', 0) for f in test_files)
    if test_additions == 0:
        return False, "no_test_additions"

    return True, "passed"


def fetch_merged_prs(owner: str, repo: str, max_prs: int = 200) -> List[Dict[str, Any]]:
    """Fetch merged PRs using GitHub API with pagination."""
    url = f'https://api.github.com/repos/{owner}/{repo}/pulls'
    params = {
        'state': 'closed',
        'sort': 'updated',
        'direction': 'desc',
        'per_page': 100
    }

    all_prs = []
    page = 1

    print(f"Fetching PRs from {owner}/{repo}...")

    while len(all_prs) < max_prs:
        params['page'] = page
        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code != 200:
            print(f"Error fetching PRs: {response.status_code}")
            print(response.text)
            break

        prs = response.json()

        if not prs:
            print(f"No more PRs found at page {page}")
            break

        # Filter for merged PRs only
        merged_prs = [pr for pr in prs if pr.get('merged_at')]
        all_prs.extend(merged_prs)

        print(f"  Page {page}: Found {len(merged_prs)} merged PRs (total: {len(all_prs)})")

        page += 1

        if len(prs) < 100:  # Last page
            break

    return all_prs[:max_prs]


def get_pr_files(owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
    """Fetch files changed in a PR."""
    url = f'https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files'
    params = {'per_page': 100}

    all_files = []
    page = 1

    while True:
        params['page'] = page
        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code != 200:
            print(f"  Error fetching files for PR #{pr_number}: {response.status_code}")
            return []

        files = response.json()

        if not files:
            break

        all_files.extend(files)
        page += 1

        if len(files) < 100:  # Last page
            break

    return all_files


def process_repo(repo_config: Dict[str, str]) -> Dict[str, Any]:
    """Process a single repository and return results."""
    owner = repo_config['owner']
    repo = repo_config['repo']
    repo_name = repo_config['name']
    target_prs = repo_config['target_prs']

    print(f"\n{'='*60}")
    print(f"Processing {owner}/{repo}")
    print(f"{'='*60}\n")

    # Create output directory
    output_dir = Path(f'logs/prs/{repo_name}')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch merged PRs
    prs = fetch_merged_prs(owner, repo, max_prs=500)
    print(f"\nTotal merged PRs fetched: {len(prs)}")

    # Filter PRs
    filtered_prs = []
    filter_stats = {}

    for i, pr in enumerate(prs, 1):
        pr_number = pr['number']

        if i % 10 == 0:
            print(f"Processing PR {i}/{len(prs)} (filtered: {len(filtered_prs)})...")

        # Get files for this PR
        files = get_pr_files(owner, repo, pr_number)

        if not files:
            continue

        # Apply filtering
        is_good, reason = is_good_pr_candidate(pr, files)

        # Track filter reasons
        if reason not in filter_stats:
            filter_stats[reason] = 0
        filter_stats[reason] += 1

        if is_good:
            # Extract relevant data
            test_files = [f['filename'] for f in files if
                f['filename'].endswith(('.test.ts', '.test.tsx', '.spec.ts', '.spec.tsx'))
                and '.snap' not in f['filename']]

            code_files = [f['filename'] for f in files if
                f['filename'].endswith(('.ts', '.tsx'))
                and '.test.' not in f['filename']
                and '.spec.' not in f['filename']
                and 'node_modules' not in f['filename']
                and '__snapshots__' not in f['filename']]

            total_changes = sum(f.get('additions', 0) + f.get('deletions', 0) for f in files)

            filtered_pr = {
                'number': pr_number,
                'title': pr['title'],
                'merged_at': pr['merged_at'],
                'merge_commit_sha': pr['merge_commit_sha'],
                'base_sha': pr['base']['sha'],
                'head_sha': pr['head']['sha'],
                'test_files': test_files,
                'code_files': code_files,
                'total_changes': total_changes,
                'html_url': pr['html_url']
            }

            filtered_prs.append(filtered_pr)

            # Stop if we have enough
            if len(filtered_prs) >= target_prs:
                print(f"\nReached target of {target_prs} filtered PRs!")
                break

    # Save results
    output_file = output_dir / 'filtered_prs.json'
    with open(output_file, 'w') as f:
        json.dump(filtered_prs, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print(f"Summary for {owner}/{repo}")
    print(f"{'='*60}")
    print(f"Total PRs fetched: {len(prs)}")
    print(f"Filtered PRs: {len(filtered_prs)}")
    print(f"Output file: {output_file}")
    print(f"\nFilter statistics:")
    for reason, count in sorted(filter_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {reason}: {count}")

    return {
        'repo': f"{owner}/{repo}",
        'total_prs': len(prs),
        'filtered_prs': len(filtered_prs),
        'output_file': str(output_file),
        'filter_stats': filter_stats
    }


def main():
    """Main function to process all repos."""
    print("Starting PR collection for PostHog and ToolJet...")
    print(f"Using GitHub token: {GITHUB_TOKEN[:20]}...")

    results = []

    for repo_config in REPOS:
        try:
            result = process_repo(repo_config)
            results.append(result)
        except Exception as e:
            print(f"\nError processing {repo_config['owner']}/{repo_config['repo']}: {e}")
            import traceback
            traceback.print_exc()

    # Print overall summary
    print(f"\n{'='*60}")
    print("OVERALL SUMMARY")
    print(f"{'='*60}")

    total_filtered = sum(r['filtered_prs'] for r in results)

    for result in results:
        print(f"\n{result['repo']}:")
        print(f"  Total PRs: {result['total_prs']}")
        print(f"  Filtered: {result['filtered_prs']}")
        print(f"  Output: {result['output_file']}")

    print(f"\nTotal filtered PRs across all repos: {total_filtered}")

    if total_filtered < 80:
        print(f"\nWARNING: Only {total_filtered} PRs collected. Target was 80+.")
    else:
        print(f"\nSUCCESS: Collected {total_filtered} high-quality PR candidates!")


if __name__ == '__main__':
    main()
