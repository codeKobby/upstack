# Project State and Command Gate

Upstack is project-aware. Every command first resolves the requested path to a canonical project root and then reads the project’s persisted state before performing workflow logic. The host’s opened workspace or command path is the learner context; the installed `SKILL.md` directory is a resource path, never the default learner project.

## Resolution order

1. Prefer the nearest ancestor containing `.upstack/STATE.json` or `.upstack/PROJECT.json`.
2. Otherwise use the nearest Git root.
3. Otherwise use the nearest directory with recognizable project markers.
4. If no project is identified, report `project_selection_required` and ask for an explicit path. Never select a child of a broad workspace implicitly.

A project identity is the stable hash of its canonical local root path, stored in `.upstack/PROJECT.json` together with the root, display name, state path, creation time, and onboarding status. The identity is local and must not be presented as a remote repository identity.

## Shared command gate

Run:

```bash
python3 scripts/project_state.py . --command <subcommand>
```

For `/upstack continue` or `/upstack resume`, use the explicit fast path:

```bash
python3 scripts/project_state.py . --command continue
python3 scripts/onboarding.py . --command continue --json
```

A known-project result is a resume instruction, not an onboarding question. Follow its `next_action` and persisted pointers; do not invoke the initial intent question.

The result is controller data, not a user-facing prompt. A `known_project` result means the command must load the persisted state and resume. An `onboarding_required` result means the command must route through onboarding before project work. A `project_selection_required` result means the command must ask for an explicit project path. A `resume_unavailable` result from `continue` or `resume` means no established project was found; offer initialization or an explicit project path without silently starting a new route. A command must not restart the initial intent or create a second curriculum merely because the user invoked a different Upstack subcommand.

## Persisted state

A confirmed initialization writes:

```text
.upstack/PROJECT.json       local project identity
.upstack/STATE.json         onboarding, mode, stage, evidence, next action
.upstack/STATE.md           concise human-readable status
.upstack/SESSION_HANDOFF.json approved live-chat change directive
.upstack/SESSION_HANDOFF.md   human-readable handoff and continuation record
.upstack/PRODUCT_BRIEF.md   learner-approved product contract
.upstack/PACKAGE_MANAGER.md selected/detected package-manager contract
.upstack/HISTORY.jsonl       append-only session, lesson, evidence, and handoff events
.upstack/lessons/plan.json  complete curriculum with current and locked stages
.upstack/lessons/CURRICULUM.md
.upstack/lessons/LESSON_BLUEPRINT.md
.upstack/lessons/CURRENT_LESSON.md  created only after an explicit lesson request
.upstack/lessons/progress.json
```

State is written only after explicit confirmation or an explicit write command. The tutor records attempts without unlocking by default. To unlock a stage, the learner must provide an attempt, approved verification, an explanation or teach-back, and feedback. Incomplete evidence leaves the same stage active. The selected or detected package manager and its read-only evidence are persisted in `STATE.json` and `PACKAGE_MANAGER.md` so later commands and lessons use the same manager.

### Pointer and resume contract

`STATE.json` must include a `pointers` object containing absolute canonical paths for `project_root`, `workspace_root`, `destination`, the state and project files, the curriculum artifacts, the current lesson, the design artifacts, and `HISTORY.jsonl`. Its `source` pointer records the selected local source path or public repository URL when one exists. Its `current_lesson` pointer records the stable lesson ID, sequence, title, generation status, and `CURRENT_LESSON.md` path when generated. Its `design` pointer records the portable design artifacts and whether Stitch was selected, pending confirmation, available, unavailable, or completed. The state also retains a bounded `history` list while `HISTORY.jsonl` preserves the event trail.

On a new session, the gate must return the pointer and resume context before any onboarding question. If the input path is inside `.agents/skills/<skill>`, `.opencode/skills/<skill>`, `.claude/skills/<skill>`, `.cline/skills/<skill>`, `.clinerules/skills/<skill>`, `.github/skills/<skill>`, or `.agent/skills/<skill>`, step out to the containing workspace and resolve its `.upstack` state. A global installed skill path without a learner project must remain a broad/resource context. Never analyze the installed skill’s own scripts or references as the learner project unless the learner explicitly names that directory.

## Command behavior

| Gate result | Behavior |
| --- | --- |
| `known_project` | Show or use the persisted project pointers and resume the requested command without onboarding. |
| `resume_unavailable` | No established project exists at the resolved location; offer initialization or an explicit existing-project path. |
| `onboarding_required` | Preserve the request, complete onboarding, and ask before creating state. |
| `project_selection_required` | Ask for an explicit local project path; do not infer a child directory. |
| `intent_required` | Ask the context-independent intent question before inspecting workspace contents. |

The curriculum is addressed by stable identifiers only after the project is resolved. `/upstack curriculum` shows IDs and lock status without generating lesson content. `/upstack lesson 3`, `/upstack lesson day-two`, `/upstack lesson stage-03-vertical-slice`, `/upstack lesson <title>`, and `/upstack lesson upstack-fresh-start-core` resolve against that project’s `plan.json`. If an identifier is ambiguous or locked, report candidates or the unlock condition instead of teaching it early. `/upstack build`, `/upstack hint`, `/upstack assess`, `/upstack blueprint`, and `/upstack portfolio` must use the same gate.

When the learner corrects the active route in chat, treat the correction as a live-session change. Pause the stale plan, preserve valid answers and progress, prepare a small directive, obtain confirmation if persistence or side effects are involved, apply it through `scripts/session_handoff.py`, and then rerun the shared gate before resuming. Never silently continue with the stale route or restart onboarding.
