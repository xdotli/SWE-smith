#!/usr/bin/env python3
"""
Collect and filter merged PRs from nocodb/nocodb repository.

Enhanced version with rate limit handling.
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

# Target repository
OWNER = "nocodb"
REPO = "nocodb"

# Configuration
TOTAL_PRS_TO_FETCH = 500
DIFF_SIZE_LIMIT = 500
MAX_CODE_FILES = 5
RATE_LIMIT_SLEEP = 60  # Sleep 60 seconds when rate limited


def check_rate_limit():
    """Check GitHub API rate limit."""
    response = requests.get("https://api.github.com/rate_limit", headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        remaining = data['rate']['remaining']
        reset_time = data['rate']['reset']
        return remaining, reset_time
    return None, None


def wait_for_rate_limit_reset():
    """Wait for rate limit to reset."""
    remaining, reset_time = check_rate_limit()
    if remaining is not None and remaining < 10:
        import datetime
        reset_datetime = datetime.datetime.fromtimestamp(reset_time)
        wait_seconds = (reset_datetime - datetime.datetime.now()).total_seconds() + 10
        if wait_seconds > 0:
            print(f"  Rate limit nearly exhausted ({remaining} remaining). Waiting {wait_seconds:.0f}s...")
            time.sleep(wait_seconds)
            return True
    return False


def is_good_pr_candidate(pr: Dict, files: List[Dict]) -> tuple[bool, Optional[str]]:
    """Determine if a PR is a good candidate for PR Mirroring."""
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

    # Skip merge commits
    commit_message = pr.get('title', '').lower()
    if 'merge' in commit_message or 'merged' in commit_message:
        return False, "merge_commit"

    return True, None


def fetch_prs(per_page: int = 100) -> List[Dict]:
    """Fetch merged PRs from GitHub API with pagination."""
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls"
    all_prs = []
    page = 1

    print(f"\n[{OWNER}/{REPO}] Fetching merged PRs...")

    while len(all_prs) < TOTAL_PRS_TO_FETCH:
        params = {
            "state": "closed",
            "sort": "updated",
            "direction": "desc",
            "per_page": per_page,
            "page": page
        }

        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code == 403:
            print(f"  Rate limit hit at page {page}. Waiting...")
            wait_for_rate_limit_reset()
            continue

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
        time.sleep(0.5)

        if len(prs) < per_page:
            break

    print(f"  Total merged PRs collected: {len(all_prs)}")
    return all_prs[:TOTAL_PRS_TO_FETCH]


def get_pr_files(pr_number: int, retry_count: int = 0) -> List[Dict]:
    """Fetch the list of files changed in a PR with retry logic."""
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls/{pr_number}/files"

    response = requests.get(url, headers=HEADERS)

    if response.status_code == 403:
        if retry_count < 3:
            print(f"    Rate limit hit for PR #{pr_number}. Waiting and retrying...")
            wait_for_rate_limit_reset()
            return get_pr_files(pr_number, retry_count + 1)
        else:
            print(f"    Max retries reached for PR #{pr_number}")
            return []

    if response.status_code != 200:
        print(f"    ERROR fetching files for PR #{pr_number}: {response.status_code}")
        return []

    return response.json()


def process_repo() -> Dict:
    """Process the repository and collect filtered PRs."""
    print(f"\n{'='*80}")
    print(f"Processing: {OWNER}/{REPO}")
    print(f"{'='*80}")

    # Check initial rate limit
    remaining, _ = check_rate_limit()
    if remaining is not None:
        print(f"Initial rate limit remaining: {remaining}")

    # Create output directory
    output_dir = Path(f"logs/prs/{REPO}")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch PRs
    prs = fetch_prs()

    if not prs:
        print(f"  No PRs found for {OWNER}/{REPO}")
        return {"owner": OWNER, "repo": REPO, "total_prs": 0, "filtered_prs": 0}

    # Filter PRs
    filtered_prs = []
    rejection_reasons = {}

    print(f"\n[{OWNER}/{REPO}] Filtering PRs...")

    for i, pr in enumerate(prs, 1):
        pr_number = pr['number']

        # Fetch PR files
        files = get_pr_files(pr_number)

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
            remaining, _ = check_rate_limit()
            if remaining is not None and remaining < 50:
                print(f"  Rate limit remaining: {remaining}")

        time.sleep(0.4)  # Slightly longer delay

    # Save filtered PRs
    output_file = output_dir / "filtered_prs.json"
    with open(output_file, 'w') as f:
        json.dump(filtered_prs, f, indent=2)

    # Print summary
    print(f"\n[{OWNER}/{REPO}] SUMMARY")
    print(f"  Total PRs collected: {len(prs)}")
    print(f"  Filtered PRs (passed): {len(filtered_prs)}")
    print(f"  Rejection reasons:")
    for reason, count in sorted(rejection_reasons.items(), key=lambda x: x[1], reverse=True):
        print(f"    - {reason}: {count}")
    print(f"  Output saved to: {output_file}")

    return {
        "owner": OWNER,
        "repo": REPO,
        "total_prs": len(prs),
        "filtered_prs": len(filtered_prs),
        "rejection_reasons": rejection_reasons,
        "output_file": str(output_file)
    }


def main():
    """Main entry point."""
    print("="*80)
    print("NocoDB PR Collection Script")
    print("="*80)
    print(f"Repository: {OWNER}/{REPO}")
    print(f"PRs to fetch: {TOTAL_PRS_TO_FETCH}")
    print(f"Diff size limit: {DIFF_SIZE_LIMIT} changes")
    print(f"Max code files: {MAX_CODE_FILES}")

    result = process_repo()

    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    print(f"PRs collected: {result['total_prs']}")
    print(f"PRs after filtering: {result['filtered_prs']}")
    if result['total_prs'] > 0:
        print(f"Conversion rate: {result['filtered_prs']/result['total_prs']*100:.1f}%")
    print(f"Output: {result['output_file']}")

    if result['filtered_prs'] >= 20:
        print(f"\nâ SUCCESS: Collected {result['filtered_prs']} filtered PRs (target: 20+)")
    else:
        print(f"\nâ WARNING: Only collected {result['filtered_prs']} filtered PRs (target: 20+)")


if __name__ == "__main__":
    main()
