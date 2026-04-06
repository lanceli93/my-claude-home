---
name: skill-upgrade-helper
description: Manage and upgrade locally installed Claude Code skills. Use when the user wants to update/upgrade skills, install new skills, list installed skills, or manage skill installations. Triggers on phrases like "update skill", "upgrade skill", "install skill", "refresh skills", "manage skills".
---

# Skill Upgrade Helper

Manage skills from a curated remote catalog. Supports user-level (`~/.claude/skills/`) and project-level (`.claude/skills/`) targets.

The upgrade script is at `~/.claude/skills/skill-upgrade-helper/scripts/upgrade.py`.

## When this skill is triggered

Immediately run the list command to get current state, then present it to the user:

```bash
uv run ~/.claude/skills/skill-upgrade-helper/scripts/upgrade.py list --json
```

The JSON output has this shape:

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

### Present the skill list

Show the user a formatted table like:

```
| #  | Skill              | Status               |
|----|--------------------|----------------------|
| 1  | skill-creator      | ✓ user               |
| 2  | humanizer          | ✓ user  ✓ project    |
| 3  | aws-html-slides    | not installed         |
```

Then ask the user:
1. **Which skills** to install or update (by number, name, or "all")
2. **Where** to install: user level, project level, or both (only offer project if `project_root` is not null)

### Execute the updates

For each skill + target combination the user chose, run:

```bash
uv run ~/.claude/skills/skill-upgrade-helper/scripts/upgrade.py update <name> --target <user|project>
```

Report the results as each completes.

### Quick shortcuts

If the user's intent is unambiguous (e.g. "update all my skills"), skip the selection step and run directly:

```bash
uv run ~/.claude/skills/skill-upgrade-helper/scripts/upgrade.py update --all --target user
```
