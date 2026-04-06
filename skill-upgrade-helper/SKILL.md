---
name: skill-upgrade-helper
description: Manage and upgrade locally installed Claude Code skills. Use when the user wants to update/upgrade skills, install new skills, list installed skills, or manage skill installations. Triggers on phrases like "update skill", "upgrade skill", "install skill", "refresh skills", "manage skills".
---

# Skill Upgrade Helper

Manage skills from a curated remote catalog. Supports user-level (`~/.claude/skills/`) and project-level (`.claude/skills/`) targets.

The upgrade script is at `~/.claude/skills/skill-upgrade-helper/scripts/upgrade.py`.

## When this skill is triggered

**Step 1: Fetch current state.** Run this command immediately:

```bash
uv run ~/.claude/skills/skill-upgrade-helper/scripts/upgrade.py list --json
```

**Step 2: Parse the JSON output.** The output looks like:

```json
{
  "project_root": "/path/to/project or null",
  "skills": {
    "skill-name": {
      "repo": "https://github.com/...",
      "installed": ["user", "/path/to/project"]
    }
  }
}
```

**Step 3: Present ALL skills from the JSON to the user.** You MUST list every single skill from the `skills` object — do not skip or filter any. Format as a table:

- If `installed` is empty → status is "not installed"
- If `installed` contains `"user"` → show "✓ user"
- If `installed` contains a path → show "✓ project"

Example:

```
| #  | Skill                | Status               |
|----|----------------------|----------------------|
| 1  | aws-excalidraw-diagram | ✓ user             |
| 2  | aws-html-slides      | not installed         |
| 3  | humanizer            | ✓ user  ✓ project    |
| 4  | skill-creator        | ✓ user               |
| 5  | ui-ux-pro-max        | not installed         |
```

**Step 4: Ask the user two questions:**

1. Which skills to install or update? (by number, name, or "all")
2. Where to install? Only offer targets that apply:
   - **User level** (`~/.claude/skills/`) — always available
   - **Project level** (`.claude/skills/`) — only if `project_root` is not null

**Step 5: Execute.** For each skill + target the user chose, run:

```bash
uv run ~/.claude/skills/skill-upgrade-helper/scripts/upgrade.py update <name> --target <user|project>
```

Report results as each completes.

## Quick shortcut

If the user's intent is unambiguous (e.g. "update all my skills"), skip the selection and run:

```bash
uv run ~/.claude/skills/skill-upgrade-helper/scripts/upgrade.py update --all --target user
```
