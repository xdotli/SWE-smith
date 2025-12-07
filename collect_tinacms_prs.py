#!/usr/bin/env python3
"""
Collect PRs from tinacms/tinacms repository for PR Mirroring.

Filters:
- PR must be merged
- Must modify .test.ts or .test.tsx files (NOT just .snap files)
- Code diff should be reasonable size (< 10KB per file)
- Must have both code and test file changes
"""

import os
import json
import requests
from pathlib import Path

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
OWNER = "tinacms"
REPO = "tinacms"
TARGET_PR_COUNT = 50  # Collect up to 50 PRs

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def get_merged_prs(limit=100):
    """Get merged PRs from the repository."""
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls"
    params = {
        "state": "closed",
        "sort": "updated",
        "direction": "desc",
        "per_page": limit,
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    prs = response.json()
    # Filter for merged PRs only
    merged_prs = [pr for pr in prs if pr.get("merged_at")]

    print(f"Found {len(merged_prs)} merged PRs")
    return merged_prs


def get_pr_files(pr_number):
    """Get files changed in a PR."""
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls/{pr_number}/files"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def is_test_file(filename):
    """Check if filename is a real test file (not snapshot)."""
    return (
        filename.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
        and ".snap" not in filename
    )


def is_good_pr(pr):
    """Check if PR is suitable for PR Mirroring."""
    pr_number = pr["number"]
    print(f"Checking PR #{pr_number}...")

    try:
        files = get_pr_files(pr_number)
    except Exception as e:
        print(f"  ❌ Failed to get files: {e}")
        return False, None

    # Separate test and code files
    test_files = [f for f in files if is_test_file(f["filename"])]
    code_files = [f for f in files if not is_test_file(f["filename"]) and f["filename"].endswith((".ts", ".tsx", ".js", ".jsx"))]

    # Must have at least one real test file
    if not test_files:
        print(f"  ❌ No real test files (only {len([f for f in files if '.snap' in f['filename']])} snapshot files)")
        return False, None

    # Must have code changes
    if not code_files:
        print(f"  ❌ No code file changes")
        return False, None

    # Check file sizes (skip if too large)
    large_files = [f for f in files if f.get("changes", 0) > 500]
    if len(large_files) > 3:
        print(f"  ❌ Too many large files ({len(large_files)} files with >500 lines changed)")
        return False, None

    # Check total files (skip massive refactors)
    if len(files) > 20:
        print(f"  ❌ Too many files changed ({len(files)} files)")
        return False, None

    print(f"  ✅ Good PR: {len(test_files)} test files, {len(code_files)} code files, {len(files)} total files")

    return True, {
        "number": pr_number,
        "title": pr["title"],
        "merged_at": pr["merged_at"],
        "test_files": [f["filename"] for f in test_files],
        "code_files": [f["filename"] for f in code_files],
        "total_files": len(files),
        "additions": sum(f.get("additions", 0) for f in files),
        "deletions": sum(f.get("deletions", 0) for f in files),
    }


def main():
    # Get merged PRs
    prs = get_merged_prs(limit=150)

    # Filter for good PRs
    good_prs = []
    for pr in prs:
        is_good, pr_data = is_good_pr(pr)
        if is_good:
            good_prs.append(pr_data)
            if len(good_prs) >= TARGET_PR_COUNT:
                break

    print(f"\n{'='*60}")
    print(f"Collected {len(good_prs)} suitable PRs for PR Mirroring")
    print(f"{'='*60}")

    # Save to file
    output_dir = Path("logs/prs/tinacms")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "pr_list.json"
    with open(output_file, "w") as f:
        json.dump(good_prs, f, indent=2)

    print(f"Saved to: {output_file}")

    # Print summary
    print(f"\nSummary:")
    print(f"  Total PRs checked: {len(prs)}")
    print(f"  Suitable PRs found: {len(good_prs)}")
    print(f"  Average files per PR: {sum(p['total_files'] for p in good_prs) / len(good_prs):.1f}")
    print(f"  Average additions: {sum(p['additions'] for p in good_prs) / len(good_prs):.0f}")

    return good_prs


if __name__ == "__main__":
    main()
