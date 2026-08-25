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
BUILD_GOALS = {"interview", "portfolio", "skill-upgrade", "rebuild"}
PROJECT_MODES = {"rebuild", "scratch", "clone", "study"}
PATH_DESTINATIONS = {"new-local", "clone-local", "worktree", "notes-folder", "portfolio-repo"}


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


def _persisted_upstack_state(project: str | None) -> dict[str, Any] | None:
    if not project:
        return None
    state_file = Path(project) / ".upstack" / "STATE.json"
    try:
        if not state_file.is_file():
            return None
        value = json.loads(state_file.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def context(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    root = _git_root(path)
    project = root or (str(path) if _has_project_markers(path) else None)
    persisted = _persisted_upstack_state(project)
    return {
        "cwd": str(path),
        "is_home": _is_home(path),
        "is_project_context": bool(project),
        "is_broad_workspace": not bool(project),
        "project_root": project,
        "local_candidates": _local_candidates(path),
        "state_path": str(Path(project) / ".upstack") if project else None,
        "known_upstack_project": bool(persisted),
        "persisted_state": {
            "project_id": persisted.get("project_id"),
            "mode": persisted.get("mode"),
            "current_stage": persisted.get("current_stage"),
            "completed_stages": persisted.get("completed_stages", []),
            "last_action": persisted.get("last_action"),
            "next_action": persisted.get("next_action"),
            "updated_at": persisted.get("updated_at"),
        } if persisted else None,
        "provenance": "read-only path, marker, and optional Upstack-state inspection; no project code executed",
    }


def validate_destination(raw_path: str | Path, current_path: str | Path | None = None) -> dict[str, Any]:
    """Resolve a proposed local destination without creating or modifying it."""
    raw = str(raw_path or "").strip()
    base = Path(current_path or Path.cwd()).expanduser().resolve()
    if not raw:
        return {"valid": False, "status": "missing", "input": raw, "resolved_path": None, "write_performed": False}
    candidate = Path(raw).expanduser()
    resolved = (base / candidate if not candidate.is_absolute() else candidate).resolve()
    home = Path.home().resolve()
    if resolved in {Path("/"), home}:
        return {"valid": False, "status": "too_broad", "input": raw, "resolved_path": str(resolved), "write_performed": False}
    if resolved == base and not _has_project_markers(base):
        return {"valid": False, "status": "same_as_broad_workspace", "input": raw, "resolved_path": str(resolved), "write_performed": False}
    if resolved.exists():
        if not resolved.is_dir():
            status = "existing_file"
            valid = False
        elif _has_project_markers(resolved) or (resolved / ".git").exists():
            status = "existing_project"
            valid = True
        else:
            status = "existing_folder"
            valid = True
        return {"valid": valid, "status": status, "input": raw, "resolved_path": str(resolved), "write_performed": False}
    parent = resolved.parent
    if not parent.exists():
        status = "parent_missing"
        valid = False
    elif not parent.is_dir():
        status = "parent_not_directory"
        valid = False
    else:
        status = "new_folder_under_existing_parent"
        valid = True
    return {"valid": valid, "status": status, "input": raw, "resolved_path": str(resolved), "write_performed": False}


def _destination_path_question(project_mode: str, destination: str, *, validation: dict[str, Any] | None = None) -> dict[str, Any]:
    prompt = "What exact local folder should hold the project code or learning artifacts?"
    why = "A broad workspace is not a project destination. I need the exact path before creating files, scaffolding, cloning, or saving `.upstack/` state."
    if validation and not validation.get("valid"):
        prompt = "What different local folder should hold the project code or learning artifacts?"
        why = f"The proposed destination was not usable ({validation.get('status')}). No files were written; provide a concrete folder whose parent exists."
    return question(
        "destination_path",
        prompt,
        [
            option("I will enter an absolute or `~` path", "The path is resolved and shown back to you before any write.", "custom"),
            option("I will enter a path relative to the current workspace", "Use a child path only; Upstack will not write to the broad workspace itself.", "workspace-relative"),
        ],
        why=why,
        allow_freeform=True,
    )


def intent_context() -> dict[str, Any]:
    return {
        "inspection_deferred": True,
        "is_project_context": None,
        "is_broad_workspace": None,
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


def _job_requirements_question() -> dict[str, Any]:
    return question(
        "job_requirements",
        "What job requirements should we prepare against?",
        [
            option("Paste the job description or requirements", "Use the exact responsibilities, qualifications, stack, and level supplied by the employer.", "paste"),
            option("Provide an official job-posting URL", "Read the public posting and preserve its URL as the requirement source.", "url"),
            option("Provide a local requirements file", "Use a recruiter packet, saved job description, or interview instructions on this machine.", "file"),
            option("Give me a role summary first", "Start with your own summary while we identify what evidence is still missing.", "summary"),
        ],
        why="Interview practice should be tied to the actual role requirements before Upstack searches for question patterns or chooses a study plan.",
        allow_freeform=True,
    )


def _self_assessment_question() -> dict[str, Any]:
    return question(
        "self_assessment",
        "How would you describe your current knowledge for this role?",
        [
            option("New to most of it", "I need fundamentals, vocabulary, examples, and tightly bounded diagnostics.", "new"),
            option("Working knowledge", "I can follow and modify examples but need support with unfamiliar problems or trade-offs.", "working"),
            option("Comfortable in the core areas", "I can build and explain common solutions but want role-specific depth and speed.", "comfortable"),
            option("Strong but uneven", "I can handle much of the role, but I want to find specific gaps and interview weaknesses.", "strong-uneven"),
            option("I will describe my experience", "Give technologies, projects, responsibilities, and areas where you feel uncertain.", "freeform"),
        ],
        why="Self-report sets an initial hypothesis; Upstack will test selected dimensions with small explanations, traces, implementation tasks, debugging, or design defenses.",
        allow_freeform=True,
    )


def _project_mode_question(goal: str) -> dict[str, Any]:
    return question(
        "project_mode",
        "How should we work with the project?",
        [
            option("Rebuild an existing project", "Study a reference and reproduce it in learning-sized slices without copying it wholesale.", "rebuild"),
            option("Build from scratch", "Start with an idea and design and implement a new project progressively.", "scratch"),
            option("Clone and adapt a public project", "Choose a verified repository, clone it only after confirmation, and learn by changing bounded slices.", "clone"),
            option("Study or trace without changing the source", "Understand an existing codebase while keeping the source read-only.", "study"),
        ],
        why="The project mode determines whether Upstack needs a reference source, a new-project brief, or a later clone confirmation.",
        allow_freeform=True,
    )


def _destination_question(project_mode: str) -> dict[str, Any]:
    if project_mode == "scratch":
        options = [
            option("A new local project folder", "Create the learning project in a folder you choose after the plan is approved.", "new-local"),
            option("An isolated branch or worktree", "Keep the build separate from another local checkout; show the exact base and target first.", "worktree"),
            option("A new portfolio repository later", "Plan locally first, then ask separately before creating or publishing a repository.", "portfolio-repo"),
            option("Plan only for now", "Create the curriculum and design brief without writing project code yet.", "plan-only"),
        ]
    elif project_mode == "clone":
        options = [
            option("A new local clone folder", "Show the exact clone destination and ask before cloning.", "clone-local"),
            option("An isolated branch or worktree", "Clone or attach the reference in an isolated location after confirmation.", "worktree"),
            option("A new portfolio repository later", "Keep the reference and portfolio destination separate; publishing requires another confirmation.", "portfolio-repo"),
            option("Plan only before cloning", "Prepare the route and shortlist without cloning, installing, or executing anything.", "plan-only"),
        ]
    elif project_mode == "rebuild":
        options = [
            option("A new local rebuild folder", "Keep the original reference untouched and build in a separate folder.", "new-local"),
            option("An isolated branch or worktree", "Rebuild beside an existing checkout with the base and target shown first.", "worktree"),
            option("A new portfolio repository later", "Build locally first, then ask separately before publishing evidence or code.", "portfolio-repo"),
            option("Reference-only learning plan", "Map the rebuild without writing implementation code yet.", "plan-only"),
        ]
    else:
        options = [
            option("Keep the source unchanged and save `.upstack/` beside it", "Store only learning state and source-cited artifacts; do not modify the project.", "source-adjacent"),
            option("A separate notes folder", "Keep the source read-only and place approved learning artifacts elsewhere.", "notes-folder"),
            option("Plan only for now", "Create a route without writing files until you approve a destination.", "plan-only"),
        ]
    return question(
        "destination",
        "Where should the learning project or its artifacts live?",
        options,
        why="Destination is separate from project mode so Upstack never assumes that the opened folder is where new code, a clone, or portfolio work belongs.",
        allow_freeform=True,
    )


def _destination_confirmation_question(validation: dict[str, Any], project_mode: str) -> dict[str, Any]:
    resolved = validation.get("resolved_path") or "the proposed path"
    return question(
        "destination_confirmation",
        f"Use `{resolved}` as the local destination for this {project_mode} project?",
        [
            option("Yes, use this destination", "Keep the resolved path and continue with the plan; no files are written by this question.", "confirmed"),
            option("Choose a different destination", "Return to the exact-path question before planning or writing.", "change"),
            option("Plan only for now", "Keep the route in memory without creating code or project files.", "plan-only"),
        ],
        why="The resolved path is shown separately so a destination choice cannot be mistaken for permission to write, scaffold, clone, or save state.",
    )


def _project_brief_question() -> dict[str, Any]:
    return question(
        "project_brief",
        "What should we build from scratch?",
        [
            option("I have an idea to describe", "Give a short product, user, or technical goal in your own words.", "custom"),
            option("Turn a role or skill target into a project", "Use a job requirement or concept gap as the project brief.", "target"),
            option("Help me choose a bounded project idea", "Ask a few constraints before proposing a project-sized build.", "guided"),
        ],
        why="A scratch build needs a small product or technical brief before Upstack can map the complete curriculum or UI.",
        allow_freeform=True,
    )


def _design_question(ctx: dict[str, Any]) -> dict[str, Any]:
    options = [
        option("Create a portable Markdown wireframe first", "Produce a product brief, screen map, and low-fidelity wireframe that works in every coding agent.", "portable"),
    ]
    available = {str(item).casefold() for item in (ctx.get("design_tools") or [])}
    if "stitch-mcp" in available or "stitch" in available:
        options.append(option("Use Stitch through the connected MCP", "Generate or iterate visual screens in Stitch, then preserve the approved design contract locally.", "stitch-mcp"))
    options.extend([
        option("Use an existing visual reference", "Describe or supply an approved screenshot, URL, or design reference without assuming ownership of it.", "reference"),
        option("No graphical UI", "Start with API, CLI, data, or systems design and skip screen design for this project.", "none"),
    ])
    return question(
        "ui_design",
        "How should we design the user experience before implementation?",
        options,
        why="A scratch build should settle the user journey and interface boundary before the first implementation slice; visual tooling is optional and must have a portable fallback.",
        allow_freeform=True,
    )


def _fresh_start_mode_question() -> dict[str, Any]:
    return question(
        "fresh_start_mode",
        "How should we learn while building this fresh project?",
        [
            option("Guide me through lessons step by step", "Teach one concept and project slice, let me attempt it, review my evidence, and unlock the next stage only when I am ready.", "guided-lesson"),
            option("Show the roadmap, then teach each lesson", "Map the complete curriculum first, but still deliver one learner-led lesson at a time.", "blueprint-then-lessons"),
            option("Let me attempt each slice first", "Give me the outcome and checks, then coach or assess my attempt without taking over.", "attempt-first"),
            option("Help with one confirmed slice after I try", "Use limited assistance for a current blocker, explain every change, and keep the work reviewable.", "assisted-slice"),
        ],
        why="Upstack is an apprenticeship: a fresh project should become a sequence of lessons and learner attempts, not a complete generated implementation.",
    )


def _source_question(ctx: dict[str, Any], goal: str, project_mode: str = "study") -> dict[str, Any]:
    options = []
    if project_mode == "clone":
        options.extend([
            option("Find a public project", "Search metadata and enrich a shortlist before any clone or fork.", "discover"),
            option("Choose a local reference project", "Select a folder already on this machine before any copy or worktree action.", "local"),
            option("Provide a repository URL", "Give a public repository URL for metadata verification before cloning.", "custom"),
        ])
        return question(
            "source",
            "Which existing project should we clone and adapt?",
            options,
            why="A clone route needs an explicit reference before Upstack can show a destination and request clone confirmation.",
            allow_freeform=True,
        )
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
        why="Now that I know your intended outcome and project mode, I can ask for the source that supports it without assuming the current folder is what you want.",
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
    project_mode = str(answers.get("project_mode", "")).lower()
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

    if goal == "interview" and not answers.get("job_requirements"):
        return _job_requirements_question()

    if goal == "interview" and not answers.get("self_assessment"):
        return _self_assessment_question()

    if goal in SOURCE_GOALS and not answers.get("project_mode"):
        return _project_mode_question(goal)

    if project_mode not in PROJECT_MODES and goal in SOURCE_GOALS:
        return _project_mode_question(goal)

    if goal in SOURCE_GOALS and not answers.get("destination"):
        return _destination_question(project_mode)

    destination = str(answers.get("destination", "")).lower()
    destination_path = answers.get("destination_path")
    if destination in PATH_DESTINATIONS:
        if not destination_path or str(destination_path).lower() in {"custom", "workspace-relative"}:
            return _destination_path_question(project_mode, destination)
        validation = validate_destination(str(destination_path), ctx.get("cwd"))
        if not validation["valid"]:
            return _destination_path_question(project_mode, destination, validation=validation)
        if answers.get("destination_confirmed") != "confirmed":
            return _destination_confirmation_question(validation, project_mode)

    if project_mode == "scratch" and not answers.get("project_brief"):
        return _project_brief_question()

    if project_mode == "scratch" and not answers.get("ui_design"):
        return _design_question(ctx)

    if project_mode == "scratch" and not answers.get("fresh_start_mode"):
        return _fresh_start_mode_question()

    if project_mode in {"rebuild", "clone", "study"} and not answers.get("source"):
        return _source_question(ctx, goal, project_mode)

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


CHAINABLE_QUESTION_IDS = {"focus", "time_budget"}


def question_chain(ctx: dict[str, Any] | None, answers: dict[str, Any], *, max_questions: int = 3) -> list[dict[str, Any]]:
    """Return a short chain only for questions whose later wording is answer-independent.

    Intent, outcome detail, source, source path, and discovery candidate decisions are
    intentionally never chained because their answers change the next question or
    the safe action boundary.
    """
    if max_questions < 1:
        return []
    chain: list[dict[str, Any]] = []
    projected = dict(answers)
    while len(chain) < max_questions:
        current = next_question(ctx, projected)
        if current is None:
            break
        question_id = current.get("id")
        if question_id not in CHAINABLE_QUESTION_IDS and chain:
            break
        chain.append(current)
        if question_id not in CHAINABLE_QUESTION_IDS:
            break
        # Project a completed answer only to discover the next independent question.
        # The host still collects the real answer for the displayed question.
        if question_id == "focus":
            # Time budget is independent of the selected focus, so it is safe to
            # include as the second question. Stop before skill calibration because
            # its wording and answer choices depend on the actual focus answer.
            projected["focus"] = "__focus_selected__"
        elif question_id == "time_budget":
            projected["time_budget"] = "__time_selected__"
    return chain


def question_plan(
    ctx: dict[str, Any] | None,
    answers: dict[str, Any],
    *,
    host: str = "generic",
    question_mode: str = "auto",
) -> dict[str, Any]:
    """Build a host-neutral delivery plan from verified question capabilities."""
    if question_mode not in {"auto", "native-single", "native-multi"}:
        raise ValueError(f"unsupported question mode: {question_mode}")
    use_chain = question_mode == "native-multi" or (question_mode == "auto" and host == "opencode")
    if use_chain:
        mode = "native-multi-question-when-safe"
        questions = question_chain(ctx, answers)
    else:
        mode = "native-single-question-or-text-fallback"
        current = next_question(ctx, answers)
        questions = [current] if current else []
    native_tool = {"opencode": "question", "claude-code": "AskUserQuestion"}.get(host)
    return {
        "host": host,
        "mode": mode,
        "questions": questions,
        "delivery": {
            "required_action": "invoke_native_question_tool_if_callable",
            "native_tool": native_tool or "discover_from_current_host_tools",
            "send_only": "questions",
            "prose_prompt_allowed": native_tool is None,
            "fallback": "render_one_short_question_only_when_no_callable_native_tool_exists",
            "must_not": ["print-question-specification-as-prompt", "simulate-native-tool", "duplicate-native-prompt"],
        },
        "safety": "The planner is not the UI. Invoke the callable native question tool immediately when available; do not print a duplicate prose prompt. Recompute after dependent answers.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--answers", type=Path, help="JSON file containing normalized answers")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--host", default="generic", help="host identifier for provenance; capability is selected separately")
    parser.add_argument("--question-mode", choices=("auto", "native-single", "native-multi"), default="auto", help="verified host question capability")
    parser.add_argument("--design-tool", action="append", default=[], help="verified callable design capability, such as stitch-mcp; repeatable")
    parser.add_argument("--chain", action="store_true", help="deprecated alias for --question-mode native-multi")
    args = parser.parse_args()
    answers: dict[str, Any] = {}
    if args.answers:
        answers = json.loads(args.answers.read_text(encoding="utf-8"))
    if answers.get("goal"):
        ctx = context(args.path)
    else:
        ctx = intent_context()
    if args.chain:
        args.question_mode = "native-multi"
    if args.design_tool:
        ctx["design_tools"] = args.design_tool
    payload = {"context": ctx, "question_plan": question_plan(ctx, answers, host=args.host, question_mode=args.question_mode)}
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
