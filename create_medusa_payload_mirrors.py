#!/usr/bin/env python3
"""
Create mirror repositories for medusa and payload profiles.
"""

from swesmith.profiles.typescript import Medusa00052b9e, PayloadA07cf472

def main():
    print("Creating mirror repositories...")

    # Create Medusa mirror
    print("\n1. Creating Medusa mirror...")
    medusa = Medusa00052b9e()
    print(f"   Profile: {medusa.mirror_name}")
    try:
        medusa.create_mirror()
        print(f"   â Mirror created successfully!")
    except Exception as e:
        print(f"   â Error: {e}")

    # Create Payload mirror
    print("\n2. Creating Payload mirror...")
    payload = PayloadA07cf472()
    print(f"   Profile: {payload.mirror_name}")
    try:
        payload.create_mirror()
        print(f"   â Mirror created successfully!")
    except Exception as e:
        print(f"   â Error: {e}")

    print("\nâ Done!")

if __name__ == "__main__":
    main()
