---
name: skill-upgrade-helper
description: Manage and upgrade locally installed Claude Code skills. Use when the user wants to update/upgrade skills, install new skills, list installed skills, or manage skill installations. Triggers on phrases like "update skill", "upgrade skill", "install skill", "refresh skills", "manage skills".
---

# Skill Upgrade Helper

Manage skills from a curated remote catalog. Supports user-level and project-level targets, and works with both `.claude` and `.kiro` config directories.

## When this skill is triggered

**Step 1: Locate the upgrade script.** Find it by searching **project-level directories first, then user-level**:

```bash
find .kiro/skills .claude/skills ~/.kiro/skills ~/.claude/skills -path "*/skill-upgrade-helper/scripts/upgrade.py" 2>/dev/null | head -1
```

Save the result as `SCRIPT_PATH`. If nothing is found, tell the user the skill-upgrade-helper is not installed.

**Step 1b: Detect the current config directory.** Look at `SCRIPT_PATH` to determine if we are running under `.claude` or `.kiro`. For example:
- `.../.claude/skills/skill-upgrade-helper/scripts/upgrade.py` → config dir is `.claude`
- `.../.kiro/skills/skill-upgrade-helper/scripts/upgrade.py` → config dir is `.kiro`

Save this as `CONFIG_DIR` (either `.claude` or `.kiro`). This determines which `available_targets` to use — the user should NOT be asked to choose between `.claude` and `.kiro`.

**Step 2: Fetch current state.** Run:

```bash
uv run <SCRIPT_PATH> list --json
```

**Step 3: Parse the JSON output.** The output looks like:

```json
{
  "project_root": "/path/to/project or null",
  "available_targets": [
    {"label": "user (.claude)", "path": "/Users/foo/.claude/skills"},
    {"label": "user (.kiro)", "path": "/Users/foo/.kiro/skills"},
    {"label": "project (.claude)", "path": "/path/to/project/.claude/skills"},
    {"label": "project (.kiro)", "path": "/path/to/project/.kiro/skills"}
  ],
  "skills": { ... }
}
```

**Filter `available_targets`**: only keep entries whose label contains `CONFIG_DIR`. For example, if `CONFIG_DIR` is `.kiro`, keep only entries with `(.kiro)` in the label. This gives you the relevant targets for the current tool.

**Step 4: Present ALL skills from the JSON to the user.** You MUST list every single skill from the `skills` object — do not skip or filter any. Format as a table:

- If `installed` is empty → status is "not installed"
- If `installed` contains `"user"` → show "✓ user"
- If `installed` contains a path → show "✓ project"

Example:

```
| #  | Skill                  | Status            |
|----|------------------------|-------------------|
| 1  | aws-excalidraw-diagram | ✓ user            |
| 2  | aws-html-slides        | not installed      |
| 3  | humanizer              | ✓ user  ✓ project |
| 4  | skill-creator          | ✓ user            |
| 5  | ui-ux-pro-max          | not installed      |
```

**Step 5: Ask the user two questions:**

1. Which skills to install or update? (by number, name, or "all")
2. Where to install? Present the **filtered** targets as simple level choices:
   - **User level** — if a `user (CONFIG_DIR)` target exists
   - **Project level** — if a `project (CONFIG_DIR)` target exists
   - If only one filtered target exists, use it automatically without asking.
   - If both user and project targets exist, ask the user to choose.

**Step 6: Execute.** For each skill + target the user chose, run the update command using the `path` field from the matching `available_targets` entry:

```bash
uv run <SCRIPT_PATH> update <name> --target <path>
```

Report results as each completes.

## Quick shortcut

If the user's intent is unambiguous (e.g. "update all my skills") AND there is only one filtered target, skip the selection and run:

```bash
uv run <SCRIPT_PATH> update --all --target <path>
```

If both user and project targets exist, still ask which level before executing.
