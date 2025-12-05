#!/usr/bin/env python3
"""
Collect and filter merged PRs from GitHub repositories for PR Mirroring.

Targets repos with high-quality test coverage for fail-to-pass generation.
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not found in .env file")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Target repositories
REPOS = [
    {"owner": "hoppscotch", "repo": "hoppscotch"},
    {"owner": "nocodb", "repo": "nocodb"}
]

# Configuration
TOTAL_PRS_TO_FETCH = 500  # Fetch more to ensure we get 20+ after filtering
DIFF_SIZE_LIMIT = 500  # ~5KB, additions + deletions
MAX_CODE_FILES = 5  # Focused changes only


def is_good_pr_candidate(pr: Dict, files: List[Dict]) -> tuple[bool, Optional[str]]:
    """
    Determine if a PR is a good candidate for PR Mirroring.

    Returns:
        (is_valid, reason_for_rejection)
    """
    # Check for real test files (not snapshots)
    test_files = [f for f in files if
        (f['filename'].endswith(('.test.ts', '.test.tsx', '.spec.ts', '.spec.tsx'))
        and '.snap' not in f['filename']
        and 'node_modules' not in f['filename'])]

    # Check for code files
    code_files = [f for f in files if
        f['filename'].endswith(('.ts', '.tsx'))
        and '.test.' not in f['filename']
        and '.spec.' not in f['filename']
        and '.snap' not in f['filename']
        and 'node_modules' not in f['filename']]

    # Must have both test and code files
    if not test_files:
        return False, "no_test_files"
    if not code_files:
        return False, "no_code_files"

    # Calculate diff size (additions + deletions)
    total_changes = sum(f.get('additions', 0) + f.get('deletions', 0) for f in files)
    if total_changes > DIFF_SIZE_LIMIT:
        return False, f"diff_too_large_{total_changes}"

    # Focused changes (not too many files)
    if len(code_files) > MAX_CODE_FILES:
        return False, f"too_many_files_{len(code_files)}"

    # Skip merge commits (usually have many files)
    commit_message = pr.get('title', '').lower()
    if 'merge' in commit_message or 'merged' in commit_message:
        return False, "merge_commit"

    return True, None


def fetch_prs(owner: str, repo: str, per_page: int = 100) -> List[Dict]:
    """Fetch merged PRs from GitHub API with pagination."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    all_prs = []
    page = 1

    print(f"\n[{owner}/{repo}] Fetching merged PRs...")

    while len(all_prs) < TOTAL_PRS_TO_FETCH:
        params = {
            "state": "closed",
            "sort": "updated",
            "direction": "desc",
            "per_page": per_page,
            "page": page
        }

        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code != 200:
            print(f"  ERROR: {response.status_code} - {response.text[:200]}")
            break

        prs = response.json()
        if not prs:
            break

        # Filter for merged PRs only
        merged_prs = [pr for pr in prs if pr.get('merged_at')]
        all_prs.extend(merged_prs)

        print(f"  Page {page}: {len(merged_prs)} merged PRs (total: {len(all_prs)})")

        page += 1
        time.sleep(0.5)  # Rate limiting

        if len(prs) < per_page:
            break

    print(f"  Total merged PRs collected: {len(all_prs)}")
    return all_prs[:TOTAL_PRS_TO_FETCH]


def get_pr_files(owner: str, repo: str, pr_number: int) -> List[Dict]:
    """Fetch the list of files changed in a PR."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"

    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        print(f"    ERROR fetching files for PR #{pr_number}: {response.status_code}")
        return []

    return response.json()


def process_repo(owner: str, repo: str) -> Dict:
    """Process a single repository and collect filtered PRs."""
    print(f"\n{'='*80}")
    print(f"Processing: {owner}/{repo}")
    print(f"{'='*80}")

    # Create output directory
    output_dir = Path(f"logs/prs/{repo}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch PRs
    prs = fetch_prs(owner, repo)

    if not prs:
        print(f"  No PRs found for {owner}/{repo}")
        return {"owner": owner, "repo": repo, "total_prs": 0, "filtered_prs": 0}

    # Filter PRs
    filtered_prs = []
    rejection_reasons = {}

    print(f"\n[{owner}/{repo}] Filtering PRs...")

    for i, pr in enumerate(prs, 1):
        pr_number = pr['number']

        # Fetch PR files
        files = get_pr_files(owner, repo, pr_number)

        if not files:
            rejection_reasons['no_files'] = rejection_reasons.get('no_files', 0) + 1
            continue

        # Check if PR is a good candidate
        is_valid, reason = is_good_pr_candidate(pr, files)

        if is_valid:
            # Extract relevant info
            test_files = [f['filename'] for f in files if
                f['filename'].endswith(('.test.ts', '.test.tsx', '.spec.ts', '.spec.tsx'))
                and '.snap' not in f['filename']]

            code_files = [f['filename'] for f in files if
                f['filename'].endswith(('.ts', '.tsx'))
                and '.test.' not in f['filename']
                and '.spec.' not in f['filename']
                and '.snap' not in f['filename']
                and 'node_modules' not in f['filename']]

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
            print(f"  â PR #{pr_number}: {pr['title'][:60]} ({total_changes} changes)")
        else:
            rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

        # Progress update every 10 PRs
        if i % 10 == 0:
            print(f"  Processed {i}/{len(prs)} PRs, {len(filtered_prs)} passed filters")

        time.sleep(0.3)  # Rate limiting

    # Save filtered PRs
    output_file = output_dir / "filtered_prs.json"
    with open(output_file, 'w') as f:
        json.dump(filtered_prs, f, indent=2)

    # Print summary
    print(f"\n[{owner}/{repo}] SUMMARY")
    print(f"  Total PRs collected: {len(prs)}")
    print(f"  Filtered PRs (passed): {len(filtered_prs)}")
    print(f"  Rejection reasons:")
    for reason, count in sorted(rejection_reasons.items(), key=lambda x: x[1], reverse=True):
        print(f"    - {reason}: {count}")
    print(f"  Output saved to: {output_file}")

    return {
        "owner": owner,
        "repo": repo,
        "total_prs": len(prs),
        "filtered_prs": len(filtered_prs),
        "rejection_reasons": rejection_reasons,
        "output_file": str(output_file)
    }


def main():
    """Main entry point."""
    print("="*80)
    print("PR Collection Script for PR Mirroring")
    print("="*80)
    print(f"Target repositories: {len(REPOS)}")
    print(f"PRs to fetch per repo: {TOTAL_PRS_TO_FETCH}")
    print(f"Diff size limit: {DIFF_SIZE_LIMIT} changes")
    print(f"Max code files: {MAX_CODE_FILES}")

    results = []

    for repo_info in REPOS:
        result = process_repo(repo_info['owner'], repo_info['repo'])
        results.append(result)
        time.sleep(2)  # Rate limiting between repos

    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)

    total_collected = sum(r['total_prs'] for r in results)
    total_filtered = sum(r['filtered_prs'] for r in results)

    print(f"Total PRs collected: {total_collected}")
    print(f"Total PRs after filtering: {total_filtered}")
    print(f"Conversion rate: {total_filtered/total_collected*100:.1f}%")

    print("\nPer-repo breakdown:")
    for r in results:
        print(f"  {r['owner']}/{r['repo']}: {r['filtered_prs']}/{r['total_prs']} PRs")
        print(f"    Saved to: {r['output_file']}")

    # Check if we met the target
    if total_filtered >= 40:
        print(f"\nâ SUCCESS: Collected {total_filtered} filtered PRs (target: 40+)")
    else:
        print(f"\nâ WARNING: Only collected {total_filtered} filtered PRs (target: 40+)")
        print("  Consider increasing TOTAL_PRS_TO_FETCH or adjusting filter criteria")


if __name__ == "__main__":
    main()
