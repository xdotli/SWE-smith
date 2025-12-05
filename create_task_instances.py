#!/usr/bin/env python3
"""
Create task instances from filtered PR data.
"""

import json
from pathlib import Path


def create_task_instances(filtered_pr_file, output_file, profile_commit):
    """Create task instances in the format expected by PR mirroring."""
    with open(filtered_pr_file, "r") as f:
        prs = [json.loads(line) for line in f]

    print(f"Creating task instances from {len(prs)} PRs...")

    instances = []
    for pr in prs:
        # Extract repo info from URL
        # Example: https://github.com/medusajs/medusa/pull/14220
        url = pr.get("url") or pr.get("html_url")
        url_parts = url.split("/")
        owner = url_parts[3]
        repo = url_parts[4]

        # Create instance ID following the pattern: owner__repo.commit.pr_number
        instance_id = f"{owner}__{repo}.{profile_commit}.{pr['number']}"

        instance = {
            "instance_id": instance_id,
            "repo": f"{owner}/{repo}",
            "base_commit": pr["base_commit"],
            "head_commit": pr["head_commit"],
            "pr_number": pr["number"],
            "title": pr["title"],
            "merged_at": pr["merged_at"],
            "html_url": url,
            "test_files": pr["test_files"],
            "code_files": pr["code_files"],
            "total_changes": pr["total_changes"],
            "num_files": len(pr.get("files", []))
        }

        instances.append(instance)

    # Save to JSONL
    with open(output_file, "w") as f:
        for inst in instances:
            f.write(json.dumps(inst) + "\n")

    print(f"Created {len(instances)} task instances")
    print(f"Saved to {output_file}")


def main():
    tasks_dir = Path("logs/tasks")
    tasks_dir.mkdir(parents=True, exist_ok=True)

    prs_dir = Path("logs/prs")

    # Define all repos with their profile commits
    repos = [
        ("cal.com", "main"),
        ("twenty", "main"),
        ("posthog", "main"),
        ("nocodb", "main"),
        ("appsmith", "main"),
        ("dub", "main"),
        ("hoppscotch", "main"),
        ("medusa", "56ed9cf9"),
        ("payload", "053256d5"),
    ]

    created_files = []

    for repo_name, profile_commit in repos:
        pr_file = prs_dir / f"{repo_name}-filtered-prs.jsonl"
        if pr_file.exists():
            output_file = tasks_dir / f"{repo_name}-insts.jsonl"
            create_task_instances(pr_file, output_file, profile_commit)
            created_files.append((repo_name, output_file))
            print()

    print("\n" + "="*70)
    print("TASK INSTANCE CREATION SUMMARY")
    print("="*70)

    total_instances = 0
    for repo_name, output_file in created_files:
        if output_file.exists():
            with open(output_file, "r") as f:
                count = len(f.readlines())
            total_instances += count
            print(f"  {repo_name}: {count} instances -> {output_file}")

    print(f"\nTotal task instances created: {total_instances}")
    print("="*70)


if __name__ == "__main__":
    main()
