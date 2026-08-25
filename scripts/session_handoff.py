#!/usr/bin/env python3
"""Persist an approved change request from an already-running Upstack session."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _paths(destination: str | Path) -> dict[str, Path]:
    root = Path(destination).expanduser().resolve() / ".upstack"
    return {
        "root": root,
        "state": root / "STATE.json",
        "state_md": root / "STATE.md",
        "handoff": root / "SESSION_HANDOFF.json",
        "handoff_md": root / "SESSION_HANDOFF.md",
    }


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        if not path.is_file():
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _normalize_request(request: dict[str, Any]) -> dict[str, Any]:
    changes = request.get("changes", {})
    if not isinstance(changes, dict):
        changes = {"requested_change": str(changes)}
    preserve = request.get("preserve", ["project_identity", "onboarding_answers", "curriculum", "current_stage", "learner_evidence"])
    if not isinstance(preserve, list):
        preserve = [str(preserve)]
    return {
        "request_id": str(request.get("request_id") or f"change-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S') }"),
        "reason": str(request.get("reason") or "Learner correction from the active chat"),
        "changes": changes,
        "preserve": [str(item) for item in preserve],
        "resume_command": str(request.get("resume_command") or "resume_current_workflow"),
        "requested_at": str(request.get("requested_at") or _now()),
        "source": "active-chat-correction",
    }


def prepare_handoff(destination: str | Path, request: dict[str, Any]) -> dict[str, Any]:
    paths = _paths(destination)
    state = _load_json(paths["state"])
    normalized = _normalize_request(request)
    result = {
        "status": "confirmation_required" if state else "session_only_pending",
        "request": normalized,
        "current_state": {
            "project_id": state.get("project_id"),
            "current_stage": state.get("current_stage"),
            "last_action": state.get("last_action"),
            "next_action": state.get("next_action"),
        } if state else None,
        "continuation": "pause_stale_route_apply_change_then_resume_without_restarting_onboarding",
        "preserve": normalized["preserve"],
        "must_not": ["restart_initial_intent", "discard_completed_answers", "create_second_curriculum", "apply_unconfirmed_project_or_remote_writes"],
        "write_performed": False,
    }
    if not state:
        result["message"] = "No persisted project state was found; keep this directive in the active session and persist it after project initialization."
    else:
        result["message"] = "Confirm this change request, then apply it and resume the current project workflow from its stored state."
    return result


def _render_handoff(record: dict[str, Any]) -> str:
    request = record["request"]
    lines = [
        "# Live-Session Handoff",
        "",
        "This record captures an approved correction from the active chat. It changes the route or teaching contract without restarting project onboarding.",
        "",
        f"- Request: `{request['request_id']}`",
        f"- Reason: {request['reason']}",
        f"- Resume command: `{request['resume_command']}`",
        f"- Applied at: `{record['applied_at']}`",
        "",
        "## Changes",
        "",
    ]
    for key, value in request["changes"].items():
        lines.append(f"- **{key}:** {value}")
    lines += ["", "## Preserve", ""]
    lines.extend(f"- {item}" for item in request["preserve"])
    lines += ["", "## Continuation rule", "", "Pause the stale route, apply this directive, and resume from the persisted project state. Do not repeat completed onboarding questions or create a second curriculum.", ""]
    return "\n".join(lines)


def apply_handoff(destination: str | Path, request: dict[str, Any], *, confirm: bool = False) -> dict[str, Any]:
    paths = _paths(destination)
    state = _load_json(paths["state"])
    prepared = prepare_handoff(destination, request)
    if not state:
        return prepared
    if not confirm:
        return prepared
    normalized = prepared["request"]
    applied_at = _now()
    record = {"schema_version": SCHEMA_VERSION, "applied_at": applied_at, "request": normalized, "continuation": prepared["continuation"]}
    state["active_directive"] = normalized
    state["last_action"] = "live_change_applied"
    state["next_action"] = normalized["resume_command"]
    state["pending_confirmation"] = None
    state["updated_at"] = applied_at
    _write_json(paths["handoff"], record)
    paths["handoff_md"].write_text(_render_handoff(record), encoding="utf-8")
    _write_json(paths["state"], state)
    if paths["state_md"].exists():
        text = paths["state_md"].read_text(encoding="utf-8")
        text = text.rstrip() + f"\n- Active directive: `{normalized['request_id']}`\n- Next action: `{normalized['resume_command']}`\n"
        paths["state_md"].write_text(text, encoding="utf-8")
    return {"status": "applied", "request": normalized, "state": state, "handoff_file": str(paths["handoff"]), "resume": True, "write_performed": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "apply"):
        command = sub.add_parser(name)
        command.add_argument("--destination", required=True, type=Path)
        command.add_argument("--request-file", required=True, type=Path)
        if name == "apply":
            command.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    request = _load_json(args.request_file) or {}
    result = prepare_handoff(args.destination, request) if args.command == "prepare" else apply_handoff(args.destination, request, confirm=args.confirm)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
