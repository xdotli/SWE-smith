#!/usr/bin/env python3
"""Collect high-quality PRs using GitHub CLI."""

import subprocess
import json
import sys
from pathlib import Path

def run_gh_command(cmd):
    """Run a gh CLI command and return JSON output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout) if result.stdout else []
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print(f"stderr: {e.stderr}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return []


def get_pr_files(owner, repo, pr_number):
    """Get files changed in a PR."""
    cmd = f"gh pr view {pr_number} --repo {owner}/{repo} --json files"
    result = run_gh_command(cmd)
    return result.get("files", []) if result else []


def collect_prs(owner, repo, max_prs=30):
    """Collect PRs with strict filtering criteria."""
    print(f"\n{'='*60}")
    print(f"Collecting PRs from {owner}/{repo}")
    print(f"{'='*60}\n")

    # Get merged PRs
    cmd = f'gh pr list --repo {owner}/{repo} --state merged --limit 200 --json number,title,baseRefOid,headRefOid,mergedAt,files'

    print(f"Fetching merged PRs...")
    all_prs = run_gh_command(cmd)

    if not all_prs:
        print(f"No PRs fetched from {owner}/{repo}")
        return []

    print(f"Fetched {len(all_prs)} merged PRs, applying filters...")

    filtered_prs = []

    for pr in all_prs:
        # Get file information
        files = pr.get("files", [])

        if not files:
            continue

        # Filter for test files (exclude snapshots)
        test_files = [
            f["path"] for f in files
            if (".test.ts" in f["path"] or
                ".test.tsx" in f["path"] or
                ".spec.ts" in f["path"] or
                ".spec.tsx" in f["path"])
            and ".snap" not in f["path"]
        ]

        # Filter for code files (exclude tests)
        code_files = [
            f["path"] for f in files
            if (f["path"].endswith((".ts", ".tsx", ".js", ".jsx")) and
                ".test." not in f["path"] and
                ".spec." not in f["path"])
        ]

        # Calculate total changes
        total_changes = sum(f.get("additions", 0) + f.get("deletions", 0) for f in files)

        # Apply strict filters
        has_real_tests = len(test_files) > 0
        has_code_changes = len(code_files) > 0
        is_small = total_changes < 500 and len(files) <= 5
        not_merge = "merge" not in pr["title"].lower()

        if has_real_tests and has_code_changes and is_small and not_merge:
            pr_data = {
                "number": pr["number"],
                "title": pr["title"],
                "base_commit": pr["baseRefOid"],
                "head_commit": pr["headRefOid"],
                "merged_at": pr["mergedAt"],
                "files": [f["path"] for f in files],
                "test_files": test_files,
                "code_files": code_files,
                "total_changes": total_changes,
                "url": f"https://github.com/{owner}/{repo}/pull/{pr['number']}"
            }
            filtered_prs.append(pr_data)

            print(f"✓ PR #{pr['number']}: {pr['title'][:60]}")
            print(f"  Tests: {len(test_files)}, Code: {len(code_files)}, Changes: {total_changes}")

            if len(filtered_prs) >= max_prs:
                break

    print(f"\n{'='*60}")
    print(f"Total PRs collected: {len(filtered_prs)}")
    print(f"{'='*60}\n")

    return filtered_prs


def save_prs(owner, repo, prs):
    """Save collected PRs to logs/prs directory."""
    logs_dir = Path("logs/prs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    filename = logs_dir / f"{repo.lower()}-filtered-prs.jsonl"

    with open(filename, "w") as f:
        for pr in prs:
            f.write(json.dumps(pr) + "\n")

    print(f"Saved {len(prs)} PRs to {filename}")
    return filename


def main():
    repos = [
        ("PostHog", "posthog"),
        ("ToolJet", "ToolJet")
    ]

    results = {}

    for owner, repo in repos:
        prs = collect_prs(owner, repo, max_prs=30)
        if prs:
            filename = save_prs(owner, repo, prs)
            results[f"{owner}/{repo}"] = {
                "count": len(prs),
                "file": str(filename)
            }
        else:
            print(f"⚠ No suitable PRs found for {owner}/{repo}")
            results[f"{owner}/{repo}"] = {
                "count": 0,
                "file": None
            }

    # Summary
    print("\n" + "="*60)
    print("COLLECTION SUMMARY")
    print("="*60)
    for repo_name, data in results.items():
        print(f"{repo_name}: {data['count']} PRs")
        if data['file']:
            print(f"  File: {data['file']}")
    print("="*60)

    return results


if __name__ == "__main__":
    main()
