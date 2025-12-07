#!/usr/bin/env python3
"""
Create instances file for tinacms PR mirroring.

This script converts the PR list into the JSONL format expected by generate_ts.py
"""

import json
import os
import requests
from pathlib import Path

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
OWNER = "tinacms"
REPO = "tinacms"
COMMIT = "ac59522053c71c713057c4c2b6ce610617bce85e"  # Full commit hash

headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def get_pr_details(pr_number):
    """Get full PR details including merge commit."""
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls/{pr_number}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_pr_diff(pr_number):
    """Get the PR diff."""
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/pulls/{pr_number}"
    headers_diff = headers.copy()
    headers_diff["Accept"] = "application/vnd.github.v3.diff"
    response = requests.get(url, headers=headers_diff)
    response.raise_for_status()
    return response.text


def create_instance(pr_data):
    """Create an instance dict for a PR."""
    pr_number = pr_data["number"]
    print(f"Creating instance for PR #{pr_number}...")

    pr_details = get_pr_details(pr_number)
    diff = get_pr_diff(pr_number)

    # Get merge commit info
    merge_commit_sha = pr_details.get("merge_commit_sha")
    if not merge_commit_sha:
        print(f"  ⚠️  No merge commit SHA for PR #{pr_number}")
        return None

    # Create instance following SWE-smith format
    instance = {
        "repo": f"{OWNER}/{REPO}",
        "instance_id": f"{OWNER}__{REPO}.ac595220.{pr_number}",
        "base_commit": COMMIT,
        "pull_number": pr_number,
        "merge_commit": merge_commit_sha,
        "problem_statement": pr_details["title"],
        "patch": diff,
        "test_files": pr_data["test_files"],
        "code_files": pr_data["code_files"],
    }

    print(f"  ✅ Created instance {instance['instance_id']}")
    return instance


def main():
    # Load PR list
    pr_list_file = Path("logs/prs/tinacms/pr_list.json")
    with open(pr_list_file) as f:
        pr_list = json.load(f)

    print(f"Creating instances for {len(pr_list)} PRs...\n")

    # Create instances
    instances = []
    for pr_data in pr_list:
        instance = create_instance(pr_data)
        if instance:
            instances.append(instance)

    print(f"\n{'='*60}")
    print(f"Created {len(instances)} instances")
    print(f"{'='*60}")

    # Save to JSONL file
    output_dir = Path("logs/tasks")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "tinacms-insts.jsonl"
    with open(output_file, "w") as f:
        for instance in instances:
            f.write(json.dumps(instance) + "\n")

    print(f"Saved to: {output_file}")
    print(f"\nNext step:")
    print(f"  python -m swesmith.bug_gen.mirror.generate_ts logs/tasks/tinacms-insts.jsonl --model anthropic/claude-opus-4-5-20251101")


if __name__ == "__main__":
    main()
