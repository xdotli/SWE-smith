#!/usr/bin/env python3
"""Create SWE-bench style task instances from excalidraw PRs with actual diffs."""
import json
import os
import requests

# Load token from .env file
env_path = os.path.join(os.path.dirname(__file__), ".env")
GITHUB_TOKEN = None
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.startswith("GITHUB_TOKEN=") or line.startswith("GH_TOKEN="):
                GITHUB_TOKEN = line.split("=", 1)[1].strip()
                break

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3.diff"  # Get diff format
} if GITHUB_TOKEN else {"Accept": "application/vnd.github.v3.diff"}

# Load collected PRs
with open("logs/prs/excalidraw/prs_with_tests.json") as f:
    prs = json.load(f)

print(f"Processing {len(prs)} PRs with tests...")

instances = []
for pr in prs:
    pr_num = pr["number"]
    merge_sha = pr["merge_commit_sha"]
    base_sha = pr.get("base_sha", "")

    if not base_sha:
        print(f"  PR #{pr_num}: Skipping - no base_sha")
        continue

    # Get the diff for this PR
    diff_url = f"https://api.github.com/repos/excalidraw/excalidraw/pulls/{pr_num}"
    diff_resp = requests.get(diff_url, headers=headers)

    if diff_resp.status_code != 200:
        print(f"  PR #{pr_num}: Failed to get diff - {diff_resp.status_code}")
        continue

    patch = diff_resp.text

    # Split patch into code changes and test changes
    test_patch_lines = []
    code_patch_lines = []
    current_file = None
    current_lines = []

    for line in patch.split('\n'):
        if line.startswith('diff --git'):
            # Save previous file if any
            if current_file:
                if '.test.' in current_file or '/tests/' in current_file or '__tests__' in current_file:
                    test_patch_lines.extend(current_lines)
                else:
                    code_patch_lines.extend(current_lines)
            current_file = line.split(' b/')[-1] if ' b/' in line else None
            current_lines = [line]
        else:
            current_lines.append(line)

    # Don't forget the last file
    if current_file:
        if '.test.' in current_file or '/tests/' in current_file or '__tests__' in current_file:
            test_patch_lines.extend(current_lines)
        else:
            code_patch_lines.extend(current_lines)

    code_patch = '\n'.join(code_patch_lines)
    test_patch = '\n'.join(test_patch_lines)

    if not code_patch.strip():
        print(f"  PR #{pr_num}: Skipping - no code changes (only test changes)")
        continue

    if not test_patch.strip():
        print(f"  PR #{pr_num}: Skipping - no test changes")
        continue

    instance = {
        "repo": "excalidraw/excalidraw",
        "pull_number": pr_num,
        "instance_id": f"excalidraw__excalidraw-{pr_num}",
        "issue_numbers": [],
        "base_commit": base_sha,
        "patch": code_patch,
        "test_patch": test_patch,
        "problem_statement": pr["title"],
        "hints_text": "",
        "created_at": pr["merged_at"],
        "version": "0.0.0",
        "FAIL_TO_PASS": [],
        "PASS_TO_PASS": [],
        "environment_setup_commit": base_sha,
    }

    print(f"  PR #{pr_num}: {pr['title'][:50]}... ({len(code_patch)} code, {len(test_patch)} test)")
    instances.append(instance)

# Save instances
output_file = "logs/tasks/excalidraw-insts.jsonl"
with open(output_file, "w") as f:
    for inst in instances:
        f.write(json.dumps(inst) + "\n")

print(f"\nSaved {len(instances)} instances to {output_file}")
