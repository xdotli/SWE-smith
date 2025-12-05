#!/usr/bin/env python3
"""
Filter and collect PRs with strict criteria for fail-to-pass generation.

Criteria:
1. Must have .test.ts/.tsx/.spec.ts changes (NOT just .snap)
2. Code diff < 5KB total
3. Not a merge commit
4. Has both code and test file changes
5. At most 5 files changed
"""

import requests
import json
import os
import sys
import time
from typing import List, Dict, Any

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


def get_pr_files(owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
    """Fetch files changed in a PR."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Error fetching files for PR #{pr_number}: {e}", file=sys.stderr)
        return []


def is_good_pr_candidate(files: List[Dict[str, Any]]) -> tuple[bool, str]:
    """
    Check if PR meets criteria for fail-to-pass generation.
    Returns (is_good, reason).

    RELAXED CRITERIA per Megathink directive:
    - Allow e2e tests (treat as unit tests)
    - Allow larger repos (up to 10 files, 1000 changes)
    - Focus on having SOME test file changes
    """
    if not files:
        return False, "no_files"

    # Extract file info - RELAXED: include e2e tests, any test pattern
    test_files = [
        f for f in files
        if any(pattern in f["filename"].lower() for pattern in [
            ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx",
            "test/", "tests/", "__tests__/", "e2e/"
        ])
    ]

    code_files = [
        f for f in files
        if f["filename"].endswith((".ts", ".tsx", ".js", ".jsx"))
        and not any(ext in f["filename"] for ext in [".snap"])
        and f not in test_files  # Exclude test files from code files
    ]

    # Must have actual test files (not ONLY snapshots)
    has_real_tests = any(
        ".snap" not in f["filename"]
        for f in test_files
    )
    if not has_real_tests:
        return False, "no_real_tests"

    # Must have test changes (code files are optional - test-only PRs are OK)
    if not test_files:
        return False, "no_test_files"

    # RELAXED: Allow up to 10 files
    if len(files) > 10:
        return False, "too_many_files"

    # RELAXED: Allow up to 1000 changes (~10KB)
    total_changes = sum(f.get("changes", 0) for f in files)
    if total_changes > 1000:
        return False, "too_large"

    return True, "pass"


def filter_existing_prs(input_file: str, output_file: str, owner: str, repo: str):
    """Filter PRs from existing JSONL file."""
    print(f"\nFiltering PRs from {input_file}")
    print(f"Owner: {owner}, Repo: {repo}")

    filtered_prs = []
    stats = {
        "total": 0,
        "merged": 0,
        "no_files": 0,
        "no_real_tests": 0,
        "no_code_files": 0,
        "no_test_files": 0,
        "too_many_files": 0,
        "too_large": 0,
        "pass": 0
    }

    with open(input_file, 'r') as f:
        for line in f:
            pr_data = json.loads(line.strip())
            stats["total"] += 1

            # Skip unmerged PRs
            if not pr_data.get("merged_at"):
                continue

            stats["merged"] += 1
            pr_number = pr_data["number"]

            # Fetch files for this PR
            print(f"Checking PR #{pr_number}...", end=" ")
            files = get_pr_files(owner, repo, pr_number)

            # Check criteria
            is_good, reason = is_good_pr_candidate(files)
            stats[reason] += 1

            if is_good:
                # Extract file details
                test_files = [
                    f["filename"] for f in files
                    if any(ext in f["filename"] for ext in [".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"])
                ]
                code_files = [
                    f["filename"] for f in files
                    if f["filename"].endswith((".ts", ".tsx", ".js", ".jsx"))
                    and not any(ext in f["filename"] for ext in [".test.", ".spec.", ".snap"])
                ]
                total_changes = sum(f.get("changes", 0) for f in files)

                filtered_pr = {
                    "number": pr_number,
                    "title": pr_data.get("title", ""),
                    "base_commit": pr_data["base"]["sha"],
                    "head_commit": pr_data["head"]["sha"],
                    "merged_at": pr_data["merged_at"],
                    "files": [f["filename"] for f in files],
                    "test_files": test_files,
                    "code_files": code_files,
                    "total_changes": total_changes,
                    "html_url": pr_data["html_url"]
                }
                filtered_prs.append(filtered_pr)
                print(f"✓ PASS ({total_changes} changes, {len(files)} files)")
            else:
                print(f"✗ SKIP ({reason})")

            # Rate limiting: sleep between requests
            time.sleep(0.5)

    # Save filtered PRs
    with open(output_file, 'w') as f:
        for pr in filtered_prs:
            f.write(json.dumps(pr) + "\n")

    # Print stats
    print(f"\n{'='*60}")
    print(f"FILTERING STATS for {owner}/{repo}")
    print(f"{'='*60}")
    print(f"Total PRs in file:     {stats['total']}")
    print(f"Merged PRs:            {stats['merged']}")
    print(f"Filtered out:")
    print(f"  - No files:          {stats['no_files']}")
    print(f"  - No real tests:     {stats['no_real_tests']}")
    print(f"  - No code files:     {stats['no_code_files']}")
    print(f"  - No test files:     {stats['no_test_files']}")
    print(f"  - Too many files:    {stats['too_many_files']}")
    print(f"  - Too large:         {stats['too_large']}")
    print(f"PASSED:                {stats['pass']}")
    print(f"{'='*60}")
    print(f"Saved to: {output_file}\n")

    return filtered_prs


def collect_new_prs(owner: str, repo: str, output_file: str, max_prs: int = 50):
    """Collect new PRs directly from GitHub API with filtering."""
    print(f"\nCollecting PRs from {owner}/{repo}")

    filtered_prs = []
    stats = {
        "total_checked": 0,
        "merged": 0,
        "no_files": 0,
        "no_real_tests": 0,
        "no_code_files": 0,
        "no_test_files": 0,
        "too_many_files": 0,
        "too_large": 0,
        "pass": 0
    }

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    params = {
        "state": "closed",
        "per_page": 100,
        "sort": "updated",
        "direction": "desc"
    }

    page = 1
    while len(filtered_prs) < max_prs and page <= 5:  # Check up to 500 PRs
        print(f"\nFetching page {page}...")
        params["page"] = page

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            prs = resp.json()

            if not prs:
                break

            for pr in prs:
                stats["total_checked"] += 1

                # Skip unmerged PRs
                if not pr.get("merged_at"):
                    continue

                stats["merged"] += 1
                pr_number = pr["number"]

                # Fetch files
                print(f"Checking PR #{pr_number}...", end=" ")
                files = get_pr_files(owner, repo, pr_number)

                # Check criteria
                is_good, reason = is_good_pr_candidate(files)
                stats[reason] += 1

                if is_good:
                    test_files = [
                        f["filename"] for f in files
                        if any(ext in f["filename"] for ext in [".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"])
                    ]
                    code_files = [
                        f["filename"] for f in files
                        if f["filename"].endswith((".ts", ".tsx", ".js", ".jsx"))
                        and not any(ext in f["filename"] for ext in [".test.", ".spec.", ".snap"])
                    ]
                    total_changes = sum(f.get("changes", 0) for f in files)

                    filtered_pr = {
                        "number": pr_number,
                        "title": pr.get("title", ""),
                        "base_commit": pr["base"]["sha"],
                        "head_commit": pr["head"]["sha"],
                        "merged_at": pr["merged_at"],
                        "files": [f["filename"] for f in files],
                        "test_files": test_files,
                        "code_files": code_files,
                        "total_changes": total_changes,
                        "html_url": pr["html_url"]
                    }
                    filtered_prs.append(filtered_pr)
                    print(f"✓ PASS ({total_changes} changes, {len(files)} files)")

                    if len(filtered_prs) >= max_prs:
                        break
                else:
                    print(f"✗ SKIP ({reason})")

                time.sleep(0.5)

            page += 1

        except Exception as e:
            print(f"Error fetching page {page}: {e}", file=sys.stderr)
            break

    # Save filtered PRs
    with open(output_file, 'w') as f:
        for pr in filtered_prs:
            f.write(json.dumps(pr) + "\n")

    # Print stats
    print(f"\n{'='*60}")
    print(f"COLLECTION STATS for {owner}/{repo}")
    print(f"{'='*60}")
    print(f"Total PRs checked:     {stats['total_checked']}")
    print(f"Merged PRs:            {stats['merged']}")
    print(f"Filtered out:")
    print(f"  - No files:          {stats['no_files']}")
    print(f"  - No real tests:     {stats['no_real_tests']}")
    print(f"  - No code files:     {stats['no_code_files']}")
    print(f"  - No test files:     {stats['no_test_files']}")
    print(f"  - Too many files:    {stats['too_many_files']}")
    print(f"  - Too large:         {stats['too_large']}")
    print(f"PASSED:                {stats['pass']}")
    print(f"{'='*60}")
    print(f"Saved to: {output_file}\n")

    return filtered_prs


if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("WARNING: GITHUB_TOKEN not set. Rate limits will be strict.", file=sys.stderr)

    # Filter existing strapi PRs
    strapi_input = "logs/prs/strapi-prs.jsonl"
    strapi_output = "logs/prs/strapi-filtered.jsonl"

    if os.path.exists(strapi_input):
        filter_existing_prs(strapi_input, strapi_output, "strapi", "strapi")

    # Collect new appsmith PRs
    appsmith_output = "logs/prs/appsmith-filtered.jsonl"
    collect_new_prs("appsmithorg", "appsmith", appsmith_output, max_prs=25)
