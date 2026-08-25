# Project State and Command Gate

Upstack is project-aware. Every command first resolves the requested path to a canonical project root and then reads the project’s persisted state before performing workflow logic.

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

The result is controller data, not a user-facing prompt. A `known_project` result means the command must load the persisted state and resume. An `onboarding_required` result means the command must route through onboarding before project work. A `project_selection_required` result means the command must ask for an explicit project path. A command must not restart the initial intent or create a second curriculum merely because the user invoked a different Upstack subcommand.

## Persisted state

A confirmed initialization writes:

```text
.upstack/PROJECT.json       local project identity
.upstack/STATE.json         onboarding, mode, stage, evidence, next action
.upstack/STATE.md           concise human-readable status
.upstack/PRODUCT_BRIEF.md   learner-approved product contract
.upstack/lessons/plan.json  complete curriculum with current and locked stages
.upstack/lessons/CURRICULUM.md
.upstack/lessons/LESSON_BLUEPRINT.md
.upstack/lessons/CURRENT_LESSON.md  created only after an explicit lesson request
.upstack/lessons/progress.json
```

State is written only after explicit confirmation or an explicit write command. The tutor records attempts without unlocking by default. To unlock a stage, the learner must provide an attempt, approved verification, an explanation or teach-back, and feedback. Incomplete evidence leaves the same stage active.

## Command behavior

| Gate result | Behavior |
| --- | --- |
| `known_project` | Show or use the persisted project and resume the requested command. |
| `onboarding_required` | Preserve the request, complete onboarding, and ask before creating state. |
| `project_selection_required` | Ask for an explicit local project path; do not infer a child directory. |
| `intent_required` | Ask the context-independent intent question before inspecting workspace contents. |

The curriculum is addressed by stable identifiers only after the project is resolved. `/upstack curriculum` shows IDs and lock status without generating lesson content. `/upstack lesson 3`, `/upstack lesson day-two`, `/upstack lesson stage-03-vertical-slice`, `/upstack lesson <title>`, and `/upstack lesson upstack-fresh-start-core` resolve against that project’s `plan.json`. If an identifier is ambiguous or locked, report candidates or the unlock condition instead of teaching it early. `/upstack build`, `/upstack hint`, `/upstack assess`, `/upstack blueprint`, and `/upstack portfolio` must use the same gate.
