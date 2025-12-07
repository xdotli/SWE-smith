#!/usr/bin/env python3
"""Summarize directus PR mirroring results."""

import json
from pathlib import Path
from collections import Counter

bug_dir = Path("logs/bug_gen/directus__directus.447c91d0/pr_mirror")

print("=" * 60)
print("DIRECTUS PR MIRRORING RESULTS")
print("=" * 60)
print()

# Count by status
statuses = []
costs = []
skip_reasons = []

for metadata_file in sorted(bug_dir.rglob("metadata__pr_*.json")):
    with open(metadata_file) as f:
        data = json.load(f)
        statuses.append(data["recover_status"])
        costs.append(data.get("cost", 0))
        if data.get("skip_reason"):
            skip_reasons.append(data["skip_reason"])

status_counts = Counter(statuses)

print(f"Total instances processed: {len(statuses)}")
print(f"  ✓ Success: {status_counts['success']}")
print(f"  ✗ Skipped: {status_counts['skipped']}")
print(f"  ✗ Failed: {status_counts['failed']}")
print()

if costs:
    print(f"Total LLM cost: ${sum(costs):.2f}")
    print(f"Average cost per instance: ${sum(costs)/len(costs):.3f}")
print()

if skip_reasons:
    print("Skip reasons:")
    for reason, count in Counter(skip_reasons).most_common():
        print(f"  - {reason}: {count}")
print()

# Find bug patches
bug_files = list(bug_dir.rglob("bug_*.json"))
print(f"Bug patches generated: {len(bug_files)}")
print()

if bug_files:
    print("Sample patches:")
    for bug_file in sorted(bug_files)[:3]:
        with open(bug_file) as f:
            data = json.load(f)
            print(f"  - {data['instance_id']}")
            print(f"    PR: {data.get('pull_number', 'N/A')}")
            if data.get("test_patch"):
                lines = data["test_patch"].count("\n")
                print(f"    Patch size: {lines} lines")
print()

print("=" * 60)
print("Note: Validation requires Docker image (pnpm install failed)")
print("Patches are generated and ready for validation when Docker is fixed")
print("=" * 60)
