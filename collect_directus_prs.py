#!/usr/bin/env python3
"""Collect PRs from directus/directus with test file changes."""

import json
import os
import requests
from pathlib import Path
from datetime import datetime

# GitHub token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not set in environment")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_merged_prs(owner, repo, max_prs=50):
    """Fetch merged PRs from GitHub API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    params = {
        "state": "closed",
        "sort": "updated",
        "direction": "desc",
        "per_page": 100
    }

    prs = []
    page = 1

    while len(prs) < max_prs:
        params["page"] = page
        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code != 200:
            print(f"Error fetching PRs: {response.status_code}")
            break

        page_prs = response.json()
        if not page_prs:
            break

        for pr in page_prs:
            if pr.get("merged_at"):
                prs.append(pr)
                if len(prs) >= max_prs:
                    break

        page += 1

    return prs[:max_prs]

def get_pr_files(owner, repo, pr_number):
    """Get files changed in a PR."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        return []

    return response.json()

def get_pr_patch(owner, repo, pr_number):
    """Get the unified diff patch for a PR."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = HEADERS.copy()
    headers["Accept"] = "application/vnd.github.v3.diff"

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return ""

    return response.text

def is_good_pr(pr_data, files):
    """Filter for PRs with test file changes and reasonable size."""
    # Must have test files (not just snapshots)
    test_files = [
        f for f in files
        if (f["filename"].endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
            and ".snap" not in f["filename"])
    ]

    # Must have code file changes
    code_files = [
        f for f in files
        if f["filename"].endswith((".ts", ".tsx", ".js", ".jsx"))
        and not f["filename"].endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
        and ".snap" not in f["filename"]
    ]

    # Filter criteria
    has_test_changes = len(test_files) > 0
    has_code_changes = len(code_files) > 0
    is_focused = len(files) <= 10  # Not too many files
    reasonable_size = pr_data.get("additions", 0) + pr_data.get("deletions", 0) < 5000

    return has_test_changes and has_code_changes and is_focused and reasonable_size

def main():
    owner = "directus"
    repo = "directus"

    print(f"Collecting PRs from {owner}/{repo}...")

    # Fetch merged PRs
    prs = get_merged_prs(owner, repo, max_prs=100)
    print(f"Found {len(prs)} merged PRs")

    # Filter PRs with test changes
    good_instances = []

    for i, pr in enumerate(prs, 1):
        pr_number = pr["number"]
        print(f"\n[{i}/{len(prs)}] Checking PR #{pr_number}...", end=" ")

        files = get_pr_files(owner, repo, pr_number)

        if is_good_pr(pr, files):
            # Get test files and code files
            test_files = [
                f["filename"] for f in files
                if (f["filename"].endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
                    and ".snap" not in f["filename"])
            ]
            code_files = [
                f["filename"] for f in files
                if f["filename"].endswith((".ts", ".tsx", ".js", ".jsx"))
                and not f["filename"].endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx"))
                and ".snap" not in f["filename"]
            ]

            # Get the patch
            patch = get_pr_patch(owner, repo, pr_number)

            instance = {
                "repo": f"{owner}/{repo}",
                "instance_id": f"{owner}__{repo}.pr_mirror.{pr_number}",
                "base_commit": pr["base"]["sha"],
                "patch": patch,  # Add the actual patch
                "test_patch": "",  # Will be filled by generate_ts.py
                "problem_statement": pr.get("body", ""),
                "hints_text": "",
                "created_at": pr["created_at"],
                "pull_number": pr_number,
                "test_files": test_files,
                "code_files": code_files,
                "title": pr["title"],
                "additions": pr.get("additions", 0),
                "deletions": pr.get("deletions", 0)
            }

            good_instances.append(instance)
            print(f"✓ ({len(test_files)} test files, {len(code_files)} code files)")
        else:
            print("✗ (filtered out)")

    # Save to JSONL
    output_dir = Path("logs/tasks")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "directus-insts.jsonl"

    with open(output_file, "w") as f:
        for instance in good_instances:
            f.write(json.dumps(instance) + "\n")

    print(f"\n✓ Saved {len(good_instances)} instances to {output_file}")
    print(f"\nSummary:")
    print(f"  Total PRs checked: {len(prs)}")
    print(f"  Valid instances: {len(good_instances)}")

if __name__ == "__main__":
    main()
