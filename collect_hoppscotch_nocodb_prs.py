"""Collect high-quality PRs from hoppscotch and nocodb with strict filtering."""

import requests
import json
import os
from pathlib import Path

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

def collect_prs_strict(owner, repo, max_prs=50):
    """
    Collect PRs with STRICT filtering:
    - Changes to .test.ts/.test.tsx/.spec.ts files (NOT just .snap)
    - Code diff < 500 changes total
    - Not a merge commit
    - Has both code and test file changes
    - At most 5 files changed
    """
    prs = []
    page = 1

    print(f"\n{'='*60}")
    print(f"Collecting PRs from {owner}/{repo}")
    print(f"{'='*60}")

    while len(prs) < max_prs and page <= 10:
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        params = {
            "state": "closed",
            "per_page": 100,
            "sort": "updated",
            "direction": "desc",
            "page": page
        }

        print(f"\nFetching page {page}...")
        resp = requests.get(url, headers=headers, params=params)

        if resp.status_code != 200:
            print(f"Error: {resp.status_code} - {resp.text}")
            break

        page_prs = resp.json()
        if not page_prs:
            print("No more PRs found")
            break

        print(f"Examining {len(page_prs)} PRs...")

        for pr in page_prs:
            if len(prs) >= max_prs:
                break

            # Skip if not merged
            if not pr.get("merged_at"):
                continue

            # Skip merge commits
            if "Merge" in pr.get("title", "") or "merge" in pr.get("title", ""):
                continue

            pr_num = pr["number"]
            print(f"  PR #{pr_num}: {pr['title'][:60]}...")

            # Get file changes
            files_url = pr["url"] + "/files"
            files_resp = requests.get(files_url, headers=headers)

            if files_resp.status_code != 200:
                print(f"    ✗ Failed to fetch files")
                continue

            files = files_resp.json()

            # Filter test files (no snapshots)
            test_files = [
                f for f in files
                if (".test.ts" in f["filename"] or
                    ".test.tsx" in f["filename"] or
                    ".spec.ts" in f["filename"] or
                    ".spec.tsx" in f["filename"])
                and ".snap" not in f["filename"]
            ]

            # Filter code files (no test files)
            code_files = [
                f for f in files
                if (f["filename"].endswith((".ts", ".tsx", ".js", ".jsx")) and
                    ".test." not in f["filename"] and
                    ".spec." not in f["filename"])
            ]

            # Calculate total changes
            total_changes = sum(f.get("changes", 0) for f in files)

            # Apply filters
            has_real_tests = len(test_files) > 0
            has_code_changes = len(code_files) > 0
            is_small = total_changes < 500 and len(files) <= 5

            if not has_real_tests:
                print(f"    ✗ No real test files")
                continue
            if not has_code_changes:
                print(f"    ✗ No code changes")
                continue
            if not is_small:
                print(f"    ✗ Too large: {total_changes} changes, {len(files)} files")
                continue

            # Passed all filters!
            print(f"    ✓ PASSED ({total_changes} changes, {len(files)} files)")
            prs.append({
                "number": pr["number"],
                "title": pr["title"],
                "base_commit": pr["base"]["sha"],
                "head_commit": pr["head"]["sha"],
                "merged_at": pr["merged_at"],
                "files": [f["filename"] for f in files],
                "test_files": [f["filename"] for f in test_files],
                "code_files": [f["filename"] for f in code_files],
                "total_changes": total_changes,
                "file_count": len(files)
            })

        page += 1

    print(f"\n{'='*60}")
    print(f"Total collected: {len(prs)} PRs")
    print(f"{'='*60}")
    return prs


if __name__ == "__main__":
    # Create output directory
    output_dir = Path("logs/prs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect from hoppscotch
    hoppscotch_prs = collect_prs_strict("hoppscotch", "hoppscotch", max_prs=25)
    hoppscotch_file = output_dir / "hoppscotch-prs.jsonl"
    with open(hoppscotch_file, "w") as f:
        for pr in hoppscotch_prs:
            f.write(json.dumps(pr) + "\n")
    print(f"\nSaved {len(hoppscotch_prs)} hoppscotch PRs to {hoppscotch_file}")

    # Collect from nocodb
    nocodb_prs = collect_prs_strict("nocodb", "nocodb", max_prs=25)
    nocodb_file = output_dir / "nocodb-prs.jsonl"
    with open(nocodb_file, "w") as f:
        for pr in nocodb_prs:
            f.write(json.dumps(pr) + "\n")
    print(f"Saved {len(nocodb_prs)} nocodb PRs to {nocodb_file}")

    # Summary
    print(f"\n{'='*60}")
    print(f"COLLECTION SUMMARY")
    print(f"{'='*60}")
    print(f"hoppscotch: {len(hoppscotch_prs)} PRs")
    print(f"nocodb: {len(nocodb_prs)} PRs")
    print(f"TOTAL: {len(hoppscotch_prs) + len(nocodb_prs)} PRs")
    print(f"{'='*60}")
