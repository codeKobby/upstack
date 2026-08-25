#!/usr/bin/env python3
"""Resolve project identity and persisted Upstack state for every command."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


STATE_DIRNAME = ".upstack"
STATE_FILENAME = "STATE.json"
PROJECT_FILENAME = "PROJECT.json"
PROJECT_MARKERS = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "Gemfile",
    "composer.json",
    "Dockerfile",
    "Makefile",
    "README.md",
    ".git",
}


def canonical(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def has_project_markers(path: Path) -> bool:
    try:
        return any((path / marker).exists() for marker in PROJECT_MARKERS)
    except OSError:
        return False


def git_root(path: Path) -> Path | None:
    current = canonical(path)
    if current.is_file():
        current = current.parent
    while True:
        try:
            if (current / ".git").exists():
                return current
        except OSError:
            return None
        if current.parent == current:
            return None
        current = current.parent


def state_paths(root: Path) -> dict[str, Path]:
    state_dir = root / STATE_DIRNAME
    return {
        "root": state_dir,
        "state": state_dir / STATE_FILENAME,
        "project": state_dir / PROJECT_FILENAME,
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        if not path.is_file():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def project_id(root: str | Path) -> str:
    return hashlib.sha256(str(canonical(root)).encode("utf-8")).hexdigest()[:16]


def resolve_project_root(start: str | Path) -> tuple[Path | None, str]:
    """Return the nearest known project, git root, or marker project."""
    path = canonical(start)
    if path.is_file():
        path = path.parent
    current = path
    while True:
        paths = state_paths(current)
        if paths["state"].is_file() or paths["project"].is_file():
            return current, "persisted_upstack_state"
        if (current / ".git").exists():
            return current, "git_root"
        if has_project_markers(current):
            return current, "project_markers"
        if current.parent == current:
            break
        current = current.parent
    return None, "broad_workspace"


def command_gate(start: str | Path, command: str) -> dict[str, Any]:
    path = canonical(start)
    root, detection = resolve_project_root(path)
    result: dict[str, Any] = {
        "schema_version": 1,
        "command": command,
        "input_path": str(path),
        "project_root": str(root) if root else None,
        "detection": detection,
        "write_performed": False,
        "resume_required": False,
    }
    if root is None:
        result.update({
            "status": "project_selection_required",
            "command_allowed": False,
            "next_action": "ask_for_explicit_project_path_or_start_onboarding",
            "message": "The current location is a broad workspace; do not choose a child project implicitly.",
        })
        return result
    paths = state_paths(root)
    state = _read_json(paths["state"])
    project = _read_json(paths["project"])
    if state is None:
        result.update({
            "status": "onboarding_required",
            "command_allowed": command in {"init", "capabilities"},
            "next_action": "run_or_resume_onboarding_before_project_command",
            "message": "This project has no valid persisted Upstack state. Start onboarding; do not restart a second curriculum.",
            "state_path": str(paths["root"]),
        })
        return result
    result.update({
        "status": "known_project",
        "command_allowed": True,
        "next_action": state.get("next_action") or "resume_current_lesson",
        "resume_required": True,
        "state_path": str(paths["state"]),
        "project_id": state.get("project_id") or (project or {}).get("project_id") or project_id(root),
        "project": project or state.get("project", {}),
        "state": {
            "onboarding": state.get("onboarding", {}),
            "mode": state.get("mode"),
            "current_stage": state.get("current_stage"),
            "completed_stages": state.get("completed_stages", []),
            "last_action": state.get("last_action"),
            "pending_confirmation": state.get("pending_confirmation"),
            "updated_at": state.get("updated_at"),
        },
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--command", default="upstack", help="Upstack subcommand being requested")
    args = parser.parse_args()
    print(json.dumps(command_gate(args.path, args.command), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
