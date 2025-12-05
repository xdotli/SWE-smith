#!/usr/bin/env python3
"""Collect PRs from zod repository for PR mirroring."""

import os
import sys
import subprocess
from pathlib import Path
from swesmith.bug_gen.mirror.collect.print_pulls import main as print_pulls
from swesmith.bug_gen.mirror.collect.build_dataset import main as build_dataset

def main():
    # Set up paths
    path_prs = "logs/prs"
    path_tasks = "logs/tasks"
    repo = "colinhacks/zod"
    repo_name = "zod"
    max_pulls = 100

    # Ensure directories exist
    Path(path_prs).mkdir(exist_ok=True, parents=True)
    Path(path_tasks).mkdir(exist_ok=True, parents=True)

    # Get GitHub token from gh CLI
    try:
        github_token = subprocess.check_output(['gh', 'auth', 'token']).decode().strip()
    except Exception as e:
        print(f"Error getting GitHub token: {e}")
        sys.exit(1)

    # Define output paths
    path_pr = os.path.join(path_prs, f"{repo_name}-prs.jsonl")
    path_task = os.path.join(path_tasks, f"{repo_name}-insts.jsonl")

    # Collect PRs
    print(f"Collecting PRs from {repo}...")
    if not os.path.exists(path_pr):
        print_pulls(repo, path_pr, github_token, max_pulls=max_pulls)
        print(f"✅ Successfully saved PR data to {path_pr}")
    else:
        print(f"📁 PR data already exists at {path_pr}, skipping...")

    # Build dataset
    print(f"\nBuilding task instance dataset...")
    if not os.path.exists(path_task):
        build_dataset(path_pr, path_task, github_token)
        print(f"✅ Successfully saved task instance data to {path_task}")
    else:
        print(f"📁 Task instance data already exists at {path_task}, skipping...")

    # Count PRs and task instances
    pr_count = 0
    task_count = 0

    if os.path.exists(path_pr):
        with open(path_pr, 'r') as f:
            pr_count = sum(1 for _ in f)

    if os.path.exists(path_task):
        with open(path_task, 'r') as f:
            task_count = sum(1 for _ in f)

    print(f"\n{'='*60}")
    print(f"Collection Summary:")
    print(f"  Repository: {repo}")
    print(f"  PRs collected: {pr_count}")
    print(f"  Task instances created: {task_count}")
    print(f"  PR data: {path_pr}")
    print(f"  Task data: {path_task}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
