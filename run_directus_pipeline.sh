#!/bin/bash
set -e

cd /Users/suzilewie/benchflow/env-demo/.conductor/san-juan/swe-smith
source .venv/bin/activate
source .env

echo "=== Directus PR Mirroring Pipeline ==="
echo ""
echo "Step 5: Running PR Mirroring with Claude Opus 4.5..."
python -m swesmith.bug_gen.mirror.generate_ts logs/tasks/directus-insts.jsonl \
    --model anthropic/claude-opus-4-5-20251101

echo ""
echo "Step 6: Consolidating patches..."
python3 -c "
import json
from pathlib import Path

# Collect all bug patches
bug_dir = Path('logs/bug_gen/directus__directus.447c91d0/pr_mirror')
instances = []

if bug_dir.exists():
    for bug_file in sorted(bug_dir.glob('bug_*.json')):
        with open(bug_file) as f:
            data = json.load(f)
            instances.append(data)

# Save consolidated file
output_file = Path('logs/task_insts/directus_patches.json')
output_file.parent.mkdir(parents=True, exist_ok=True)

with open(output_file, 'w') as f:
    json.dump(instances, f, indent=2)

print(f'Consolidated {len(instances)} patches to {output_file}')
"

echo ""
echo "Step 7: Running validation..."
python -m swesmith.harness.valid logs/task_insts/directus_patches.json -w 1

echo ""
echo "=== Pipeline Complete ==="
echo ""
echo "Checking results..."
python3 -c "
import json
from pathlib import Path

# Find validation report
for report_path in Path('logs/run_validation').rglob('report.json'):
    if 'directus' in str(report_path):
        with open(report_path) as f:
            data = json.load(f)

        f2p_count = len(data.get('FAIL_TO_PASS', []))
        p2p_count = len(data.get('PASS_TO_PASS', []))

        print(f'Validation Report: {report_path}')
        print(f'  FAIL_TO_PASS: {f2p_count}')
        print(f'  PASS_TO_PASS: {p2p_count}')
        break
"
