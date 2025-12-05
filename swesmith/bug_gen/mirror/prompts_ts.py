"""
TypeScript-specific prompts for PR mirroring diff reversal.
"""

RECOVERY_PROMPT_TS = """You are given the source code of a TypeScript/TSX file and a corresponding diff patch that reflects changes made to this file.
Your task is to rewrite the entire source code while reversing the changes indicated by the diff patch.
That is, if a line was added in the diff, remove it; if a line was removed, add it back; and if a line was modified, restore it to its previous state.

DO NOT MAKE ANY OTHER CHANGES TO THE SOURCE CODE. If a line was not explicitly added or removed in the diff, it should remain unchanged in the output.

INPUT:
<source_code>
Source code will be provided here.
</source_code>

<diff_patch>
Diff patch will be provided here.
</diff_patch>

OUTPUT:
The fully rewritten source code, after undoing all changes specified in the diff.
The output should be valid TypeScript/TSX code.
"""

DEMO_PROMPT_TS = """Demonstration:

INPUT:
<source_code>
export function greet(name: string): void {
    console.log(`Hi, ${name}! How's it going?`);
    console.log("Even though this line is not in the diff, it should remain unchanged.");
}

export function farewell(name: string): void {
    console.log(`Goodbye, ${name}!`);
}
</source_code>

<diff_patch>
diff --git a/greet.ts b/greet.ts
index 1234567..7654321 100644
--- a/greet.ts
+++ b/greet.ts
@@ -1,4 +1,4 @@
 export function greet(name: string): void {
-    console.log(`Hello, ${name}! How are you?`);
+    console.log(`Hi, ${name}! How's it going?`);
     console.log("Even though this line is not in the diff, it should remain unchanged.");
 }
</diff_patch>
</input>

OUTPUT:
export function greet(name: string): void {
    console.log(`Hello, ${name}! How are you?`);
    console.log("Even though this line is not in the diff, it should remain unchanged.");
}

export function farewell(name: string): void {
    console.log(`Goodbye, ${name}!`);
}
"""

TASK_PROMPT_TS = """Task:

INPUT:
<source_code>
{}
</source_code>

<diff_patch>
{}
</diff_patch>
</input>

NOTES:
- As a reminder, DO NOT MAKE ANY OTHER CHANGES TO THE SOURCE CODE. If a line was not explicitly added or removed in the diff, it should remain unchanged in the output.
- Only make changes based on lines that were:
    * Added (have a + in front of them)
    * Removed (have a - in front of them)
- DO NOT PROVIDE ANY TEXT ASIDE FROM THE REWRITTEN FILE. ANSWER WITH ONLY THE REWRITTEN CODE.
- Preserve all TypeScript type annotations, interfaces, and React/JSX syntax exactly as they appear.

OUTPUT:"""
