#!/usr/bin/env python3
"""Plan one relevant Upstack onboarding question at a time.

The helper never asks the learner directly and never writes files. It emits a
question specification for a host-native question/choice UI or text fallback.
The first question is deliberately context-independent: callers should not
inspect a repository before the learner has stated what they want to achieve.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


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

SOURCE_GOALS = {"understand", "interview", "portfolio", "skill-upgrade", "rebuild", "discover"}


def _is_home(path: Path) -> bool:
    return path == Path.home().resolve()


def _has_project_markers(path: Path) -> bool:
    try:
        return any((path / marker).exists() for marker in PROJECT_MARKERS)
    except OSError:
        return False


def _git_root(path: Path) -> str | None:
    current = path
    while True:
        if (current / ".git").exists():
            return str(current)
        if current.parent == current:
            return None
        current = current.parent


def _local_candidates(path: Path, limit: int = 8) -> list[dict[str, str]]:
    if _has_project_markers(path):
        return []
    candidates: list[dict[str, str]] = []
    try:
        children = sorted(path.iterdir(), key=lambda item: item.name.lower())
    except OSError:
        return []
    for child in children:
        if not child.is_dir() or child.name.startswith("."):
            continue
        if _git_root(child) == str(child) or _has_project_markers(child):
            candidates.append({"name": child.name, "path": str(child)})
        if len(candidates) >= limit:
            break
    return candidates


def context(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    root = _git_root(path)
    project = root or (str(path) if _has_project_markers(path) else None)
    return {
        "cwd": str(path),
        "is_home": _is_home(path),
        "is_project_context": bool(project),
        "project_root": project,
        "local_candidates": _local_candidates(path),
        "state_path": str(Path(project) / ".upstack") if project else None,
        "provenance": "read-only path and marker inspection; no project code executed",
    }


def intent_context() -> dict[str, Any]:
    return {
        "inspection_deferred": True,
        "is_project_context": None,
        "project_root": None,
        "local_candidates": [],
        "state_path": None,
        "provenance": "intent gate only; repository and folder contents have not been inspected",
    }


def option(label: str, description: str, value: str) -> dict[str, str]:
    return {"label": label, "description": description, "value": value}


def question(question_id: str, text: str, options: list[dict[str, str]], *, why: str, allow_freeform: bool = False) -> dict[str, Any]:
    return {
        "id": question_id,
        "text": text,
        "options": options,
        "allow_freeform": allow_freeform,
        "why_this_now": why,
        "can_skip": True,
        "answer_format": "single-choice unless the host supports a clearly labelled multi-select",
    }


def _intent_question() -> dict[str, Any]:
    return question(
        "goal",
        "What would you like to accomplish first?",
        [
            option("Learn how an existing project works", "Understand a real codebase, architecture, or feature.", "understand"),
            option("Prepare for a technical interview", "Practice the concepts, implementation, and explanations a role requires.", "interview"),
            option("Build a portfolio project", "Create a substantial project and document evidence of what you built.", "portfolio"),
            option("Upgrade a specific skill", "Use a focused project to improve a technology or engineering ability.", "skill-upgrade"),
            option("Build or rebuild a real project", "Follow a staged apprenticeship from an idea or reference to working slices.", "rebuild"),
        ],
        why="Your outcome determines the project workflow. I will ask about a repository or source only after you choose what you want from the work.",
        allow_freeform=True,
    )


def _outcome_question(goal: str) -> dict[str, Any]:
    if goal == "interview":
        return question(
            "outcome_detail",
            "What role or interview target should we prepare for?",
            [
                option("Frontend or React", "Focus on UI architecture, browser behavior, state, and accessibility.", "frontend"),
                option("Backend or API", "Focus on services, data, authentication, and reliability.", "backend"),
                option("Full-stack", "Connect frontend, backend, data, testing, and deployment.", "fullstack"),
                option("Language or systems", "Focus on runtime behavior, data structures, protocols, or tooling.", "systems"),
            ],
            why="Interview preparation must be tied to a role or skill requirement before choosing project material and practice format.",
            allow_freeform=True,
        )
    if goal == "portfolio":
        return question(
            "outcome_detail",
            "What kind of portfolio signal do you want to demonstrate?",
            [
                option("Product engineering", "A user-facing feature with thoughtful architecture and testing.", "product"),
                option("Frontend depth", "UI quality, state, accessibility, performance, and component design.", "frontend"),
                option("Backend depth", "APIs, data modeling, authentication, reliability, and observability.", "backend"),
                option("Systems or developer tooling", "Protocols, parsing, performance, concurrency, or automation.", "systems"),
            ],
            why="A portfolio project is strongest when its intended engineering signal is explicit before choosing project material.",
            allow_freeform=True,
        )
    if goal == "skill-upgrade":
        return question(
            "outcome_detail",
            "Which skill or concept do you most want to improve?",
            [
                option("A language or framework", "Choose a specific technology and map it to project evidence.", "technology"),
                option("Architecture and design", "Practice boundaries, data flow, trade-offs, and decomposition.", "architecture"),
                option("Testing and debugging", "Practice verification, failure analysis, and maintainable changes.", "quality"),
                option("Databases, APIs, or infrastructure", "Practice integration and production-oriented engineering.", "operations"),
            ],
            why="The target skill determines which project slice and difficulty signals matter.",
            allow_freeform=True,
        )
    if goal == "rebuild":
        return question(
            "outcome_detail",
            "What kind of real project or rebuild do you want to pursue?",
            [
                option("Rebuild an existing project", "Use a local or public repository as a reference without copying it wholesale.", "existing"),
                option("Build a serious new project", "Start from an idea and create a project-sized learning recipe.", "new"),
                option("Rebuild one feature or flow", "Choose a narrow vertical slice from a larger system.", "feature"),
                option("Build toward a role requirement", "Use an explicit job or skill requirement to choose the project scope.", "role"),
            ],
            why="The project shape determines whether Upstack should inspect a reference, define a new build, or target one slice.",
            allow_freeform=True,
        )
    return question(
        "outcome_detail",
        "What part of the project do you want to understand?",
        [
            option("The overall architecture", "Map the main modules, boundaries, and data flows.", "architecture"),
            option("A feature or user journey", "Trace one request or flow from entrypoint to outcome.", "feature"),
            option("A specific file, symbol, or test", "Start with a tightly bounded source target.", "target"),
            option("The stack and concepts", "Create an ingredients map before tracing a deeper path.", "inventory"),
        ],
        why="A concrete understanding target keeps the first explanation grounded and manageable.",
        allow_freeform=True,
    )


def _source_question(ctx: dict[str, Any], goal: str) -> dict[str, Any]:
    options = []
    if ctx.get("is_project_context"):
        options.append(option("Use the current project", "Use the project opened in the coding agent after your intent is clear.", "current"))
    options.extend([
        option("Choose another local project", "Select a folder already on this machine.", "local"),
        option("Find a public project", "Search metadata and enrich a shortlist before any clone or fork.", "discover"),
    ])
    if goal in {"interview", "skill-upgrade", "portfolio"}:
        options.append(option("Start without a repository", "Create a role, skill, or portfolio plan before selecting source code.", "none"))
    if goal in {"rebuild", "understand"}:
        options.append(option("Provide a project path", "Use a local folder that is not listed here.", "custom"))
    candidates = ctx.get("local_candidates") or []
    options.extend(option(item["name"], item["path"], item["path"]) for item in candidates[:4])
    return question(
        "source",
        "Where should we draw the project or practice material from?",
        options,
        why="Now that I know your intended outcome, I can ask for the source that supports it without assuming the current folder is what you want.",
        allow_freeform=True,
    )


def _local_source_question(ctx: dict[str, Any]) -> dict[str, Any]:
    options = [option("Use the current folder", "Use the folder opened in the coding agent.", "current")]
    options.extend(option(item["name"], item["path"], item["path"]) for item in (ctx.get("local_candidates") or [])[:6])
    options.append(option("I will provide a path", "Use a different local folder.", "custom"))
    return question(
        "source_path",
        "Which local project should I use?",
        options,
        why="You chose local material, so I need a concrete folder before reading its files.",
        allow_freeform=True,
    )


def _public_source_question() -> dict[str, Any]:
    return question(
        "source_detail",
        "What kind of public project should I find?",
        [
            option("A serious web application", "Search across frontend, backend, data, and deployment signals.", "web-app"),
            option("A frontend project", "Prioritize UI, state, accessibility, and frontend architecture.", "frontend"),
            option("A backend or API project", "Prioritize services, data, authentication, and testing.", "backend"),
            option("A tool, CLI, or systems project", "Prioritize runtimes, protocols, parsing, and operations.", "systems"),
            option("I have a specific idea or job requirement", "Describe it in your own words for the metadata search.", "custom"),
        ],
        why="A narrower public-project search produces a more useful shortlist and better learning fit.",
        allow_freeform=True,
    )


def next_question(ctx: dict[str, Any] | None, answers: dict[str, Any]) -> dict[str, Any] | None:
    """Return the next question without inspecting context before the intent gate."""
    ctx = ctx or intent_context()
    goal = str(answers.get("goal", "")).lower()
    source = str(answers.get("source", "")).lower()

    if not answers.get("goal"):
        return _intent_question()

    if goal in {"preview", "preview-workspace"} and not answers.get("source"):
        return question(
            "source",
            "What would you like me to preview?",
            [
                option("The current workspace", "Describe folders and project markers without saving state.", "current"),
                option("A specific local project", "Provide a path to the folder you want to inspect.", "custom"),
            ],
            why="A preview is read-only, but I still need to know which folder you want to inspect.",
            allow_freeform=True,
        )

    if goal in {"understand", "interview", "portfolio", "skill-upgrade", "rebuild"} and not answers.get("outcome_detail"):
        return _outcome_question(goal)

    if goal in SOURCE_GOALS and not answers.get("source"):
        return _source_question(ctx, goal)

    if source == "local" and not answers.get("source_path"):
        return _local_source_question(ctx)

    if source == "discover" and not answers.get("source_detail"):
        return _public_source_question()

    if not answers.get("focus"):
        return question(
            "focus",
            "What should we focus on first?",
            [
                option("The full project", "Work across the main layers.", "fullstack"),
                option("Frontend only", "Pages, components, state, accessibility, and browser behavior.", "frontend"),
                option("Backend or API only", "Routes, services, data, auth, jobs, or integrations.", "backend"),
                option("One feature or user journey", "Follow one vertical slice from entrypoint to outcome.", "feature"),
                option("A specific file, symbol, or test", "Start with a tightly bounded source target.", "target"),
            ],
            why="A concrete focus keeps the first inventory, practice plan, or rebuild slice manageable.",
            allow_freeform=True,
        )

    if not answers.get("time_budget"):
        return question(
            "time_budget",
            "How much time should the first stage fit into?",
            [
                option("About 30 minutes", "Keep the stage to one trace or very small change.", "30m"),
                option("About 1–2 hours", "Use one vertical slice with focused checks.", "1-2h"),
                option("A few sessions", "Create a short sequence of connected stages.", "sessions"),
                option("I want a deep project", "Allow a longer roadmap, still delivered one stage at a time.", "deep"),
            ],
            why="Time budget determines stage size and prevents an overwhelming all-at-once tutorial.",
        )

    if not answers.get("skill_profile"):
        target = answers.get("focus") or answers.get("outcome_detail") or "this project"
        return question(
            "skill_profile",
            f"How comfortable are you with the relevant technologies or concepts in {target}?",
            [
                option("New to most of them", "Start with vocabulary, a trace, and tight scaffolding.", "new"),
                option("I can follow examples", "Use guided decisions and small implementation tasks.", "guided"),
                option("I can build with some gaps", "Use outcomes and checks with targeted hints.", "independent"),
                option("I am comfortable; challenge me", "Emphasize trade-offs, failure modes, and independent design.", "systems"),
            ],
            why="This is the minimum calibration needed to choose the right explanation depth and stage size.",
            allow_freeform=True,
        )

    if not answers.get("mode"):
        return question(
            "mode",
            "How should Upstack guide you?",
            [
                option("Coach me step by step", "Ask for predictions, give one next decision, and fade support gradually.", "coach"),
                option("Give me the blueprint first", "Show the recipe, then guide each stage when I select it.", "blueprint"),
                option("Let me attempt first", "Provide outcomes and checks, then help only when I ask.", "attempt"),
            ],
            why="Your preferred amount of scaffolding changes how much Upstack reveals before your attempt.",
        )
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--answers", type=Path, help="JSON file containing normalized answers")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()
    answers: dict[str, Any] = {}
    if args.answers:
        answers = json.loads(args.answers.read_text(encoding="utf-8"))
    if answers.get("goal"):
        ctx = context(args.path)
    else:
        ctx = intent_context()
    print(json.dumps({"context": ctx, "next_question": next_question(ctx, answers)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
