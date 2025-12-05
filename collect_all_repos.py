#!/usr/bin/env python3
"""Collect high-quality PRs from multiple repositories."""

import subprocess
import json
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
    except Exception as e:
        print(f"Error: {e}")
        return []


def collect_prs(owner, repo, max_prs=30):
    """Collect PRs with relaxed filtering criteria."""
    print(f"\n{'='*70}")
    print(f"Collecting PRs from {owner}/{repo}")
    print(f"{'='*70}\n")

    cmd = f'gh pr list --repo {owner}/{repo} --state merged --limit 200 --json number,title,baseRefOid,headRefOid,mergedAt,files'

    print(f"Fetching merged PRs...")
    all_prs = run_gh_command(cmd)

    if not all_prs:
        return []

    print(f"Fetched {len(all_prs)} merged PRs, applying filters...")

    filtered_prs = []

    for pr in all_prs:
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

        # RELAXED filters: up to 8 files, 800 changes
        has_real_tests = len(test_files) > 0
        has_code_changes = len(code_files) > 0
        is_reasonable = total_changes < 800 and len(files) <= 8
        not_merge = "merge" not in pr["title"].lower()

        if has_real_tests and has_code_changes and is_reasonable and not_merge:
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

            if len(filtered_prs) <= 5 or len(filtered_prs) >= max_prs - 5:
                # Only print first 5 and last 5 to reduce noise
                print(f"✓ PR #{pr['number']}: {pr['title'][:65]}")
                print(f"  Tests: {len(test_files)}, Code: {len(code_files)}, Changes: {total_changes}, Files: {len(files)}")

            if len(filtered_prs) >= max_prs:
                break

    print(f"\n{'='*70}")
    print(f"Total PRs collected: {len(filtered_prs)}")
    print(f"{'='*70}\n")

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
    # Priority repos with good test coverage
    repos = [
        ("calcom", "cal.com", 28),          # 28 PRs available
        ("twentyhq", "twenty", 14),         # 14 PRs available
        ("PostHog", "posthog", 9),          # 9 PRs available
        ("nocodb", "nocodb", 8),            # 8 PRs available
        ("appsmithorg", "appsmith", 8),     # 8 PRs available
        ("dubinc", "dub", 7),               # 7 PRs available
        ("hoppscotch", "hoppscotch", 4),    # 4 PRs available
    ]

    results = {}
    total_collected = 0

    for owner, repo, expected in repos:
        prs = collect_prs(owner, repo, max_prs=expected)
        if prs:
            filename = save_prs(owner, repo, prs)
            results[f"{owner}/{repo}"] = {
                "count": len(prs),
                "expected": expected,
                "file": str(filename)
            }
            total_collected += len(prs)
        else:
            print(f"⚠ No suitable PRs found for {owner}/{repo}")
            results[f"{owner}/{repo}"] = {
                "count": 0,
                "expected": expected,
                "file": None
            }

    # Summary
    print("\n" + "="*70)
    print("COLLECTION SUMMARY")
    print("="*70)
    for repo_name, data in results.items():
        status = "✓" if data['count'] >= data['expected'] * 0.8 else "⚠"
        print(f"{status} {repo_name}: {data['count']}/{data['expected']} PRs")
        if data['file']:
            print(f"  File: {data['file']}")
    print(f"\nTotal PRs collected: {total_collected}")
    print("="*70)

    return results


if __name__ == "__main__":
    main()
