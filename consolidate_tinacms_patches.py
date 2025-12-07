#!/usr/bin/env python3
"""
Consolidate tinacms bug patches into a JSON file for validation.
"""

import json
from pathlib import Path

def main():
    base_dir = Path("logs/bug_gen/tinacms__tinacms.ac595220/pr_mirror")

    instances = []

    for instance_dir in base_dir.glob("tinacms__tinacms.ac595220.*"):
        instance_id = instance_dir.name
        bug_file = instance_dir / f"bug__pr_{instance_id.split('.')[-1]}.diff"
        metadata_file = instance_dir / f"metadata__pr_{instance_id.split('.')[-1]}.json"

        if bug_file.exists() and metadata_file.exists():
            # Load metadata
            with open(metadata_file) as f:
                metadata = json.load(f)

            # Load bug patch
            with open(bug_file) as f:
                bug_patch = f.read()

            # Create instance entry
            instance = {
                "instance_id": instance_id,
                "repo": "tinacms__tinacms.ac595220",  # Use repo_name, not owner/repo
                "base_commit": "ac59522053c71c713057c4c2b6ce610617bce85e",
                "patch": bug_patch,
                "problem_statement": metadata.get("problem_statement", ""),
                "FAIL_TO_PASS": "[]",
                "PASS_TO_PASS": "[]",
            }

            instances.append(instance)
            print(f"✅ Added {instance_id}")

    # Save to JSON file
    output_file = Path("logs/task_insts/tinacms_patches.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(instances, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Consolidated {len(instances)} instances")
    print(f"Saved to: {output_file}")
    print(f"\nNext step:")
    print(f"  python -m swesmith.harness.valid logs/task_insts/tinacms_patches.json -w 1")

if __name__ == "__main__":
    main()
