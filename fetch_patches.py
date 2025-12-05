#!/usr/bin/env python3
"""Fetch PR patches from GitHub and enrich instance files."""

import json
import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    print("ERROR: GITHUB_TOKEN not set in environment")
    sys.exit(1)

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3.diff",
}

def fetch_pr_patch(owner: str, repo: str, pull_number: int) -> str | None:
    """Fetch the patch/diff for a PR from GitHub."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"

    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            return response.text
        elif response.status_code == 403:
            print(f"  Rate limited, waiting 60s...")
            time.sleep(60)
            return fetch_pr_patch(owner, repo, pull_number)
        else:
            print(f"  Failed to fetch PR {pull_number}: {response.status_code}")
            return None
    except Exception as e:
        print(f"  Error fetching PR {pull_number}: {e}")
        return None


def enrich_instance_file(input_file: str, output_file: str = None):
    """Read instance file, fetch patches, and write enriched file."""
    if output_file is None:
        output_file = input_file.replace("-insts.jsonl", "-enriched.jsonl")

    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        print(f"Input file not found: {input_file}")
        return

    print(f"\nProcessing {input_file}...")

    instances = []
    with open(input_path, "r") as f:
        for line in f:
            if line.strip():
                instances.append(json.loads(line))

    print(f"  Found {len(instances)} instances")

    enriched_count = 0
    with open(output_path, "w") as f:
        for i, inst in enumerate(instances):
            # Skip if already has patch
            if "patch" in inst and inst["patch"]:
                f.write(json.dumps(inst) + "\n")
                enriched_count += 1
                continue

            # Parse repo owner/name
            repo_full = inst.get("repo", "")
            if "/" in repo_full:
                owner, repo = repo_full.split("/", 1)
            else:
                print(f"  Skipping {inst.get('instance_id')}: invalid repo format")
                continue

            pull_number = inst.get("pull_number")
            if not pull_number:
                print(f"  Skipping {inst.get('instance_id')}: no pull_number")
                continue

            print(f"  [{i+1}/{len(instances)}] Fetching PR #{pull_number} from {repo_full}...")

            patch = fetch_pr_patch(owner, repo, pull_number)
            if patch:
                inst["patch"] = patch
                enriched_count += 1
            else:
                inst["patch"] = ""  # Empty patch will be skipped by generate_ts.py

            f.write(json.dumps(inst) + "\n")

            # Rate limiting - be gentle with GitHub API
            time.sleep(0.5)

    print(f"  Enriched {enriched_count}/{len(instances)} instances")
    print(f"  Output: {output_path}")
    return output_path


def main():
    # Find all instance files
    tasks_dir = Path("logs/tasks")
    if not tasks_dir.exists():
        print("logs/tasks directory not found")
        return

    # Process specific repos (the 7 TypeScript repos with mirrors)
    target_repos = [
        "cal.com",
        "twenty",
        "posthog",
        "appsmith",
        "hoppscotch",
        "dub",
        "medusa",
    ]

    for repo in target_repos:
        input_file = tasks_dir / f"{repo}-insts.jsonl"
        if input_file.exists():
            enrich_instance_file(str(input_file))
        else:
            print(f"Skipping {repo}: no instance file found at {input_file}")


if __name__ == "__main__":
    main()
