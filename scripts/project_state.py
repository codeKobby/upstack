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
SKILL_HOST_DIRS = {".agents", ".opencode", ".claude", ".cline", ".clinerules", ".github", ".agent", ".codex"}
RESUME_COMMANDS = {"continue", "resume"}


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


def _resume_pointers(root: Path, state: dict[str, Any], project: dict[str, Any] | None) -> dict[str, Any]:
    """Derive read-only pointers for legacy states without changing them."""
    state_dir = root / STATE_DIRNAME
    pointers = dict(state.get("pointers")) if isinstance(state.get("pointers"), dict) else {}
    pointers.setdefault("project_root", str(root))
    pointers.setdefault("workspace_root", str(root.parent))
    pointers.setdefault("destination", str(root))
    pointers.setdefault("state_file", str(state_dir / STATE_FILENAME))
    pointers.setdefault("project_file", str(state_dir / PROJECT_FILENAME))
    pointers.setdefault("history_file", str(state_dir / "HISTORY.jsonl"))
    plan_path = state_dir / "lessons" / "plan.json"
    plan = _read_json(plan_path) or {}
    curriculum = dict(state.get("curriculum")) if isinstance(state.get("curriculum"), dict) else {}
    plan_curriculum = plan.get("curriculum") if isinstance(plan.get("curriculum"), dict) else {}
    curriculum.setdefault("id", plan_curriculum.get("id"))
    curriculum.setdefault("title", plan_curriculum.get("title"))
    curriculum.setdefault("plan", str(plan_path))
    curriculum.setdefault("markdown", str(state_dir / "lessons" / "CURRICULUM.md"))
    curriculum.setdefault("blueprint", str(state_dir / "lessons" / "LESSON_BLUEPRINT.md"))
    curriculum.setdefault("progress", str(state_dir / "lessons" / "progress.json"))
    pointers.setdefault("curriculum", curriculum)
    stage = int(state.get("current_stage") or 1)
    stages = plan.get("stages") if isinstance(plan.get("stages"), list) else []
    item = stages[stage - 1] if 0 < stage <= len(stages) and isinstance(stages[stage - 1], dict) else {}
    lesson = dict(state.get("current_lesson")) if isinstance(state.get("current_lesson"), dict) else {}
    lesson_path = state_dir / "lessons" / "CURRENT_LESSON.md"
    lesson.setdefault("sequence", stage)
    lesson.setdefault("id", item.get("id"))
    lesson.setdefault("title", item.get("title"))
    lesson.setdefault("status", "active" if lesson_path.is_file() else "not_generated")
    lesson.setdefault("path", str(lesson_path) if lesson_path.is_file() else None)
    lesson.setdefault("requested", lesson_path.is_file())
    pointers.setdefault("current_lesson", lesson)
    design = dict(state.get("design")) if isinstance(state.get("design"), dict) else {}
    design_path = state_dir / "design" / "design-plan.json"
    design_plan = _read_json(design_path) or {}
    integration = design_plan.get("integration") if isinstance(design_plan.get("integration"), dict) else {}
    design["mode"] = design_plan.get("mode") or design.get("mode") or "not_selected"
    design["status"] = integration.get("status") or design.get("status") or "not_started"
    stitch = design.get("stitch") if isinstance(design.get("stitch"), dict) else {}
    design["stitch"] = {**stitch, "selected": design_plan.get("mode") == "stitch-mcp" or bool(stitch.get("selected")), "status": integration.get("status") or stitch.get("status") or "not_selected"}
    design.setdefault("artifacts", {"brief": str(state_dir / "design" / "BRIEF.md"), "wireframe": str(state_dir / "design" / "WIREFRAME.md"), "contract": str(state_dir / "design" / "DESIGN.md"), "plan": str(design_path)})
    pointers.setdefault("design", design)
    source = pointers.get("source")
    if not isinstance(source, dict):
        source = {}
    pointers["source"] = source
    return pointers


def project_id(root: str | Path) -> str:
    return hashlib.sha256(str(canonical(root)).encode("utf-8")).hexdigest()[:16]


def installed_skill_context(start: str | Path) -> dict[str, str | None]:
    """Identify a project-local installed skill without treating the skill as code."""
    path = canonical(start)
    if path.is_file():
        path = path.parent
    parts = path.parts
    for index, part in enumerate(parts):
        if part not in SKILL_HOST_DIRS or index + 2 >= len(parts) or parts[index + 1] != "skills":
            continue
        skill_root = Path(*parts[: index + 3])
        if not (skill_root / "SKILL.md").is_file():
            continue
        project_root = Path(*parts[:index]) if index else Path(parts[0])
        if project_root == Path.home().resolve():
            return {"skill_root": str(skill_root), "project_root": None}
        return {"skill_root": str(skill_root), "project_root": str(project_root)}
    return {"skill_root": None, "project_root": None}


def _resolution_start(start: str | Path) -> tuple[Path, str | None]:
    path = canonical(start)
    if path.is_file():
        path = path.parent
    skill_context = installed_skill_context(path)
    if skill_context["skill_root"] and skill_context["project_root"]:
        return canonical(skill_context["project_root"]), skill_context["skill_root"]
    if skill_context["skill_root"]:
        return path, skill_context["skill_root"]
    return path, None


def resolve_project_root(start: str | Path) -> tuple[Path | None, str]:
    """Return the nearest known project, git root, or marker project."""
    path, skill_root = _resolution_start(start)
    skill_context = installed_skill_context(start)
    if skill_root and not skill_context["project_root"]:
        return None, "installed_skill_path"
    current = path
    while True:
        paths = state_paths(current)
        if paths["state"].is_file() or paths["project"].is_file():
            return current, "project_from_installed_skill_path" if skill_root else "persisted_upstack_state"
        if (current / ".git").exists():
            return current, "project_from_installed_skill_path" if skill_root else "git_root"
        if has_project_markers(current):
            return current, "project_from_installed_skill_path" if skill_root else "project_markers"
        if current.parent == current:
            break
        current = current.parent
    return None, "broad_workspace"


def command_gate(start: str | Path, command: str) -> dict[str, Any]:
    path = canonical(start)
    root, detection = resolve_project_root(path)
    skill_context = installed_skill_context(path)
    result: dict[str, Any] = {
        "schema_version": 2,
        "command": command,
        "input_path": str(path),
        "project_root": str(root) if root else None,
        "detection": detection,
        "skill_resource_path": skill_context["skill_root"],
        "write_performed": False,
        "resume_required": False,
    }
    if root is None:
        is_resume = command.casefold() in RESUME_COMMANDS
        result.update({
            "status": "resume_unavailable" if is_resume else "project_selection_required",
            "command_allowed": False,
            "next_action": "offer_initialize_or_choose_existing_project" if is_resume else "ask_for_explicit_project_path_or_start_onboarding",
            "message": "No established Upstack project was found at this location; choose an existing project or start initialization." if is_resume else "The current location is a broad workspace; do not choose a child project implicitly.",
        })
        return result
    paths = state_paths(root)
    state = _read_json(paths["state"])
    project = _read_json(paths["project"])
    if state is None:
        is_resume = command.casefold() in RESUME_COMMANDS
        result.update({
            "status": "resume_unavailable" if is_resume else "onboarding_required",
            "command_allowed": command in {"init", "capabilities"},
            "next_action": "offer_initialize_or_choose_existing_project" if is_resume else "run_or_resume_onboarding_before_project_command",
            "message": "This project has no established Upstack state to resume; preserve the request and offer initialization." if is_resume else "This project has no valid persisted Upstack state. Start onboarding; do not restart a second curriculum.",
            "state_path": str(paths["root"]),
        })
        return result
    pointers = _resume_pointers(root, state, project)
    pointer_root = pointers.get("project_root") or (project or {}).get("root")
    if pointer_root and canonical(pointer_root) != root:
        result.update({
            "status": "state_pointer_mismatch",
            "command_allowed": False,
            "next_action": "ask_to_reconcile_project_pointer",
            "message": "Persisted project state points to a different canonical root; do not merge projects silently.",
            "state_path": str(paths["state"]),
            "pointer_root": str(canonical(pointer_root)),
        })
        return result
    current_lesson = state.get("current_lesson") if isinstance(state.get("current_lesson"), dict) else pointers.get("current_lesson", {})
    curriculum = state.get("curriculum") if isinstance(state.get("curriculum"), dict) else pointers.get("curriculum", {})
    design = state.get("design") if isinstance(state.get("design"), dict) else pointers.get("design", {})
    history = state.get("history") if isinstance(state.get("history"), list) else []
    if not history and Path(pointers["history_file"]).is_file():
        try:
            history = [line for line in Path(pointers["history_file"]).read_text(encoding="utf-8").splitlines() if line.strip()]
        except OSError:
            history = []
    result.update({
        "status": "known_project",
        "command_allowed": True,
        "next_action": state.get("next_action") or "resume_current_lesson",
        "resume_required": True,
        "state_path": str(paths["state"]),
        "project_id": state.get("project_id") or (project or {}).get("project_id") or project_id(root),
        "project": project or state.get("project", {}),
        "active_directive": state.get("active_directive"),
        "pointers": pointers,
        "resume_context": {
            "project_root": pointers.get("project_root") or str(root),
            "workspace_root": pointers.get("workspace_root"),
            "destination": pointers.get("destination"),
            "source": pointers.get("source"),
            "curriculum": curriculum or pointers.get("curriculum"),
            "current_lesson": current_lesson or pointers.get("current_lesson"),
            "design": design or pointers.get("design"),
            "history_file": pointers.get("history_file"),
            "history_count": len(history),
            "next_action": state.get("next_action") or "resume_current_lesson",
        },
        "state": {
            "onboarding": state.get("onboarding", {}),
            "mode": state.get("mode"),
            "current_stage": state.get("current_stage"),
            "completed_stages": state.get("completed_stages", []),
            "last_action": state.get("last_action"),
            "pending_confirmation": state.get("pending_confirmation"),
            "active_directive": state.get("active_directive"),
            "updated_at": state.get("updated_at"),
            "pointers": pointers,
            "curriculum": curriculum,
            "current_lesson": current_lesson,
            "design": design,
            "history_count": len(history),
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
