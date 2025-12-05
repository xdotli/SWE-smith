"""Create task instances from collected hoppscotch PRs."""

import json
from pathlib import Path

def create_instances_from_prs(pr_file, output_file, repo_owner, repo_name):
    """Convert PR data to task instances."""
    instances = []

    with open(pr_file, "r") as f:
        for line in f:
            if not line.strip():
                continue
            pr = json.loads(line)

            # Create instance ID using format: owner__repo.commit.pr_number
            instance_id = f"{repo_owner}__{repo_name}.{pr['base_commit'][:8]}.{pr['number']}"

            instance = {
                "repo": f"{repo_owner}/{repo_name}",
                "instance_id": instance_id,
                "base_commit": pr["base_commit"],
                "head_commit": pr["head_commit"],
                "pr_number": pr["number"],
                "test_files": pr["test_files"],
                "problem_statement": pr["title"]
            }
            instances.append(instance)

    # Write as JSONL
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        for inst in instances:
            f.write(json.dumps(inst) + "\n")

    print(f"Created {len(instances)} instances in {output_file}")
    return instances

if __name__ == "__main__":
    # Create hoppscotch instances
    hoppscotch_insts = create_instances_from_prs(
        "logs/prs/hoppscotch-prs.jsonl",
        "logs/tasks/hoppscotch-insts.jsonl",
        "hoppscotch",
        "hoppscotch"
    )

    print("\nHoppscotch instances:")
    for inst in hoppscotch_insts:
        print(f"  - {inst['instance_id']}: {inst['problem_statement']}")
