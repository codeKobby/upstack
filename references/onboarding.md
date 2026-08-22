# Upstack Onboarding Contract

Upstack onboarding is a short adaptive interview, not a questionnaire dump. Its purpose is to collect only the decisions that change the first project route, focus, stage size, or evidence plan.

## First-run behavior

The agent should first inspect only the current workspace context:

- Is the current directory the user’s home directory or another broad workspace?
- Is it inside a Git repository?
- Does it contain recognizable project markers?
- Are there obvious child project folders when the current directory is broad?
- Does the selected project already contain `.upstack/` state?

Do not describe the home directory as a project. Do not scan or summarize unrelated sibling directories as though they are one repository. If the current location is broad, ask the learner what they want to work on before choosing a project. If obvious local candidates exist, include their names as options; do not silently choose one.

Use user-facing language. Never mention internal helper names, internal routing phases, legacy state-directory names, or internal initializer wording. Start by asking what the learner wants to accomplish, not where the project comes from. For a broad workspace, say:

> I’m not going to treat this folder as the project. What would you like to accomplish first?

Offer these intent options:

- **Understand an existing project** — trace a local or later-selected codebase.
- **Rebuild a real project or feature** — create a staged apprenticeship rather than a generic tutorial.
- **Find a public project to build** — search repository metadata and show a shortlist before any clone or fork.
- **Start a new project** — choose a meaningful project idea and create a guided build plan.
- **Preview a workspace** — inspect without saving a learning workspace.

If a specific project path is already provided, announce:

> I’ll inspect that project without running its code, identify the stack and major flows, and show you a draft inventory. I’ll ask before saving your Upstack workspace.

## One question per turn

When the host exposes a native question or choice tool—such as `AskUserQuestion`, a selectable prompt, or an equivalent—use it. Make one question-tool call per turn with:

- one clear question;
- two to five mutually understandable options;
- a short description for each option;
- a free-form option when a path, technology, feature, or job requirement needs text;
- no internal command names in labels;
- no option that silently performs a side effect.

If no native question tool exists, render the same question as a short numbered or lettered list. Do not claim that text options are clickable.

Do not ask all onboarding questions in one message. After each answer, normalize it and choose the next question from the answer. Skip questions that no longer affect the route.

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

### Broad workspace

First ask:

> What would you like to accomplish first?

Offer the intent options above. After “Understand an existing project” or “Rebuild a real project or feature,” ask which local project or source to use. After “Find a public project to build,” ask what kind of project to search for. After “Start a new project,” ask what project shape. After “Preview a workspace,” inspect read-only and do not ask skill questions until the learner chooses to continue.

### Known local repository

First ask:

> What would you like to accomplish first?

Options:

- **Understand the existing code**
- **Rebuild a feature**
- **Build a similar project**
- **Map the stack and concepts first**

Then ask focus, time budget, relevant skill confidence, and guidance mode. Do not ask where the repository is; it is already known.

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
