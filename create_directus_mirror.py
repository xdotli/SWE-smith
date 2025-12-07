#!/usr/bin/env python3
"""Create mirror and build Docker image for directus/directus."""

import sys
import os

# Add swe-smith to path
sys.path.insert(0, '/Users/suzilewie/benchflow/env-demo/.conductor/san-juan/swe-smith')

from swesmith.profiles.typescript import DirectusDirectusa4220675

def main():
    print("Creating DirectusDirectusa4220675 profile...")
    profile = DirectusDirectusa4220675()

    print(f"\n1. Creating mirror on BenchFlow-Hub...")
    print(f"   Mirror name: {profile.mirror_name}")
    profile.create_mirror()
    print("   ✓ Mirror created")

    print(f"\n2. Building Docker image...")
    print(f"   This may take 5-10 minutes...")
    profile.build_image()
    print("   ✓ Docker image built")

    print(f"\n✓ Setup complete!")
    print(f"   Mirror: https://github.com/{profile.mirror_name}")
    print(f"   Image: {profile.image_name}")

if __name__ == "__main__":
    main()
