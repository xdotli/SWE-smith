#!/usr/bin/env python3
"""
Create task instance files from collected PRs.
Format matches SWE-smith's expected input for PR mirroring.
"""
import json
from pathlib import Path
from swesmith.profiles.python import (
    ClickFde47b4b4,
    Marshmallow9716fc62,
    Sympy2ab64612,
    MypyE93f06ce,
    AstroidB114f6b5,
)

PROFILES = {
    'click': ClickFde47b4b4,
    'marshmallow': Marshmallow9716fc62,
    'sympy': Sympy2ab64612,
    'mypy': MypyE93f06ce,
    'astroid': AstroidB114f6b5,
}

def create_instances(repo_name: str, pr_numbers: list):
    """Create instance file for a repo."""
    profile_cls = PROFILES[repo_name]
    profile = profile_cls()

    instances = []
    for pr_num in pr_numbers:
        instance = {
            'repo': f"{profile.owner}__{profile.repo}.{profile.commit[:8]}",
            'pr_number': pr_num,
            'base_commit': profile.commit,
        }
        instances.append(instance)

    return instances

def main():
    prs_dir = Path('logs/prs/python')
    output_dir = Path('logs/tasks')
    output_dir.mkdir(parents=True, exist_ok=True)

    total_instances = 0

    for repo_name, profile_cls in PROFILES.items():
        pr_file = prs_dir / f"{repo_name}-prs.json"
        if not pr_file.exists():
            print(f"Skipping {repo_name}: no PR file found")
            continue

        with open(pr_file) as f:
            prs = json.load(f)

        pr_numbers = [pr['number'] for pr in prs]
        instances = create_instances(repo_name, pr_numbers)

        output_file = output_dir / f"{repo_name}-insts.jsonl"
        with open(output_file, 'w') as f:
            for inst in instances:
                f.write(json.dumps(inst) + '\n')

        print(f"{repo_name}: Created {len(instances)} instances -> {output_file}")
        total_instances += len(instances)

    print(f"\nTotal instances created: {total_instances}")
    print(f"\nNext step: Run PR mirroring with:")
    print("  python -m swesmith.bug_gen.mirror.generate logs/tasks/REPO-insts.jsonl --model anthropic/claude-opus-4-5-20251101")

if __name__ == '__main__':
    main()
