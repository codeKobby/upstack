# Upstack UI Design Workflow

Use this reference when the learner chooses **build from scratch** and the project has a graphical interface. The design workflow is a gate before the first UI implementation slice, not a request to generate an entire application or a finished visual system in one response.

## Design outputs

Always preserve three local artifacts under `.upstack/design/`:

| Artifact | Purpose |
| --- | --- |
| `BRIEF.md` | Product problem, audience, primary outcome, constraints, intended stack, and non-goals. |
| `WIREFRAME.md` | Primary journey, screen responsibilities, actions, transitions, and loading/empty/error/success states in portable Markdown. |
| `DESIGN.md` | Learner-approved visual and interaction contract: tokens, accessibility assumptions, responsive behavior, component decisions, and open questions. |

The Markdown wireframe is the minimum cross-agent source of truth. It can be read in a terminal, editor, pull request, or lesson and does not require a visual design connector. Keep it even when a visual tool is used.

## Question route

Ask destination before accepting the brief. Then ask for the brief, and ask how the learner wants to design the user experience. Offer **portable Markdown wireframe** in every host. Offer **Stitch through the connected MCP** only when the current host exposes a verified callable Stitch capability. Offer an existing visual reference only when the learner can identify it. Offer **no graphical UI** for API, CLI, data, or systems projects.

The native question tool is the only prompt when it is callable. Do not print a prose menu beside it, and do not expose planner JSON or integration metadata to the learner.

## Portable-first stages

Use this staged sequence:

```text
product brief → user journey → low-fidelity wireframe → state/accessibility review
→ optional visual exploration → approved design contract → app shell
→ first UI vertical slice → verify → explain → next slice
```

Map the complete project curriculum and design dependencies before teaching. Generate only the current design or implementation stage when the learner requests or unlocks it. Do not generate all screens, all components, all lessons, or all code at once.

## Optional Stitch MCP lane

Stitch is an optional accelerator for visual exploration. The official Stitch MCP setup documents project and screen inspection, text-to-screen generation, screen editing, variants, and design-system operations [1]. Treat any project creation or modification as a remote write.

When Stitch is selected and the MCP is callable:

1. Announce the provider, exact operation, remote destination, and sanitized brief or design data to be sent.
2. Ask for explicit confirmation before creating a project, generating a screen, editing screens, generating variants, or writing a design system.
3. Use only the tools and fields exposed by the active MCP server; do not guess schemas or claim a design was created without tool output.
4. Keep private source code, secrets, personal data, and unreviewed repository content out of the request unless the learner explicitly approves that exact transfer.
5. After the learner approves a screen or flow, record the decisions in local `DESIGN.md` and relate them to the next Upstack stage.
6. If Stitch is unavailable, unauthenticated, denied, or declined, continue with `WIREFRAME.md` and `DESIGN.md` without blocking the build.

A connector may need to be configured separately by the learner or through the host’s approved integration flow. Upstack must inspect availability first and must not silently enable, create, or modify a connector.

## Example brief input

```json
{
  "name": "Focus Board",
  "problem": "Help learners track one active project stage.",
  "audience": "Developers learning by building.",
  "primary_outcome": "Open the next stage and record evidence.",
  "constraints": ["keyboard accessible", "responsive", "no private data in remote design tools"],
  "stack": ["TypeScript", "React"],
  "screens": [
    {
      "name": "Home",
      "user_goal": "Choose the next stage",
      "primary_action": "Open stage",
      "elements": ["stage list", "progress", "current-stage summary"],
      "states": ["loading", "empty", "error", "success"],
      "next": ["Stage detail"]
    }
  ]
}
```

Generate the local artifacts only after the learner approves the requested persistence destination:

```bash
python3 scripts/ui_design.py /path/to/brief.json --mode portable --write
```

### Reference

[1]: https://stitch.withgoogle.com/docs/mcp/setup "Stitch via MCP — official setup and tool reference"
