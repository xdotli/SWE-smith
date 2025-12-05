#!/usr/bin/env python3
"""
Fetch patches from GitHub and run PR mirroring.
This script:
1. Reads task instances from JSONL files
2. Fetches patches from GitHub API
3. Runs LLM reversal to create bug patches
"""
import json
import os
import requests
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

# Load GitHub token
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3.diff"
} if GITHUB_TOKEN else {"Accept": "application/vnd.github.v3.diff"}


def fetch_pr_patch(owner: str, repo: str, pr_number: int, max_retries: int = 3) -> str | None:
    """Fetch the patch for a PR from GitHub API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.text
            elif resp.status_code == 403:
                # Rate limited
                reset_time = int(resp.headers.get('X-RateLimit-Reset', time.time() + 60))
                wait_time = max(0, reset_time - time.time()) + 5
                print(f"  Rate limited, waiting {wait_time:.0f}s...")
                time.sleep(min(wait_time, 60))
            elif resp.status_code == 404:
                print(f"  PR #{pr_number} not found")
                return None
            else:
                print(f"  HTTP {resp.status_code} for PR #{pr_number}")
                time.sleep(2 ** attempt)
        except Exception as e:
            print(f"  Error fetching PR #{pr_number}: {e}")
            time.sleep(2 ** attempt)

    return None


def process_instance(inst: dict) -> dict | None:
    """Fetch patch for a single instance."""
    repo_full = inst.get("repo", "")
    pr_num = inst.get("pull_number")

    if not repo_full or not pr_num:
        return None

    owner, repo = repo_full.split("/")

    patch = fetch_pr_patch(owner, repo, pr_num)
    if not patch:
        return None

    inst["patch"] = patch
    return inst


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="logs/tasks/all-insts.jsonl",
                       help="Input JSONL file with task instances")
    parser.add_argument("--output", type=str, default="logs/tasks/all-insts-with-patches.jsonl",
                       help="Output JSONL file with patches")
    parser.add_argument("--workers", type=int, default=5,
                       help="Number of parallel workers")
    parser.add_argument("--limit", type=int, default=0,
                       help="Limit number of instances to process (0=all)")
    args = parser.parse_args()

    # Load instances
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return

    instances = []
    with open(input_path) as f:
        for line in f:
            if line.strip():
                instances.append(json.loads(line))

    if args.limit > 0:
        instances = instances[:args.limit]

    print(f"Processing {len(instances)} instances...")

    # Process instances
    successful = []
    failed = 0

    for i, inst in enumerate(instances):
        print(f"[{i+1}/{len(instances)}] {inst.get('instance_id', 'unknown')}...", end=" ")
        result = process_instance(inst)
        if result:
            successful.append(result)
            print(f"OK ({len(result.get('patch', ''))} bytes)")
        else:
            failed += 1
            print("FAILED")

        # Small delay between requests
        time.sleep(0.3)

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        for inst in successful:
            f.write(json.dumps(inst) + "\n")

    print(f"\n=== SUMMARY ===")
    print(f"Total: {len(instances)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {failed}")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
