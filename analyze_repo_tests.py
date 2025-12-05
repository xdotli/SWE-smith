#!/usr/bin/env python3
"""
Analyze TypeScript repositories to identify which have strong unit test coverage
by examining recent PRs that include test file changes.
"""

import requests
import os
from collections import defaultdict

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

# Target repos from our curated list
REPOS = [
    "tldraw/tldraw",
    "payloadcms/payload",
    "medusajs/medusa",
    "excalidraw/excalidraw",
    "hoppscotch/hoppscotch",
    "strapi/strapi",
    "unkeyed/unkey",
]

TEST_FILE_PATTERNS = [
    ".test.ts", ".test.tsx", ".test.js", ".test.jsx",
    ".spec.ts", ".spec.tsx", ".spec.js", ".spec.jsx",
    "__tests__/"
]

def is_test_file(filename):
    """Check if a file is a test file (not snapshot)."""
    if ".snap" in filename:
        return False
    return any(pattern in filename for pattern in TEST_FILE_PATTERNS)

def is_code_file(filename):
    """Check if a file is TypeScript/JavaScript code (not config/docs)."""
    exts = (".ts", ".tsx", ".js", ".jsx")
    if filename.endswith(exts):
        # Exclude config files
        if any(x in filename for x in ["config", ".config", "setup", "vitest", "jest"]):
            return False
        return True
    return False

def analyze_pr(repo, pr_number):
    """Analyze a single PR to see what types of files it modifies."""
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            return None

        files = resp.json()

        test_files = []
        code_files = []

        for f in files:
            filename = f["filename"]
            if is_test_file(filename):
                test_files.append(filename)
            elif is_code_file(filename):
                code_files.append(filename)

        return {
            "pr_number": pr_number,
            "test_files": test_files,
            "code_files": code_files,
            "has_real_tests": len(test_files) > 0,
            "changes": f["changes"] if files else 0,
        }
    except Exception as e:
        print(f"Error analyzing PR {pr_number}: {e}")
        return None

def get_recent_merged_prs(repo, limit=50):
    """Get recent merged PRs for a repo."""
    url = f"https://api.github.com/repos/{repo}/pulls"
    params = {"state": "closed", "per_page": limit, "sort": "updated", "direction": "desc"}

    try:
        resp = requests.get(url, headers=HEADERS, params=params)
        if resp.status_code != 200:
            print(f"Error fetching PRs for {repo}: {resp.status_code}")
            return []

        prs = resp.json()
        # Filter for merged PRs only
        merged_prs = [pr for pr in prs if pr.get("merged_at")]
        return merged_prs[:limit]
    except Exception as e:
        print(f"Error fetching PRs for {repo}: {e}")
        return []

def analyze_repo(repo):
    """Analyze a repo to determine test coverage patterns."""
    print(f"\n{'='*80}")
    print(f"Analyzing {repo}")
    print(f"{'='*80}")

    prs = get_recent_merged_prs(repo, limit=30)
    if not prs:
        print(f"  No merged PRs found")
        return None

    print(f"  Found {len(prs)} recent merged PRs")

    stats = {
        "repo": repo,
        "total_prs": len(prs),
        "prs_with_tests": 0,
        "prs_with_code_only": 0,
        "prs_small_focused": 0,  # <5 files, has tests
        "test_examples": [],
    }

    for pr in prs[:20]:  # Analyze first 20 PRs in detail
        pr_data = analyze_pr(repo, pr["number"])
        if not pr_data:
            continue

        has_tests = pr_data["has_real_tests"]
        num_files = len(pr_data["test_files"]) + len(pr_data["code_files"])

        if has_tests:
            stats["prs_with_tests"] += 1

            # Is it a good candidate? Small, focused, has tests
            if num_files <= 5 and len(pr_data["code_files"]) > 0:
                stats["prs_small_focused"] += 1
                stats["test_examples"].append({
                    "pr_number": pr["number"],
                    "title": pr["title"],
                    "test_files": pr_data["test_files"],
                    "code_files": pr_data["code_files"],
                })
        elif len(pr_data["code_files"]) > 0:
            stats["prs_with_code_only"] += 1

    # Calculate percentages
    stats["test_coverage_rate"] = (stats["prs_with_tests"] / stats["total_prs"] * 100) if stats["total_prs"] > 0 else 0
    stats["focused_pr_rate"] = (stats["prs_small_focused"] / stats["total_prs"] * 100) if stats["total_prs"] > 0 else 0

    # Print summary
    print(f"\n  Results:")
    print(f"    Total PRs analyzed: {stats['total_prs']}")
    print(f"    PRs with test changes: {stats['prs_with_tests']} ({stats['test_coverage_rate']:.1f}%)")
    print(f"    PRs with code only (no tests): {stats['prs_with_code_only']}")
    print(f"    Small focused PRs with tests: {stats['prs_small_focused']} ({stats['focused_pr_rate']:.1f}%)")

    if stats["test_examples"]:
        print(f"\n  Example PRs with tests:")
        for ex in stats["test_examples"][:5]:
            print(f"    PR #{ex['pr_number']}: {ex['title'][:60]}")
            print(f"      Tests: {len(ex['test_files'])}, Code: {len(ex['code_files'])}")

    return stats

def main():
    """Analyze all repos and provide recommendations."""
    print("="*80)
    print("TypeScript Repo Test Coverage Analysis")
    print("="*80)

    if not GITHUB_TOKEN:
        print("Warning: GITHUB_TOKEN not set. API rate limits will be restrictive.")
        print("Set with: export GITHUB_TOKEN=ghp_...")

    results = []
    for repo in REPOS:
        result = analyze_repo(repo)
        if result:
            results.append(result)

    # Sort by focused PR rate
    results.sort(key=lambda x: x["focused_pr_rate"], reverse=True)

    print("\n\n" + "="*80)
    print("RECOMMENDATIONS - Best repos for F2P generation")
    print("="*80)

    for i, r in enumerate(results[:3], 1):
        print(f"\n{i}. {r['repo']}")
        print(f"   - Test coverage: {r['test_coverage_rate']:.1f}%")
        print(f"   - Focused PRs with tests: {r['prs_small_focused']} ({r['focused_pr_rate']:.1f}%)")
        print(f"   - Good candidate: {'YES' if r['focused_pr_rate'] > 15 else 'MAYBE' if r['focused_pr_rate'] > 5 else 'NO'}")

if __name__ == "__main__":
    main()
