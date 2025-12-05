#!/usr/bin/env python3
"""
Reverse diffs using LLM (Claude or GPT) for PR mirroring.

This is a simplified version of generate_ts.py that doesn't require
the full SWE-smith infrastructure (no Docker, no GitHub mirrors).

Usage: python scripts/reverse_diffs.py logs/prs/unkey/instances.jsonl --model anthropic/claude-opus-4-5-20251101
"""

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import litellm
try:
    import litellm
    from litellm import completion, completion_cost
    litellm.drop_params = True
    litellm.suppress_debug_info = True
except ImportError:
    print("Error: litellm not installed. Run: pip install litellm")
    exit(1)

# Output directory
OUTPUT_DIR = Path("logs/reversed")

# Prompts for TypeScript reversal
RECOVERY_PROMPT_TS = """You are given the source code of a file and a corresponding diff patch that reflects changes made to this file.
Your task is to rewrite the entire source code while reversing the changes indicated by the diff patch.
That is, if a line was added in the diff, remove it; if a line was removed, add it back; and if a line was modified, restore it to its previous state.

DO NOT MAKE ANY OTHER CHANGES TO THE SOURCE CODE. If a line was not explicitly added or removed in the diff, it should remain unchanged in the output.

INPUT:
<source_code>
Source code will be provided here.
</source_code>

<diff_patch>
Diff patch will be provided here.
</diff_patch>

OUTPUT:
The fully rewritten source code, after undoing all changes specified in the diff.
The output should be valid TypeScript/JavaScript code.
"""

DEMO_PROMPT_TS = """Demonstration:

INPUT:
<source_code>
function greet(name: string): void {
    console.log(`Hi, ${name}! How's it going?`);
    console.log("Even though this line is not in the diff, it should remain unchanged.");
}

function farewell(name: string): void {
    console.log(`Goodbye, ${name}!`);
}
</source_code>

<diff_patch>
diff --git a/greet.ts b/greet.ts
index 1234567..7654321 100644
--- a/greet.ts
+++ b/greet.ts
@@ -1,4 +1,4 @@
 function greet(name: string): void {
-    console.log(`Hello, ${name}! How are you?`);
+    console.log(`Hi, ${name}! How's it going?`);

 function farewell(name: string): void {
     console.log(`Goodbye, ${name}!`);
</diff_patch>
</input>

OUTPUT:
function greet(name: string): void {
    console.log(`Hello, ${name}! How are you?`);
    console.log("Even though this line is not in the diff, it should remain unchanged.");
}

function farewell(name: string): void {
    console.log(`Goodbye, ${name}!`);
}
"""

TASK_PROMPT_TS = """Task:

INPUT:
<source_code>
{}
</source_code>

<diff_patch>
{}
</diff_patch>
</input>

NOTES:
- As a reminder, DO NOT MAKE ANY OTHER CHANGES TO THE SOURCE CODE. If a line was not explicitly added or removed in the diff, it should remain unchanged in the output.
- Only make changes based on lines that were:
    * Added (have a + in front of them)
    * Removed (have a - in front of them)
- DO NOT PROVIDE ANY TEXT ASIDE FROM THE REWRITTEN FILE. ANSWER WITH ONLY THE REWRITTEN CODE.

OUTPUT:"""


def extract_output(output: str) -> str:
    """Extract code from LLM response, handling various code block formats."""
    # Try TypeScript code blocks first
    for lang in ["typescript", "tsx", "javascript", "jsx", "ts", "js"]:
        pattern = re.compile(rf"^```{lang}\s*\n([\s\S]*)^```\s*$", re.MULTILINE)
        if pattern.search(output):
            output = output.split(f"```{lang}", 1)[1]
            output = output.rsplit("```", 1)[0]
            return output.strip()

    # Try generic code block
    pattern = re.compile(r"^```\s*\n([\s\S]*)^```\s*$", re.MULTILINE)
    if pattern.search(output):
        output = output.split("```", 1)[1]
        output = output.rsplit("```", 1)[0]
        return output.strip()

    return output.strip()


def parse_diff_files(patch: str) -> list[dict]:
    """Parse a unified diff and extract file information."""
    files = []
    current_file = None
    current_diff = []

    for line in patch.split('\n'):
        if line.startswith('diff --git'):
            if current_file:
                files.append({
                    'path': current_file,
                    'diff': '\n'.join(current_diff)
                })
            # Extract path from "diff --git a/path b/path"
            parts = line.split()
            if len(parts) >= 4:
                current_file = parts[2][2:]  # Remove 'a/' prefix
            current_diff = [line]
        elif current_file:
            current_diff.append(line)

    if current_file:
        files.append({
            'path': current_file,
            'diff': '\n'.join(current_diff)
        })

    return files


def is_ts_file(path: str) -> bool:
    """Check if file is TypeScript/JavaScript."""
    return path.endswith(('.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs'))


def reverse_file_diff(source_code: str, file_diff: str, model: str) -> tuple[str, float]:
    """Use LLM to reverse a diff for a single file."""
    response = completion(
        model=model,
        messages=[
            {"role": "user", "content": RECOVERY_PROMPT_TS},
            {"role": "user", "content": DEMO_PROMPT_TS},
            {"role": "user", "content": TASK_PROMPT_TS.format(source_code, file_diff)},
        ],
        n=1,
        temperature=0,
    )

    cost = completion_cost(completion_response=response)
    output = response.choices[0].message.content.strip()
    extracted = extract_output(output)

    return extracted, cost


def simulate_source_from_diff(diff: str) -> str:
    """
    Simulate what the source code looks like AFTER the PR was applied.
    This is the "current" state that we want to reverse.

    For lines with + prefix: include them (they were added by the PR)
    For lines with - prefix: exclude them (they were removed by the PR)
    For context lines (space prefix): include them
    """
    lines = []
    in_hunk = False

    for line in diff.split('\n'):
        # Skip diff headers
        if line.startswith(('diff --git', 'index ', '---', '+++', '@@')):
            if line.startswith('@@'):
                in_hunk = True
            continue

        if not in_hunk:
            continue

        if line.startswith('+'):
            # Line was added by PR - include it in "current" state
            lines.append(line[1:])
        elif line.startswith('-'):
            # Line was removed by PR - exclude from "current" state
            pass
        elif line.startswith(' '):
            # Context line - include as-is
            lines.append(line[1:])
        elif line == '':
            # Empty line
            lines.append('')

    return '\n'.join(lines)


def process_instance(instance: dict, model: str, output_dir: Path) -> dict:
    """Process a single instance and generate reversed diffs."""
    instance_id = instance['instance_id']
    patch = instance['patch']

    # Parse the diff into files
    files = parse_diff_files(patch)
    ts_files = [f for f in files if is_ts_file(f['path'])]

    if not ts_files:
        return {
            'instance_id': instance_id,
            'status': 'skipped',
            'reason': 'No TypeScript/JavaScript files in diff'
        }

    # Create output directory for this instance
    inst_dir = output_dir / instance_id
    inst_dir.mkdir(parents=True, exist_ok=True)

    total_cost = 0
    reversed_files = {}

    for file_info in ts_files:
        file_path = file_info['path']
        file_diff = file_info['diff']

        # Simulate what the current source looks like
        # (This is a simplification - in reality we'd need to fetch the actual file)
        simulated_source = simulate_source_from_diff(file_diff)

        if not simulated_source.strip():
            print(f"    Skipping {file_path}: could not simulate source")
            continue

        try:
            reversed_code, cost = reverse_file_diff(simulated_source, file_diff, model)
            total_cost += cost
            reversed_files[file_path] = {
                'original_diff': file_diff,
                'simulated_source': simulated_source,
                'reversed_code': reversed_code,
                'cost': cost
            }
            print(f"    Reversed {file_path} (${cost:.4f})")
        except Exception as e:
            print(f"    Error reversing {file_path}: {e}")
            continue

    # Save results
    result = {
        'instance_id': instance_id,
        'repo': instance['repo'],
        'pull_number': instance['pull_number'],
        'base_commit': instance['base_commit'],
        'status': 'success' if reversed_files else 'failed',
        'total_cost': total_cost,
        'files_reversed': len(reversed_files),
        'reversed_files': reversed_files
    }

    with open(inst_dir / 'result.json', 'w') as f:
        json.dump(result, f, indent=2)

    # Save original patch
    with open(inst_dir / 'original.diff', 'w') as f:
        f.write(patch)

    return result


def main():
    parser = argparse.ArgumentParser(description='Reverse PR diffs using LLM')
    parser.add_argument('instances_file', help='Path to instances.jsonl file')
    parser.add_argument('--model', default='anthropic/claude-opus-4-5-20251101',
                        help='Model to use for reversal')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit number of instances to process')
    args = parser.parse_args()

    # Load instances
    instances = []
    with open(args.instances_file) as f:
        for line in f:
            if line.strip():
                instances.append(json.loads(line))

    if args.limit:
        instances = instances[:args.limit]

    print(f"Loaded {len(instances)} instances from {args.instances_file}")
    print(f"Using model: {args.model}")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Process each instance
    results = []
    total_cost = 0

    for i, instance in enumerate(instances, 1):
        print(f"\n[{i}/{len(instances)}] Processing {instance['instance_id']}...")
        result = process_instance(instance, args.model, OUTPUT_DIR)
        results.append(result)
        if 'total_cost' in result:
            total_cost += result['total_cost']
        print(f"  Status: {result['status']}")

    # Summary
    print(f"\n{'='*50}")
    print(f"Summary:")
    print(f"  Total instances: {len(instances)}")
    print(f"  Successful: {sum(1 for r in results if r['status'] == 'success')}")
    print(f"  Skipped: {sum(1 for r in results if r['status'] == 'skipped')}")
    print(f"  Failed: {sum(1 for r in results if r['status'] == 'failed')}")
    print(f"  Total cost: ${total_cost:.4f}")

    # Save summary
    summary = {
        'timestamp': datetime.now().isoformat(),
        'model': args.model,
        'instances_file': args.instances_file,
        'total_instances': len(instances),
        'total_cost': total_cost,
        'results': results
    }

    with open(OUTPUT_DIR / 'summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nResults saved to {OUTPUT_DIR}/")


if __name__ == '__main__':
    main()
