#!/usr/bin/env python3
"""Plan one relevant Upstack onboarding question at a time.

The helper never asks the learner directly and never writes files. It emits a
question specification for a host-native question/choice UI or text fallback.
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


def next_question(ctx: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any] | None:
    goal = str(answers.get("goal", "")).lower()
    source = str(answers.get("source", "")).lower()
    focus = str(answers.get("focus", "")).lower()
    if not answers.get("goal"):
        if ctx.get("is_project_context"):
            options = [
                option("Understand the existing code", "Trace the architecture and one or more real flows.", "understand"),
                option("Rebuild a feature", "Recreate a focused slice without copying the implementation.", "rebuild"),
                option("Build a similar project", "Use this project as a reference for a staged rebuild.", "apprentice"),
                option("Map the stack and concepts", "Create an ingredients report before choosing a build or study path.", "inventory"),
                option("Find a different public project", "Search for a project that better matches a goal or portfolio direction.", "discover"),
            ]
            why = "I found a project in the current workspace. Your goal comes first; I will choose the smallest useful source and learning path after you answer."
        else:
            options = [
                option("Understand an existing project", "Trace a local codebase or a project you will select next.", "understand"),
                option("Rebuild a real project or feature", "Create a staged apprenticeship instead of a generic tutorial.", "rebuild"),
                option("Find a public project to build", "Search repository metadata and show a shortlist before any clone or fork.", "discover"),
                option("Start a new project", "Choose a meaningful project idea and create a guided build plan.", "new"),
                option("Preview a workspace", "Inspect a folder without creating persistent Upstack state.", "preview"),
            ]
            why = "This workspace is broad, so I will identify your intended outcome before asking which project or source to use."
            candidates = ctx.get("local_candidates") or []
            if candidates:
                names = ", ".join(item["name"] for item in candidates[:5])
                why += f" Possible local projects include: {names}."
        return question(
            "goal",
            "What would you like to accomplish first?",
            options,
            why=why,
            allow_freeform=True,
        )
    if goal in {"understand", "rebuild", "apprentice", "inventory", "preview"} and not ctx.get("is_project_context") and not answers.get("source"):
        return question(
            "source",
            "Which local project should I inspect?",
            [
                option("Use the current folder", "Use the folder you opened in the coding agent.", "current"),
                *[option(item["name"], item["path"], item["path"]) for item in (ctx.get("local_candidates") or [])[:6]],
                option("I will provide a path", "Use a different local folder.", "custom"),
            ],
            why="You chose to learn from an existing local codebase, so I need a concrete folder before reading its files.",
            allow_freeform=True,
        )
    if goal == "discover" and not answers.get("source"):
        return question(
            "source",
            "What kind of project should I find?",
            [
                option("A serious web application", "Search across frontend, backend, data, and deployment signals.", "web-app"),
                option("A frontend project", "Prioritize UI, state, accessibility, and frontend architecture.", "frontend"),
                option("A backend or API project", "Prioritize services, data, authentication, and testing.", "backend"),
                option("A tool, CLI, or systems project", "Prioritize runtimes, protocols, parsing, and operations.", "systems"),
                option("I have a specific idea", "Describe the project, stack, or job requirement in your own words.", "custom"),
            ],
            why="A narrower project type produces better metadata search results and a more useful shortlist.",
            allow_freeform=True,
        )
    if goal == "new" and not answers.get("source"):
        return question(
            "source",
            "What kind of project would you like to build?",
            [
                option("A real product-style web app", "Something with users, data, APIs, and deployable behavior.", "web-app"),
                option("A frontend experience", "A polished UI with meaningful state and interaction.", "frontend"),
                option("A backend or developer tool", "An API, service, CLI, parser, or automation tool.", "backend"),
                option("Match a job requirement", "Use a role or skill list to choose a demonstrable project scope.", "role"),
            ],
            why="The project shape controls the stack assumptions and the first blueprint stages.",
            allow_freeform=True,
        )
    if not answers.get("focus"):
        return question(
            "focus",
            "Where should we focus first?",
            [
                option("Full project", "Understand or build across the main layers.", "fullstack"),
                option("Frontend only", "Pages, components, state, accessibility, and browser behavior.", "frontend"),
                option("Backend or API only", "Routes, services, data, auth, jobs, or integrations.", "backend"),
                option("One feature or user journey", "Follow one vertical slice from entrypoint to outcome.", "feature"),
                option("A specific file, symbol, or test", "Start with a tightly bounded source target.", "target"),
            ],
            why="A concrete focus keeps the first inventory and blueprint small enough to learn from.",
            allow_freeform=True,
        )
    if not answers.get("time_budget"):
        return question(
            "time_budget",
            "How much time should the first build or study stage fit into?",
            [
                option("About 30 minutes", "Keep the stage to one trace or very small change.", "30m"),
                option("About 1–2 hours", "Use one vertical slice with focused checks.", "1-2h"),
                option("A few sessions", "Create a short sequence of connected stages.", "sessions"),
                option("I want a deep project", "Allow a longer roadmap, still delivered one stage at a time.", "deep"),
            ],
            why="Time budget determines stage size and prevents an overwhelming all-at-once tutorial.",
        )
    if not answers.get("skill_profile"):
        focus_label = answers.get("focus") or source or "this project"
        return question(
            "skill_profile",
            f"How comfortable are you with the main technologies or concepts in {focus_label}?",
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
    ctx = context(args.path)
    answers: dict[str, Any] = {}
    if args.answers:
        answers = json.loads(args.answers.read_text(encoding="utf-8"))
    payload = {"context": ctx, "next_question": next_question(ctx, answers)}
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
