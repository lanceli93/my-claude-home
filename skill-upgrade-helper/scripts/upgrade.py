#!/usr/bin/env python3
"""Skill upgrade helper – registry-backed installer."""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REGISTRY_URL = (
    "https://raw.githubusercontent.com/lanceli93/my-claude-home"
    "/main/skill-upgrade-helper/registry.json"
)
LOCAL_REGISTRY = Path(__file__).resolve().parent.parent / "registry.json"
USER_SKILLS_DIR = Path.home() / ".claude" / "skills"


def fetch_registry() -> dict:
    """Fetch skill catalog from remote, fall back to local bundled copy."""
    try:
        resp = urllib.request.urlopen(REGISTRY_URL, timeout=10)
        return json.loads(resp.read())
    except Exception:
        if LOCAL_REGISTRY.exists():
            return json.loads(LOCAL_REGISTRY.read_text())
        return {}


def find_project_root() -> Path | None:
    """Find git root of the current working directory."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
        )
        if r.returncode == 0:
            return Path(r.stdout.strip())
    except Exception:
        pass
    return None


def scan_installed() -> dict[str, list[str]]:
    """Scan user and project skill dirs.

    Returns {name: [loc, ...]} where loc is "user" or a project root path.
    """
    found: dict[str, list[str]] = {}

    if USER_SKILLS_DIR.exists():
        for d in USER_SKILLS_DIR.iterdir():
            if d.is_dir() and (d / "SKILL.md").exists():
                found.setdefault(d.name, []).append("user")

    proj = find_project_root()
    if proj:
        pdir = proj / ".claude" / "skills"
        if pdir.exists():
            for d in pdir.iterdir():
                if d.is_dir() and (d / "SKILL.md").exists():
                    found.setdefault(d.name, []).append(str(proj))

    return found


def skills_dir_for(target: str) -> Path:
    """Convert a target label to the actual skills directory path."""
    if target == "user":
        return USER_SKILLS_DIR
    return Path(target) / ".claude" / "skills"


def pull_skill(name: str, info: dict, target_dir: Path) -> bool:
    """Clone repo into a temp dir and copy the skill subdirectory to target."""
    dest = target_dir / name
    with tempfile.TemporaryDirectory() as tmp:
        print(f"  Cloning {info['repo']} ...")
        r = subprocess.run(
            ["git", "clone", "--depth", "1", info["repo"], tmp],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            print(f"  FAILED: {r.stderr.strip()}")
            return False

        src = Path(tmp) / info["path"]
        if not src.exists():
            print(f"  FAILED: path '{info['path']}' not found in repo")
            return False

        if dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest)
        print(f"  ✓ {name} → {dest}")
        return True


def _loc_label(loc: str) -> str:
    return "user" if loc == "user" else f"project({Path(loc).name})"


def cmd_list(as_json: bool = False):
    """List all available skills and their install status."""
    registry = fetch_registry()
    installed = scan_installed()
    project_root = find_project_root()

    if as_json:
        result = {
            "project_root": str(project_root) if project_root else None,
            "skills": {},
        }
        for name in sorted(registry):
            result["skills"][name] = {
                "repo": registry[name]["repo"],
                "installed": installed.get(name, []),
            }
        print(json.dumps(result))
        return

    if not registry:
        print("Registry is empty.")
        return

    for name in sorted(registry):
        locs = installed.get(name, [])
        status = ", ".join(_loc_label(l) for l in locs) if locs else "not installed"
        print(f"  {name}  [{status}]")
        print(f"    repo: {registry[name]['repo']}")


def cmd_update(name: str | None, target: str, all_: bool):
    """Update one or all skills to the specified target."""
    registry = fetch_registry()

    if target == "project":
        proj = find_project_root()
        if not proj:
            sys.exit("Not inside a git project.")
        target = str(proj)

    if all_:
        names = list(registry)
    elif name:
        names = [name]
    else:
        sys.exit("Specify a skill name or --all.")

    td = skills_dir_for(target)
    ok = total = 0
    for n in names:
        if n not in registry:
            print(f"  Not in registry: {n}")
            continue
        total += 1
        ok += pull_skill(n, registry[n], td)

    print(f"\nDone — {ok}/{total} succeeded.")


def main():
    p = argparse.ArgumentParser(description="Skill upgrade helper")
    sub = p.add_subparsers(dest="command")

    ls = sub.add_parser("list", help="List available and installed skills")
    ls.add_argument("--json", action="store_true", dest="as_json",
                    help="Output as JSON for programmatic use")

    up = sub.add_parser("update", help="Update skill(s)")
    up.add_argument("name", nargs="?")
    up.add_argument("--all", action="store_true", dest="all_")
    up.add_argument(
        "--target",
        default="user",
        help="'user', 'project', or absolute path to project root",
    )

    args = p.parse_args()

    match args.command:
        case "list":
            cmd_list(as_json=args.as_json)
        case "update":
            cmd_update(args.name, args.target, args.all_)
        case _:
            p.print_help()


if __name__ == "__main__":
    main()
