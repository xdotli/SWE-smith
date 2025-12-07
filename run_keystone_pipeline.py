#!/usr/bin/env python3
"""
Run the complete Keystone pipeline:
1. Create mirror
2. Build Docker image
3. Collect PRs
4. Generate bug patches
5. Validate
"""

import json
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from swesmith.profiles.typescript import KeystonejsKeystone052f5b1b

# Load environment variables
load_dotenv()

def main():
    profile = KeystonejsKeystone052f5b1b()

    print(f"Profile: {profile}")
    print(f"Mirror name: {profile.mirror_name}")

    # Step 1: Create mirror
    print("\n=== Step 1: Creating mirror ===")
    try:
        profile.create_mirror()
        print(f"✓ Mirror created: https://github.com/{profile.mirror_name}")
    except Exception as e:
        print(f"✗ Mirror creation error: {e}")
        print("  This may be okay if the mirror already exists")

    # Step 2: Build Docker image
    print("\n=== Step 2: Building Docker image ===")
    try:
        profile.build_image()
        print(f"✓ Docker image built: {profile.image_name}")
    except Exception as e:
        print(f"✗ Docker build error: {e}")
        return

    print("\n=== Pipeline setup complete ===")
    print(f"Next steps:")
    print(f"1. Create PR collection script (collect_keystone_prs.py)")
    print(f"2. Run: python collect_keystone_prs.py")
    print(f"3. Run: python -m swesmith.bug_gen.mirror.generate_ts logs/tasks/keystone-insts.jsonl --model anthropic/claude-opus-4-5-20251101")
    print(f"4. Run: python -m swesmith.harness.valid logs/task_insts/keystone_patches.json -w 1")

if __name__ == "__main__":
    main()
