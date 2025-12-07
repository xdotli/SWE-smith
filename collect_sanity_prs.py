#!/usr/bin/env python3
"""
Collect PRs from sanity-io/sanity repository for PR mirroring pipeline.
Filters for PRs with actual test file changes (not just snapshots).
"""

import json
import sys
from pathlib import Path
import requests
from typing import List, Dict, Any

# Configuration
REPO_OWNER = "sanity-io"
REPO_NAME = "sanity"
BASE_COMMIT = "615e6c01"
MAX_PRS = 50  # Collect up to 50 PRs
MAX_DIFF_SIZE_KB = 100  # Increased from 10KB to 100KB to allow larger changes

# API endpoints
GITHUB_API = "https://api.github.com"
SEARCH_PRS_URL = f"{GITHUB_API}/search/issues"
PR_DETAILS_URL = f"{GITHUB_API}/repos/{REPO_OWNER}/{REPO_NAME}/pulls"


def is_good_pr_candidate(pr_files: List[Dict[str, Any]]) -> tuple[bool, str]:
    """
    Check if a PR is a good candidate for mirroring.

    Returns:
        (is_good, reason)
    """
    test_files = []
    code_files = []
    total_changes = 0

    for file in pr_files:
        filename = file.get("filename", "")
        additions = file.get("additions", 0)
        deletions = file.get("deletions", 0)
        total_changes += additions + deletions

        # Categorize files
        if any(filename.endswith(ext) for ext in ['.test.ts', '.test.tsx', '.spec.ts', '.spec.tsx']):
            if '.snap' not in filename:  # Exclude snapshot files
                test_files.append(filename)
        elif filename.endswith(('.ts', '.tsx', '.js', '.jsx')):
            code_files.append(filename)

    # Must have actual test files (not snapshots)
    if not test_files:
        return False, "No test files (.test.ts/.tsx)"

    # Must have both code and test changes
    if not code_files:
        return False, "No code files changed"

    # Check diff size (rough estimate)
    if total_changes > MAX_DIFF_SIZE_KB * 50:  # ~50 lines per KB
        return False, f"Diff too large: {total_changes} lines"

    # Should be focused (not too many files)
    if len(code_files) > 10:
        return False, f"Too many files: {len(code_files)} code files"

    return True, f"✓ {len(test_files)} test files, {len(code_files)} code files, {total_changes} lines"


def collect_prs():
    """Collect eligible PRs from sanity-io/sanity repository."""
    print(f"Collecting PRs from {REPO_OWNER}/{REPO_NAME}...")
    print(f"Base commit: {BASE_COMMIT}")
    print(f"Max PRs: {MAX_PRS}")
    print(f"Max diff size: {MAX_DIFF_SIZE_KB}KB")
    print("-" * 80)

    # Search for merged PRs
    query = f"repo:{REPO_OWNER}/{REPO_NAME} is:pr is:merged"
    params = {
        "q": query,
        "sort": "updated",
        "order": "desc",
        "per_page": 100
    }

    print(f"\nSearching for merged PRs...")
    response = requests.get(SEARCH_PRS_URL, params=params)

    if response.status_code != 200:
        print(f"Error searching PRs: {response.status_code}")
        print(response.text)
        return []

    search_results = response.json()
    total_prs = search_results.get("total_count", 0)
    print(f"Found {total_prs} merged PRs")

    instances = []
    checked = 0
    skipped_reasons = {}

    for item in search_results.get("items", [])[:MAX_PRS]:
        pr_number = item["number"]
        checked += 1

        # Get PR details with files
        pr_url = f"{PR_DETAILS_URL}/{pr_number}"
        pr_response = requests.get(pr_url)

        if pr_response.status_code != 200:
            print(f"PR #{pr_number}: Error fetching details")
            continue

        pr_data = pr_response.json()

        # Get PR files
        files_url = f"{pr_url}/files"
        files_response = requests.get(files_url)

        if files_response.status_code != 200:
            print(f"PR #{pr_number}: Error fetching files")
            continue

        pr_files = files_response.json()

        # Check if this is a good candidate
        is_good, reason = is_good_pr_candidate(pr_files)

        if not is_good:
            skipped_reasons[reason] = skipped_reasons.get(reason, 0) + 1
            continue

        # Create instance
        instance = {
            "repo": f"{REPO_OWNER}/{REPO_NAME}",
            "base_commit": BASE_COMMIT,
            "pr_number": pr_number,
            "pr_url": pr_data["html_url"],
            "title": pr_data["title"],
            "merged_at": pr_data.get("merged_at"),
            "head_sha": pr_data["head"]["sha"],
            "base_sha": pr_data["base"]["sha"],
            "files_changed": len(pr_files),
            "additions": pr_data.get("additions", 0),
            "deletions": pr_data.get("deletions", 0)
        }

        instances.append(instance)
        print(f"PR #{pr_number}: ✓ {reason}")

        if len(instances) >= MAX_PRS:
            break

    # Summary
    print("\n" + "=" * 80)
    print(f"Collection Summary:")
    print(f"  PRs checked: {checked}")
    print(f"  PRs collected: {len(instances)}")
    print(f"\nSkipped reasons:")
    for reason, count in sorted(skipped_reasons.items(), key=lambda x: x[1], reverse=True):
        print(f"  {count:3d} - {reason}")

    return instances


def main():
    instances = collect_prs()

    if not instances:
        print("\n❌ No eligible PRs found")
        return 1

    # Save to JSONL file
    output_dir = Path("logs/tasks")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "sanity-insts.jsonl"

    with open(output_file, "w") as f:
        for instance in instances:
            f.write(json.dumps(instance) + "\n")

    print(f"\n✓ Saved {len(instances)} instances to {output_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
