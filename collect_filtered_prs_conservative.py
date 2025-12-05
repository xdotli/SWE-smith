#!/usr/bin/env python3
"""
Collect and filter PRs with conservative API usage.
Uses diff URLs instead of files API when possible.
"""

import json
import os
import requests
import sys
import time
from typing import List, Dict, Any

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

def check_rate_limit():
    """Check GitHub API rate limit."""
    url = "https://api.github.com/rate_limit"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            core = data["resources"]["core"]
            print(f"  Rate limit: {core['remaining']}/{core['limit']} (resets at {time.ctime(core['reset'])})")
            return core["remaining"]
        return 0
    except:
        return 0

def get_pr_diff(diff_url: str) -> str:
    """Fetch PR diff."""
    try:
        resp = requests.get(diff_url, timeout=30)
        if resp.status_code == 200:
            return resp.text
        return ""
    except:
        return ""

def analyze_diff(diff_text: str) -> Dict[str, Any]:
    """Analyze diff to extract file changes."""
    files = []
    current_file = None
    additions = 0
    deletions = 0

    for line in diff_text.split('\n'):
        if line.startswith('diff --git'):
            if current_file:
                files.append({
                    "filename": current_file,
                    "additions": additions,
                    "deletions": deletions,
                    "changes": additions + deletions
                })
            # Extract filename: diff --git a/file.ts b/file.ts
            parts = line.split()
            if len(parts) >= 4:
                current_file = parts[3].lstrip('b/')
                additions = 0
                deletions = 0
        elif line.startswith('+') and not line.startswith('+++'):
            additions += 1
        elif line.startswith('-') and not line.startswith('---'):
            deletions += 1

    if current_file:
        files.append({
            "filename": current_file,
            "additions": additions,
            "deletions": deletions,
            "changes": additions + deletions
        })

    return {
        "files": files,
        "total_changes": sum(f["changes"] for f in files)
    }

def filter_pr(pr_data: Dict[str, Any]) -> bool:
    """
    Apply STRICT filtering criteria using diff URL.
    """
    # Must be merged
    if not pr_data.get("merged_at"):
        return False

    # Get diff
    diff_url = pr_data.get("diff_url")
    if not diff_url:
        return False

    # Fetch and analyze diff
    diff_text = get_pr_diff(diff_url)
    if not diff_text:
        return False

    diff_analysis = analyze_diff(diff_text)
    files = diff_analysis["files"]
    total_changes = diff_analysis["total_changes"]

    # File count check (at most 5 files)
    if len(files) > 5:
        return False

    # Total changes check (< 500 lines)
    if total_changes >= 500:
        return False

    # Categorize files
    test_files = []
    code_files = []

    for f in files:
        filename = f["filename"]
        if ".test.ts" in filename or ".spec.ts" in filename:
            test_files.append(filename)
        elif filename.endswith((".ts", ".tsx")) and ".test." not in filename and ".spec." not in filename:
            code_files.append(filename)

    # Must have real test files (not snapshots)
    has_real_tests = any(".snap" not in f for f in test_files)
    if not has_real_tests or not test_files:
        return False

    # Must have code files
    if not code_files:
        return False

    # Store file info
    pr_data["_files"] = files
    pr_data["_test_files"] = test_files
    pr_data["_code_files"] = code_files
    pr_data["_total_changes"] = total_changes

    return True

def collect_prs_from_file(jsonl_path: str, max_prs: int = 50) -> List[Dict[str, Any]]:
    """Load PRs from existing JSONL file and filter."""
    filtered_prs = []

    if not os.path.exists(jsonl_path):
        print(f"File not found: {jsonl_path}", file=sys.stderr)
        return []

    print(f"Reading PRs from {jsonl_path}...")

    with open(jsonl_path, 'r') as f:
        lines = f.readlines()

    print(f"Total PRs in file: {len(lines)}")

    for i, line in enumerate(lines):
        if len(filtered_prs) >= max_prs:
            break

        try:
            pr_data = json.loads(line.strip())
            print(f"  Checking PR #{pr_data['number']}: {pr_data['title'][:60]}...", end=" ")

            if filter_pr(pr_data):
                filtered_prs.append(pr_data)
                print(f"✓ ({pr_data['_total_changes']} changes, {len(pr_data['_files'])} files)")
            else:
                print("✗")

            # Be nice to GitHub (even for diff URLs)
            if i % 10 == 0 and i > 0:
                time.sleep(1)

        except Exception as e:
            print(f"  Error processing line {i}: {e}", file=sys.stderr)

    return filtered_prs

def collect_prs_from_github(owner: str, repo: str, max_prs: int = 50) -> List[Dict[str, Any]]:
    """Collect PRs directly from GitHub API."""
    print(f"\nCollecting PRs from {owner}/{repo}...")

    # Check rate limit first
    remaining = check_rate_limit()
    if remaining < 10:
        print("  Rate limit too low, skipping GitHub collection")
        return []

    filtered_prs = []
    page = 1

    while len(filtered_prs) < max_prs and page <= 3:  # Limit to 3 pages
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        params = {
            "state": "closed",
            "per_page": 100,
            "page": page,
            "sort": "updated",
            "direction": "desc"
        }

        print(f"  Fetching page {page}...")
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            if resp.status_code == 429:
                print("  Rate limited, stopping")
                break
            if resp.status_code != 200:
                print(f"  Error: {resp.status_code}", file=sys.stderr)
                break

            prs = resp.json()
            if not prs:
                break

            # Save all PRs to file first
            prs_output = f"/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/logs/prs/{repo}-prs-page{page}.jsonl"
            with open(prs_output, 'w') as f:
                for pr in prs:
                    f.write(json.dumps(pr) + '\n')
            print(f"  Saved page {page} to {prs_output}")

            # Filter PRs
            for pr_data in prs:
                if len(filtered_prs) >= max_prs:
                    break

                print(f"  Checking PR #{pr_data['number']}: {pr_data['title'][:60]}...", end=" ")
                if filter_pr(pr_data):
                    filtered_prs.append(pr_data)
                    print(f"✓ ({pr_data['_total_changes']} changes, {len(pr_data['_files'])} files)")
                else:
                    print("✗")

                time.sleep(0.5)  # Be nice

            page += 1
            time.sleep(2)  # Longer delay between pages

        except Exception as e:
            print(f"  Exception: {e}", file=sys.stderr)
            break

    return filtered_prs

def create_task_instances(prs: List[Dict[str, Any]], repo_owner: str, repo_name: str, commit_suffix: str) -> List[Dict[str, Any]]:
    """Create task instances from filtered PRs."""
    instances = []

    for pr in prs:
        instance = {
            "repo": f"{repo_owner}/{repo_name}",
            "instance_id": f"{repo_owner.lower()}__{repo_name.lower()}.{commit_suffix}.{pr['number']}",
            "base_commit": pr["base"]["sha"],
            "head_commit": pr["head"]["sha"],
            "pr_number": pr["number"],
            "test_files": pr.get("_test_files", []),
            "code_files": pr.get("_code_files", []),
            "all_files": [f["filename"] for f in pr.get("_files", [])],
            "total_changes": pr.get("_total_changes", 0),
            "title": pr["title"],
            "merged_at": pr["merged_at"]
        }
        instances.append(instance)

    return instances

def main():
    print("=" * 80)
    print("PR Collection with STRICT Filtering (Conservative API Usage)")
    print("=" * 80)

    # Check rate limit
    check_rate_limit()

    # Excalidraw: filter from existing file
    print("\n### EXCALIDRAW ###")
    excalidraw_prs_file = "/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/logs/prs/excalidraw-prs.jsonl"
    excalidraw_prs = collect_prs_from_file(excalidraw_prs_file, max_prs=25)
    print(f"\nFiltered excalidraw PRs: {len(excalidraw_prs)}")

    # Create excalidraw instances
    excalidraw_instances = create_task_instances(excalidraw_prs, "excalidraw", "excalidraw", "8d18078f")
    excalidraw_output = "/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/logs/tasks/excalidraw-filtered-insts.jsonl"
    with open(excalidraw_output, 'w') as f:
        for inst in excalidraw_instances:
            f.write(json.dumps(inst) + '\n')
    print(f"Wrote {len(excalidraw_instances)} instances to {excalidraw_output}")

    # tldraw: collect from GitHub
    print("\n### TLDRAW ###")
    tldraw_prs = collect_prs_from_github("tldraw", "tldraw", max_prs=25)
    print(f"\nFiltered tldraw PRs: {len(tldraw_prs)}")

    if tldraw_prs:
        # Create tldraw instances
        tldraw_instances = create_task_instances(tldraw_prs, "tldraw", "tldraw", "main")
        tldraw_output = "/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/logs/tasks/tldraw-filtered-insts.jsonl"
        with open(tldraw_output, 'w') as f:
            for inst in tldraw_instances:
                f.write(json.dumps(inst) + '\n')
        print(f"Wrote {len(tldraw_instances)} instances to {tldraw_output}")
    else:
        tldraw_instances = []

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Excalidraw: {len(excalidraw_instances)} filtered PRs")
    print(f"Tldraw:     {len(tldraw_instances)} filtered PRs")
    print(f"TOTAL:      {len(excalidraw_instances) + len(tldraw_instances)} filtered PRs")
    print("\nFiles created:")
    print(f"  - {excalidraw_output}")
    if tldraw_instances:
        print(f"  - {tldraw_output}")

    # Check rate limit at end
    print("\nFinal rate limit:")
    check_rate_limit()

if __name__ == "__main__":
    main()
