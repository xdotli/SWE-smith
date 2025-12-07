#!/usr/bin/env python3
"""Collect PRs from trigger.dev repository for PR Mirroring."""

import json
import os
import subprocess
from pathlib import Path
from datetime import datetime

def run_gh_command(cmd):
    """Run gh CLI command and return output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    return result.stdout.strip()

def get_pr_files(pr_number):
    """Get list of files changed in a PR."""
    cmd = f"gh pr view {pr_number} --repo triggerdotdev/trigger.dev --json files --jq '.files[].path'"
    output = run_gh_command(cmd)
    if output:
        return output.split('\n')
    return []

def is_good_pr_candidate(pr_number, files):
    """Check if PR is a good candidate for mirroring."""
    # Must have .test.ts/.test.tsx files (not just .snap)
    test_files = [f for f in files if '.test.' in f and '.snap' not in f]

    # Must have code files (.ts/.tsx)
    code_files = [f for f in files if f.endswith(('.ts', '.tsx')) and '.test.' not in f and '.spec.' not in f]

    # Filter criteria
    has_real_tests = len(test_files) > 0
    has_code_changes = len(code_files) > 0
    is_focused = len(files) <= 20  # Not too many files

    if has_real_tests and has_code_changes and is_focused:
        print(f"  ✓ PR #{pr_number}: {len(test_files)} test files, {len(code_files)} code files")
        return True
    else:
        reason = []
        if not has_real_tests:
            reason.append("no test files")
        if not has_code_changes:
            reason.append("no code files")
        if not is_focused:
            reason.append(f"too many files ({len(files)})")
        print(f"  ✗ PR #{pr_number}: {', '.join(reason)}")
        return False

def collect_prs(max_prs=50, limit=10):
    """Collect merged PRs from trigger.dev."""
    print(f"Collecting up to {limit} good PRs from the last {max_prs} merged PRs...")

    # Get recent merged PRs
    cmd = f'gh pr list --repo triggerdotdev/trigger.dev --state merged --limit {max_prs} --json number,title,mergedAt,author'
    output = run_gh_command(cmd)

    if not output:
        print("Failed to fetch PRs")
        return []

    prs = json.loads(output)
    print(f"Found {len(prs)} merged PRs")

    good_prs = []
    for pr in prs:
        if len(good_prs) >= limit:
            break

        pr_number = pr['number']
        files = get_pr_files(pr_number)

        if is_good_pr_candidate(pr_number, files):
            # Get PR diff size
            cmd = f"gh pr diff {pr_number} --repo triggerdotdev/trigger.dev | wc -c"
            diff_size = int(run_gh_command(cmd) or 0)

            good_prs.append({
                'number': pr_number,
                'title': pr['title'],
                'mergedAt': pr['mergedAt'],
                'author': pr['author']['login'] if pr['author'] else 'unknown',
                'files': files,
                'diff_size': diff_size
            })

    print(f"\nCollected {len(good_prs)} good PR candidates")
    return good_prs

def create_instances_file(prs):
    """Create JSONL file with PR instances."""
    output_dir = Path("logs/tasks")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "triggerdev-insts.jsonl"

    with open(output_file, 'w') as f:
        for pr in prs:
            instance = {
                'repo': 'triggerdotdev/trigger.dev',
                'pr_number': pr['number'],
                'title': pr['title'],
                'merged_at': pr['mergedAt'],
                'author': pr['author']
            }
            f.write(json.dumps(instance) + '\n')

    print(f"\n✓ Created instances file: {output_file}")
    print(f"  Total instances: {len(prs)}")
    return output_file

def main():
    # Collect PRs
    prs = collect_prs(max_prs=100, limit=15)

    if not prs:
        print("No good PR candidates found")
        return

    # Create instances file
    instances_file = create_instances_file(prs)

    # Print summary
    print("\n" + "="*60)
    print("COLLECTION SUMMARY")
    print("="*60)
    print(f"Repository: triggerdotdev/trigger.dev")
    print(f"Good PRs collected: {len(prs)}")
    print(f"Instances file: {instances_file}")
    print("\nTop PRs:")
    for i, pr in enumerate(prs[:5], 1):
        print(f"  {i}. PR #{pr['number']}: {pr['title'][:60]}")
        print(f"     Files: {len(pr['files'])}, Diff size: {pr['diff_size']} bytes")

    print("\nNext steps:")
    print(f"1. Run: python -m swesmith.bug_gen.mirror.generate_ts {instances_file} --model anthropic/claude-opus-4-5-20251101")
    print(f"2. Validate: python -m swesmith.harness.valid logs/task_insts/triggerdev_patches.json -w 1")

if __name__ == "__main__":
    main()
