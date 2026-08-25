#!/usr/bin/env python3
"""Persist and resume Upstack's lesson-led apprenticeship.

This controller is intentionally conservative. It writes only after explicit
confirmation or the --write flag, never implements project code, and never
unlocks a lesson without learner evidence.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from lesson_plan import build_plan, current_lesson, render_lesson, resolve_lesson, write_artifacts
from onboarding import validate_destination
from package_manager import plan as package_manager_plan
from project_state import project_id, state_paths


SCHEMA_VERSION = 2
STATE_FILENAME = "STATE.json"
PLAN_FILENAME = "plan.json"


def _load_json(path: Path | None, default: Any) -> Any:
    if path is None:
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _state_paths(destination: Path) -> dict[str, Path]:
    paths = state_paths(destination)
    paths["plan"] = paths["root"] / "lessons" / PLAN_FILENAME
    paths["curriculum"] = paths["root"] / "lessons" / "CURRICULUM.md"
    paths["blueprint"] = paths["root"] / "lessons" / "LESSON_BLUEPRINT.md"
    paths["progress"] = paths["root"] / "lessons" / "progress.json"
    paths["history"] = paths["root"] / "HISTORY.jsonl"
    return paths


def _canonical_pointer(value: Any, base: Path) -> str | None:
    if value in (None, ""):
        return None
    raw = Path(str(value)).expanduser()
    return str((base / raw if not raw.is_absolute() else raw).resolve())


def _build_pointers(target: Path, paths: dict[str, Path], answers: dict[str, Any], plan: dict[str, Any], *, workspace: str | Path | None = None) -> dict[str, Any]:
    workspace_root = _canonical_pointer(workspace, target.parent) or _canonical_pointer(answers.get("workspace_root"), target.parent) or str(target.parent)
    source_path = _canonical_pointer(answers.get("source_path"), Path(workspace_root))
    source = {
        "kind": answers.get("source") or ("scratch" if answers.get("project_mode") == "scratch" else "unknown"),
        "path": source_path,
        "url": answers.get("source_url") or answers.get("repository_url") or answers.get("repo_url"),
        "detail": answers.get("source_detail"),
        "candidate_id": answers.get("candidate_id"),
    }
    source = {key: value for key, value in source.items() if value not in (None, "", [])}
    design_mode = answers.get("ui_design") or answers.get("design_mode") or "not_selected"
    stitch_status = answers.get("stitch_status") or ("selected-awaiting-confirmation" if design_mode == "stitch-mcp" else "not_selected")
    curriculum = {
        "id": plan.get("curriculum", {}).get("id"),
        "title": plan.get("curriculum", {}).get("title"),
        "plan": str(paths["plan"]),
        "markdown": str(paths["curriculum"]),
        "blueprint": str(paths["blueprint"]),
        "progress": str(paths["progress"]),
    }
    design = {
        "mode": design_mode,
        "status": answers.get("design_status") or ("portable" if design_mode == "portable" else "not_started"),
        "stitch": {"selected": design_mode == "stitch-mcp", "status": stitch_status, "remote_project": answers.get("stitch_project_id")},
        "artifacts": {
            "brief": str(paths["root"] / "design" / "BRIEF.md"),
            "wireframe": str(paths["root"] / "design" / "WIREFRAME.md"),
            "contract": str(paths["root"] / "design" / "DESIGN.md"),
            "plan": str(paths["root"] / "design" / "design-plan.json"),
        },
    }
    stage = plan["stages"][0]
    current_lesson = {"sequence": 1, "id": stage["id"], "title": stage["title"], "status": "not_generated", "path": None, "requested": False}
    return {
        "project_root": str(target),
        "workspace_root": workspace_root,
        "destination": str(target),
        "state_file": str(paths["state"]),
        "project_file": str(paths["project"]),
        "source": source,
        "curriculum": curriculum,
        "current_lesson": current_lesson,
        "design": design,
        "history_file": str(paths["history"]),
    }


def _record_history(state: dict[str, Any], paths: dict[str, Path], event: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    entry = {"at": _now(), "event": event, "current_stage": state.get("current_stage"), "next_action": state.get("next_action")}
    if details:
        entry["details"] = details
    state.setdefault("history", []).append(entry)
    paths["history"].parent.mkdir(parents=True, exist_ok=True)
    with paths["history"].open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")
    return entry


def _design_pointer(target: Path, design: dict[str, Any]) -> dict[str, Any]:
    plan_path = target / ".upstack" / "design" / "design-plan.json"
    try:
        if plan_path.is_file():
            saved = json.loads(plan_path.read_text(encoding="utf-8"))
            integration = saved.get("integration", {}) if isinstance(saved, dict) else {}
            design = {**design, "mode": saved.get("mode") or design.get("mode"), "status": integration.get("status") or design.get("status"), "screens": len(saved.get("screens", [])) if isinstance(saved, dict) and isinstance(saved.get("screens"), list) else design.get("screens", 0), "stitch": {**(design.get("stitch") or {}), "selected": saved.get("mode") == "stitch-mcp", "status": integration.get("status") or (design.get("stitch") or {}).get("status"), "remote_project": (design.get("stitch") or {}).get("remote_project")}}
    except (OSError, json.JSONDecodeError):
        pass
    return design


def _ensure_resume_fields(state: dict[str, Any], target: Path, paths: dict[str, Path], plan: dict[str, Any]) -> dict[str, Any]:
    """Upgrade legacy state in memory without writing unless the caller writes."""
    pointers = state.get("pointers") if isinstance(state.get("pointers"), dict) else {}
    pointers.setdefault("project_root", str(target))
    pointers.setdefault("workspace_root", str(target.parent))
    pointers.setdefault("destination", str(target))
    pointers.setdefault("state_file", str(paths["state"]))
    pointers.setdefault("project_file", str(paths["project"]))
    pointers.setdefault("history_file", str(paths["history"]))
    pointers.setdefault("source", {})
    pointers.setdefault("curriculum", {"id": plan.get("curriculum", {}).get("id"), "title": plan.get("curriculum", {}).get("title"), "plan": str(paths["plan"]), "markdown": str(paths["curriculum"]), "blueprint": str(paths["blueprint"]), "progress": str(paths["progress"])})
    stage = int(state.get("current_stage") or 1)
    stage = max(1, min(stage, len(plan.get("stages", [])) or 1))
    lesson = plan.get("stages", [])[stage - 1] if plan.get("stages") else {"id": f"stage-{stage:02d}", "title": f"Lesson {stage}"}
    current_lesson = state.get("current_lesson") if isinstance(state.get("current_lesson"), dict) else {}
    lesson_path = paths["root"] / "lessons" / "CURRENT_LESSON.md"
    lesson_requested = bool(current_lesson.get("requested")) or lesson_path.is_file()
    current_lesson = {"sequence": stage, "id": current_lesson.get("id") or lesson.get("id"), "title": current_lesson.get("title") or lesson.get("title"), "status": current_lesson.get("status") or ("active" if lesson_requested else "not_generated"), "path": current_lesson.get("path") or (str(lesson_path) if lesson_requested else None), "requested": lesson_requested}
    pointers["current_lesson"] = current_lesson
    design = _design_pointer(target, state.get("design") if isinstance(state.get("design"), dict) else {"mode": "not_selected", "status": "not_started", "stitch": {"selected": False, "status": "not_selected"}})
    pointers["design"] = design
    state["pointers"] = pointers
    state["curriculum"] = state.get("curriculum") if isinstance(state.get("curriculum"), dict) else pointers["curriculum"]
    state["current_lesson"] = current_lesson
    state["design"] = design
    state.setdefault("history", [])
    state.setdefault("attempts", [])
    state["schema_version"] = max(int(state.get("schema_version") or 1), SCHEMA_VERSION)
    return state


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _render_product_brief(brief: dict[str, Any]) -> str:
    lines = ["# Product Brief", "", "This is the learner-approved product or technical brief for the Upstack apprenticeship.", ""]
    preferred = [
        ("name", "Product"),
        ("problem", "Problem"),
        ("audience", "Audience"),
        ("primary_outcome", "Primary outcome"),
        ("constraints", "Constraints"),
        ("stack", "Intended stack"),
        ("primary_journey", "Primary journey"),
    ]
    used: set[str] = set()
    for key, label in preferred:
        if key in brief and brief[key] not in (None, "", []):
            value = brief[key]
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)
            lines += [f"## {label}", "", str(value), ""]
            used.add(key)
    extras = [(key, value) for key, value in brief.items() if key not in used and value not in (None, "", [])]
    if extras:
        lines += ["## Additional brief details", ""]
        for key, value in extras:
            if isinstance(value, list):
                value = ", ".join(str(item) for item in value)
            lines.append(f"- **{key}:** {value}")
        lines.append("")
    lines += ["## Ownership boundary", "", "The brief is a learning contract. Upstack teaches and reviews one slice at a time; it does not generate the complete implementation by default.", ""]
    return "\n".join(lines)


def _render_package_manager(report: dict[str, Any]) -> str:
    selected = report.get("selected") or report.get("detected") or report.get("recommended") or "pending learner choice"
    lines = [
        "# Package Manager Contract",
        "",
        f"- Selected or detected manager: **{selected}**",
        f"- Status: **{report.get('status', 'unknown')}**",
        f"- Detected: **{report.get('detected') or 'none'}**",
        f"- Declared: **{report.get('declared') or 'none'}**",
        f"- Lockfiles: **{', '.join(sum(report.get('lockfiles', {}).values(), [])) or 'none'}**",
        f"- Recommendation for new JavaScript/TypeScript work: **{report.get('recommended') or report.get('recommended_for_new_js_ts') or 'not applicable'}**",
        "",
        report.get("reason", "No package-manager decision has been recorded."),
        "",
        "Installation, lockfile migration, and package scripts require explicit learner confirmation. Do not mix package-manager commands in one stage.",
        "",
    ]
    return "\n".join(lines)


def _render_state_summary(state: dict[str, Any]) -> str:
    pointers = state.get("pointers", {})
    lesson = state.get("current_lesson", {})
    design = state.get("design", {})
    return "\n".join([
        "# Apprenticeship State",
        "",
        f"- Project: `{state.get('project', {}).get('name') or 'unnamed'}`",
        f"- Project root: `{pointers.get('project_root') or state.get('project', {}).get('destination') or 'unknown'}`",
        f"- Source pointer: `{(pointers.get('source') or {}).get('path') or (pointers.get('source') or {}).get('url') or 'none'}`",
        f"- Mode: `{state.get('mode')}`",
        f"- Curriculum: `{(state.get('curriculum') or {}).get('id') or 'unknown'}`",
        f"- Current lesson: `{lesson.get('id') or state.get('current_stage')}`",
        f"- Completed lessons: `{len(state.get('completed_stages', []))}`",
        f"- Design route: `{design.get('mode') or 'not selected'}` ({design.get('status') or 'unknown'})",
        f"- Last action: `{state.get('last_action')}`",
        f"- Next action: `{state.get('next_action')}`",
        f"- History entries: `{len(state.get('history', []))}`",
        "",
        "Use the tutor command to resume the current lesson. Do not restart onboarding when this state exists.",
        "",
    ])


def initialize_project(
    destination: str | Path,
    brief: dict[str, Any],
    learner_profile: dict[str, Any] | None = None,
    *,
    workspace: str | Path | None = None,
    mode: str = "guided-lesson",
    onboarding_answers: dict[str, Any] | None = None,
    active_directive: dict[str, Any] | None = None,
    confirm: bool = False,
) -> dict[str, Any]:
    target = Path(destination).expanduser()
    validation = validate_destination(target, workspace)
    paths = _state_paths(target.resolve())
    if not validation["valid"]:
        return {"status": "invalid_destination", "validation": validation, "write_performed": False}
    if paths["state"].exists():
        state = json.loads(paths["state"].read_text(encoding="utf-8"))
        return {"status": "already_initialized", "state": state, "resume": True, "write_performed": False}
    if not confirm:
        return {
            "status": "confirmation_required",
            "resolved_destination": validation["resolved_path"],
            "message": "Pass explicit confirmation before creating the destination or .upstack state.",
            "write_performed": False,
        }
    target = Path(validation["resolved_path"])
    target.mkdir(parents=True, exist_ok=True)
    profile = learner_profile or {}
    answers = onboarding_answers or {}
    selected_manager = answers.get("package_manager") if answers.get("package_manager") in {"pnpm", "npm", "bun", "yarn"} else None
    package_report = package_manager_plan(target, selected=selected_manager, new_project=answers.get("project_mode") == "scratch")
    plan = build_plan(brief, profile, mode=mode)
    pointers = _build_pointers(target, paths, answers, plan, workspace=workspace)
    lesson_dir = paths["root"] / "lessons"
    written = write_artifacts(plan, lesson_dir, 1, include_current=False)
    project_name = brief.get("name") or brief.get("title") or target.name
    project_record = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id(target),
        "root": str(target),
        "name": project_name,
        "created_at": _now(),
        "onboarding_status": "initialized",
        "state_file": str(paths["state"]),
    }
    state = {
        "schema_version": SCHEMA_VERSION,
        "created_at": _now(),
        "updated_at": _now(),
        "project_id": project_record["project_id"],
        "project": {"name": project_name, "destination": str(target)},
        "mode": mode,
        "learner_profile": profile,
        "package_manager": package_report.get("selected") or answers.get("package_manager"),
        "package_manager_plan": package_report,
        "onboarding": {"status": "initialized", "answers_persisted": True, "answers": onboarding_answers or {}},
        "pointers": pointers,
        "curriculum": pointers["curriculum"],
        "current_lesson": pointers["current_lesson"],
        "design": pointers["design"],
        "history": [],
        "current_stage": 1,
        "completed_stages": [],
        "attempts": [],
        "last_action": "initialized_with_live_directive" if active_directive else "initialized",
        "next_action": (active_directive or {}).get("resume_command") or "resume_current_lesson",
        "active_directive": active_directive,
        "pending_confirmation": None,
        "progression_gate": plan["progression_gate"],
    }
    _record_history(state, paths, "project_initialized", {"mode": mode, "project_root": str(target)})
    _write_json(paths["plan"], plan)
    project_record["pointers"] = pointers
    _write_json(paths["project"], project_record)
    _write_json(paths["state"], state)
    (paths["root"] / "PRODUCT_BRIEF.md").write_text(_render_product_brief(brief), encoding="utf-8")
    package_file = paths["root"] / "PACKAGE_MANAGER.md"
    package_file.write_text(_render_package_manager(package_report), encoding="utf-8")
    (paths["root"] / "STATE.md").write_text(_render_state_summary(state), encoding="utf-8")
    return {"status": "initialized", "project": project_record, "state": state, "written_files": written | {"project": str(paths["project"]), "state": str(paths["state"]), "plan": str(paths["plan"]), "product_brief": str(paths["root"] / "PRODUCT_BRIEF.md"), "package_manager": str(package_file)}, "write_performed": True}


def load_project(destination: str | Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path]]:
    target = Path(destination).expanduser().resolve()
    paths = _state_paths(target)
    if not paths["state"].exists() or not paths["plan"].exists():
        raise FileNotFoundError(f"No persisted Upstack apprenticeship found at {paths['root']}")
    state = json.loads(paths["state"].read_text(encoding="utf-8"))
    plan = json.loads(paths["plan"].read_text(encoding="utf-8"))
    return _ensure_resume_fields(state, target, paths, plan), plan, paths


def resume_project(destination: str | Path, identifier: Any = None, *, write: bool = False) -> dict[str, Any]:
    state, plan, paths = load_project(destination)
    lookup = resolve_lesson(plan, identifier)
    if lookup["status"] in {"ambiguous", "not_found"}:
        return {"status": lookup["status"], "identifier": lookup.get("identifier"), "candidates": lookup.get("candidates", []), "curriculum": plan.get("curriculum"), "resume": True, "write_performed": False}
    selected = int(lookup["stage"])
    current_stage = int(state["current_stage"])
    if selected > current_stage and selected not in state.get("completed_stages", []):
        return {"status": "locked", "identifier": lookup.get("identifier"), "curriculum": plan.get("curriculum"), "stage": selected, "title": lookup["lesson"].get("title"), "current_stage": current_stage, "unlock_after": current_stage, "message": "This lesson is on the curriculum but is locked until the current stage evidence gate is complete.", "resume": True, "write_performed": False}
    lesson = current_lesson(plan, selected)
    pointers = state.get("pointers", {}) if isinstance(state.get("pointers"), dict) else {}
    result = {"status": "resumed", "identifier": lookup.get("identifier"), "curriculum": plan.get("curriculum"), "state": state, "lesson": lesson, "pointers": pointers, "resume_context": {"project_root": pointers.get("project_root") or str(Path(destination).expanduser().resolve()), "source": pointers.get("source"), "curriculum": state.get("curriculum") or pointers.get("curriculum"), "current_lesson": state.get("current_lesson") or pointers.get("current_lesson"), "design": state.get("design") or pointers.get("design"), "next_action": state.get("next_action")}, "state_file": str(paths["state"]), "resume": True, "write_performed": False}
    if write:
        lesson_path = paths["root"] / "lessons" / "CURRENT_LESSON.md"
        lesson_path.parent.mkdir(parents=True, exist_ok=True)
        lesson_path.write_text(render_lesson(lesson, plan), encoding="utf-8")
        state["current_lesson"] = {"sequence": selected, "id": lesson["id"], "title": lesson["title"], "status": "active", "path": str(lesson_path), "requested": True, "requested_identifier": lookup.get("identifier"), "requested_at": _now()}
        if isinstance(state.get("pointers"), dict):
            state["pointers"]["current_lesson"] = state["current_lesson"]
        state["last_action"] = "lesson_requested"
        state["next_action"] = "record_current_lesson_evidence"
        _record_history(state, paths, "lesson_requested", {"identifier": lookup.get("identifier"), "lesson_id": lesson["id"], "path": str(lesson_path)})
        state["updated_at"] = _now()
        _write_json(paths["state"], state)
        (paths["root"] / "STATE.md").write_text(_render_state_summary(state), encoding="utf-8")
        result["written_file"] = str(lesson_path)
        result["write_performed"] = True
    return result


def record_evidence(destination: str | Path, stage: int, evidence: dict[str, Any], *, write: bool = False) -> dict[str, Any]:
    state, plan, paths = load_project(destination)
    if stage != int(state["current_stage"]):
        return {"status": "wrong_stage", "current_stage": state["current_stage"], "requested_stage": stage, "write_performed": False}
    required = ["attempt", "verification", "explanation", "feedback"]
    present = {key: evidence.get(key) not in (None, "", [], {}) for key in required}
    complete = all(present.values())
    result = {"status": "ready_to_unlock" if complete else "evidence_incomplete", "stage": stage, "evidence_present": present, "unlocked": False, "write_performed": False}
    if not write:
        return result
    attempt_record = {"stage": stage, "recorded_at": _now(), "evidence": evidence, "complete": complete}
    state.setdefault("attempts", []).append(attempt_record)
    if complete:
        state["completed_stages"].append(stage)
        state["completed_stages"] = sorted(set(state["completed_stages"]))
        next_stage = stage + 1
        state["current_stage"] = next_stage if next_stage <= len(plan["stages"]) else stage
        state["last_action"] = "stage_completed" if next_stage <= len(plan["stages"]) else "curriculum_completed"
        state["next_action"] = "resume_current_lesson" if next_stage <= len(plan["stages"]) else "portfolio_or_review"
        result["unlocked"] = next_stage <= len(plan["stages"])
        if next_stage <= len(plan["stages"]):
            write_artifacts(plan, paths["root"] / "lessons", next_stage, include_current=False, completed_stages=state["completed_stages"])
            next_item = plan["stages"][next_stage - 1]
            state["current_lesson"] = {"sequence": next_stage, "id": next_item["id"], "title": next_item["title"], "status": "not_generated", "path": None, "requested": False}
            if isinstance(state.get("pointers"), dict):
                state["pointers"]["current_lesson"] = state["current_lesson"]
        else:
            state["current_lesson"] = {"sequence": stage, "id": plan["stages"][stage - 1]["id"], "title": plan["stages"][stage - 1]["title"], "status": "completed", "path": (state.get("current_lesson") or {}).get("path"), "requested": True}
    else:
        state["last_action"] = "evidence_recorded_stage_remains_active"
        state["next_action"] = "resume_current_lesson"
    _record_history(state, paths, "evidence_recorded", {"stage": stage, "complete": complete, "evidence_present": present})
    state["updated_at"] = _now()
    _write_json(paths["state"], state)
    (paths["root"] / "STATE.md").write_text(_render_state_summary(state), encoding="utf-8")
    result["state"] = state
    result["write_performed"] = True
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="initialize a confirmed project and persist its lesson plan")
    init.add_argument("--destination", required=True, type=Path)
    init.add_argument("--workspace", type=Path, help="broad workspace used to validate the destination")
    init.add_argument("--brief-file", required=True, type=Path)
    init.add_argument("--learner-profile-file", type=Path)
    init.add_argument("--mode", choices=["guided-lesson", "blueprint-then-lessons", "attempt-first", "assisted-slice"], default="guided-lesson")
    init.add_argument("--answers-file", type=Path, help="JSON containing normalized onboarding answers")
    init.add_argument("--directive-file", type=Path, help="JSON containing an approved live-session directive to carry into state")
    init.add_argument("--confirm", action="store_true", help="confirm local folder and .upstack writes")

    status = sub.add_parser("status", help="show persisted project and lesson status")
    status.add_argument("--destination", required=True, type=Path)

    curriculum = sub.add_parser("curriculum", help="show the persisted curriculum without generating a lesson")
    curriculum.add_argument("--destination", required=True, type=Path)

    lesson = sub.add_parser("lesson", help="generate one requested curriculum lesson")
    lesson.add_argument("--destination", required=True, type=Path)
    lesson.add_argument("identifier", nargs="?", help="curriculum ID, day number, stage ID, alias, or title")
    lesson.add_argument("--stage", type=int, help="legacy numeric alias for the lesson identifier")
    lesson.add_argument("--write", action="store_true", help="write only the requested lesson artifact")

    record = sub.add_parser("record", help="record learner evidence and optionally unlock the next stage")
    record.add_argument("--destination", required=True, type=Path)
    record.add_argument("--stage", required=True, type=int)
    record.add_argument("--evidence-file", required=True, type=Path)
    record.add_argument("--write", action="store_true", help="persist the attempt and unlock only when evidence is complete")

    args = parser.parse_args()
    if args.command == "init":
        result = initialize_project(args.destination, _load_json(args.brief_file, {}), _load_json(args.learner_profile_file, {}), workspace=args.workspace, mode=args.mode, onboarding_answers=_load_json(args.answers_file, {}), active_directive=_load_json(args.directive_file, {}), confirm=args.confirm)
    elif args.command == "status":
        state, plan, paths = load_project(args.destination)
        result = {"status": "active", "curriculum": plan.get("curriculum"), "state": state, "stage_count": len(plan["stages"]), "state_file": str(paths["state"]), "resume": True, "write_performed": False}
    elif args.command == "curriculum":
        state, plan, paths = load_project(args.destination)
        result = {"status": "curriculum", "curriculum": plan.get("curriculum"), "stages": [{"id": item["id"], "day": item.get("day"), "day_id": item.get("day_id"), "title": item["title"], "status": "complete" if int(item["sequence"]) in state.get("completed_stages", []) else ("current" if int(item["sequence"]) == int(state["current_stage"]) else "locked")} for item in plan["stages"]], "resume": True, "write_performed": False}
    elif args.command == "lesson":
        result = resume_project(args.destination, args.identifier or args.stage, write=args.write)
    else:
        result = record_evidence(args.destination, args.stage, _load_json(args.evidence_file, {}), write=args.write)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
