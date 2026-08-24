#!/usr/bin/env python3
"""Create portable UI-design artifacts and an optional Stitch-MCP execution plan.

The helper is intentionally local and side-effect free until the caller has
obtained the learner's persistence approval. It never calls an MCP, uploads
source code, or creates a remote design project. A host may use the emitted
execution contract with a verified Stitch MCP capability, while the Markdown
brief and wireframe remain the portable source of truth.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


MODES = {"portable", "stitch-mcp", "reference", "none"}
STITCH_TOOLS = {
    "create_project",
    "get_project",
    "list_projects",
    "list_screens",
    "get_screen",
    "generate_screen_from_text",
    "edit_screens",
    "generate_variants",
    "create_design_system",
    "update_design_system",
    "list_design_systems",
    "apply_design_system",
}


def _clean(value: Any, default: str = "") -> str:
    return " ".join(str(value or default).split()).strip()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "project"


def _items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_clean(item) for item in value if _clean(item)]


def normalize_screen(screen: dict[str, Any], index: int) -> dict[str, Any]:
    name = _clean(screen.get("name"), f"Screen {index + 1}")
    return {
        "id": _clean(screen.get("id"), f"screen-{index + 1:02d}-{_slug(name)}"),
        "name": name,
        "user_goal": _clean(screen.get("user_goal") or screen.get("goal"), "Complete the next useful step."),
        "entry": _clean(screen.get("entry"), "User opens the project."),
        "primary_action": _clean(screen.get("primary_action"), "Continue"),
        "elements": _items(screen.get("elements")) or ["Page title", "Primary content", "Primary action"],
        "states": _items(screen.get("states")) or ["loading", "empty", "error", "success"],
        "next": _items(screen.get("next")) or ["The next screen or completion state"],
        "repository_anchors": _items(screen.get("repository_anchors") or screen.get("source_anchors")),
    }


def build_design_plan(
    brief: dict[str, Any],
    *,
    screens: list[dict[str, Any]] | None = None,
    mode: str = "portable",
    design_capabilities: list[str] | None = None,
) -> dict[str, Any]:
    """Build a local design contract without calling external tools."""
    if mode not in MODES:
        raise ValueError(f"unsupported design mode: {mode}")
    name = _clean(brief.get("name") or brief.get("title"), "Untitled project")
    capabilities = {item.casefold() for item in (design_capabilities or [])}
    stitch_available = bool({"stitch", "stitch-mcp"} & capabilities)
    if mode == "stitch-mcp" and stitch_available:
        integration_status = "available_after_confirmation"
    elif mode == "stitch-mcp":
        integration_status = "unavailable_use_portable_fallback"
    elif mode == "reference":
        integration_status = "learner_reference_required"
    elif mode == "none":
        integration_status = "not_applicable"
    else:
        integration_status = "not_required"
    normalized_screens = [normalize_screen(item, index) for index, item in enumerate(screens or brief.get("screens") or []) if isinstance(item, dict)]
    if not normalized_screens and mode != "none":
        normalized_screens = [normalize_screen({}, 0)]
    return {
        "version": 1,
        "project": {
            "name": name,
            "slug": _slug(name),
            "problem": _clean(brief.get("problem") or brief.get("purpose"), "Define the problem before implementation."),
            "audience": _clean(brief.get("audience"), "The intended learner or end user."),
            "primary_outcome": _clean(brief.get("primary_outcome") or brief.get("primary_action"), "Complete the primary user task."),
            "constraints": _items(brief.get("constraints")),
            "stack": _items(brief.get("stack")),
        },
        "workflow": {
            "curriculum_scope": "map_the_complete_project_before_teaching",
            "lesson_delivery": "generate_one_current_stage_at_a_time",
            "design_gate": "approve_brief_and_wireframe_before_first_ui_implementation_slice",
            "feedback_loop": "design_or_trace -> implement_one_slice -> verify -> explain -> unlock_next_slice",
        },
        "mode": mode,
        "integration": {
            "provider": "stitch" if mode == "stitch-mcp" else None,
            "status": integration_status,
            "remote_write": mode == "stitch-mcp" and stitch_available,
            "requires_confirmation": mode == "stitch-mcp" and stitch_available,
            "portable_fallback": [".upstack/design/BRIEF.md", ".upstack/design/WIREFRAME.md", ".upstack/design/DESIGN.md"],
            "allowed_tools": sorted(STITCH_TOOLS) if mode == "stitch-mcp" else [],
            "do_not_send_without_approval": ["private source code", "secrets", "personal data", "unreviewed repository content"],
        },
        "screens": normalized_screens,
        "artifacts": {
            "brief": ".upstack/design/BRIEF.md",
            "wireframe": ".upstack/design/WIREFRAME.md",
            "design_contract": ".upstack/design/DESIGN.md",
            "plan": ".upstack/design/design-plan.json",
        },
        "side_effects": [],
    }


def render_brief_markdown(plan: dict[str, Any]) -> str:
    project = plan["project"]
    lines = [
        f"# {project['name']} — Product Brief",
        "",
        "> This brief defines the product boundary before implementation. Upstack maps the full project, but teaches and generates only the current stage when requested.",
        "",
        f"**Problem or purpose:** {project['problem']}",
        f"**Audience:** {project['audience']}",
        f"**Primary outcome:** {project['primary_outcome']}",
        "",
        "## Constraints",
        "",
    ]
    constraints = project.get("constraints") or ["No constraints recorded yet."]
    lines.extend(f"- {item}" for item in constraints)
    if project.get("stack"):
        lines.extend(["", "## Intended stack", ""])
        lines.extend(f"- {item}" for item in project["stack"])
    lines.extend([
        "",
        "## Learning contract",
        "",
        "Upstack will first create a complete stage map and evidence plan. It will not generate every lesson, implementation file, or exercise in one pass. Each stage is unlocked after the learner reviews the outcome, attempts the task, verifies the result, and explains the relevant decisions.",
        "",
        f"**Design mode:** `{plan['mode']}`",
        f"**Integration status:** `{plan['integration']['status']}`",
        "",
    ])
    return "\n".join(lines) + "\n"


def _wire_block(screen: dict[str, Any]) -> list[str]:
    elements = screen["elements"]
    width = 54
    top = "+" + "-" * width + "+"
    rows = [top, f"| {screen['name'][:width - 2]:<{width - 2}} |", "|" + " " * width + "|"]
    for element in elements[:8]:
        rows.append(f"| [ ] {_clean(element)[:width - 6]:<{width - 6}} |")
    rows.extend(["|" + " " * width + "|", f"| [>] {screen['primary_action'][:width - 6]:<{width - 6}} |", top])
    return rows


def render_wireframe_markdown(plan: dict[str, Any]) -> str:
    lines = [
        f"# {plan['project']['name']} — Wireframe",
        "",
        "> Low-fidelity, portable wireframe. Treat it as a conversation and implementation boundary, not as a final visual design.",
        "",
        "## User journey",
        "",
    ]
    for index, screen in enumerate(plan.get("screens") or [], start=1):
        lines.extend([
            f"{index}. **{screen['name']}** — {screen['user_goal']}",
            f"   - Entry: {screen['entry']}",
            f"   - Primary action: {screen['primary_action']}",
            f"   - Next: {', '.join(screen['next'])}",
        ])
    for screen in plan.get("screens") or []:
        lines.extend(["", f"## {screen['name']}", "", f"**User goal:** {screen['user_goal']}", "", "```text"])
        lines.extend(_wire_block(screen))
        lines.extend(["```", "", "### Required states", ""])
        lines.extend(f"- {state}" for state in screen["states"])
        if screen["repository_anchors"]:
            lines.extend(["", "### Source or design anchors", ""])
            lines.extend(f"- `{anchor}`" for anchor in screen["repository_anchors"])
    lines.extend([
        "",
        "## Review gate",
        "",
        "Before the first UI implementation slice, review the primary journey, empty/loading/error states, accessibility assumptions, and what is deliberately out of scope. If Stitch is used, preserve the approved decisions in `DESIGN.md`; if it is unavailable, continue with this Markdown artifact.",
        "",
    ])
    return "\n".join(lines) + "\n"


def render_design_contract_markdown(plan: dict[str, Any]) -> str:
    project = plan["project"]
    lines = [
        f"# {project['name']} — Design Contract",
        "",
        "> This file is the portable design handoff between Upstack and any visual design tool. Update it only from learner-approved design decisions.",
        "",
        "## Principles",
        "",
        "- Keep the primary user journey obvious.",
        "- Design loading, empty, error, success, and keyboard states before polishing visuals.",
        "- Prefer accessible semantics and visible focus over decorative complexity.",
        "- Implement one approved screen or flow slice at a time.",
        "",
        "## Visual decisions to settle",
        "",
        "- Typography scale and hierarchy.",
        "- Color roles and contrast requirements.",
        "- Spacing, radius, borders, and elevation tokens.",
        "- Responsive breakpoints and interaction states.",
        "- Component names and reusable patterns.",
        "",
        "## Integration record",
        "",
        f"- Mode: `{plan['mode']}`",
        f"- Status: `{plan['integration']['status']}`",
        "- Remote design writes: require explicit confirmation.",
        "- Portable fallback: `BRIEF.md` + `WIREFRAME.md` + this file.",
        "",
    ]
    return "\n".join(lines) + "\n"


def write_artifacts(plan: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "brief": output_dir / "BRIEF.md",
        "wireframe": output_dir / "WIREFRAME.md",
        "design_contract": output_dir / "DESIGN.md",
        "plan": output_dir / "design-plan.json",
    }
    files["brief"].write_text(render_brief_markdown(plan), encoding="utf-8")
    files["wireframe"].write_text(render_wireframe_markdown(plan), encoding="utf-8")
    files["design_contract"].write_text(render_design_contract_markdown(plan), encoding="utf-8")
    files["plan"].write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return {key: str(path) for key, path in files.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("brief", type=Path, help="JSON file containing project brief and optional screens")
    parser.add_argument("--output-dir", type=Path, default=Path(".upstack/design"))
    parser.add_argument("--mode", choices=sorted(MODES), default="portable")
    parser.add_argument("--design-capability", action="append", default=[], help="verified capability, such as stitch-mcp")
    parser.add_argument("--write", action="store_true", help="write the portable artifacts after the caller has approval")
    args = parser.parse_args()
    brief = json.loads(args.brief.read_text(encoding="utf-8"))
    plan = build_design_plan(brief, mode=args.mode, design_capabilities=args.design_capability)
    if args.write:
        plan["written_files"] = write_artifacts(plan, args.output_dir)
    print(json.dumps(plan, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
