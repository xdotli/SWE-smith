#!/usr/bin/env python3
"""Create GitHub mirror for trigger.dev repository."""

from swesmith.profiles.typescript import TriggerdotdevTriggerd1c3bfb9

def main():
    profile = TriggerdotdevTriggerd1c3bfb9()
    print(f"Creating mirror for {profile.owner}/{profile.repo} at commit {profile.commit}")
    print(f"Mirror will be: {profile.mirror_name}")

    # Create the mirror repository
    profile.create_mirror()
    print(f"✓ Mirror created successfully: https://github.com/{profile.mirror_name}")

if __name__ == "__main__":
    main()
