#!/usr/bin/env python3
"""
Create GitHub mirror repositories for strapi and hoppscotch.
"""

from swesmith.profiles.typescript import HoppscotchLatest, StrapiLatest

def main():
    repos = [
        ("hoppscotch", HoppscotchLatest()),
        ("strapi", StrapiLatest()),
    ]

    for name, profile in repos:
        print(f"\n{'='*60}")
        print(f"Creating mirror for {name}")
        print(f"{'='*60}")

        try:
            profile.create_mirror()
            print(f"â Successfully created mirror: {profile.mirror_name}")
        except Exception as e:
            print(f"â Error creating mirror: {e}")
            print(f"Mirror may already exist: {profile.mirror_name}")

if __name__ == "__main__":
    main()
