#!/usr/bin/env python3
"""
Collect PRs for multiple Python repos in parallel.
Filters for PRs with:
- Test file changes
- Small/focused diffs (< 10 changed files)
- Not dependency updates or merge commits
"""
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict

# Target repos with good test coverage
REPOS = [
    ('pallets', 'click', 'ClickFde47b4b4'),
    ('marshmallow-code', 'marshmallow', 'Marshmallow9716fc62'),
    ('sympy', 'sympy', 'Sympy2ab64612'),
    ('python', 'mypy', 'MypyE93f06ce'),
    ('pylint-dev', 'astroid', 'AstroidB114f6b5'),  # Already has 3 F2P, collect more
]

def get_prs(owner: str, repo: str, limit: int = 30) -> List[Dict]:
    """Fetch merged PRs from GitHub."""
    cmd = [
        'gh', 'pr', 'list',
        '--repo', f'{owner}/{repo}',
        '--state', 'merged',
        '--limit', str(limit),
        '--json', 'number,title,mergedAt,changedFiles,additions,deletions'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error fetching PRs for {owner}/{repo}: {result.stderr}", file=sys.stderr)
        return []

    return json.loads(result.stdout)

def filter_prs(prs: List[Dict]) -> List[Dict]:
    """Filter PRs likely to produce fail-to-pass instances."""
    filtered = []

    for pr in prs:
        title = pr['title'].lower()

        # Skip dependency updates
        if any(word in title for word in ['bump', 'update', '[pre-commit.ci]', 'merge stable']):
            continue

        # Skip docs-only changes
        if 'docs' in title and 'fix' not in title:
            continue

        # Prefer focused changes (< 10 files)
        if pr.get('changedFiles', 0) > 10:
            continue

        # Skip very large PRs
        additions = pr.get('additions', 0)
        deletions = pr.get('deletions', 0)
        if additions + deletions > 500:
            continue

        filtered.append(pr)

    return filtered

def main():
    logs_dir = Path('logs/prs/python')
    logs_dir.mkdir(parents=True, exist_ok=True)

    total_collected = 0

    for owner, repo, profile in REPOS:
        print(f"\n{'='*60}")
        print(f"Collecting PRs for {owner}/{repo}")
        print(f"{'='*60}")

        prs = get_prs(owner, repo, limit=50)
        print(f"Fetched {len(prs)} PRs")

        filtered = filter_prs(prs)
        print(f"Filtered to {len(filtered)} PRs")

        if filtered:
            output_file = logs_dir / f"{repo}-prs.json"
            with open(output_file, 'w') as f:
                json.dump(filtered, f, indent=2)
            print(f"Saved to {output_file}")
            total_collected += len(filtered)

            # Show sample PRs
            print("\nSample PRs:")
            for pr in filtered[:5]:
                print(f"  #{pr['number']}: {pr['title'][:60]} ({pr['changedFiles']} files)")
        else:
            print("No suitable PRs found")

    print(f"\n{'='*60}")
    print(f"Total PRs collected: {total_collected}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
