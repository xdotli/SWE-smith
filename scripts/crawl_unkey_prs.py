#!/usr/bin/env python3
"""
Crawl merged PRs from unkeyed/unkey and save them in SWE-smith format.

Usage: python scripts/crawl_unkey_prs.py
"""

import json
import subprocess
import sys
from pathlib import Path

# Output file
OUTPUT_DIR = Path(__file__).parent.parent / "logs" / "prs" / "unkey"
OUTPUT_FILE = OUTPUT_DIR / "instances.jsonl"

# PR selection criteria
MIN_TS_FILES = 1
MAX_TS_FILES = 6
MIN_ADDITIONS = 5
MAX_ADDITIONS = 250
MAX_CHANGED_FILES = 10


def run_gh_command(args: list[str]) -> str:
    """Run a gh command and return output."""
    result = subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout


def get_merged_prs(repo: str, limit: int = 100) -> list[dict]:
    """Get merged PRs from a repo."""
    jq_filter = """
    [.[] | . as $pr |
     [.files[].path | select(test("\\\\.(ts|tsx)$"))] as $tsFiles |
     select(($tsFiles | length) >= {min_ts} and ($tsFiles | length) <= {max_ts}) |
     select(.additions >= {min_add} and .additions <= {max_add}) |
     select(.changedFiles <= {max_files}) |
     {{
       number: $pr.number,
       title: $pr.title,
       additions: $pr.additions,
       deletions: $pr.deletions,
       changedFiles: $pr.changedFiles,
       mergeCommit: $pr.mergeCommit.oid,
       tsFiles: $tsFiles
     }}
    ]
    """.format(
        min_ts=MIN_TS_FILES,
        max_ts=MAX_TS_FILES,
        min_add=MIN_ADDITIONS,
        max_add=MAX_ADDITIONS,
        max_files=MAX_CHANGED_FILES
    ).replace('\n', ' ')

    output = run_gh_command([
        "pr", "list",
        "--repo", repo,
        "--state", "merged",
        "--limit", str(limit),
        "--json", "number,title,additions,deletions,changedFiles,files,mergeCommit",
        "--jq", jq_filter
    ])
    return json.loads(output)


def get_pr_diff(repo: str, pr_number: int) -> str:
    """Get the diff for a PR."""
    return run_gh_command(["pr", "diff", str(pr_number), "--repo", repo])


def get_pr_base_commit(repo: str, pr_number: int) -> str:
    """Get the base commit (parent of merge commit) for a PR."""
    output = run_gh_command([
        "pr", "view", str(pr_number),
        "--repo", repo,
        "--json", "mergeCommit",
        "--jq", ".mergeCommit.parents[0].oid"
    ])
    return output.strip()


def main():
    repo = "unkeyed/unkey"

    print(f"Crawling PRs from {repo}...")
    prs = get_merged_prs(repo, limit=100)
    print(f"Found {len(prs)} candidate PRs")

    # Take first 20
    prs = prs[:20]

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    instances = []
    for pr in prs:
        pr_num = pr["number"]
        print(f"Processing PR #{pr_num}: {pr['title'][:50]}...")

        try:
            # Get diff
            diff = get_pr_diff(repo, pr_num)

            # Get base commit (before the merge)
            base_commit = get_pr_base_commit(repo, pr_num)

            instance = {
                "instance_id": f"unkeyed__unkey-{pr_num}",
                "repo": repo,
                "pull_number": pr_num,
                "base_commit": base_commit,
                "patch": diff
            }
            instances.append(instance)
            print(f"  â Added ({len(diff)} bytes, base: {base_commit[:8]})")

        except Exception as e:
            print(f"  â Failed: {e}")
            continue

    # Write to JSONL
    with open(OUTPUT_FILE, "w") as f:
        for inst in instances:
            f.write(json.dumps(inst) + "\n")

    print(f"\nWrote {len(instances)} instances to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
