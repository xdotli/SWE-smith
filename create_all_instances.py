#!/usr/bin/env python3
"""
Create SWE-bench style task instances from all collected PRs.
This script:
1. Reads all filtered_prs.json files
2. Fetches the actual diff for each PR
3. Creates task instances in JSONL format
"""
import json
import os
import requests
import time
from pathlib import Path

# Load GitHub token
env_path = Path(__file__).parent / ".env"
GITHUB_TOKEN = None
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if line.startswith("GITHUB_TOKEN=") or line.startswith("GH_TOKEN="):
                GITHUB_TOKEN = line.split("=", 1)[1].strip()
                break

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3.diff"
} if GITHUB_TOKEN else {"Accept": "application/vnd.github.v3.diff"}

# Repository mappings (owner/repo)
REPO_MAPPINGS = {
    "excalidraw": "excalidraw/excalidraw",
    "tldraw": "tldraw/tldraw",
    "medusa": "medusajs/medusa",
    "payload": "payloadcms/payload",
    "hoppscotch": "hoppscotch/hoppscotch",
    "strapi": "strapi/strapi",
    "appsmith": "appsmithorg/appsmith",
    "posthog": "PostHog/posthog",
    "tooljet": "ToolJet/ToolJet",
}

def get_pr_diff(owner: str, repo: str, pr_number: int) -> str | None:
    """Fetch the diff for a PR from GitHub API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.text
        elif resp.status_code == 403:
            print(f"  Rate limited, waiting 60s...")
            time.sleep(60)
            return get_pr_diff(owner, repo, pr_number)
        else:
            print(f"  Failed to get diff for PR #{pr_number}: {resp.status_code}")
            return None
    except Exception as e:
        print(f"  Error fetching PR #{pr_number}: {e}")
        return None

def split_patch(patch: str) -> tuple[str, str]:
    """Split patch into code changes and test changes."""
    test_lines = []
    code_lines = []
    current_file = None
    current_lines = []

    for line in patch.split('\n'):
        if line.startswith('diff --git'):
            # Save previous file
            if current_file:
                if '.test.' in current_file or '.spec.' in current_file or '/tests/' in current_file or '__tests__' in current_file:
                    test_lines.extend(current_lines)
                else:
                    code_lines.extend(current_lines)
            current_file = line.split(' b/')[-1] if ' b/' in line else None
            current_lines = [line]
        else:
            current_lines.append(line)

    # Handle last file
    if current_file:
        if '.test.' in current_file or '.spec.' in current_file or '/tests/' in current_file or '__tests__' in current_file:
            test_lines.extend(current_lines)
        else:
            code_lines.extend(current_lines)

    return '\n'.join(code_lines), '\n'.join(test_lines)

def create_instances_from_file(json_path: Path, repo_key: str) -> list[dict]:
    """Create task instances from a filtered PRs JSON file."""
    instances = []

    if not json_path.exists():
        return instances

    with open(json_path) as f:
        prs = json.load(f)

    if not prs:
        return instances

    repo_full = REPO_MAPPINGS.get(repo_key)
    if not repo_full:
        print(f"  Unknown repo key: {repo_key}")
        return instances

    owner, repo = repo_full.split("/")
    print(f"\nProcessing {repo_full}: {len(prs)} PRs")

    for i, pr in enumerate(prs):
        pr_num = pr.get("number")
        if not pr_num:
            continue

        print(f"  [{i+1}/{len(prs)}] PR #{pr_num}...", end=" ")

        # Get the diff
        patch = get_pr_diff(owner, repo, pr_num)
        if not patch:
            print("SKIP (no diff)")
            continue

        # Split into code and test patches
        code_patch, test_patch = split_patch(patch)

        if not code_patch.strip():
            print("SKIP (no code changes)")
            continue

        # Create instance
        instance = {
            "repo": repo_full,
            "pull_number": pr_num,
            "instance_id": f"{owner}__{repo}-{pr_num}",
            "issue_numbers": [],
            "base_commit": pr.get("base_sha", pr.get("merge_commit_sha", "")),
            "patch": code_patch,
            "test_patch": test_patch,
            "problem_statement": pr.get("title", ""),
            "hints_text": "",
            "created_at": pr.get("merged_at", ""),
            "version": "0.0.0",
            "FAIL_TO_PASS": [],
            "PASS_TO_PASS": [],
            "environment_setup_commit": pr.get("base_sha", ""),
        }

        instances.append(instance)
        print(f"OK ({len(code_patch)} bytes)")

        # Rate limiting
        time.sleep(0.5)

    return instances

def main():
    prs_dir = Path(__file__).parent / "logs" / "prs"
    output_dir = Path(__file__).parent / "logs" / "tasks"
    output_dir.mkdir(parents=True, exist_ok=True)

    all_instances = []

    # Process each repo
    for repo_key in REPO_MAPPINGS.keys():
        repo_dir = prs_dir / repo_key

        # Try different file patterns
        for pattern in ["filtered_prs_relaxed.json", "filtered_prs.json"]:
            json_path = repo_dir / pattern
            if json_path.exists():
                instances = create_instances_from_file(json_path, repo_key)
                all_instances.extend(instances)

                # Save per-repo instances
                if instances:
                    repo_output = output_dir / f"{repo_key}-insts.jsonl"
                    with open(repo_output, "w") as f:
                        for inst in instances:
                            f.write(json.dumps(inst) + "\n")
                    print(f"  Saved {len(instances)} instances to {repo_output}")
                break  # Use first matching file

    # Save combined instances
    combined_output = output_dir / "all-insts.jsonl"
    with open(combined_output, "w") as f:
        for inst in all_instances:
            f.write(json.dumps(inst) + "\n")

    print(f"\n=== SUMMARY ===")
    print(f"Total instances created: {len(all_instances)}")
    print(f"Combined file: {combined_output}")

    # Print per-repo breakdown
    repo_counts = {}
    for inst in all_instances:
        repo = inst["repo"]
        repo_counts[repo] = repo_counts.get(repo, 0) + 1

    print("\nPer-repo breakdown:")
    for repo, count in sorted(repo_counts.items(), key=lambda x: -x[1]):
        print(f"  {repo}: {count}")

if __name__ == "__main__":
    main()
