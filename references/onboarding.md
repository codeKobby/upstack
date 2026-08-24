# Upstack Onboarding Contract

Upstack onboarding is a short adaptive interview, not a questionnaire dump. Its purpose is to collect only the decisions that change the first project route, focus, stage size, or evidence plan.

## First-run behavior

The agent must begin with the learner’s intent. It must not inspect the current folder, repository, files, stack, home-directory contents, or child project names to decide the first question. The first turn is an intent gate only.

After the intent answer, inspect only the context required by that route:

- Is the selected source a local project, public project, or new-project brief?
- Is a local path inside a Git repository or a broad workspace?
- Does the selected project contain recognizable project markers?
- Does the selected project already contain `.upstack/` state?

Do not describe the home directory as a project. Do not scan or summarize unrelated sibling directories as though they are one repository. Do not list local candidates until the learner has chosen an intent that needs local material. If that intent needs a source, then inspect the workspace and offer candidate paths; do not silently choose one.

Use user-facing language. Never mention internal helper names, internal routing phases, legacy state-directory names, or internal initializer wording. Start by asking what the learner wants to accomplish, not where the project comes from. Do not inspect the repository or describe the workspace before this first question. For the first intent turn, say only:

> What would you like to accomplish first?

Offer these intent options:

- **Learn how an existing project works** — understand a real codebase, architecture, or feature.
- **Prepare for a technical interview** — practice the concepts, implementation, and explanations a role requires.
- **Build a portfolio project** — create a substantial project and document evidence of what was built.
- **Upgrade a specific skill** — use a focused project to improve a technology or engineering ability.
- **Build or rebuild a real project** — follow a staged apprenticeship from an idea or reference to working slices.

If a specific project path is already provided, announce:

> I’ll inspect that project without running its code, identify the stack and major flows, and show you a draft inventory. I’ll ask before saving your Upstack workspace.

## One active decision per turn

When the host exposes a native question or choice tool—such as `AskUserQuestion`, a selectable prompt, or an equivalent—use it. The default is one question-tool call containing one active decision per turn. OpenCode is an explicit capability exception: its native `question` tool can display multiple questions before the learner submits, so Upstack may submit a short precomputed chain when all included questions are answer-independent and have no side effects.

- one clear question;
- two to five mutually understandable options;
- a short description for each option;
- a free-form option when a path, technology, feature, or job requirement needs text;
- no internal command names in labels;
- no option that silently performs a side effect.

If no native question tool exists, render the same active question as a short numbered or lettered list. Do not claim that text options are clickable. Do not print the prose list and then invoke the native question tool; native question output is the only user-facing prompt for that turn.

For OpenCode, use `scripts/onboarding.py <path> --host opencode --chain` when a chain is safe. The chain may include only a precomputed independent prefix such as focus followed by time budget. Never chain intent with source selection, outcome detail with a dependent source question, skill calibration whose wording depends on the selected focus, external-action approvals, or discovery action and candidate selection. Recompute after answers to any dependent question. If the host’s chaining behavior is unknown, use one question per call.

Do not ask all onboarding questions in one message. After each submitted answer set, normalize the answers and choose or compute the next question. Skip questions that no longer affect the route.

## Question order

Use this order, with conditional branches:

| Order | Question | Ask when |
| ---: | --- | --- |
| 1 | What would you like to accomplish first? | Always when the request is broad or the learner has not stated a goal. |
| 2 | Which project or project type should we use? | Only when the chosen goal needs a source and one is not already selected. |
| 3 | Where should we focus first? | After the goal and source or project type are known. |
| 4 | How much time should the first stage fit into? | Before creating a staged blueprint or rebuild slice. |
| 5 | How comfortable are you with the relevant technologies/concepts? | After focus is known, using only the selected focus. |
| 6 | How should Upstack guide you? | Before choosing scaffold and reveal depth. |
| 7 | Should I save this plan in `.upstack/`? | After the draft inventory and first blueprint summary are shown. |

Do not ask for a target role unless the learner chooses role matching, mentions a job, or requests portfolio alignment. Do not ask about GitHub CLI unless the learner chooses public discovery or authenticated source preparation. Do not ask about MCP configuration unless a relevant capability would improve the chosen route and a fallback is available.

## Branch examples

### Any starting location

First ask, without inspecting the workspace:

> What would you like to accomplish first?

Offer the intent options above. After “Learn how an existing project works,” “Prepare for a technical interview,” “Build a portfolio project,” “Upgrade a specific skill,” or “Build or rebuild a real project,” ask the next outcome-specific question. Only then ask where the project or practice material should come from. This ordering is the same whether the agent starts in a home directory, an existing repository, or a broad editor workspace.

### Known local repository

Still ask the same intent question first. Do not assume that opening a repository means the learner wants to study it. After the learner chooses an intent, offer **use the current project** as one possible source alongside another local project, public discovery, or no repository when the selected goal supports that option. Then ask focus, time budget, relevant skill confidence, and guidance mode.

### Public discovery

Ask project type before skill level, because the relevant skill vector depends on the target. Then ask focus and time budget. Read metadata first. Only after the top candidates are enriched and displayed should the learner choose a candidate. Fork, clone, install, and execution are later separate confirmations.

## Persistence and resumption

Keep an in-memory draft while the interview is incomplete. If the host can persist session context, store only normalized answers and a continuation token until the learner confirms `.upstack/` creation. After confirmation, write `USER_PROFILE.md`, `FOCUS.md`, `PROJECT_INVENTORY.md`, and `progress.json` together as the initial state.

If the learner returns later with a partial `.upstack/`, resume from the first unanswered decision. Do not repeat questions whose answers are present and still valid. If the repository changed materially, mark affected inventory fields stale and ask whether to refresh them.

## Question quality checks

Before asking, verify:

- The question changes a route, focus, stage size, scaffold level, or safety decision.
- The learner can answer without knowing Upstack’s internal vocabulary.
- Options are mutually understandable and not overloaded.
- The next question can be selected from the answer.
- The question does not request secrets or authorize external side effects.
- The wording is concise enough for a native question UI.

If none of the remaining questions changes the plan, stop interviewing and show the draft route. Ask only for the persistence confirmation before writing `.upstack/`.
