"""Collect PRs with rate limit handling and delays."""

import requests
import json
import os
import time
from pathlib import Path

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

def check_rate_limit():
    """Check GitHub API rate limit status."""
    resp = requests.get("https://api.github.com/rate_limit", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        core = data["resources"]["core"]
        print(f"\nRate limit: {core['remaining']}/{core['limit']} remaining")
        if core['remaining'] < 10:
            reset_time = core['reset']
            wait_time = max(0, reset_time - time.time())
            print(f"Low on rate limit. Reset in {wait_time/60:.1f} minutes")
            return False
        return True
    return True

def collect_prs_with_delay(owner, repo, max_prs=50, delay=2):
    """
    Collect PRs with delays between requests to avoid rate limiting.
    """
    prs = []
    page = 1

    print(f"\n{'='*60}")
    print(f"Collecting PRs from {owner}/{repo}")
    print(f"{'='*60}")

    # Check rate limit first
    if not check_rate_limit():
        print("Skipping due to rate limit")
        return prs

    while len(prs) < max_prs and page <= 5:  # Reduced pages
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        params = {
            "state": "closed",
            "per_page": 50,  # Reduced per page
            "sort": "updated",
            "direction": "desc",
            "page": page
        }

        print(f"\nFetching page {page}...")
        time.sleep(delay)  # Delay between requests
        resp = requests.get(url, headers=headers, params=params)

        if resp.status_code == 429:
            print("Rate limited. Stopping collection.")
            break
        elif resp.status_code != 200:
            print(f"Error: {resp.status_code}")
            break

        page_prs = resp.json()
        if not page_prs:
            break

        print(f"Examining {len(page_prs)} PRs...")
        examined = 0

        for pr in page_prs:
            if len(prs) >= max_prs:
                break

            examined += 1

            # Skip if not merged
            if not pr.get("merged_at"):
                continue

            # Skip merge commits
            if "Merge" in pr.get("title", "") or "merge" in pr.get("title", ""):
                continue

            pr_num = pr["number"]
            print(f"  PR #{pr_num}: {pr['title'][:60]}...")

            # Delay before fetching files
            time.sleep(delay)

            # Get file changes
            files_url = pr["url"] + "/files"
            files_resp = requests.get(files_url, headers=headers)

            if files_resp.status_code == 429:
                print(f"    ✗ Rate limited on files")
                return prs  # Stop entirely
            elif files_resp.status_code != 200:
                print(f"    ✗ Failed to fetch files: {files_resp.status_code}")
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

            # Filter code files
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

            # Every 10 examined PRs, check rate limit
            if examined % 10 == 0:
                if not check_rate_limit():
                    print("Stopping due to rate limit")
                    return prs

        page += 1

    print(f"\n{'='*60}")
    print(f"Total collected: {len(prs)} PRs")
    print(f"{'='*60}")
    return prs


if __name__ == "__main__":
    output_dir = Path("logs/prs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect from nocodb first (we have 0 from it)
    print("\n" + "="*60)
    print("STARTING NOCODB COLLECTION")
    print("="*60)
    nocodb_prs = collect_prs_with_delay("nocodb", "nocodb", max_prs=25, delay=3)

    if nocodb_prs:
        nocodb_file = output_dir / "nocodb-prs.jsonl"
        with open(nocodb_file, "w") as f:
            for pr in nocodb_prs:
                f.write(json.dumps(pr) + "\n")
        print(f"\nSaved {len(nocodb_prs)} nocodb PRs to {nocodb_file}")

    # Wait before collecting from hoppscotch (add to existing)
    print("\n\nWaiting 60 seconds before hoppscotch collection...")
    time.sleep(60)

    print("\n" + "="*60)
    print("STARTING HOPPSCOTCH COLLECTION (ADDITIONAL)")
    print("="*60)
    hoppscotch_prs = collect_prs_with_delay("hoppscotch", "hoppscotch", max_prs=25, delay=3)

    if hoppscotch_prs:
        # Load existing PRs
        existing_file = output_dir / "hoppscotch-prs.jsonl"
        existing_prs = []
        if existing_file.exists():
            with open(existing_file, "r") as f:
                for line in f:
                    if line.strip():
                        existing_prs.append(json.loads(line))

        existing_numbers = {pr["number"] for pr in existing_prs}
        new_prs = [pr for pr in hoppscotch_prs if pr["number"] not in existing_numbers]

        # Append new PRs
        with open(existing_file, "a") as f:
            for pr in new_prs:
                f.write(json.dumps(pr) + "\n")

        print(f"\nAdded {len(new_prs)} new hoppscotch PRs (total: {len(existing_prs) + len(new_prs)})")

    # Summary
    print(f"\n{'='*60}")
    print(f"COLLECTION SUMMARY")
    print(f"{'='*60}")
    print(f"nocodb: {len(nocodb_prs)} PRs collected")
    print(f"hoppscotch: {len(hoppscotch_prs)} new PRs collected")
    print(f"{'='*60}")
