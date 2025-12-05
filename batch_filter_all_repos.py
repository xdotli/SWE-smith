#!/usr/bin/env python3
"""
Batch filter all existing PR data with RELAXED criteria.

This script processes all existing PR JSONL files in logs/prs/
and applies the relaxed filtering criteria to find more suitable
candidates for fail-to-pass generation.

Relaxed criteria:
- Allow e2e tests (treat as unit tests)
- Allow up to 10 files changed
- Allow up to 1000 changes (~10KB)
- Include test files with patterns: .test., .spec., test/, tests/, e2e/
"""

import requests
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


def get_pr_files(owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
    """Fetch files changed in a PR."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  Error fetching files for PR #{pr_number}: {e}", file=sys.stderr)
        return []


def is_good_pr_candidate_relaxed(files: List[Dict[str, Any]]) -> tuple[bool, str]:
    """
    Check if PR meets RELAXED criteria for fail-to-pass generation.
    Returns (is_good, reason).
    """
    if not files:
        return False, "no_files"

    # RELAXED: include e2e tests, any test pattern
    test_files = [
        f for f in files
        if any(pattern in f["filename"].lower() for pattern in [
            ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx",
            ".test.js", ".test.jsx", ".spec.js", ".spec.jsx",
            "/test/", "/tests/", "/__tests__/", "/e2e/"
        ])
    ]

    code_files = [
        f for f in files
        if f["filename"].endswith((".ts", ".tsx", ".js", ".jsx"))
        and not any(ext in f["filename"] for ext in [".snap"])
        and f not in test_files
    ]

    # Must have actual test files (not ONLY snapshots)
    has_real_tests = any(
        ".snap" not in f["filename"]
        for f in test_files
    )
    if not has_real_tests:
        return False, "no_real_tests"

    # Must have test changes
    if not test_files:
        return False, "no_test_files"

    # RELAXED: Allow up to 10 files
    if len(files) > 10:
        return False, "too_many_files"

    # RELAXED: Allow up to 1000 changes
    total_changes = sum(f.get("changes", 0) for f in files)
    if total_changes > 1000:
        return False, "too_large"

    return True, "pass"


def process_repo_prs(input_file: Path, owner: str, repo: str, output_dir: Path) -> Dict[str, int]:
    """Process PRs from a single repo file."""
    print(f"\n{'='*70}")
    print(f"Processing: {owner}/{repo}")
    print(f"Input: {input_file.name}")
    print(f"{'='*70}")

    filtered_prs = []
    stats = {
        "total": 0,
        "merged": 0,
        "no_files": 0,
        "no_real_tests": 0,
        "no_test_files": 0,
        "too_many_files": 0,
        "too_large": 0,
        "pass": 0
    }

    with open(input_file, 'r') as f:
        for line in f:
            if not line.strip():
                continue

            pr_data = json.loads(line.strip())
            stats["total"] += 1

            # Skip unmerged PRs
            if not pr_data.get("merged_at"):
                continue

            stats["merged"] += 1
            pr_number = pr_data["number"]

            # Fetch files for this PR
            print(f"  PR #{pr_number}...", end=" ")
            files = get_pr_files(owner, repo, pr_number)

            # Check relaxed criteria
            is_good, reason = is_good_pr_candidate_relaxed(files)
            stats[reason] += 1

            if is_good:
                test_files = [
                    f["filename"] for f in files
                    if any(pattern in f["filename"].lower() for pattern in [
                        ".test.", ".spec.", "/test/", "/tests/", "/e2e/"
                    ])
                ]
                code_files = [
                    f["filename"] for f in files
                    if f["filename"].endswith((".ts", ".tsx", ".js", ".jsx"))
                    and ".snap" not in f["filename"]
                    and f["filename"] not in test_files
                ]
                total_changes = sum(f.get("changes", 0) for f in files)

                filtered_pr = {
                    "number": pr_number,
                    "title": pr_data.get("title", ""),
                    "base_commit": pr_data["base"]["sha"],
                    "head_commit": pr_data["head"]["sha"],
                    "merged_at": pr_data["merged_at"],
                    "files": [f["filename"] for f in files],
                    "test_files": test_files,
                    "code_files": code_files,
                    "total_changes": total_changes,
                    "html_url": pr_data["html_url"]
                }
                filtered_prs.append(filtered_pr)
                print(f"✓ PASS ({total_changes} changes, {len(files)} files)")
            else:
                print(f"✗ {reason}")

            # Rate limiting
            time.sleep(0.7)

    # Save filtered PRs
    output_file = output_dir / f"{owner.replace('/', '_')}_{repo}_relaxed.jsonl"
    with open(output_file, 'w') as f:
        for pr in filtered_prs:
            f.write(json.dumps(pr) + "\n")

    # Print stats
    print(f"\nSTATS for {owner}/{repo}:")
    print(f"  Total PRs:         {stats['total']}")
    print(f"  Merged:            {stats['merged']}")
    print(f"  Passed filters:    {stats['pass']}")
    print(f"  Filtered out:")
    print(f"    - No files:      {stats['no_files']}")
    print(f"    - No real tests: {stats['no_real_tests']}")
    print(f"    - No test files: {stats['no_test_files']}")
    print(f"    - Too many:      {stats['too_many_files']}")
    print(f"    - Too large:     {stats['too_large']}")
    print(f"  Output: {output_file.name}")

    return stats


def main():
    """Process all PR files in logs/prs/"""
    if not GITHUB_TOKEN:
        print("=" * 70)
        print("WARNING: GITHUB_TOKEN not set. Rate limits will be strict (60/hour).")
        print("Set GITHUB_TOKEN environment variable for higher limits (5000/hour).")
        print("=" * 70)
        print()

    prs_dir = Path("logs/prs")
    output_dir = Path("logs/prs_filtered_relaxed")
    output_dir.mkdir(exist_ok=True)

    # Repo mappings
    repo_map = {
        "strapi-prs.jsonl": ("strapi", "strapi"),
        "payload-prs.jsonl": ("payloadcms", "payload"),
        "excalidraw-prs.jsonl": ("excalidraw", "excalidraw"),
        "marked-prs.jsonl": ("markedjs", "marked"),
        "marked-prs-200.jsonl": ("markedjs", "marked"),
        "dayjs-prs.jsonl": ("iamkun", "dayjs"),
        "axios-prs.jsonl": ("axios", "axios"),
        "zod-prs.jsonl": ("colinhacks", "zod"),
        "lodash-prs.jsonl": ("lodash", "lodash"),
        "date-fns-prs.jsonl": ("date-fns", "date-fns"),
        "commander-prs.jsonl": ("tj", "commander.js"),
        "commander.js-prs.jsonl": ("tj", "commander.js"),
    }

    all_stats = {}
    total_passed = 0

    for pr_file in sorted(prs_dir.glob("*.jsonl")):
        if pr_file.name not in repo_map:
            print(f"Skipping unknown file: {pr_file.name}")
            continue

        owner, repo = repo_map[pr_file.name]

        try:
            stats = process_repo_prs(pr_file, owner, repo, output_dir)
            all_stats[f"{owner}/{repo}"] = stats
            total_passed += stats["pass"]
        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Saving current progress...")
            break
        except Exception as e:
            print(f"ERROR processing {pr_file.name}: {e}")
            continue

    # Final summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"{'Repository':<30} {'Total':<8} {'Merged':<8} {'Passed':<8}")
    print(f"{'-'*70}")

    for repo_name, stats in all_stats.items():
        print(f"{repo_name:<30} {stats['total']:<8} {stats['merged']:<8} {stats['pass']:<8}")

    print(f"{'-'*70}")
    print(f"{'TOTAL PASSED':<30} {'':<8} {'':<8} {total_passed:<8}")
    print(f"{'='*70}")
    print(f"\nFiltered PRs saved to: {output_dir}/")


if __name__ == "__main__":
    main()
