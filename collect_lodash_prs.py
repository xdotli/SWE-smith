#!/usr/bin/env python3
"""Collect PRs from lodash repository for PR mirroring."""

import os
import sys
from swesmith.bug_gen.mirror.collect import collect_prs_for_repo

def main():
    # Set up paths
    path_prs = "logs/prs"
    path_tasks = "logs/tasks"

    # Ensure directories exist
    os.makedirs(path_prs, exist_ok=True)
    os.makedirs(path_tasks, exist_ok=True)

    # Get GitHub token from gh CLI
    import subprocess
    try:
        github_token = subprocess.check_output(['gh', 'auth', 'token']).decode().strip()
        os.environ['GITHUB_TOKENS'] = github_token
    except Exception as e:
        print(f"Error getting GitHub token: {e}")
        sys.exit(1)

    # Collect PRs for lodash
    print("Collecting PRs from lodash/lodash...")
    result = collect_prs_for_repo(
        repo="lodash/lodash",
        path_prs=path_prs,
        path_tasks=path_tasks,
        max_pulls=100
    )

    print(f"\nCollection complete!")
    print(f"PR data saved to: {path_prs}")
    print(f"Task data saved to: {path_tasks}")

    return result

if __name__ == "__main__":
    main()
