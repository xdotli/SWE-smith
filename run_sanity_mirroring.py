#!/usr/bin/env python3
"""
Run PR mirroring for sanity-io/sanity with a workaround for mirror check.
"""

import sys
import os

# Add swe-smith to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Monkeypatch the _mirror_exists method to return True
from swesmith.profiles.base import RepoProfile

def patched_mirror_exists(self):
    """Override mirror check - always return True if local clone exists."""
    if os.path.exists(self.repo_name):
        return True
    return False

# Patch the method on the class
RepoProfile._mirror_exists = patched_mirror_exists

# Now run the generate_ts script
from swesmith.bug_gen.mirror import generate_ts

if __name__ == "__main__":
    # Call main function directly
    generate_ts.main(
        sweb_insts_files=["logs/tasks/sanity-enriched.jsonl"],
        model="anthropic/claude-opus-4-5-20251101",
        redo_existing=False,
        redo_skipped=False,
        api_key=None
    )
