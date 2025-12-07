#!/usr/bin/env python3
"""
Add patch data to trigger.dev instances by fetching PR diffs from GitHub.
"""

import json
import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3.diff"
}

def fetch_pr_diff(owner: str, repo: str, pr_number: int) -> str:
    """Fetch the diff for a PR."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

    # First get PR data to check base/head commits
    response = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if response.status_code != 200:
        print(f"Error fetching PR #{pr_number}: {response.status_code}")
        return None

    # Now get the diff
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Error fetching diff for PR #{pr_number}: {response.status_code}")
        return None

    return response.text


def main():
    input_file = Path("logs/tasks/triggerdev-insts.jsonl")
    output_file = Path("logs/tasks/triggerdev-insts-with-patches.jsonl")

    print(f"Reading instances from {input_file}...")

    instances = []
    with open(input_file, 'r') as f:
        for line in f:
            instances.append(json.loads(line))

    print(f"Found {len(instances)} instances")
    print("\nFetching patches from GitHub...")

    completed = 0
    with open(output_file, 'w') as f:
        for i, inst in enumerate(instances, 1):
            pr_number = inst['pull_number']
            repo = inst['repo']
            owner, repo_name = repo.split('/')

            print(f"  [{i}/{len(instances)}] PR #{pr_number}...", end=" ")

            # Fetch the diff
            patch = fetch_pr_diff(owner, repo_name, pr_number)

            if patch:
                # Add patch to instance
                inst['patch'] = patch
                inst['test_patch'] = ""  # Empty test patch for now
                inst['problem_statement'] = ""
                inst['hints_text'] = ""

                # Write to output
                f.write(json.dumps(inst) + '\n')
                completed += 1
                print(f"✓ ({len(patch)} chars)")
            else:
                print("✗ (failed to fetch)")

    print(f"\n✓ Saved {completed} instances with patches to {output_file}")
    print(f"\nNext step:")
    print(f"  python -m swesmith.bug_gen.mirror.generate_ts {output_file} --model anthropic/claude-opus-4-5-20251101")


if __name__ == "__main__":
    main()
