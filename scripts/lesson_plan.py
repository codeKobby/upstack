#!/usr/bin/env python3
"""Plan lesson-led fresh-start projects without generating the whole implementation.

The helper produces a complete roadmap and one current lesson contract. It does
not scaffold, write project code, run commands, or assess an attempt unless a
host explicitly performs those actions after the learner's confirmation.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2
CURRICULUM_ID = "upstack-fresh-start-core"
NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}

STAGE_TEMPLATES = [
    {
        "id": "stage-01-orient",
        "title": "Orient and make the first decision",
        "outcome": "Explain the product or technical goal, users, constraints, and the smallest useful first slice.",
        "learner_work": "State the goal in your own words, choose one first-slice behavior, and predict how you will know it works.",
        "agent_role": "Explain only the concepts needed for the decision, ask one focused question, and record the learner's decision.",
        "evidence": ["learner explanation", "chosen first slice", "acceptance check"],
    },
    {
        "id": "stage-02-foundation",
        "title": "Build the runnable foundation",
        "outcome": "Run the smallest project foundation and explain its entrypoint, data flow, and verification command.",
        "learner_work": "Create or approve only the minimum foundation, run it, trace the entrypoint, and explain one choice.",
        "agent_role": "Provide a tiny example or targeted scaffold only when requested and confirmed; do not implement the feature on the learner's behalf.",
        "evidence": ["runnable check", "entrypoint trace", "learner-authored decision"],
    },
    {
        "id": "stage-03-vertical-slice",
        "title": "Implement one vertical slice",
        "outcome": "Implement one user-visible or system-visible behavior across its relevant layers.",
        "learner_work": "Predict the path, write the slice, run approved checks, and describe one edge case.",
        "agent_role": "Teach the next concept, ask for a plan before code, review the learner's work, and give a hint before a patch.",
        "evidence": ["learner-authored code", "approved test or check", "edge-case explanation"],
    },
    {
        "id": "stage-04-expansion",
        "title": "Expand by transfer",
        "outcome": "Extend the first slice to a nearby feature while reusing concepts deliberately rather than copying blindly.",
        "learner_work": "Compare the new task with the prior slice, choose what to reuse, implement the delta, and update checks.",
        "agent_role": "Ask the learner to identify the delta, expose trade-offs, and review only the bounded change.",
        "evidence": ["delta plan", "learner implementation", "updated verification"],
    },
    {
        "id": "stage-05-hardening",
        "title": "Harden and explain",
        "outcome": "Improve failure handling, tests, accessibility or security, maintainability, and operational clarity for the learned slice.",
        "learner_work": "Find a risk, propose a mitigation, implement one hardening change, and explain its trade-off.",
        "agent_role": "Use questions and targeted review to surface failure modes; do not silently harden the code.",
        "evidence": ["risk statement", "mitigation", "regression check", "trade-off explanation"],
    },
    {
        "id": "stage-06-capstone",
        "title": "Independent capstone slice",
        "outcome": "Design and implement a new bounded slice with reduced scaffolding, then teach back the important decisions.",
        "learner_work": "Own the plan, implementation, verification, and explanation; request help only at the current blocker.",
        "agent_role": "Act as reviewer and interviewer, fade support, and assess the learner's evidence without taking over.",
        "evidence": ["independent plan", "implementation", "verification", "teach-back"],
    },
]


def _load_json(path: Path | None, default: Any) -> Any:
    if path is None:
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(f"{key} {_text(item)}" for key, item in value.items())
    return str(value)


def build_plan(brief: dict[str, Any], learner_profile: dict[str, Any] | None = None, *, mode: str = "guided-lesson") -> dict[str, Any]:
    learner_profile = learner_profile or {}
    if mode not in {"guided-lesson", "blueprint-then-lessons", "attempt-first", "assisted-slice"}:
        raise ValueError(f"unsupported fresh-start mode: {mode}")
    learner_name = _text(learner_profile.get("name") or "learner")
    stages = []
    for index, template in enumerate(STAGE_TEMPLATES, start=1):
        item = dict(template)
        item["sequence"] = index
        item["day"] = index
        item["day_id"] = f"day-{index:02d}"
        word = NUMBER_WORDS.get(index)
        item["aliases"] = [str(index), f"day {index}", f"day-{index:02d}", f"stage {index}", f"stage-{index:02d}"] + ([f"day {word}", f"day-{word}", f"stage {word}", f"stage-{word}"] if word else [])
        item["status"] = "current" if index == 1 else "locked"
        item["mode"] = mode
        stages.append(item)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "upstack-lesson-led-fresh-start",
        "curriculum": {"id": CURRICULUM_ID, "title": "Fresh-start project apprenticeship", "version": 1, "lesson_generation": "explicit-request-only"},
        "project_brief": brief,
        "learner": {"name": learner_name, "profile": learner_profile},
        "mode": mode,
        "default_behavior": "teach_then_learner_attempt_then_verify_then_feedback_then_unlock",
        "agent_boundary": {
            "default": "guide_not_take_over",
            "may_do": ["explain current concept", "show a small isolated example when useful", "ask for a learner plan", "review learner work", "run explicitly approved checks"],
            "must_not_do": ["generate every lesson at once", "implement the meaningful feature before the learner attempts it", "silently rewrite learner code", "unlock the next stage without evidence", "scaffold or write files without confirmation"],
            "assisted_slice": "If selected, assistance is limited to the exact confirmed current slice after the learner has attempted or requested a concrete blocker; explain every generated change and keep it reviewable.",
        },
        "progression_gate": {
            "required_before_unlock": ["learner attempt", "approved verification", "learner explanation or teach-back", "feedback recorded"],
            "failure_behavior": "Keep the stage active, correct the earliest material gap, offer a hint or smaller variant, and reassess the same concept.",
        },
        "stages": stages,
    }


def _normalize_identifier(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().casefold())


def resolve_lesson(plan: dict[str, Any], identifier: Any = None) -> dict[str, Any]:
    """Resolve a curriculum, day, stage ID, alias, or title without generating content."""
    raw = "" if identifier is None else str(identifier).strip()
    normalized = _normalize_identifier(raw)
    curriculum = plan.get("curriculum", {"id": CURRICULUM_ID, "title": "Fresh-start project apprenticeship"})
    if not normalized or normalized in {_normalize_identifier(curriculum.get("id")), "curriculum", "roadmap", "current"}:
        stage_number = next((int(item["sequence"]) for item in plan["stages"] if item.get("status") == "current"), 1)
        return {"status": "curriculum" if normalized in {_normalize_identifier(curriculum.get("id")), "curriculum", "roadmap"} else "resolved", "identifier": raw or "current", "curriculum": curriculum, "stage": stage_number, "lesson": plan["stages"][stage_number - 1]}
    for item in plan["stages"]:
        values = {item.get("id"), item.get("day_id"), item.get("title"), *(item.get("aliases") or [])}
        if normalized in {_normalize_identifier(value) for value in values}:
            return {"status": "resolved", "identifier": raw, "curriculum": curriculum, "stage": int(item["sequence"]), "lesson": item}
    word_match = next((number for number, word in NUMBER_WORDS.items() if normalized in {f"day {word}", f"day-{word}", f"stage {word}", f"stage-{word}", word}), None)
    if word_match is not None and word_match <= len(plan["stages"]):
        item = plan["stages"][word_match - 1]
        return {"status": "resolved", "identifier": raw, "curriculum": curriculum, "stage": word_match, "lesson": item}
    match = re.fullmatch(r"(?:day|stage)[ -]?(\d+)", normalized) or re.fullmatch(r"(\d+)", normalized)
    if match:
        number = int(match.group(1))
        if 1 <= number <= len(plan["stages"]):
            item = plan["stages"][number - 1]
            return {"status": "resolved", "identifier": raw, "curriculum": curriculum, "stage": number, "lesson": item}
    title_matches = [item for item in plan["stages"] if normalized and normalized in _normalize_identifier(item.get("title"))]
    if len(title_matches) == 1:
        item = title_matches[0]
        return {"status": "resolved", "identifier": raw, "curriculum": curriculum, "stage": int(item["sequence"]), "lesson": item}
    if len(title_matches) > 1:
        return {"status": "ambiguous", "identifier": raw, "candidates": [{"id": item["id"], "day": item["day"], "title": item["title"]} for item in title_matches]}
    return {"status": "not_found", "identifier": raw, "candidates": [{"id": item["id"], "day": item["day"], "title": item["title"]} for item in plan["stages"]]}


def current_lesson(plan: dict[str, Any], stage: int = 1) -> dict[str, Any]:
    if stage < 1 or stage > len(plan["stages"]):
        raise ValueError(f"stage must be between 1 and {len(plan['stages'])}")
    current = dict(plan["stages"][stage - 1])
    current["status"] = "current"
    current["lesson_flow"] = [
        "State the lesson outcome and why it matters to this project.",
        "Connect one concept to the current brief or stack.",
        "Ask the learner to predict, choose, or explain before showing a solution.",
        "Give the learner one bounded implementation or investigation task.",
        "Run only approved checks and inspect the learner's evidence.",
        "Give reasoned feedback, then unlock or repeat a smaller variant.",
    ]
    current["learner_submission"] = {
        "required": current["evidence"],
        "preserve_original": True,
        "output_options": ["inline", "markdown", "both"],
    }
    return current


def render_blueprint(plan: dict[str, Any]) -> str:
    lines = ["# Fresh-Start Lesson Blueprint", "", f"- Mode: `{plan['mode']}`", f"- Behavior: `{plan['default_behavior']}`", "", "The project is a complete curriculum, but only the current lesson is delivered. Meaningful project work remains learner-authored by default.", "", "| Stage | Outcome | Learner evidence | Status |", "| --- | --- | --- | --- |"]
    for stage in plan["stages"]:
        lines.append(f"| {stage['sequence']}. {stage['title']} | {stage['outcome']} | {', '.join(stage['evidence'])} | `{stage['status']}` |")
    lines += ["", "## Progression gate", "", f"- Required: {', '.join(plan['progression_gate']['required_before_unlock'])}", f"- If incomplete: {plan['progression_gate']['failure_behavior']}", "", "## Agent boundary", ""]
    lines.extend(f"- May: {item}" for item in plan["agent_boundary"]["may_do"])
    lines.extend(f"- Must not: {item}" for item in plan["agent_boundary"]["must_not_do"])
    return "\n".join(lines) + "\n"


def render_lesson(lesson: dict[str, Any], plan: dict[str, Any]) -> str:
    lines = [f"# Current Lesson — {lesson['title']}", "", f"**Outcome:** {lesson['outcome']}", "", f"**Mode:** `{plan['mode']}`", "", "## Your work", "", lesson["learner_work"], "", "## How Upstack will guide", "", lesson["agent_role"], "", "## Lesson flow", ""]
    lines.extend(f"{index}. {item}" for index, item in enumerate(lesson["lesson_flow"], start=1))
    lines += ["", "## Evidence to submit", ""]
    lines.extend(f"- {item}" for item in lesson["evidence"])
    lines += ["", "> The original attempt is preserved. The next stage is not unlocked until the learner has an attempt, approved verification, an explanation or teach-back, and recorded feedback.", ""]
    return "\n".join(lines)


def render_curriculum(plan: dict[str, Any]) -> str:
    return render_blueprint(plan).replace("# Fresh-Start Lesson Blueprint", "# Curriculum")


def write_artifacts(plan: dict[str, Any], output_dir: Path, stage: int = 1, *, include_current: bool = True, completed_stages: list[int] | None = None) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "curriculum": output_dir / "CURRICULUM.md",
        "blueprint": output_dir / "LESSON_BLUEPRINT.md",
        "progress": output_dir / "progress.json",
    }
    files["curriculum"].write_text(render_curriculum(plan), encoding="utf-8")
    files["blueprint"].write_text(render_blueprint(plan), encoding="utf-8")
    if include_current:
        files["current_lesson"] = output_dir / "CURRENT_LESSON.md"
        files["current_lesson"].write_text(render_lesson(current_lesson(plan, stage), plan), encoding="utf-8")
    files["progress"].write_text(json.dumps({"curriculum_id": plan.get("curriculum", {}).get("id", CURRICULUM_ID), "current_stage": stage, "completed_stages": completed_stages or [], "mode": plan["mode"]}, indent=2) + "\n", encoding="utf-8")
    return {key: str(value) for key, value in files.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brief-file", type=Path, required=True, help="JSON containing the approved project brief")
    parser.add_argument("--learner-profile-file", type=Path, help="JSON containing learner experience and current skill evidence")
    parser.add_argument("--mode", choices=["guided-lesson", "blueprint-then-lessons", "attempt-first", "assisted-slice"], default="guided-lesson")
    parser.add_argument("--stage", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=Path(".upstack/lessons"))
    parser.add_argument("--write", action="store_true", help="write lesson artifacts; never writes without this flag")
    args = parser.parse_args()
    plan = build_plan(_load_json(args.brief_file, {}), _load_json(args.learner_profile_file, {}), mode=args.mode)
    lesson = current_lesson(plan, args.stage)
    result = {"plan": plan, "current_lesson": lesson}
    if args.write:
        result["written_files"] = write_artifacts(plan, args.output_dir, args.stage)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
