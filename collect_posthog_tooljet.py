#!/usr/bin/env python3
"""Collect high-quality PRs from PostHog and ToolJet repositories."""

import requests
import json
import os
import sys
from pathlib import Path

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

def collect_prs(owner, repo, max_prs=50):
    """Collect PRs with strict filtering criteria."""
    prs = []
    page = 1

    print(f"\n{'='*60}")
    print(f"Collecting PRs from {owner}/{repo}")
    print(f"{'='*60}\n")

    while len(prs) < max_prs and page <= 5:  # Limit to 5 pages
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        params = {
            "state": "closed",
            "per_page": 100,
            "page": page,
            "sort": "updated",
            "direction": "desc"
        }

        print(f"Fetching page {page}...")
        resp = requests.get(url, headers=headers, params=params)

        if resp.status_code != 200:
            print(f"Error: {resp.status_code} - {resp.text}")
            break

        pulls = resp.json()
        if not pulls:
            break

        for pr in pulls:
            if not pr.get("merged_at"):
                continue

            # Get PR files
            files_url = pr["url"] + "/files"
            files_resp = requests.get(files_url, headers=headers)

            if files_resp.status_code != 200:
                continue

            files = files_resp.json()

            # Filter for test files (exclude snapshots)
            test_files = [
                f for f in files
                if (".test.ts" in f["filename"] or
                    ".test.tsx" in f["filename"] or
                    ".spec.ts" in f["filename"] or
                    ".spec.tsx" in f["filename"])
                and ".snap" not in f["filename"]
            ]

            # Filter for code files (exclude tests)
            code_files = [
                f for f in files
                if (f["filename"].endswith((".ts", ".tsx", ".js", ".jsx")) and
                    ".test." not in f["filename"] and
                    ".spec." not in f["filename"])
            ]

            # Calculate total changes
            total_changes = sum(f.get("changes", 0) for f in files)

            # Apply strict filters
            has_real_tests = len(test_files) > 0
            has_code_changes = len(code_files) > 0
            is_small = total_changes < 500 and len(files) <= 5
            not_merge = "merge" not in pr["title"].lower()

            if has_real_tests and has_code_changes and is_small and not_merge:
                pr_data = {
                    "number": pr["number"],
                    "title": pr["title"],
                    "base_commit": pr["base"]["sha"],
                    "head_commit": pr["head"]["sha"],
                    "merged_at": pr["merged_at"],
                    "files": [f["filename"] for f in files],
                    "test_files": [f["filename"] for f in test_files],
                    "code_files": [f["filename"] for f in code_files],
                    "total_changes": total_changes,
                    "url": pr["html_url"]
                }
                prs.append(pr_data)

                print(f"✓ PR #{pr['number']}: {pr['title'][:60]}")
                print(f"  Tests: {len(test_files)}, Code: {len(code_files)}, Changes: {total_changes}")

                if len(prs) >= max_prs:
                    break

        page += 1

    print(f"\n{'='*60}")
    print(f"Total PRs collected: {len(prs)}")
    print(f"{'='*60}\n")

    return prs


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
    if not GITHUB_TOKEN:
        print("⚠ Warning: GITHUB_TOKEN not set. API rate limits will be restricted.")
        print("Set it with: export GITHUB_TOKEN='your_token'")

    main()
