#!/usr/bin/env python3
"""Create GitHub mirrors for all TypeScript profiles that need them."""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Verify token is set
token = os.environ.get("GITHUB_TOKEN")
if not token:
    print("ERROR: GITHUB_TOKEN not set in environment")
    exit(1)

print(f"Using GitHub token: {token[:20]}...")

from swesmith.profiles.typescript import (
    CalcomCalComMain,
    TwentyhqTwentyMain,
    PostHogPosthogMain,
    NocodbNocodbDevelop,
    AppsmithorgAppsmith7046aeb3,
    HoppscotchHoppscotchMain,
    DubincDubMain,
    MedusajsMedusa56ed9cf9,
)

profiles = [
    ("cal.com", CalcomCalComMain),
    ("twenty", TwentyhqTwentyMain),
    ("posthog", PostHogPosthogMain),
    ("nocodb", NocodbNocodbDevelop),
    ("appsmith", AppsmithorgAppsmith7046aeb3),
    ("hoppscotch", HoppscotchHoppscotchMain),
    ("dub", DubincDubMain),
    ("medusa", MedusajsMedusa56ed9cf9),
]

print(f"\nCreating mirrors for {len(profiles)} repositories...")
print("=" * 60)

results = []
for name, ProfileClass in profiles:
    print(f"\n[{name}] Creating mirror...")
    try:
        profile = ProfileClass()
        print(f"  Mirror name: {profile.mirror_name}")
        profile.create_mirror()
        print(f"  ✅ Mirror created successfully!")
        results.append((name, "SUCCESS"))
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        results.append((name, f"FAILED: {e}"))

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
for name, status in results:
    print(f"  {name}: {status}")

successes = sum(1 for _, s in results if s == "SUCCESS")
print(f"\nTotal: {successes}/{len(profiles)} mirrors created")
