"""
Simple test script to validate TypeScript PR reversal using LLM.
This tests the core PR mirroring concept without full SWE-smith infrastructure.
"""

import os
from dotenv import load_dotenv
from litellm import completion

load_dotenv()

# TypeScript-specific prompts
RECOVERY_PROMPT = """You are given the source code of a file and a corresponding diff patch that reflects changes made to this file.
Your task is to rewrite the entire source code while reversing the changes indicated by the diff patch.
That is, if a line was added in the diff, remove it; if a line was removed, add it back; and if a line was modified, restore it to its previous state.

DO NOT MAKE ANY OTHER CHANGES TO THE SOURCE CODE. If a line was not explicitly added or removed in the diff, it should remain unchanged in the output.

OUTPUT:
The fully rewritten source code, after undoing all changes specified in the diff.
The output should be valid TypeScript/JavaScript code.
"""

# Simple test case: reverse a small TypeScript change
TEST_SOURCE = '''import { trpc } from "@/lib/trpc/client";

export const useCreateKey = (onSuccess: (data: any) => void) => {
  const trpcUtils = trpc.useUtils();

  const key = trpc.key.create.useMutation({
    onSuccess(data) {
      trpcUtils.api.keys.list.invalidate();
      trpcUtils.api.overview.keyCount.invalidate();
      onSuccess(data);
    },
    onError(err) {
      console.error(err);
    },
  });

  return key;
};
'''

TEST_DIFF = '''diff --git a/use-create-key.tsx b/use-create-key.tsx
index 6b1f9e9efe..7a3d98b02f 100644
--- a/use-create-key.tsx
+++ b/use-create-key.tsx
@@ -12,6 +12,7 @@ export const useCreateKey = (
   const key = trpc.key.create.useMutation({
     onSuccess(data) {
       trpcUtils.api.keys.list.invalidate();
+      trpcUtils.api.overview.keyCount.invalidate();
       onSuccess(data);
     },
     onError(err) {
'''

EXPECTED_REVERSED = '''import { trpc } from "@/lib/trpc/client";

export const useCreateKey = (onSuccess: (data: any) => void) => {
  const trpcUtils = trpc.useUtils();

  const key = trpc.key.create.useMutation({
    onSuccess(data) {
      trpcUtils.api.keys.list.invalidate();
      onSuccess(data);
    },
    onError(err) {
      console.error(err);
    },
  });

  return key;
};
'''

TASK_PROMPT = """Task:

INPUT:
<source_code>
{}
</source_code>

<diff_patch>
{}
</diff_patch>

NOTES:
- Reverse the changes: if a line was added (+), remove it. If a line was removed (-), add it back.
- DO NOT MAKE ANY OTHER CHANGES TO THE SOURCE CODE.
- Answer with ONLY the rewritten code, no explanations.

OUTPUT:"""


def test_reversal(model: str = "openai/gpt-4o-mini"):
    print(f"Testing TypeScript PR reversal with {model}...")
    print("-" * 50)

    response = completion(
        model=model,
        messages=[
            {"role": "system", "content": RECOVERY_PROMPT},
            {"role": "user", "content": TASK_PROMPT.format(TEST_SOURCE, TEST_DIFF)},
        ],
        temperature=0,
    )

    result = response.choices[0].message.content.strip()

    # Clean up code blocks if present
    if result.startswith("```"):
        lines = result.split("\n")
        result = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

    print("INPUT SOURCE:")
    print(TEST_SOURCE)
    print("-" * 50)
    print("DIFF TO REVERSE:")
    print(TEST_DIFF)
    print("-" * 50)
    print("LLM OUTPUT:")
    print(result)
    print("-" * 50)

    # Check if the key line was removed
    has_keycount_line = "trpcUtils.api.overview.keyCount.invalidate()" in result

    if not has_keycount_line:
        print("SUCCESS: The added line was correctly removed!")
    else:
        print("FAILED: The added line was NOT removed")

    return not has_keycount_line


if __name__ == "__main__":
    # Test with different models
    models = ["openai/gpt-4o-mini", "openai/o3-mini"]

    for model in models:
        print(f"\n{'='*60}")
        print(f"Testing with {model}")
        print("=" * 60)
        try:
            success = test_reversal(model)
            print(f"Result: {'PASS' if success else 'FAIL'}")
        except Exception as e:
            print(f"Error: {e}")
