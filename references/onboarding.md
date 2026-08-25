# Upstack Onboarding Contract

Upstack onboarding is a short adaptive interview, not a questionnaire dump. Its purpose is to collect only the decisions that change the first project route, focus, stage size, evidence plan, destination, or design gate.

## Shared project gate for every command

Before handling `/upstack` or any Upstack subcommand, resolve the current project with:

```bash
python3 scripts/project_state.py . --command <subcommand>
```

If the result is `known_project`, load `.upstack/PROJECT.json` and `.upstack/STATE.json`, including canonical project/workspace/destination/source pointers, curriculum artifacts, current lesson, design/Stitch status, history, pending confirmations, and next action. Resume the requested command directly without asking the initial intent question or fresh onboarding questions. If the input path is inside a project-local installed skill directory such as `.agents/skills/upstack`, step out to the containing workspace first; never inspect the installed skill package as the learner project. If the result is `onboarding_required`, preserve the requested command while completing onboarding. If it returns `project_selection_required`, ask for an explicit project path instead of selecting a child of a broad workspace. This gate applies to project, inventory, concepts, focus, blueprint, reverse, build, stage, lesson, hint, assess, discover, choose, source, role, portfolio, and status commands.

After confirmed initialization, use `scripts/tutor.py` to persist the project record, normalized onboarding answers, learner profile, canonical pointers, curriculum, current lesson status, design/Stitch route, history, current stage, attempts, evidence, pending confirmations, and next action. Resume with `scripts/tutor.py status` or `scripts/tutor.py lesson`; do not create a second `.upstack/` state tree.

## First-run behavior

The agent must begin with the learner’s intent. It must not inspect the current folder, repository, files, stack, home-directory contents, or child project names to decide the first question. The first turn is an intent gate only.

After the intent answer, inspect only the context required by that route:

- If the intent is interview preparation, what exact job requirements, role, level, interview horizon, and AI-use policy should guide the plan?
- If the intent is interview preparation, what does the learner currently know and what can they demonstrate in a small diagnostic?
- Is the selected project mode rebuild, scratch, clone, or study-only?
- Is the selected destination a new local folder, isolated worktree, source-adjacent notes, portfolio repository later, or plan-only?
- If code or artifacts will be local, what exact folder should hold them, and does its parent exist?
- Is the selected source a local project, public project, or new-project brief?
- If this is a fresh start, should Upstack guide the learner step by step, show the roadmap first, let the learner attempt first, or provide tightly bounded help after an attempt?
- Which package manager should a JavaScript/TypeScript project use: pnpm (recommended for new work), npm, Bun, Yarn, or another specified manager?
- If an existing manager is detected, should Upstack preserve it or plan a separately confirmed migration?
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

When the host exposes a callable native question or choice tool—such as `AskUserQuestion`, OpenCode’s `question`, a selectable prompt, or an equivalent—**invoke it immediately** after computing the current question. A planner result is not a prompt and must not be printed as a substitute. Send only the current question payload to the native tool, and let that tool render the user-facing interaction. The default is one native-tool call containing one active decision per turn. A host with verified multi-question support may submit a short precomputed chain when all included questions are answer-independent and have no side effects.

- one clear question;
- two to five mutually understandable options;
- a short description for each option;
- a free-form option when a path, technology, feature, or job requirement needs text;
- no internal command names in labels;
- no option that silently performs a side effect.

If no callable native question tool exists, render the same active question as a short numbered or lettered list. Do not claim that text options are clickable. Do not print the prose list and then invoke the native question tool; native question output is the only user-facing prompt for that turn.

Use `scripts/onboarding.py <path> --json` as a controller and follow its `delivery` object. For a native host, invoke the named or verified equivalent tool and send only `questions`; for a text-only host, render only the current question. A chain plan is not permission to print a menu or to simulate a tool call. A host with verified multi-question support may use `scripts/onboarding.py <path> --host HOST_ID --question-mode native-multi --json`; the chain may include only a precomputed independent prefix such as focus followed by time budget. Never chain intent with source selection, outcome detail with a dependent source question, skill calibration whose wording depends on the selected focus, external-action approvals, or discovery action and candidate selection. Recompute after answers to any dependent question. If the host’s chaining behavior is unknown, use one question per call.

Do not ask all onboarding questions in one message. After each submitted answer set, normalize the answers and choose or compute the next question. Skip questions that no longer affect the route.

## Question order

Use this order, with conditional branches:

| Order | Question | Ask when |
| ---: | --- | --- |
| 1 | What would you like to accomplish first? | Always when the request is broad or the learner has not stated a goal. |
| 2 | What role or interview target should we prepare for? | For interview intent, before choosing source material. |
| 3 | What job requirements should guide the preparation? | For interview intent; accept pasted requirements, official URL, local file, or a labelled summary. |
| 4 | What is your current skill and knowledge level? | For interview intent, before selecting questions; treat it as an initial hypothesis to test. |
| 5 | What kind of project work should we do? | For other project-oriented goals; choose rebuild, scratch, clone-and-adapt, or study-only. |
| 6 | Where should the project or artifacts live? | Immediately after project mode, before selecting a source or creating files. |
| 7 | What exact local folder should hold the code or artifacts? | Whenever the destination involves local code, a clone, a worktree, or local notes; especially from a broad workspace. |
| 8 | Confirm the resolved local destination. | Before creating files, scaffolding, cloning, branch/worktree state, or saving project state. |
| 9 | What should we build from scratch? | Only for scratch mode when the learner has not supplied a brief. |
| 10 | Which existing project should we use? | For rebuild, clone, or study mode when a source is not already selected. |
| 11 | How should we design the user experience? | For a scratch project with a graphical interface; always offer portable Markdown and offer Stitch only when its MCP is verified callable. |
| 12 | How should we teach while building from scratch? | For scratch mode; default to lesson-led guidance and keep meaningful implementation learner-authored. |
| 13 | Which package manager should we use? | For JavaScript/TypeScript projects; recommend pnpm for new work, preserve a detected manager by default, and ask separately before migration. |
| 14 | Where should we focus first? | After the project brief/source, design gate, fresh-start lesson mode, and package-manager decision are known. |
| 15 | How much time should the first stage fit into? | Before creating a staged blueprint or implementation slice. |
| 16 | How comfortable are you with the relevant technologies/concepts? | After focus is known, using only the selected focus. |
| 17 | How should Upstack guide you? | Before choosing scaffold and reveal depth for non-scratch routes. |
| 18 | Should I save this plan in `.upstack/`? | After the draft inventory, design artifacts, and first blueprint summary are shown. |

Destination and project mode are distinct decisions. Never infer “clone,” “rebuild,” or “build from scratch” from the current working directory, a repository URL, or a portfolio goal. When the learner starts in a home directory, editor workspace, or other broad folder, ask for the exact local destination path instead of writing into that broad folder or silently selecting one of its children. Resolve relative paths against the stated workspace, reject `/`, the home directory, the broad workspace itself when it has no project markers, files, and paths whose parent does not exist, then show the resolved path. A valid path still requires explicit destination confirmation before any write. A destination choice does not authorize cloning, forking, branch/worktree creation, publishing, or file writes; those remain separate confirmations. When a known project is resumed, its persisted destination pointer is authoritative unless the learner explicitly requests a correction through the live-session handoff route.

For JavaScript/TypeScript projects, run the read-only package-manager resolver after the source or brief is known. For a new project, recommend pnpm but ask the learner to choose. For an existing project, treat a lockfile or `package.json:packageManager` as observed evidence and preserve that manager unless the learner explicitly selects another. A different selection creates a separate migration-confirmation question; do not delete or regenerate lockfiles, change scripts, install dependencies, or mix manager commands before that confirmation.

## Complete curriculum, staged lessons

For every project mode, first map the complete project into an ordered curriculum: stages, concepts, source or design anchors, implementation outcomes, checks, proof questions, and finish gates. Do not generate every lesson, code patch, exercise, or assessment at once. Generate only the current stage when the learner requests or unlocks it, and recompute later stages when evidence or project scope changes. The learner may view the roadmap without receiving all lesson content.

A scratch project uses this design gate before UI implementation:

1. Create `.upstack/design/BRIEF.md` with the product problem, audience, primary outcome, constraints, and intended stack.
2. Create `.upstack/design/WIREFRAME.md` with the primary user journey, screen responsibilities, screen states, and low-fidelity Markdown wireframes.
3. Create `.upstack/design/DESIGN.md` as the portable design contract for approved tokens, accessibility assumptions, responsive behavior, and component decisions.
4. If the learner chooses Stitch and a verified Stitch MCP is callable, announce the external design action and ask for confirmation before creating or changing remote design data. Use the MCP to create or inspect a Stitch project, generate or edit screens, generate variants, or manage a design system only within the tool’s exposed schema. Preserve learner-approved decisions in the local design contract.
5. If Stitch is unavailable, unauthenticated, not permitted, or declined, continue with the Markdown artifacts. Do not block the apprenticeship on a design connector.

The portable Markdown wireframe is not a disposable fallback. It is the minimum source of truth across coding agents and remains alongside any visual design. Do not send private source code, secrets, personal data, or unreviewed repository content to a remote design service without explicit approval.

Do not ask for a target role unless the learner chooses role matching, mentions a job, or requests portfolio alignment. Do not ask about GitHub CLI unless the learner chooses public discovery or authenticated source preparation. Do not ask about MCP configuration unless a relevant capability would improve the chosen route and a fallback is available.

## Branch examples

### Any starting location

First ask, without inspecting the workspace:

> What would you like to accomplish first?

Offer the intent options above. For interview preparation, ask the role, exact requirements, AI-use policy, and learner skill/knowledge profile before asking for a source or generic question. For other project outcomes, ask the project mode and destination before asking for a source. If the route uses local code or artifacts, collect and confirm the exact destination path before selecting a source or creating files. For a scratch build, ask for the brief, UI-design path, and fresh-start lesson mode; for rebuild, clone, or study-only, ask for the existing source. In every scratch lesson, require a learner attempt, approved verification, explanation or teach-back, and feedback before unlocking the next stage.
 This ordering is the same whether the agent starts in a home directory, an existing repository, or a broad editor workspace.

### Known local repository

First run the shared project-state gate. If the repository has valid `.upstack/STATE.json`, treat it as the established learner project: load its canonical pointers, curriculum, current lesson, design/Stitch status, history, active directive, and next action, then continue that lesson or command. Do not ask the initial intent question again, do not create a second curriculum, and do not treat the installed skill directory as the repository. Only use the fresh intent and onboarding sequence when the project is unknown or the learner explicitly requests a new route.

### Public discovery

Ask project mode and destination before source discovery. For clone-and-adapt, ask which public or local reference to use, enrich public candidates, and show the exact clone destination only after the candidate is chosen. Read metadata first. Only after the top candidates are enriched and displayed should the learner choose a candidate. Fork, clone, install, and execution are later separate confirmations.

### Build from scratch

Ask for the destination category and exact local path before accepting a project brief. Build the complete curriculum map first, then ask for a brief and UI-design path. For a JavaScript/TypeScript brief, ask for the package manager and recommend pnpm for a new project. Always generate the portable Markdown brief, wireframe, and design contract as the local design gate. Offer a Stitch MCP path only when the current host exposes a verified callable Stitch capability; never auto-configure it or make it a prerequisite.

## Persistence and resumption

Keep an in-memory draft while the interview is incomplete. If the host can persist session context, store only normalized answers and a continuation token until the learner confirms `.upstack/` creation. After confirmation, write the project identity, normalized onboarding answers, learner profile, first curriculum plan, current lesson, and `STATE.json` together as the initial state.

If the learner returns later with `.upstack/STATE.json`, resolve the project first and resume from its `current_stage`, `completed_stages`, `attempts`, `pending_confirmation`, and `next_action`. Do not repeat questions whose answers are present and still valid, do not restart the initial intent question for another Upstack command, and do not create a second curriculum. If the repository changed materially, mark affected inventory fields stale and ask whether to refresh them.

If a project has recognizable source markers but no valid `.upstack/STATE.json`, return `onboarding_required`; do not treat it as known or claim that onboarding was completed. If the current location is a broad workspace, return `project_selection_required` and ask for the exact project path.

## Question quality checks

Before asking, verify:

- The question changes a route, focus, stage size, scaffold level, or safety decision.
- The learner can answer without knowing Upstack’s internal vocabulary.
- Options are mutually understandable and not overloaded.
- The next question can be selected from the answer.
- The question does not request secrets or authorize external side effects.
- The wording is concise enough for a native question UI.

If none of the remaining questions changes the plan, stop interviewing and show the draft route. Ask only for the persistence confirmation before writing `.upstack/`.
