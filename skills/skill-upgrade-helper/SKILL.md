---
name: skill-upgrade-helper
description: Manage and upgrade locally installed Claude Code skills. Use when the user wants to update/upgrade skills, register new skill sources, list installed skills, or remove skill registrations. Triggers on phrases like "update skill", "upgrade skill", "install skill from github", "refresh skills".
---

# Skill Upgrade Helper

Automate skill installation and upgrades via a registry-backed script. No version checking — always pulls latest and replaces.

## Registry

The registry file is at `~/.claude/skills/skill-upgrade-helper/registry.json`. It maps skill names to their GitHub clone source and subdirectory path.

## Usage

Run the script directly — do not reimplement the logic inline.

```bash
python ~/.claude/skills/skill-upgrade-helper/scripts/upgrade.py <command> [args]
```

### Commands

| Command | Description |
|---------|-------------|
| `list` | Show all registered skills |
| `add <name> --repo <url> --path <subdir>` | Register a skill source |
| `remove <name>` | Remove a skill from registry |
| `update <name>` | Pull latest and replace one skill |
| `update --all` | Pull latest and replace all registered skills |

### Examples

Register a new skill:
```bash
python ~/.claude/skills/skill-upgrade-helper/scripts/upgrade.py add skill-creator --repo https://github.com/anthropics/skills.git --path skills/skill-creator
```

Update one skill:
```bash
python ~/.claude/skills/skill-upgrade-helper/scripts/upgrade.py update skill-creator
```

Update all skills:
```bash
python ~/.claude/skills/skill-upgrade-helper/scripts/upgrade.py update --all
```
