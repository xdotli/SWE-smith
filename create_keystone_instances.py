#!/usr/bin/env python3
"""
Create task instances for Keystone PRs using build_dataset format.
"""

import json
import subprocess
from pathlib import Path
from swesmith.profiles.typescript import KeystonejsKeystone052f5b1b

def main():
    profile = KeystonejsKeystone052f5b1b()

    # PR numbers we collected
    pr_numbers = [9737, 9730, 9700, 9691, 9656, 9673]

    print(f"Creating instances for {len(pr_numbers)} Keystone PRs...")

    instances = []
    for pr_num in pr_numbers:
        instance = {
            "instance_id": f"{profile.owner}__{profile.repo}.pr_mirror.{pr_num}",
            "repo": f"{profile.owner}/{profile.repo}",
            "pull_number": pr_num,
            "base_commit": profile.commit,  # Use the profile's fixed commit
        }
        instances.append(instance)

    # Save instances
    output_dir = Path("logs/tasks")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "keystone-insts.jsonl"

    with open(output_file, "w") as f:
        for inst in instances:
            f.write(json.dumps(inst) + "\n")

    print(f"✓ Saved {len(instances)} instances to {output_file}")
    print(f"\nNext step:")
    print(f"python -m swesmith.bug_gen.mirror.generate_ts {output_file} --model anthropic/claude-opus-4-5-20251101")

if __name__ == "__main__":
    main()
