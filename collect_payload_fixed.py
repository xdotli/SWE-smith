#!/usr/bin/env python3
"""
Collect PRs from Payload CMS using FIXED-COMMIT strategy.

This script fixes the commit mismatch issue by using a single base_commit
for all instances, rather than using each PR's individual base commit.

Usage:
    python collect_payload_fixed.py --base-commit abc123 --limit 50
"""

import argparse
import json
import os
import requests
from datetime import datetime
from typing import List, Dict, Optional

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

REPO = "payloadcms/payload"
TEST_PATTERNS = [".test.ts", ".test.tsx", ".test.js", ".test.jsx", ".spec.ts", ".spec.tsx"]

def get_commit_date(repo: str, commit_sha: str) -> str:
    """Get the date when a commit was created."""
    url = f"https://api.github.com/repos/{repo}/commits/{commit_sha}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        data = resp.json()
        return data["commit"]["committer"]["date"]
    else:
        print(f"Error fetching commit {commit_sha}: {resp.status_code}")
        return None

def get_merged_prs_after_date(repo: str, since_date: str, limit: int = 100) -> List[Dict]:
    """Fetch merged PRs after a specific date."""
    url = f"https://api.github.com/repos/{repo}/pulls"
    params = {
        "state": "closed",
        "sort": "updated",
        "direction": "desc",
        "per_page": 100,
    }

    all_prs = []
    page = 1
    since_dt = datetime.fromisoformat(since_date.replace("Z", "+00:00"))

    while len(all_prs) < limit:
        params["page"] = page
        resp = requests.get(url, headers=HEADERS, params=params)

        if resp.status_code != 200:
            print(f"Error fetching PRs (page {page}): {resp.status_code}")
            break

        prs = resp.json()
        if not prs:
            break

        for pr in prs:
            # Only include merged PRs
            if not pr.get("merged_at"):
                continue

            merged_dt = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))

            # Only PRs merged AFTER our base commit
            if merged_dt > since_dt:
                all_prs.append(pr)

            # Stop if we've gone past our date range
            if merged_dt < since_dt:
                return all_prs[:limit]

        page += 1

        # Stop if we've collected enough
        if len(all_prs) >= limit:
            return all_prs[:limit]

        # API rate limit check
        if resp.headers.get("X-RateLimit-Remaining") == "0":
            print("Warning: GitHub API rate limit reached")
            break

    return all_prs[:limit]

def get_pr_files(repo: str, pr_number: int) -> Optional[Dict]:
    """Get list of files changed in a PR."""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    resp = requests.get(url, headers=HEADERS)

    if resp.status_code != 200:
        print(f"Error fetching files for PR {pr_number}: {resp.status_code}")
        return None

    files = resp.json()

    test_files = []
    code_files = []
    has_snapshots_only = True

    for f in files:
        filename = f["filename"]

        # Check if it's a test file
        if any(pattern in filename for pattern in TEST_PATTERNS):
            if ".snap" not in filename:
                test_files.append(filename)
                has_snapshots_only = False
            # Else: skip snapshot files
        # Check if it's a code file
        elif filename.endswith((".ts", ".tsx", ".js", ".jsx")):
            # Skip config files
            if not any(x in filename for x in ["config", ".config", "setup", "vitest", "jest"]):
                code_files.append(filename)

    total_changes = sum(f.get("changes", 0) for f in files)

    return {
        "test_files": test_files,
        "code_files": code_files,
        "total_files": len(test_files) + len(code_files),
        "total_changes": total_changes,
        "has_snapshots_only": has_snapshots_only,
    }

def get_pr_diff(repo: str, pr_number: int) -> Optional[str]:
    """Get the unified diff for a PR."""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    headers_with_diff = HEADERS.copy()
    headers_with_diff["Accept"] = "application/vnd.github.v3.diff"

    resp = requests.get(url, headers=headers_with_diff)

    if resp.status_code == 200:
        return resp.text
    else:
        print(f"Error fetching diff for PR {pr_number}: {resp.status_code}")
        return None

def should_include_pr(pr_info: Dict) -> tuple[bool, str]:
    """Determine if a PR should be included based on filtering criteria."""
    # Must have real test files (not just snapshots)
    if len(pr_info["test_files"]) == 0:
        return False, "No test files"

    if pr_info["has_snapshots_only"]:
        return False, "Only snapshot tests"

    # Must have code changes too
    if len(pr_info["code_files"]) == 0:
        return False, "No code files"

    # Should be small and focused (1-5 files total)
    if pr_info["total_files"] > 8:
        return False, f"Too many files ({pr_info['total_files']})"

    # Should have reasonable size changes
    if pr_info["total_changes"] > 500:
        return False, f"Too many changes ({pr_info['total_changes']})"

    return True, "OK"

def create_instance(pr: Dict, pr_info: Dict, base_commit: str, repo: str) -> Dict:
    """Create a task instance from a PR using fixed base commit."""
    pr_number = pr["number"]
    pr_diff = get_pr_diff(repo, pr_number)

    if not pr_diff:
        return None

    # Create instance with FIXED base_commit (same for all)
    instance = {
        "repo": repo,
        "instance_id": f"{repo.replace('/', '__')}.fixed.{pr_number}",
        "base_commit": base_commit,  # SAME for all instances!
        "patch": pr_diff,
        "problem_statement": f"{pr['title']}\n\n{pr['body'] or ''}",
        "test_files": pr_info["test_files"],
        "code_files": pr_info["code_files"],
        "pull_number": pr_number,
        "original_patch": pr_diff,  # Store original for reference
        "FAIL_TO_PASS": [],  # Will be populated after validation
        "PASS_TO_PASS": [],  # Will be populated after validation
    }

    return instance

def collect_instances(repo: str, base_commit: str, limit: int = 50, output_file: str = None):
    """Main function to collect instances with fixed-commit strategy."""
    print("="*80)
    print("Fixed-Commit PR Collection for Payload CMS")
    print("="*80)

    # Get base commit date
    print(f"\n1. Fetching base commit date for {base_commit[:8]}...")
    commit_date = get_commit_date(repo, base_commit)
    if not commit_date:
        print("Error: Could not fetch commit date")
        return

    print(f"   Base commit date: {commit_date}")

    # Fetch PRs merged after this commit
    print(f"\n2. Fetching merged PRs after {commit_date}...")
    prs = get_merged_prs_after_date(repo, commit_date, limit=limit * 3)  # Fetch more than needed
    print(f"   Found {len(prs)} merged PRs")

    # Filter PRs
    print(f"\n3. Filtering PRs for test coverage...")
    instances = []
    stats = {
        "total": len(prs),
        "no_test_files": 0,
        "snapshots_only": 0,
        "no_code_files": 0,
        "too_large": 0,
        "included": 0,
    }

    for pr in prs:
        pr_number = pr["number"]
        pr_info = get_pr_files(repo, pr_number)

        if not pr_info:
            continue

        should_include, reason = should_include_pr(pr_info)

        if should_include:
            instance = create_instance(pr, pr_info, base_commit, repo)
            if instance:
                instances.append(instance)
                stats["included"] += 1
                print(f"   â PR #{pr_number}: {pr['title'][:50]}")
                print(f"      Tests: {len(pr_info['test_files'])}, Code: {len(pr_info['code_files'])}")
        else:
            if "test" in reason.lower():
                stats["no_test_files"] += 1
            elif "snapshot" in reason.lower():
                stats["snapshots_only"] += 1
            elif "code" in reason.lower():
                stats["no_code_files"] += 1
            elif "large" in reason.lower() or "many" in reason.lower():
                stats["too_large"] += 1

        # Stop if we've collected enough
        if len(instances) >= limit:
            break

    # Print statistics
    print(f"\n{'='*80}")
    print("Collection Statistics")
    print(f"{'='*80}")
    print(f"Total PRs analyzed: {stats['total']}")
    print(f"  â Included: {stats['included']}")
    print(f"  â No test files: {stats['no_test_files']}")
    print(f"  â Snapshots only: {stats['snapshots_only']}")
    print(f"  â No code files: {stats['no_code_files']}")
    print(f"  â Too large: {stats['too_large']}")

    # Save to file
    if output_file:
        with open(output_file, "w") as f:
            json.dump(instances, f, indent=2)
        print(f"\nâ Saved {len(instances)} instances to {output_file}")

    return instances

def main():
    parser = argparse.ArgumentParser(
        description="Collect Payload CMS PRs with fixed-commit strategy"
    )
    parser.add_argument(
        "--base-commit",
        type=str,
        required=True,
        help="Fixed base commit SHA to use for all instances",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Target number of instances to collect (default: 50)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="logs/tasks/payload-fixed-insts.jsonl",
        help="Output file path",
    )

    args = parser.parse_args()

    if not GITHUB_TOKEN:
        print("Warning: GITHUB_TOKEN not set. API rate limits will be restrictive.")
        print("Set with: export GITHUB_TOKEN=ghp_...")

    collect_instances(REPO, args.base_commit, args.limit, args.output)

if __name__ == "__main__":
    main()
