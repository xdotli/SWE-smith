#!/usr/bin/env python3
"""
Export reversed diffs to SWE-smith native format.

Usage: python scripts/export_task_instances.py
"""

import json
from pathlib import Path
from datetime import datetime

# Paths
REVERSED_DIR = Path("logs/reversed")
OUTPUT_FILE = Path("logs/task_insts/unkeyed__unkey.task_instances.json")
EXAMPLES_DIR = Path(__file__).parent.parent.parent / "docs" / "data" / "examples"


def generate_problem_statement(instance_id: str, pr_data: dict, files: list[str]) -> str:
    """Generate a problem statement for the task instance."""
    # This is a simplified problem statement generator
    # In a real pipeline, you'd use an LLM to generate more detailed descriptions

    files_str = "\n".join(f"- `{f}`" for f in files)

    return f"""## Bug Report

The codebase has a regression in the following files:

{files_str}

The issue manifests as broken functionality that was previously working.
Tests are now failing due to this regression.

### Expected Behavior
The code should function as it did before the regression was introduced.

### Actual Behavior
The code has been modified in a way that breaks existing functionality.

### Steps to Reproduce
1. Run the test suite
2. Observe failing tests

### Environment
- Repository: unkeyed/unkey
- Instance ID: {instance_id}
"""


def create_reversed_patch(result: dict) -> str:
    """Create a unified diff that represents the reversed (broken) state."""
    patch_lines = []

    for file_path, file_data in result.get('reversed_files', {}).items():
        original_diff = file_data.get('original_diff', '')

        # The reversed code IS the buggy state
        # We want to show what was changed to introduce the bug
        # This is the inverse of the original PR

        # Parse the original diff and invert it
        inverted_lines = []
        for line in original_diff.split('\n'):
            if line.startswith('+++'):
                inverted_lines.append(line.replace('+++', '---'))
            elif line.startswith('---'):
                inverted_lines.append(line.replace('---', '+++'))
            elif line.startswith('+') and not line.startswith('+++'):
                inverted_lines.append('-' + line[1:])
            elif line.startswith('-') and not line.startswith('---'):
                inverted_lines.append('+' + line[1:])
            else:
                inverted_lines.append(line)

        patch_lines.append('\n'.join(inverted_lines))

    return '\n'.join(patch_lines)


def main():
    # Load summary
    summary_file = REVERSED_DIR / "summary.json"
    if not summary_file.exists():
        print(f"Error: {summary_file} not found. Run reverse_diffs.py first.")
        return

    with open(summary_file) as f:
        summary = json.load(f)

    task_instances = []

    for result in summary['results']:
        if result['status'] != 'success':
            continue

        instance_id = result['instance_id']

        # Load full result
        result_file = REVERSED_DIR / instance_id / "result.json"
        if not result_file.exists():
            continue

        with open(result_file) as f:
            full_result = json.load(f)

        # Get list of files
        files = list(full_result.get('reversed_files', {}).keys())

        # Create the reversed patch (the buggy state)
        reversed_patch = create_reversed_patch(full_result)

        # Generate problem statement
        problem_statement = generate_problem_statement(instance_id, full_result, files)

        task_instance = {
            "instance_id": f"{instance_id}.pr_mirror",
            "repo": full_result['repo'],
            "repo_name": f"https://github.com/{full_result['repo']}",
            "base_commit": full_result['base_commit'],
            "patch": reversed_patch,
            "problem_statement": problem_statement,
            "FAIL_TO_PASS": [],  # Would need test validation to fill these
            "PASS_TO_PASS": [],  # Would need test validation to fill these
            "created_at": summary['timestamp'],
            "generation_cost": full_result.get('total_cost', 0),
            "files_changed": files,
        }

        task_instances.append(task_instance)
        print(f"Created task instance: {instance_id}")

    # Save to task_insts directory
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(task_instances, f, indent=2)
    print(f"\nSaved {len(task_instances)} task instances to {OUTPUT_FILE}")

    # Also save to docs/data/examples in a simpler format for the landing page
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    examples_summary = {
        "generated_at": summary['timestamp'],
        "method": "PR Mirroring",
        "model": summary['model'],
        "total_cost": summary['total_cost'],
        "total_instances": len(task_instances),
        "repository": "unkeyed/unkey",
        "instances": []
    }

    for inst in task_instances:
        examples_summary["instances"].append({
            "instance_id": inst["instance_id"],
            "files_changed": inst["files_changed"],
            "generation_cost": inst["generation_cost"]
        })

    examples_file = EXAMPLES_DIR / "generated_instances.json"
    with open(examples_file, 'w') as f:
        json.dump(examples_summary, f, indent=2)
    print(f"Saved examples summary to {examples_file}")


if __name__ == '__main__':
    main()
