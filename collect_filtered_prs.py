#!/usr/bin/env python3
"""
Collect and filter PRs from excalidraw and tldraw repos.
Apply STRICT filtering criteria for F2P instance generation.
"""

import json
import os
import requests
import sys
from typing import List, Dict, Any

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

def get_pr_files(owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
    """Fetch files changed in a PR."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"  Error fetching files for PR #{pr_number}: {resp.status_code}", file=sys.stderr)
            return []
    except Exception as e:
        print(f"  Exception fetching files for PR #{pr_number}: {e}", file=sys.stderr)
        return []

def filter_pr(pr_data: Dict[str, Any]) -> bool:
    """
    Apply STRICT filtering criteria:
    - Must be merged
    - Must have .test.ts/.tsx changes (NOT just .snap)
    - Code diff < 5KB (< 500 lines changed)
    - At most 5 files changed
    - Has both code and test file changes
    - Not a merge commit
    """
    # Must be merged
    if not pr_data.get("merged_at"):
        return False

    # Get PR number and files
    pr_number = pr_data.get("number")
    owner = pr_data["base"]["repo"]["owner"]["login"]
    repo_name = pr_data["base"]["repo"]["name"]

    # Fetch files
    files = get_pr_files(owner, repo_name, pr_number)
    if not files:
        return False

    # File count check
    if len(files) > 5:
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

    # Total changes check (< 500 lines)
    total_changes = sum(f.get("changes", 0) for f in files)
    if total_changes >= 500:
        return False

    # Check if it's a merge commit (has multiple parents)
    # This is harder to detect via API, skip for now

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

    with open(jsonl_path, 'r') as f:
        for i, line in enumerate(f):
            if len(filtered_prs) >= max_prs:
                break

            try:
                pr_data = json.loads(line.strip())
                if filter_pr(pr_data):
                    filtered_prs.append(pr_data)
                    print(f"  ✓ PR #{pr_data['number']}: {pr_data['title'][:60]} ({pr_data['_total_changes']} changes, {len(pr_data['_files'])} files)")
            except Exception as e:
                print(f"  Error processing line {i}: {e}", file=sys.stderr)

    return filtered_prs

def collect_prs_from_github(owner: str, repo: str, max_prs: int = 50) -> List[Dict[str, Any]]:
    """Collect PRs directly from GitHub API."""
    print(f"\nCollecting PRs from {owner}/{repo}...")

    filtered_prs = []
    page = 1

    while len(filtered_prs) < max_prs and page <= 5:  # Limit to 5 pages (500 PRs max)
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
            if resp.status_code != 200:
                print(f"  Error: {resp.status_code}", file=sys.stderr)
                break

            prs = resp.json()
            if not prs:
                break

            for pr_data in prs:
                if len(filtered_prs) >= max_prs:
                    break

                if filter_pr(pr_data):
                    filtered_prs.append(pr_data)
                    print(f"  ✓ PR #{pr_data['number']}: {pr_data['title'][:60]} ({pr_data['_total_changes']} changes, {len(pr_data['_files'])} files)")

            page += 1

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
    print("PR Collection with STRICT Filtering")
    print("=" * 80)

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

    # Save tldraw PRs
    tldraw_prs_output = "/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/logs/prs/tldraw-prs.jsonl"
    with open(tldraw_prs_output, 'w') as f:
        for pr in tldraw_prs:
            f.write(json.dumps(pr) + '\n')
    print(f"Saved tldraw PRs to {tldraw_prs_output}")

    # Create tldraw instances (use 'main' as commit suffix for now)
    tldraw_instances = create_task_instances(tldraw_prs, "tldraw", "tldraw", "main")
    tldraw_output = "/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/logs/tasks/tldraw-filtered-insts.jsonl"
    with open(tldraw_output, 'w') as f:
        for inst in tldraw_instances:
            f.write(json.dumps(inst) + '\n')
    print(f"Wrote {len(tldraw_instances)} instances to {tldraw_output}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Excalidraw: {len(excalidraw_instances)} filtered PRs")
    print(f"Tldraw:     {len(tldraw_instances)} filtered PRs")
    print(f"TOTAL:      {len(excalidraw_instances) + len(tldraw_instances)} filtered PRs")
    print("\nFiles created:")
    print(f"  - {excalidraw_output}")
    print(f"  - {tldraw_output}")
    print(f"  - {tldraw_prs_output}")

if __name__ == "__main__":
    main()
