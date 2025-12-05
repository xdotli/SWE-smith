#!/usr/bin/env python3
"""Direct PR collection for strapi without multiprocessing"""

import os
from pathlib import Path
from swesmith.bug_gen.mirror.collect.print_pulls import main as print_pulls
from swesmith.bug_gen.mirror.collect.build_dataset import main as build_dataset
from dotenv import load_dotenv

load_dotenv()

# Get GitHub token
token = os.getenv("GITHUB_TOKEN") or os.popen("gh auth token").read().strip()
if not token:
    raise Exception("No GitHub token found")

# Paths
path_prs = Path("logs/prs")
path_tasks = Path("logs/tasks")
path_prs.mkdir(exist_ok=True, parents=True)
path_tasks.mkdir(exist_ok=True, parents=True)

# Repo
repo = "strapi/strapi"
repo_name = repo.split("/")[1]

# Collect PRs
path_pr = path_prs / f"{repo_name}-prs.jsonl"
if not path_pr.exists():
    print(f"Collecting PRs from {repo}...")
    print_pulls(repo, str(path_pr), token, max_pulls=50)
    print(f"â Saved PR data to {path_pr}")
else:
    print(f"ð PR data already exists at {path_pr}")

# Build task instances
path_task = path_tasks / f"{repo_name}-insts.jsonl"
if not path_task.exists():
    print(f"Building task instances from {path_pr}...")
    build_dataset(str(path_pr), str(path_task), token)
    print(f"â Saved task instance data to {path_task}")
else:
    print(f"ð Task instance data already exists at {path_task}")

print(f"\nâ Collection complete!")
print(f"PRs: {path_pr}")
print(f"Tasks: {path_task}")
