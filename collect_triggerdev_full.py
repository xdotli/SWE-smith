#!/usr/bin/env python3
"""
Collect and filter merged PRs from triggerdotdev/trigger.dev for PR Mirroring.
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

# Configuration
OWNER = "triggerdotdev"
REPO = "trigger.dev"
TOTAL_PRS_TO_FETCH = 200
TARGET_INSTANCES = 10
DIFF_SIZE_LIMIT = 1000  # ~10KB, additions + deletions
MAX_CODE_FILES = 20


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

        print(f"  Fetching page {page}...", end=" ")
        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code == 403:
            print("\n  Rate limit exceeded. Waiting 60 seconds...")
            time.sleep(60)
            continue

        if response.status_code != 200:
            print(f"\n  Error: {response.status_code}")
            break

        prs = response.json()
        if not prs:
            print("No more PRs")
            break

        # Filter for merged PRs
        merged_prs = [pr for pr in prs if pr.get('merged_at')]
        all_prs.extend(merged_prs)
        print(f"{len(merged_prs)} merged PRs (total: {len(all_prs)})")

        page += 1
        time.sleep(0.5)  # Rate limiting

    print(f"  Total fetched: {len(all_prs)} merged PRs")
    return all_prs[:TOTAL_PRS_TO_FETCH]


def fetch_pr_files(pr_number: int) -> List[Dict]:
    """Fetch files changed in a PR."""
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls/{pr_number}/files"

    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"    Error fetching files for PR #{pr_number}: {response.status_code}")
        return []

    return response.json()


def filter_prs(prs: List[Dict]) -> List[Dict]:
    """Filter PRs to find good candidates for PR Mirroring."""
    print(f"\nFiltering {len(prs)} PRs for good candidates...")

    good_prs = []
    rejection_stats = {}

    for i, pr in enumerate(prs, 1):
        if len(good_prs) >= TARGET_INSTANCES:
            break

        pr_number = pr['number']
        print(f"  [{i}/{len(prs)}] PR #{pr_number}: {pr['title'][:50]}...", end=" ")

        # Fetch files
        files = fetch_pr_files(pr_number)
        if not files:
            print("⨯ (no files)")
            rejection_stats["no_files"] = rejection_stats.get("no_files", 0) + 1
            continue

        # Check if it's a good candidate
        is_valid, reason = is_good_pr_candidate(pr, files)

        if is_valid:
            test_files = [f['filename'] for f in files if '.test.' in f['filename']]
            code_files = [f['filename'] for f in files if f['filename'].endswith(('.ts', '.tsx')) and '.test.' not in f['filename']]
            total_changes = sum(f.get('additions', 0) + f.get('deletions', 0) for f in files)

            print(f"✓ ({len(test_files)} tests, {len(code_files)} code, {total_changes} changes)")

            good_prs.append({
                'instance_id': f"{OWNER}__{REPO}.pr_mirror.{pr_number}",
                'repo': f"{OWNER}/{REPO}",
                'base_commit': pr['base']['sha'],
                'head_commit': pr['head']['sha'],
                'title': pr['title'],
                'merged_at': pr['merged_at'],
                'html_url': pr['html_url'],
                'test_files': test_files,
                'code_files': code_files,
                'total_changes': total_changes,
                'num_files': len(files),
                'pull_number': pr_number
            })
        else:
            print(f"⨯ ({reason})")
            rejection_stats[reason] = rejection_stats.get(reason, 0) + 1

        time.sleep(0.3)  # Rate limiting

    print(f"\nFiltering complete:")
    print(f"  Good candidates: {len(good_prs)}")
    print(f"  Rejection reasons:")
    for reason, count in sorted(rejection_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"    {reason}: {count}")

    return good_prs


def save_instances(instances: List[Dict]):
    """Save instances to JSONL file."""
    output_dir = Path("logs/tasks")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "triggerdev-insts.jsonl"

    with open(output_file, 'w') as f:
        for inst in instances:
            f.write(json.dumps(inst) + '\n')

    print(f"\n✓ Saved {len(instances)} instances to {output_file}")

    # Print summary
    print("\n" + "="*70)
    print("COLLECTION SUMMARY")
    print("="*70)
    print(f"Repository: {OWNER}/{REPO}")
    print(f"Instances collected: {len(instances)}")
    print(f"Output file: {output_file}")

    print("\nTop instances:")
    for i, inst in enumerate(instances[:5], 1):
        print(f"  {i}. PR #{inst['pull_number']}: {inst['title'][:60]}")
        print(f"     Tests: {len(inst['test_files'])}, Code files: {len(inst['code_files'])}, Changes: {inst['total_changes']}")

    print("\nNext steps:")
    print(f"1. Run: python -m swesmith.bug_gen.mirror.generate_ts {output_file} --model anthropic/claude-opus-4-5-20251101")
    print(f"2. Validate: python -m swesmith.harness.valid logs/task_insts/triggerdev_patches.json -w 1")


def main():
    print("="*70)
    print(f"PR Collection for {OWNER}/{REPO}")
    print("="*70)

    # Fetch PRs
    prs = fetch_prs()

    if not prs:
        print("No PRs found!")
        return

    # Filter PRs
    good_prs = filter_prs(prs)

    if not good_prs:
        print("\nNo good PR candidates found!")
        return

    # Save instances
    save_instances(good_prs)


if __name__ == "__main__":
    main()
