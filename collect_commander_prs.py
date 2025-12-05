#!/usr/bin/env python3
"""Collect PRs for tj/commander.js without multiprocessing"""

import os
from pathlib import Path
from dotenv import load_dotenv
from swesmith.bug_gen.mirror.collect.print_pulls import main as print_pulls
from swesmith.bug_gen.mirror.collect.build_dataset import main as build_dataset

load_dotenv()

def main():
    repo = "tj/commander.js"
    repo_name = "commander.js"
    path_prs = "logs/prs"
    path_tasks = "logs/tasks"
    max_pulls = 30

    # Create directories
    Path(path_prs).mkdir(exist_ok=True, parents=True)
    Path(path_tasks).mkdir(exist_ok=True, parents=True)

    # Get GitHub token
    token = os.getenv("GITHUB_TOKENS")
    if not token:
        import subprocess
        token = subprocess.check_output(["gh", "auth", "token"]).decode().strip()

    print(f"Collecting PRs for {repo}...")

    # Collect PRs
    path_pr = os.path.join(path_prs, f"{repo_name}-prs.jsonl")
    if not os.path.exists(path_pr):
        print(f"Creating PR data at {path_pr}...")
        print_pulls(repo, path_pr, token, max_pulls=max_pulls, cutoff_date=None)
        print(f"â Successfully saved PR data to {path_pr}")
    else:
        print(f"ð PR data already exists at {path_pr}")

    # Build task instances
    path_task = os.path.join(path_tasks, f"{repo_name}-insts.jsonl")
    if not os.path.exists(path_task):
        print(f"Creating task instances at {path_task}...")
        build_dataset(path_pr, path_task, token)
        print(f"â Successfully saved task instances to {path_task}")
    else:
        print(f"ð Task instances already exist at {path_task}")

    # Count results
    import json
    with open(path_task) as f:
        instances = [json.loads(line) for line in f]
    print(f"\nð Total task instances collected: {len(instances)}")

if __name__ == "__main__":
    main()
