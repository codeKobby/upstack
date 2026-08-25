#!/usr/bin/env python3
"""Route Upstack commands through project state before any workflow or side effect.

This helper is controller-only. It reads the current workspace and persisted
`.upstack/` state, then returns a dispatch plan for the host agent. It never
writes project files, generates lessons, calls MCP tools, installs packages,
clones repositories, or executes learner-project commands.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from project_state import command_gate
except ImportError:  # pragma: no cover - supports direct package loading
    from .project_state import command_gate


HELP_COMMANDS = {"help", "upstack-help"}
RESUME_COMMANDS = {"continue", "resume"}
ALIASES = {"resume": "continue", "upstack-help": "help"}
PROJECT_COMMANDS = {
    "upstack", "init", "inventory", "concepts", "focus", "blueprint", "reverse",
    "build", "stage", "curriculum", "lesson", "hint", "assess", "discover",
    "choose", "source", "role", "portfolio", "status", "update", "continue",
}


def _canonical_command(command: str | None) -> str:
    value = (command or "upstack").strip().casefold() or "upstack"
    return ALIASES.get(value, value)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _state_value(gate: dict[str, Any], key: str, default: Any = None) -> Any:
    state = gate.get("state") if isinstance(gate.get("state"), dict) else {}
    if key in state:
        return state[key]
    raw = gate.get("raw_state") if isinstance(gate.get("raw_state"), dict) else {}
    return raw.get(key, default)


def _resume_context(gate: dict[str, Any]) -> dict[str, Any]:
    value = gate.get("resume_context")
    return value if isinstance(value, dict) else {}


def _current_lesson(gate: dict[str, Any]) -> dict[str, Any]:
    context = _resume_context(gate)
    value = context.get("current_lesson")
    if isinstance(value, dict):
        return value
    state = gate.get("state") if isinstance(gate.get("state"), dict) else {}
    value = state.get("current_lesson")
    return value if isinstance(value, dict) else {}


def _design(gate: dict[str, Any]) -> dict[str, Any]:
    context = _resume_context(gate)
    value = context.get("design")
    return value if isinstance(value, dict) else {}


def _has_generated_lesson(gate: dict[str, Any]) -> bool:
    lesson = _current_lesson(gate)
    status = str(lesson.get("status") or "").casefold()
    if status in {"active", "generated", "in_progress", "complete", "completed"}:
        return True
    path = lesson.get("path")
    if path:
        try:
            return Path(str(path)).is_file()
        except OSError:
            return False
    root = gate.get("project_root")
    if root:
        return (Path(str(root)) / ".upstack" / "lessons" / "CURRENT_LESSON.md").is_file()
    return False


def _lesson_identifier(gate: dict[str, Any]) -> str | None:
    lesson = _current_lesson(gate)
    identifier = lesson.get("id") or lesson.get("sequence")
    return str(identifier) if identifier not in (None, "") else None


def _design_pending(gate: dict[str, Any]) -> bool:
    design = _design(gate)
    mode = str(design.get("mode") or "").casefold()
    status = str(design.get("status") or design.get("integration_status") or "").casefold()
    if mode in {"stitch-mcp", "stitch", "visual"} and status not in {"complete", "completed", "approved", "declined", "unavailable"}:
        return True
    return status in {"pending", "awaiting_confirmation", "awaiting_approval", "design_required"}


def _tutor_dispatch(gate: dict[str, Any], command: str, args: list[str], *, write: bool = False) -> dict[str, Any]:
    root = gate.get("project_root")
    dispatch: dict[str, Any] = {
        "helper": "scripts/tutor.py",
        "command": command,
        "destination": root,
        "arguments": list(args),
        "write": write,
        "side_effects": "write only when explicitly confirmed and requested" if write else "read-only",
    }
    return dispatch


def _known_project_route(gate: dict[str, Any], command: str, args: list[str]) -> dict[str, Any]:
    context = _resume_context(gate)
    next_action = str(context.get("next_action") or gate.get("next_action") or "resume_current_lesson")
    lesson_id = _lesson_identifier(gate)

    if command == "curriculum":
        return {"action": "show_curriculum", "dispatch": _tutor_dispatch(gate, "curriculum", args)}
    if command == "lesson":
        identifier = args[0] if args else lesson_id
        if not identifier:
            return {"action": "ask_for_lesson_identifier", "dispatch": None}
        return {"action": "show_requested_lesson", "lesson_identifier": identifier, "dispatch": _tutor_dispatch(gate, "lesson", [identifier])}
    if command == "status":
        return {"action": "show_project_status", "dispatch": _tutor_dispatch(gate, "status", args)}
    if command in RESUME_COMMANDS or command == "upstack":
        if _design_pending(gate):
            return {
                "action": "resume_design_route",
                "next_action": next_action,
                "design": context.get("design"),
                "dispatch": {"helper": "scripts/ui_design.py", "command": "read-local-plan", "destination": gate.get("project_root"), "side_effects": "read-only"},
            }
        if _has_generated_lesson(gate) and lesson_id:
            return {
                "action": "resume_current_lesson",
                "next_action": next_action,
                "lesson_identifier": lesson_id,
                "dispatch": _tutor_dispatch(gate, "lesson", [lesson_id]),
            }
        return {
            "action": "show_curriculum_and_current_lesson",
            "next_action": next_action,
            "current_lesson": context.get("current_lesson"),
            "dispatch": _tutor_dispatch(gate, "curriculum", args),
            "lesson_generation": "not automatic; generate only after an explicit lesson identifier",
        }
    return {
        "action": "dispatch_requested_project_command",
        "requested_command": command,
        "arguments": list(args),
        "next_action": next_action,
        "dispatch": {"helper": "host-agent", "command": command, "destination": gate.get("project_root"), "arguments": list(args), "side_effects": "follow the command-specific confirmation contract"},
    }


def route(path: str | Path, command: str = "upstack", args: list[str] | None = None) -> dict[str, Any]:
    """Return a controller-only route plan for one Upstack invocation."""
    requested = _canonical_command(command)
    command_args = list(args or [])
    if requested == "help":
        return {
            "schema_version": 1,
            "command": command,
            "normalized_command": "help",
            "input_path": str(Path(path).expanduser().resolve()),
            "status": "help_available",
            "action": "show_help",
            "dispatch": None,
            "must_not": ["resolve-project-for-help", "ask-initial-intent", "start-onboarding", "use-generic-/help"],
        }

    gate = command_gate(path, requested)
    result: dict[str, Any] = {
        "schema_version": 1,
        "command": command,
        "normalized_command": requested,
        "input_path": gate.get("input_path"),
        "status": gate.get("status"),
        "project_root": gate.get("project_root"),
        "skill_resource_path": gate.get("skill_resource_path"),
        "gate": gate,
    }
    if gate.get("status") == "known_project":
        result.update(_known_project_route(gate, requested, command_args))
        result["resume_context"] = gate.get("resume_context")
        result["onboarding"] = False
        return result
    if requested in RESUME_COMMANDS:
        result.update({
            "action": "offer_initialize_or_choose_existing_project",
            "message": gate.get("message") or "No established Upstack project was found at the resolved location.",
            "onboarding": False,
            "must_not": ["ask-initial-intent", "inspect-installed-skill-as-project", "create-second-curriculum"],
        })
        return result
    result.update({
        "action": "run_or_resume_onboarding",
        "requested_command": requested,
        "arguments": command_args,
        "onboarding": True,
        "message": gate.get("message") or "Complete onboarding before project work.",
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--command", default="upstack", help="Upstack command or alias: help, continue, resume, lesson, status, or another project command")
    parser.add_argument("command_args", nargs="*", help="arguments forwarded to the selected command")
    parser.add_argument("--json", action="store_true", help="emit JSON controller data")
    args = parser.parse_args()
    command = args.command
    command_args = list(args.command_args)
    if command.casefold() == "upstack" and command_args and command_args[0].casefold() in (PROJECT_COMMANDS | HELP_COMMANDS | RESUME_COMMANDS):
        command = command_args.pop(0)
    print(json.dumps(route(args.path, command, command_args), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

