#!/usr/bin/env python3
"""Skill upgrade helper - registry-backed skill installer/updater."""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILLS_DIR = Path.home() / ".claude" / "skills"
REGISTRY_PATH = Path(__file__).resolve().parent.parent / "registry.json"


def load_registry() -> dict:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text())
    return {}


def save_registry(registry: dict):
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n")


def cmd_list(args):
    registry = load_registry()
    if not registry:
        print("No skills registered.")
        return
    for name, info in registry.items():
        installed = (SKILLS_DIR / name).exists()
        status = "installed" if installed else "not installed"
        print(f"  {name} [{status}]")
        print(f"    repo: {info['repo']}")
        print(f"    path: {info['path']}")


def cmd_add(args):
    registry = load_registry()
    registry[args.name] = {"repo": args.repo, "path": args.path}
    save_registry(registry)
    print(f"Registered: {args.name}")


def cmd_remove(args):
    registry = load_registry()
    if args.name not in registry:
        print(f"Not found in registry: {args.name}")
        sys.exit(1)
    del registry[args.name]
    save_registry(registry)
    print(f"Removed from registry: {args.name}")


def pull_skill(name: str, info: dict):
    """Clone repo to temp dir, copy skill subdirectory, cleanup."""
    target = SKILLS_DIR / name
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Cloning {info['repo']} ...")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", info["repo"], tmpdir],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  FAILED to clone: {result.stderr.strip()}")
            return False

        src = Path(tmpdir) / info["path"]
        if not src.exists():
            print(f"  FAILED: path '{info['path']}' not found in repo")
            return False

        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(src, target)
        print(f"  Updated: {name}")
        return True


def cmd_update(args):
    registry = load_registry()

    if args.all:
        names = list(registry.keys())
    elif args.name:
        names = [args.name]
    else:
        print("Specify a skill name or --all")
        sys.exit(1)

    for name in names:
        if name not in registry:
            print(f"Not in registry: {name}")
            continue
        pull_skill(name, registry[name])


def main():
    parser = argparse.ArgumentParser(description="Skill upgrade helper")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List registered skills")

    p_add = sub.add_parser("add", help="Register a skill source")
    p_add.add_argument("name")
    p_add.add_argument("--repo", required=True)
    p_add.add_argument("--path", required=True)

    p_rm = sub.add_parser("remove", help="Remove from registry")
    p_rm.add_argument("name")

    p_up = sub.add_parser("update", help="Update skill(s)")
    p_up.add_argument("name", nargs="?")
    p_up.add_argument("--all", action="store_true")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    {"list": cmd_list, "add": cmd_add, "remove": cmd_remove, "update": cmd_update}[args.command](args)


if __name__ == "__main__":
    main()
