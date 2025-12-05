#!/usr/bin/env python3
"""
Filter existing PR data to find good candidates for PR mirroring.
Uses GitHub API to fetch file details for PRs that look promising.
"""

import json
import requests
import os
import time
from pathlib import Path

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}


def is_good_pr_candidate(pr_data, files_data):
    """Apply STRICT filtering criteria."""
    files = files_data

    # Separate test and code files
    test_files = [
        f for f in files
        if (".test.ts" in f["filename"] or ".spec.ts" in f["filename"] or
            ".test.tsx" in f["filename"] or ".spec.tsx" in f["filename"])
    ]

    code_files = [
        f for f in files
        if (f["filename"].endswith((".ts", ".tsx", ".js", ".jsx")) and
            ".test." not in f["filename"] and ".spec." not in f["filename"])
    ]

    # Must have real test files (not just snapshots)
    has_real_tests = any(".snap" not in f["filename"] for f in test_files)

    # Must have code files too
    has_code = len(code_files) > 0

    # Total changes should be small (<500 lines)
    total_changes = sum(f.get("changes", 0) for f in files)
    is_small = total_changes < 500

    # Not too many files
    is_focused = len(files) <= 5

    # Check merge commit via title
    is_merge = "merge" in pr_data.get("title", "").lower()

    return has_real_tests and has_code and is_small and is_focused and not is_merge


def process_pr_file(input_file, output_file, max_prs=50):
    """Process existing PR JSONL file and filter for good candidates."""
    print(f"\n{'='*60}")
    print(f"Processing {input_file}")
    print(f"{'='*60}")

    good_prs = []
    total_checked = 0
    rate_limited = False

    with open(input_file, "r") as f:
        prs = [json.loads(line) for line in f]

    print(f"Total PRs in file: {len(prs)}")

    for pr in prs:
        if len(good_prs) >= max_prs:
            break

        if rate_limited:
            break

        total_checked += 1

        # Skip non-merged
        if not pr.get("merged_at"):
            continue

        # Get files for this PR
        pr_number = pr["number"]
        repo_url = pr["html_url"].split("/pull/")[0]
        files_url = f"{pr['url']}/files"

        try:
            files_resp = requests.get(files_url, headers=HEADERS, timeout=30)

            if files_resp.status_code == 429 or files_resp.status_code == 403:
                print(f"\n  ⚠️  Rate limited at PR #{pr_number}")
                rate_limited = True
                break

            files_resp.raise_for_status()
            files = files_resp.json()

        except Exception as e:
            print(f"  Error fetching files for PR #{pr_number}: {e}")
            continue

        # Apply strict filtering
        if is_good_pr_candidate(pr, files):
            test_files = [
                f["filename"] for f in files
                if (".test.ts" in f["filename"] or ".spec.ts" in f["filename"] or
                    ".test.tsx" in f["filename"] or ".spec.tsx" in f["filename"])
            ]
            code_files = [
                f["filename"] for f in files
                if (f["filename"].endswith((".ts", ".tsx", ".js", ".jsx")) and
                    ".test." not in f["filename"] and ".spec." not in f["filename"])
            ]
            total_changes = sum(f.get("changes", 0) for f in files)

            pr_data = {
                "number": pr["number"],
                "title": pr["title"],
                "base_commit": pr["base"]["sha"],
                "head_commit": pr["head"]["sha"],
                "merged_at": pr["merged_at"],
                "html_url": pr["html_url"],
                "files": [f["filename"] for f in files],
                "test_files": test_files,
                "code_files": code_files,
                "total_changes": total_changes,
                "num_files": len(files)
            }

            good_prs.append(pr_data)
            print(f"  ✓ PR #{pr['number']}: {pr['title'][:60]}... ({total_changes} changes, {len(files)} files)")

        # Rate limit: sleep briefly between API calls
        time.sleep(0.2)

        # Progress indicator
        if total_checked % 10 == 0:
            print(f"  Checked {total_checked}/{len(prs)} PRs, found {len(good_prs)} candidates...")

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Total PRs checked: {total_checked}")
    print(f"  PRs passing filters: {len(good_prs)}")
    print(f"  Rate limited: {rate_limited}")
    print(f"{'='*60}\n")

    # Save to file
    with open(output_file, "w") as f:
        for pr in good_prs:
            f.write(json.dumps(pr) + "\n")

    print(f"Saved {len(good_prs)} PRs to {output_file}")
    return len(good_prs), rate_limited


def main():
    logs_dir = Path("logs/prs")

    # Process payload PRs
    payload_input = logs_dir / "payload-prs.jsonl"
    payload_output = logs_dir / "payload-filtered-prs.jsonl"

    if payload_input.exists() and not payload_output.exists():
        count, rate_limited = process_pr_file(payload_input, payload_output, max_prs=50)
        print(f"\nPayload: {count} good PRs found")
        if rate_limited:
            print("⚠️  Rate limited - results may be incomplete")
    elif payload_output.exists():
        with open(payload_output, "r") as f:
            count = len(f.readlines())
        print(f"\nPayload: {count} good PRs (already filtered)")
    else:
        print(f"\nPayload: No data found")


if __name__ == "__main__":
    main()
