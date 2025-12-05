#!/usr/bin/env python3
"""
Collect and filter PRs from medusajs/medusa and payloadcms/payload repositories.
Target: 40+ filtered PRs from EACH repo (80+ total)
"""

import os
import json
import requests
import time
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Configuration
REPOS = {
    "medusa": "medusajs/medusa",
    "payload": "payloadcms/payload"
}

OUTPUT_DIR = Path("/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/logs/prs")
MAX_PRS_TO_FETCH = 500  # Fetch more PRs before filtering
TARGET_FILTERED_PRS = 40  # Target per repo

# Load GitHub token
def load_github_token():
    env_path = Path("/Users/suzilewie/benchflow/env-demo/.conductor/nairobi/swe-smith/.env")
    with open(env_path) as f:
        for line in f:
            if line.startswith("GITHUB_TOKEN="):
                return line.strip().split("=", 1)[1]
    raise ValueError("GITHUB_TOKEN not found in .env")

GITHUB_TOKEN = load_github_token()
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def is_good_pr_candidate(pr: Dict, files: List[Dict]) -> tuple[bool, str]:
    """
    Check if PR is a good candidate for PR mirroring.
    Returns (is_good, reason) tuple.
    """
    # Check for merge commits
    if pr.get("merge_commit_sha") and "merge" in pr.get("title", "").lower():
        return False, "merge commit"

    # Check for real test files (not snapshots)
    test_files = [f for f in files if
        (f['filename'].endswith(('.test.ts', '.test.tsx', '.spec.ts', '.spec.tsx'))
        and '.snap' not in f['filename']
        and '__snapshots__' not in f['filename'])]

    # Check for code files (TypeScript/TSX)
    code_files = [f for f in files if
        f['filename'].endswith(('.ts', '.tsx'))
        and '.test.' not in f['filename']
        and '.spec.' not in f['filename']
        and '.snap' not in f['filename']
        and 'node_modules' not in f['filename']
        and '.d.ts' not in f['filename']]  # Exclude type definitions

    # Must have both test and code files
    if not test_files:
        return False, "no test files"
    if not code_files:
        return False, "no code files"

    # Calculate diff size (additions + deletions)
    total_changes = sum(f.get('additions', 0) + f.get('deletions', 0) for f in files)
    if total_changes > 500:  # ~5KB assuming 10 chars per line
        return False, f"diff too large ({total_changes} changes)"

    if total_changes < 10:  # Too trivial
        return False, f"diff too small ({total_changes} changes)"

    # Focused changes (not too many files)
    if len(code_files) > 5:
        return False, f"too many code files ({len(code_files)})"

    # Check for TypeScript files (not just type definitions)
    has_implementation = any(
        not f['filename'].endswith('.d.ts') and
        not f['filename'].endswith('.types.ts')
        for f in code_files
    )
    if not has_implementation:
        return False, "only type definition files"

    return True, "passed all filters"

def fetch_prs_paginated(repo: str, max_prs: int = 500) -> List[Dict]:
    """Fetch merged PRs with pagination."""
    url = f"https://api.github.com/repos/{repo}/pulls"
    params = {
        "state": "closed",
        "sort": "updated",
        "direction": "desc",
        "per_page": 100
    }

    all_prs = []
    page = 1

    print(f"\nð¥ Fetching PRs from {repo}...")

    while len(all_prs) < max_prs:
        params["page"] = page
        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code == 403:
            # Rate limit hit
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
            wait_time = max(reset_time - time.time(), 0) + 1
            print(f"â³ Rate limit hit. Waiting {wait_time:.0f}s...")
            time.sleep(wait_time)
            continue

        if response.status_code != 200:
            print(f"â Error fetching page {page}: {response.status_code}")
            break

        prs = response.json()
        if not prs:
            break

        # Filter for merged PRs only
        merged_prs = [pr for pr in prs if pr.get("merged_at")]
        all_prs.extend(merged_prs)

        print(f"  Page {page}: {len(merged_prs)} merged PRs (total: {len(all_prs)})")
        page += 1

        if len(prs) < 100:  # Last page
            break

        time.sleep(0.5)  # Be nice to GitHub API

    return all_prs[:max_prs]

def get_pr_files(repo: str, pr_number: int) -> List[Dict]:
    """Get files changed in a PR."""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    params = {"per_page": 100}

    all_files = []
    page = 1

    while True:
        params["page"] = page
        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code == 403:
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
            wait_time = max(reset_time - time.time(), 0) + 1
            time.sleep(wait_time)
            continue

        if response.status_code != 200:
            return []

        files = response.json()
        if not files:
            break

        all_files.extend(files)
        page += 1

        if len(files) < 100:
            break

        time.sleep(0.3)

    return all_files

def process_repository(repo_key: str, repo_full_name: str) -> Dict[str, Any]:
    """Process a single repository and collect filtered PRs."""
    print(f"\n{'='*80}")
    print(f"ð Processing {repo_full_name}")
    print(f"{'='*80}")

    # Fetch PRs
    prs = fetch_prs_paginated(repo_full_name, MAX_PRS_TO_FETCH)
    print(f"\nâ Fetched {len(prs)} merged PRs")

    # Filter PRs
    filtered_prs = []
    filter_stats = {}

    print(f"\nð¬ Filtering PRs (target: {TARGET_FILTERED_PRS})...")

    for i, pr in enumerate(prs, 1):
        pr_number = pr["number"]

        # Get files changed
        files = get_pr_files(repo_full_name, pr_number)
        if not files:
            filter_stats["no files"] = filter_stats.get("no files", 0) + 1
            continue

        # Apply filters
        is_good, reason = is_good_pr_candidate(pr, files)

        if is_good:
            # Extract test and code files
            test_files = [f['filename'] for f in files if
                (f['filename'].endswith(('.test.ts', '.test.tsx', '.spec.ts', '.spec.tsx'))
                and '.snap' not in f['filename'])]

            code_files = [f['filename'] for f in files if
                f['filename'].endswith(('.ts', '.tsx'))
                and '.test.' not in f['filename']
                and '.spec.' not in f['filename']
                and '.snap' not in f['filename']
                and 'node_modules' not in f['filename']
                and '.d.ts' not in f['filename']]

            total_changes = sum(f.get('additions', 0) + f.get('deletions', 0) for f in files)

            filtered_pr = {
                "number": pr_number,
                "title": pr["title"],
                "merged_at": pr["merged_at"],
                "merge_commit_sha": pr["merge_commit_sha"],
                "base_sha": pr["base"]["sha"],
                "test_files": test_files,
                "code_files": code_files,
                "total_changes": total_changes,
                "url": pr["html_url"]
            }

            filtered_prs.append(filtered_pr)
            print(f"  â PR #{pr_number}: {pr['title'][:60]}... ({total_changes} changes)")

            if len(filtered_prs) >= TARGET_FILTERED_PRS:
                print(f"\nð¯ Reached target of {TARGET_FILTERED_PRS} filtered PRs!")
                break
        else:
            filter_stats[reason] = filter_stats.get(reason, 0) + 1

        # Progress update every 20 PRs
        if i % 20 == 0:
            print(f"  Progress: {i}/{len(prs)} PRs checked, {len(filtered_prs)} passed filters")

    # Save results
    output_dir = OUTPUT_DIR / repo_key
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "filtered_prs.json"
    with open(output_file, "w") as f:
        json.dump(filtered_prs, f, indent=2)

    # Print statistics
    print(f"\n{'='*80}")
    print(f"ð Statistics for {repo_full_name}")
    print(f"{'='*80}")
    print(f"Total PRs fetched: {len(prs)}")
    print(f"PRs passed filters: {len(filtered_prs)}")
    print(f"Filter rejection reasons:")
    for reason, count in sorted(filter_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {reason}: {count}")
    print(f"\nð¾ Saved to: {output_file}")

    return {
        "repo": repo_full_name,
        "total_fetched": len(prs),
        "filtered": len(filtered_prs),
        "output_file": str(output_file),
        "filter_stats": filter_stats
    }

def main():
    """Main entry point."""
    print("ð Starting PR collection for medusa and payload")
    print(f"Target: {TARGET_FILTERED_PRS}+ filtered PRs per repo")
    print(f"Max PRs to fetch per repo: {MAX_PRS_TO_FETCH}")

    results = {}

    for repo_key, repo_full_name in REPOS.items():
        try:
            result = process_repository(repo_key, repo_full_name)
            results[repo_key] = result
        except Exception as e:
            print(f"\nâ Error processing {repo_full_name}: {e}")
            import traceback
            traceback.print_exc()
            results[repo_key] = {"error": str(e)}

    # Final summary
    print(f"\n{'='*80}")
    print("ð FINAL SUMMARY")
    print(f"{'='*80}")

    total_filtered = 0
    for repo_key, result in results.items():
        if "error" in result:
            print(f"\nâ {REPOS[repo_key]}: ERROR - {result['error']}")
        else:
            print(f"\nâ {result['repo']}:")
            print(f"   - Fetched: {result['total_fetched']} PRs")
            print(f"   - Filtered: {result['filtered']} PRs")
            print(f"   - Output: {result['output_file']}")
            total_filtered += result['filtered']

    print(f"\nð¯ Total filtered PRs across all repos: {total_filtered}")

    if total_filtered >= TARGET_FILTERED_PRS * len(REPOS):
        print(f"â SUCCESS: Reached target of {TARGET_FILTERED_PRS * len(REPOS)}+ PRs!")
    else:
        print(f"â ï¸  WARNING: Only collected {total_filtered} PRs, target was {TARGET_FILTERED_PRS * len(REPOS)}")

if __name__ == "__main__":
    main()
