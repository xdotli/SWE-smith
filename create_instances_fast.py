#!/usr/bin/env python3
"""
Fast instance creation from filtered PRs.
Creates task instances directly from collected PR metadata without fetching diffs.
The generate_ts.py script will fetch diffs when running PR mirroring.
"""
import json
import os
from pathlib import Path

# Repository mappings (owner/repo)
REPO_MAPPINGS = {
    "excalidraw": "excalidraw/excalidraw",
    "tldraw": "tldraw/tldraw",
    "medusa": "medusajs/medusa",
    "payload": "payloadcms/payload",
    "hoppscotch": "hoppscotch/hoppscotch",
    "strapi": "strapi/strapi",
    "appsmith": "appsmithorg/appsmith",
    "posthog": "PostHog/posthog",
    "tooljet": "ToolJet/ToolJet",
}

def create_instances_from_file(json_path: Path, repo_key: str) -> list[dict]:
    """Create task instances from a filtered PRs JSON file."""
    instances = []

    if not json_path.exists():
        return instances

    with open(json_path) as f:
        prs = json.load(f)

    if not prs:
        return instances

    repo_full = REPO_MAPPINGS.get(repo_key)
    if not repo_full:
        print(f"  Unknown repo key: {repo_key}")
        return instances

    owner, repo = repo_full.split("/")

    for pr in prs:
        pr_num = pr.get("number")
        if not pr_num:
            continue

        # Create a placeholder instance - patch will be fetched by generate_ts.py
        instance = {
            "repo": repo_full,
            "pull_number": pr_num,
            "instance_id": f"{owner}__{repo}-{pr_num}",
            "issue_numbers": [],
            "base_commit": pr.get("base_sha", pr.get("merge_commit_sha", "")),
            "patch": "",  # Will be populated by PR mirroring
            "test_patch": "",
            "problem_statement": pr.get("title", ""),
            "hints_text": "",
            "created_at": pr.get("merged_at", ""),
            "version": "0.0.0",
            "FAIL_TO_PASS": [],
            "PASS_TO_PASS": [],
            "environment_setup_commit": pr.get("base_sha", ""),
            # Extra metadata for generate_ts.py
            "test_files": pr.get("test_files", []),
            "code_files": pr.get("code_files", []),
            "total_changes": pr.get("total_changes", 0),
        }

        instances.append(instance)

    return instances

def main():
    prs_dir = Path(__file__).parent / "logs" / "prs"
    output_dir = Path(__file__).parent / "logs" / "tasks"
    output_dir.mkdir(parents=True, exist_ok=True)

    all_instances = []
    repo_stats = {}

    # Process each repo - prioritize by PR count
    for repo_key in REPO_MAPPINGS.keys():
        repo_dir = prs_dir / repo_key

        # Try different file patterns (prefer relaxed for posthog)
        for pattern in ["filtered_prs_relaxed.json", "filtered_prs.json"]:
            json_path = repo_dir / pattern
            if json_path.exists():
                instances = create_instances_from_file(json_path, repo_key)

                if instances:
                    all_instances.extend(instances)
                    repo_stats[repo_key] = len(instances)

                    # Save per-repo instances
                    repo_output = output_dir / f"{repo_key}-insts.jsonl"
                    with open(repo_output, "w") as f:
                        for inst in instances:
                            f.write(json.dumps(inst) + "\n")
                    print(f"  {repo_key}: {len(instances)} instances -> {repo_output}")
                break  # Use first matching file

    # Save combined instances
    combined_output = output_dir / "all-insts.jsonl"
    with open(combined_output, "w") as f:
        for inst in all_instances:
            f.write(json.dumps(inst) + "\n")

    print(f"\n=== SUMMARY ===")
    print(f"Total instances created: {len(all_instances)}")
    print(f"Combined file: {combined_output}")

    # Print per-repo breakdown
    print("\nPer-repo breakdown:")
    for repo, count in sorted(repo_stats.items(), key=lambda x: -x[1]):
        print(f"  {repo}: {count}")

if __name__ == "__main__":
    main()
