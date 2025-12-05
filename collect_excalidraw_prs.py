#!/usr/bin/env python3
"""Collect excalidraw PRs that have both test and code changes."""
import os
import json
import requests

# Load token from .env file directly
env_path = os.path.join(os.path.dirname(__file__), ".env")
GITHUB_TOKEN = None
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.startswith("GITHUB_TOKEN=") or line.startswith("GH_TOKEN="):
                GITHUB_TOKEN = line.split("=", 1)[1].strip()
                break

headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

owner = "excalidraw"
repo = "excalidraw"
base_url = f"https://api.github.com/repos/{owner}/{repo}"

print(f"Collecting PRs for {owner}/{repo}...")

# Get merged PRs
prs_url = f"{base_url}/pulls?state=closed&per_page=100&sort=updated&direction=desc"
response = requests.get(prs_url, headers=headers)
prs = response.json()

print(f"Found {len(prs)} closed PRs")

# Filter for merged PRs with test file changes
collected = []
for pr in prs:
    if not pr.get("merged_at"):
        continue

    pr_number = pr["number"]
    # Get PR files
    files_url = f"{base_url}/pulls/{pr_number}/files"
    files_resp = requests.get(files_url, headers=headers)
    files = files_resp.json()

    # Check if any file is a test file or modifies code that has tests
    has_test_changes = False
    has_code_changes = False
    test_files = []
    code_files = []

    for f in files:
        filename = f.get("filename", "")
        if ".test." in filename or "/tests/" in filename or "__tests__" in filename:
            has_test_changes = True
            test_files.append(filename)
        elif filename.endswith((".ts", ".tsx")) and "node_modules" not in filename:
            has_code_changes = True
            code_files.append(filename)

    if has_test_changes and has_code_changes:
        print(f"  PR #{pr_number}: {pr['title'][:50]}... - {len(test_files)} test files, {len(code_files)} code files")
        collected.append({
            "number": pr_number,
            "title": pr["title"],
            "merged_at": pr["merged_at"],
            "merge_commit_sha": pr["merge_commit_sha"],
            "base_sha": pr.get("base", {}).get("sha"),
            "test_files": test_files,
            "code_files": code_files
        })

print(f"\nCollected {len(collected)} PRs with both test and code changes")

# Save to file
os.makedirs("logs/prs/excalidraw", exist_ok=True)
with open("logs/prs/excalidraw/prs_with_tests.json", "w") as f:
    json.dump(collected, f, indent=2)

print(f"Saved to logs/prs/excalidraw/prs_with_tests.json")
