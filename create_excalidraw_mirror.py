#!/usr/bin/env python3
"""Create mirror repository for excalidraw"""

from swesmith.profiles.typescript import Excalidraw8d18078f
from dotenv import load_dotenv

load_dotenv()

# Create profile instance
profile = Excalidraw8d18078f()

print(f"Creating mirror repository: {profile.mirror_name}")
profile.create_mirror()
print(f"â Mirror repository created successfully")
