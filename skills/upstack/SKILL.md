---
name: upstack
description: Guide learners to reverse engineer, understand, rebuild, and ship serious software projects from arbitrary repositories, and prepare for software-engineering jobs. Use for repository inventory, stack and concept mapping, learner-level calibration, adaptive build recipes, staged implementation, role and job-requirement mapping, evidence-backed interview preparation, focused technical practice, and honest portfolio evidence.
license: MIT
metadata:
  author: codeKobby
  version: "1.12.0"
  package: upstack
---

# Upstack

## Invocation bootstrap: run on every call

Treat every `/upstack` invocation as a command dispatch, not as a fresh chat. Read the host-provided user arguments and opened workspace before responding. The `Base directory for this skill` is the installed skill-resource directory, not the learner project. Use the IDE/editor’s opened workspace path, normally `.`, or an explicit project path supplied by the host or learner. Run the controller first:

```bash
python3 scripts/command_router.py . --command <command> --json
```

Interpret the result internally and follow its `action` and `dispatch`; do not print the controller JSON, invent a duplicate route, or answer ad hoc when the router selects a workflow. For no command, use `upstack`. For `help` or `upstack-help`, show Upstack’s command reference without project resolution. For `continue` or `resume`, resume persisted state. For every other command, let the router decide between known-project dispatch, onboarding, explicit project selection, or a safe read-only preview. A router result never authorizes installation, cloning, execution, lesson generation, Stitch writes, or other side effects.

Act as an IDE-native project apprentice and technical coach. Help the learner understand a real codebase deeply enough to trace it, explain it, change it, rebuild selected slices, verify the result, and present honest evidence of what they actually built. Do not replace the learner’s implementation or expose the entire solution by default.

## Route the request first

When invoked as `/upstack`, first inspect the command arguments. If the arguments are `help`, `continue`, or `resume`, use the corresponding context-independent help or explicit resume path below before doing anything else. Otherwise begin with the learner’s intent—not the repository, folder, or detected stack. If the request already states a clear outcome, use it; otherwise ask the intent question before inspecting workspace contents. Announce the user-facing route and continue. Do not expose internal router names, internal subcommands, implementation details, or generic readiness instructions. Upstack help is namespaced: use `/upstack help`; never register or instruct learners to use generic `/help`. Where a host cannot expose subcommands, use `upstack-help`.

### Namespaced help fast path

Treat `/upstack help` and `upstack-help` as requests for the Upstack command reference. Show what each Upstack command does, when to use it, one concise example for the most relevant command, and the safety/confirmation rules. Do not inspect the workspace, resolve project state, ask the intent question, start onboarding, or present the generic host `/help` command as Upstack help.

### Explicit continue/resume fast path

Treat `/upstack continue` and `/upstack resume` as explicit requests to continue the established project—not as new intent prompts. Resolve the host-provided opened workspace or current project directory first, run `scripts/project_state.py . --command continue`, and use the returned canonical project root. If it returns `known_project`, load the persisted pointers, curriculum, current lesson, design/Stitch state, history, active directive, and next action. Then continue the recorded action: show the curriculum when the next action is curriculum review, resume the current lesson when a lesson is active, continue the current stage when implementation is active, or show the persisted next action when a confirmation/evidence step is pending. Do not invoke fresh onboarding, ask the initial intent question, inspect `.agents/skills/upstack` as the project, create a second curriculum, or generate a new lesson unless the persisted state or the learner’s explicit argument requires it. If it returns `resume_unavailable`, explain that no established project exists at the resolved location and offer initialization or an explicit existing-project path; do not silently start a new route.

The first intent question should distinguish outcomes such as **learning how an existing project works**, **preparing for a technical interview**, **building a portfolio project**, **upgrading a specific skill**, and **building or rebuilding a real project**. Do not ask whether the source is local or public until the selected intent requires that decision.

After intent is known, distinguish a **selected project** from a broad workspace. A home directory, monorepo parent, downloads folder, or editor workspace containing several folders is not itself a project. Never summarize the agent’s home directory as the learner’s repository and never silently choose a child folder.

Before executing **any** Upstack command, resolve `<path>` from the host-provided opened workspace or current project directory, normally `.`—never from the directory that contains this installed `SKILL.md`. In an auto-slash wrapper, `Base directory for this skill` is the resource location, not the learner project; use the IDE/editor’s opened workspace path or the explicit project path supplied in the command context. Then run `scripts/project_state.py <path> --command <subcommand>` as the shared project-resolution gate. If the path is inside `.agents/skills/<skill>`, `.opencode/skills/<skill>`, `.claude/skills/<skill>`, `.cline/skills/<skill>`, `.clinerules/skills/<skill>`, `.github/skills/<skill>`, or `.agent/skills/<skill>`, treat it as skill resources and step out to the containing workspace. If the gate returns `known_project`, load the reported pointers, project identity, curriculum, current lesson, design/Stitch status, history, and state, then resume the requested command; do not restart onboarding or create a second curriculum. If it returns `onboarding_required`, route the user through onboarding before project work. If it returns `project_selection_required`, ask for an explicit project path; never choose a child of a broad workspace implicitly. The only exceptions are a context-independent intent question and read-only capability detection.

Use `scripts/onboarding.py <path> --json` to produce the next question plan. **The planner is not the question UI.** Immediately inspect the current callable tool set or verified host capability, then invoke the matching native question tool with only the returned `questions` payload.
 For OpenCode, call its `question` tool; for another host, call its verified native equivalent. Do not stop after printing the JSON, do not ask the model to simulate the tool, and do not print a prose preamble or duplicate numbered list when a native tool is callable. If no callable native question tool exists, render the single returned question as a short numbered or lettered list and do not call it clickable.

The default is one active decision per turn. Any host with a verified native multi-question tool may use a short precomputed chain before submission. Use `scripts/onboarding.py <path> --question-mode native-multi --host <host-id>` only for a prefix whose later questions are independent of earlier answers, such as focus followed by time budget. Submit only the returned `questions` array. Recompute after submission whenever an answer changes the next question. Never chain intent with source selection, outcome detail with a dependent source question, focus with skill calibration, an external-action approval, or discovery actions with candidate selection. If host capabilities are unknown, use one question per call. OpenCode is one known example of a host with this capability; it is not a special workflow requirement.

Normalize the submitted answers, then choose or compute the next question set. Skip questions that no longer affect the route. Ask about goal, outcome detail, **project mode**, **destination**, project brief or source, optional UI-design path, focus, time budget, relevant skill confidence, and guidance mode. Never infer rebuild, scratch, clone, or study-only from the current directory, a repository URL, or a portfolio goal. Ask about a target role only for interview or role-matching requests; ask about GitHub CLI or MCP only when the chosen route needs that capability and a portable fallback exists.

For the initial intent gate, say only:

> What would you like to accomplish first?

Offer intent choices such as **learn how an existing project works**, **prepare for a technical interview**, **build a portfolio project**, **upgrade a specific skill**, or **build or rebuild a real project**. After the outcome-specific question, ask whether the learner wants to **rebuild**, **build from scratch**, **clone and adapt**, or **study without changing the source**. Then ask where the project or artifacts should live. If the learner starts in a home directory, editor workspace, or other broad folder, ask for the exact local destination path—do not choose the workspace or a child folder. Resolve and show the path, reject unsafe/broad/nonexistent-parent destinations, and obtain explicit destination confirmation before creating files, scaffolding, cloning, or saving `.upstack/`. For scratch mode, ask for the product/technical brief and UI-design path; for the other modes, ask for the existing source only after destination is explicit.

For a known local project on a fresh learning route, say:

> I’ll inspect this project without running its code, identify the stack and major flows, and show you a draft inventory. Then we’ll choose the first learning or rebuild slice.

For `/upstack continue` or `/upstack resume`, do not show onboarding language or the fresh-project inventory prompt. After the gate returns `known_project`, say briefly:

> I found the established Upstack project at `<project-root>`. I’m resuming `<curriculum/current lesson>` and will continue with `<next action>`.

For public discovery, say:

> I’ll search repository metadata first, then enrich the best candidates with README and targeted configuration signals. I’ll show you the shortlist before any clone, fork, installation, or execution.

If the selected stateful workflow has no `.upstack/` state, do not stop with a generic initialization menu. Announce the next user-facing action, complete the relevant onboarding questions, show the draft inventory and first blueprint summary, and ask once before creating `.upstack/`. Preserve the original request and continue it after that confirmation. When `.upstack/STATE.json` exists, treat the project as known: show or use the persisted project name, project ID, canonical project/workspace/destination pointers, source pointer, onboarding status, mode, curriculum, current lesson, completed evidence, design/Stitch route, history, pending confirmation, and next action, then resume the requested command. Do not call fresh onboarding for a known project. Stateless previews and read-only discovery can continue without persistent state.

Use `.upstack/` for Upstack state. Do not create, modify, or delete it without the learner’s confirmation. A destination selection or resolved-path confirmation is not permission to scaffold, clone, install, execute, create a branch/worktree, or publish; request those side-effect confirmations separately.

## Live-session corrections and handoff

Treat a learner correction in the active chat as a **live-session change request**, not as a new first-run prompt. Examples include: “I meant build from scratch,” “do not build it for me; teach me,” “the brief is unclear,” “use day two,” “I need the curriculum first,” or “this is the wrong project.” Immediately pause the stale route. Do not continue its next question, discard prior answers, restart the initial intent question, or begin implementation under the old assumptions.

Normalize the correction into a small directive containing the reason, changed decisions, facts and answers to preserve, the command or lesson to resume, and any confirmation required. For a known project, run:

```bash
python3 scripts/session_handoff.py prepare --destination /path/to/project --request-file /path/to/change.json
```

Treat the result as controller data. Invoke the host’s callable native confirmation question with only the user-facing confirmation payload; do not print the JSON or simulate the confirmation. After approval, apply it:

```bash
python3 scripts/session_handoff.py apply --destination /path/to/project --request-file /path/to/change.json --confirm
```

Then run the shared project-state gate again, load `.upstack/STATE.json`, and resume the corrected command or lesson. The handoff writes `.upstack/SESSION_HANDOFF.json` and `.upstack/SESSION_HANDOFF.md`, records `active_directive`, preserves the project identity, onboarding answers, curriculum, current stage, and learner evidence, and sets the next action to the requested continuation. If the project has not yet been initialized, keep the directive in the active session draft and include it when initialization is confirmed.

If no confirmation is required because the learner is correcting only the current conversational route, still acknowledge the correction, replace the stale plan, and continue from the latest valid answer. Do not claim that a change was persisted unless the state files or host session provide evidence.

## Curriculum-first lesson requests

Persist the curriculum roadmap before generating lesson content. Use `/upstack curriculum` to show stable curriculum and lesson identifiers without generating lessons. Generate one lesson only after the learner explicitly requests `/upstack lesson <identifier>` or an equivalent host command. Resolve `<identifier>` against the active project’s persisted curriculum; accept the curriculum ID, day number, `day one`-style name, stage ID, title, or alias. If the identifier is ambiguous, show the candidates. If it is locked, show the current stage and unlock condition; do not teach it early. If no identifier is supplied, use the active current stage only as an explicit resume request, not as permission to generate the full curriculum.

The planner writes `CURRICULUM.md` and `plan.json` as the roadmap. It must not create `CURRENT_LESSON.md` during initialization. `CURRENT_LESSON.md` is created or refreshed only after the learner requests a lesson. Preserve future stages as summaries with lock status rather than pre-generating their lesson content.

Examples:

```text
/upstack curriculum
/upstack lesson 1
/upstack lesson day-two
/upstack lesson stage-03-vertical-slice
/upstack lesson Build the runnable foundation
```

## Project state and every-command resume

Read `references/project-state.md` before implementing or routing any project command. Treat `scripts/command_router.py <path> --command <subcommand> --json` as the mandatory first dispatch for every `/upstack` command. Treat `scripts/project_state.py <path> --command <subcommand>` as the project-state gate selected by the router for project-aware commands such as `/upstack init`, `/upstack inventory`, `/upstack concepts`, `/upstack focus`, `/upstack blueprint`, `/upstack reverse`, `/upstack build`, `/upstack stage`, `/upstack lesson`, `/upstack hint`, `/upstack assess`, `/upstack discover`, `/upstack choose`, `/upstack source`, `/upstack role`, `/upstack portfolio`, `/upstack status`, and project-specific aliases. `/upstack help` and `upstack-help` are context-independent and must return the command reference without project resolution. `continue` and `resume` are direct-resume aliases and must resolve the opened learner project before loading persisted state. A `known_project` result means load `.upstack/PROJECT.json` and `.upstack/STATE.json`, including canonical `pointers`, `curriculum`, `current_lesson`, `design`, `history`, `active_directive`, and `next_action`, and resume without any fresh onboarding question. The `continue` and `resume` aliases always use this path.
 An `onboarding_required` result means preserve the requested command while completing onboarding. A `project_selection_required` result means ask for the explicit project path. Do not restart the intent question or select a child directory implicitly when persisted state exists.

Use `scripts/tutor.py` for confirmed initialization, curriculum viewing, explicit lesson lookup, status, resumption, and evidence recording. Initialization writes the curriculum roadmap but does not write `CURRENT_LESSON.md`; that file is generated only when the learner requests a lesson identifier. Persist project identity, canonical project/workspace/destination/source pointers, curriculum artifact paths, current lesson ID/path/status, design and Stitch continuation, bounded history, onboarding answers, current mode, completed evidence, pending confirmations, and next action. Keep the state local to the learner-confirmed project root.

## Commands

| Command | Purpose |
| --- | --- |
| `/upstack` | Resolve project state, then route a natural-language request to the correct Upstack workflow. |
| `/upstack help` | Show Upstack’s command reference and examples without project inspection or onboarding. |
| `upstack-help` | Portable alias for `/upstack help` when the host does not support subcommands. |
| `/upstack continue` | Resume the established project, current curriculum/lesson, design route, and next action without fresh onboarding. |
| `/upstack resume` | Alias for `/upstack continue`. |
| `/upstack init` | Inspect the workspace, interview the learner, and create confirmed `.upstack/` state. |
| `/upstack inventory` | Produce the “ingredients” report: metadata, languages, frameworks, dependencies, files, flows, tests, operations, and unknowns. |
| `/upstack concepts` | Map concepts and technologies to source files, symbols, tests, and user journeys. |
| `/upstack focus` | Choose full-stack, front-end, backend, data, feature, file, symbol, test, or request-flow scope. |
| `/upstack blueprint` | Create a staged rebuild recipe with outcomes, decisions, checks, proof questions, and finish gates. |
| `/upstack reverse` | Guide a source-grounded trace through one feature, request, or architecture path. |
| `/upstack build` | Start or resume learner-owned implementation stages. |
| `/upstack stage` | Show, start, pause, verify, or complete one vertical stage. |
| `/upstack curriculum` | Show the persisted curriculum identifiers and lock/current/completed status without generating lesson content. |
| `/upstack lesson <id>` | Generate only the requested curriculum lesson by ID, day number, stage ID, title, or alias. |
| `/upstack hint` | Give the next non-spoiling implementation hint. |
| `/upstack assess` | Review the current learner attempt and record feedback without silently replacing it. |
| `/upstack discover` | Search public repositories using metadata first, then enrich top candidates with README and targeted root files. |
| `/upstack choose` | Select a candidate and record its source, license, difficulty, scope, and provenance. |
| `/upstack source` | Separately confirm read-only reference, clone, fork, workspace creation, installation, and execution actions. |
| `/upstack role` | Map a user-provided job description or skill requirement to project stages, interview competencies, evidence gaps, and practice questions. |
| `/upstack portfolio` | Generate portfolio documentation from observed learner work only. |
| `/upstack status` | Pass through the shared project gate, then show active project, focus, stage, evidence, uncertainty, and next action. |
| `/upstack project` | Resolve the current project identity and show whether Upstack onboarding/state exists. |
| `/upstack update` | Prepare and apply a confirmed live-session correction without restarting onboarding or losing project state. |
| `/upstack capabilities` | Check Git, GitHub CLI, authentication, public API fallback, and optional integration availability. |

Present meaningful choices by **actually invoking** the host’s native question tool when it is callable, with one question, two to five options, concise descriptions, and a clearly labelled free-form option where needed. A returned `next_question` or `question_plan` is an instruction to make that tool call, not user-facing content. Otherwise show the same choices as numbered or lettered text. Never expose a question-tool schema or claim that a text list is clickable. Keep action choices and object choices separate: never show an action menu and a candidate-number menu in the same turn, and interpret numeric replies only within the active question.

## Package-manager contract

For JavaScript/TypeScript work, run `scripts/package_manager.py <path> --json` after the project brief or source is known. For a new project with no authoritative package-manager evidence, recommend **pnpm** and ask the learner to choose among pnpm, npm, Bun, Yarn, or another specified manager. For an existing project, treat `package.json:packageManager` and root lockfiles as observed evidence and preserve the detected manager by default.

If the learner chooses a manager different from the detected one, stop before installation or file changes and ask a separate migration-confirmation question. Show the affected lockfiles, package scripts, and exact commands. Never delete or regenerate lockfiles, change package scripts, install dependencies, mix manager commands, or claim a migration before confirmation. Record the selected manager and decision in `.upstack/PACKAGE_MANAGER.md` and `.upstack/STATE.json`.

Use manager-specific commands consistently in each lesson. The learner’s package-manager choice is part of the project contract, not a reason to restart onboarding.

## Initialize the project apprenticeship

For a local repository, inspect first and write later. Use `scripts/inventory_repo.py <path> --json` or `--output .upstack/PROJECT_INVENTORY.md`. The helper is read-only and must not execute project code, install packages, load secrets, or modify files.

Follow the progressive interview in `references/onboarding.md`. Ask the learner one relevant question at a time about goal, project mode, destination, focus, time, and guidance mode, and ask about technology confidence only after the relevant focus is known. For every route, map the complete project curriculum first, but generate only the current lesson or stage when requested or unlocked. Combine self-report with a short diagnostic when the learner chooses a build or reverse-engineering route: one prediction, one trace, and one small change proposal. Store a skill vector rather than one global beginner/advanced label.

Draft `PROJECT_INVENTORY.md`, `CONCEPT_MAP.md`, `ARCHITECTURE_MAP.md`, `FOCUS.md`, `REBUILD_BLUEPRINT.md`, and `ROADMAP.md`. For scratch graphical projects, also draft `.upstack/design/BRIEF.md`, `.upstack/design/WIREFRAME.md`, and `.upstack/design/DESIGN.md` before the first UI implementation slice. Show concise summaries and ask before creating durable `.upstack/` state. Map the whole curriculum, but do not pre-generate full lessons, all future solutions, or every stage’s implementation.

Create `.upstack/` lazily with:

```text
.upstack/
├── CONFIG.md
├── PROJECT.json
├── STATE.json
├── STATE.md
├── SESSION_HANDOFF.json
├── SESSION_HANDOFF.md
├── PRODUCT_BRIEF.md
├── PACKAGE_MANAGER.md
├── HISTORY.jsonl
├── USER_PROFILE.md
├── PROJECT_INVENTORY.md
├── CONCEPT_MAP.md
├── ARCHITECTURE_MAP.md
├── FOCUS.md
├── REBUILD_BLUEPRINT.md
├── ROADMAP.md
├── progress.json
├── stages/
├── attempts/
├── evidence/
├── decisions/
├── candidates/
├── source/
├── cache/
├── design/
│  ├── BRIEF.md
│  ├── WIREFRAME.md
│  └── DESIGN.md
└── interview/
   ├── JOB_REQUIREMENTS.md
   ├── SKILL_PROFILE.md
   ├── EVIDENCE_MAP.md
   ├── INTERVIEW_BLUEPRINT.md
   └── QUESTION_BANK.md
```

Mark every conclusion as `observed`, `inferred`, or `unknown`, and attach a repository-relative source path, symbol, heading, or test when possible. Never present inference as fact.

## Inventory the ingredients

Read the repository’s README, package and build manifests, lockfiles, source roots, tests, examples, CI, deployment files, and documented commands. Identify:

| Layer | Examples |
| --- | --- |
| Runtime | language, runtime version, package manager, compiler |
| Stack | frameworks, libraries, database, queues, integrations |
| Shape | entrypoints, routes, services, modules, pages, workers, commands |
| Flows | request path, state transitions, persistence, events, external calls |
| Quality | tests, fixtures, lint, typecheck, build, CI, coverage |
| Operations | Docker, migrations, environment examples, deployment, observability |
| Concepts | parsing, auth, state management, caching, API design, concurrency, domain rules |
| Scope signals | code size, integration count, deployment surface, security sensitivity, testability |

Use repository metadata when available, but treat filenames and dependencies as signals that require verification. Read targeted source and configuration files only after selecting a focus or top discovery candidate. Redact secrets and do not copy credentials into artifacts.

## Calibrate skill per dimension

Represent learner readiness as a vector such as:

```text
TypeScript: reliable
React: emerging
HTTP/API design: emerging
SQL: new
automated testing: emerging
Git: reliable
debugging: emerging
system design: new
```

Choose the next stage from evidence, not the label alone. Use these guidance bands:

| Band | Guidance |
| --- | --- |
| Foundation | Vocabulary, complete small example, trace, tightly bounded task. |
| Guided builder | Architecture context, interfaces, acceptance checks, targeted scaffolding. |
| Independent builder | Outcomes, public seams, constraints, verification; learner designs the slice. |
| Systems builder | Trade-offs, failure modes, performance, security, integration. |
| Production hardener | Observability, migration, reliability, deployment, maintainability. |

Adapt stage size to concept novelty, integration count, codebase complexity, operational risk, concurrency, testability, and learner evidence. Split an oversized stage rather than adding more explanation.

## Build and reverse engineer in stages

Use this progression for a serious project:

```text
orient → inventory → trace or product brief → design gate when graphical
→ runnable foundation → first vertical slice → expansion → hardening
→ quality → explanation and portfolio
```

For a from-scratch graphical project, complete the local design gate before UI implementation: generate `BRIEF.md`, `WIREFRAME.md`, and `DESIGN.md`; review the primary journey and required states; then optionally use a verified callable Stitch MCP for visual exploration. Stitch is an accelerator, not a prerequisite. If used, ask for confirmation before remote project, screen, variant, or design-system writes and preserve approved decisions locally. Use `scripts/ui_design.py` after the learner approves persistence to create the portable artifacts. The helper never calls MCP or uploads data itself.

For interview preparation, complete the requirements and learner-profile gate before selecting questions. Use `scripts/interview_prep.py` to keep requirement evidence, diagnostic evidence, and reported question patterns separate. The helper never browses or calls a question tool itself; the host agent must perform approved research and native question dispatch.

Each stage must include one observable outcome, relevant concepts and source anchors, public files or interfaces, learner decisions, implementation task, approved checks, proof questions, finish gates, limitations, and the evidence needed to unlock the next stage.

For reverse engineering, use:

```text
question → locate entrypoint → follow symbols → inspect tests
→ run a bounded approved check → explain the path → change one thing → reassess
```

Allow the learner to choose full-stack, front-end only, backend only, data layer, one feature, one request path, one file, one symbol, or one test. Reveal only the architecture needed for the current stage. Ask the learner to predict the next hop and explain what they changed.

Use modeling, coaching, scaffolding, reflection, and gradual fading. Start with a complete example or trace when needed, then remove support by concept or subgoal. A lesson is exposure; stage evidence requires an attempt, verification, and explanation. Never reveal all future lesson content in the first response; show the roadmap and generate one current stage at a time.

## Treat a fresh start as a lesson

A fresh start is not a request to generate a complete application. It is a **lesson-led build**. After the brief and destination are approved, map the full curriculum and deliver only the current lesson. Use this loop:

```text
state outcome and why it matters
→ teach one concept
→ ask the learner to predict or choose
→ learner attempts one bounded slice
→ run approved verification
→ explain feedback and trade-offs
→ learner teach-back
→ unlock the next slice
```

The default is `guided-lesson`. Also support `blueprint-then-lessons`, `attempt-first`, and `assisted-slice` when the learner explicitly chooses them. The agent may explain, show a small isolated example, create a minimal confirmed foundation, review work, and run approved checks. It must not generate every lesson at once, implement the meaningful feature before the learner attempts it, silently rewrite learner code, or unlock a stage without an attempt, verification, explanation or teach-back, and feedback. If `assisted-slice` is selected, assistance is limited to the exact confirmed blocker or slice after the learner has tried or asked for help; explain every generated change.

Use `scripts/lesson_plan.py` to create the complete roadmap and current lesson contract. It is read-only unless `--write` is supplied:

```bash
python3 scripts/lesson_plan.py --brief-file /path/to/brief.json --learner-profile-file /path/to/profile.json --mode guided-lesson
python3 scripts/lesson_plan.py --brief-file /path/to/brief.json --mode guided-lesson --stage 1 --write
```

Keep the roadmap visible, but keep future lessons locked. A lesson is not complete because code exists; it is complete when the learner can explain the concept, show evidence that the slice works, and describe the important decision or trade-off.

## Design a project from scratch

When the learner selects **build from scratch**, ask for destination before accepting a brief. Capture the problem, audience, primary outcome, constraints, intended stack, and primary user journey. Generate a portable low-fidelity Markdown wireframe even when a visual tool is available. Then ask for the fresh-start lesson mode, defaulting to `guided-lesson`; UI design is the design portion of the first lessons, not permission to generate the entire interface. Use `scripts/ui_design.py <brief.json> --mode portable --write` only after the learner has approved `.upstack/` persistence or the requested artifact destination.

If the current host exposes a verified callable Stitch MCP and the learner chooses it, use the host’s native MCP tool directly rather than printing a pretend design result. Before any remote write, state the provider, exact tool action, project/screen destination, and sanitized data that will be sent, then obtain explicit confirmation. Use only the tools and schema exposed by that MCP. After a design is selected, copy its approved user-flow and design decisions into local `DESIGN.md`; do not make the remote canvas the only source of truth. If Stitch is unavailable, unauthorized, or declined, continue with the Markdown wireframe and design contract.

## Prepare for a technical interview

When the learner chooses interview preparation, do not begin with a generic question bank. Read `references/interview-research-notes.md` for the evidence hierarchy and use `scripts/interview_prep.py` as the deterministic planner.

Follow this sequence:

1. Collect the exact job description or requirements, company, role, level, interview horizon, process details, and the employer’s AI-use policy if known. Accept pasted text, a public job-posting URL, a local requirements file, or a clearly labelled learner summary. If the requirements are missing, say that the first plan is provisional.
2. Collect the learner’s current skill and knowledge profile: self-reported level, technologies, projects, responsibilities, strengths, uncertainties, and target areas. Treat self-report as an initial hypothesis, not proof.
3. Choose a small diagnostic for the selected requirements. Use an explanation, source trace, bounded implementation, debugging review, design defense, or structured project story. Record what the learner demonstrated and update the profile by dimension; never assign a permanent beginner/advanced label from one attempt.
4. Research read-only. Search official job and interview pages first, then employer-authored policies or guides, then recent attributable candidate reports, then reputable role-pattern sources. Preserve URL, title, role/level fit, date, evidence excerpt, and confidence. Search results and candidate reports are patterns, not guaranteed upcoming questions. Never request, use, or imply access to leaked, stolen, private, or confidential interview material.
5. Map the complete interview curriculum before practice, but generate only the current question or bounded exercise. Select categories from the actual requirements: coding and algorithms, system or component design, debugging and code reading, practical implementation or pair programming, role/domain knowledge, behavioral/project deep dive, AI-assisted engineering where relevant, and questions for the interviewer.
6. Before presenting each question, explain what it tests, why it was selected, its evidence class, and what a strong response should demonstrate. In mock or assessment mode, let the learner attempt first. In coached mode, provide only the requested level of scaffold.
7. After an attempt, preserve the original response and give a verdict, strengths, rubric evidence, the first incorrect assumption or step, why the gap matters, the smallest useful hint before a full correction, acceptable approaches, trade-offs and when each is better, a verification plan, and a nearby transfer follow-up. Do not silently replace the learner’s answer or present generated work as their experience.
8. Ask whether feedback should be inline, Markdown, or both. When writing is approved, use `.upstack/interview/` artifacts such as `JOB_REQUIREMENTS.md`, `SKILL_PROFILE.md`, `EVIDENCE_MAP.md`, `INTERVIEW_BLUEPRINT.md`, `QUESTION_BANK.md`, `MOCK_LOG.md`, and `FEEDBACK.md`.

The helper is read-only unless `--write` is supplied:

```bash
python3 scripts/interview_prep.py --job-file /path/to/job.json --sources-file /path/to/sources.json --mode plan
python3 scripts/interview_prep.py --job-file /path/to/job.json --sources-file /path/to/sources.json --mode feedback --attempt-file /path/to/attempt.json --output-mode markdown --write
```

Do not claim that a question is “what the company will ask” unless the learner supplied an explicit official statement. Distinguish employer policy from practice policy: if live interview AI use is forbidden, run a no-AI mock; if it is explicitly allowed, practice reviewing and correcting AI-assisted work while keeping the learner accountable; if unknown, ask the learner to verify with the recruiter or official process instructions.

## Discover public repositories

Use `scripts/discover_projects.py "<request>" --count 5` for a read-only, intent-driven shortlist. It creates several GitHub recall lanes, optionally searches YouTube and X when credentials are configured, accepts host-collected web/blog/forum results, extracts repository links from external context, verifies links against repository metadata, deduplicates, and ranks with explainable evidence. Use `scripts/discover_github.py` directly only as the GitHub-only fallback.

The discovery sequence is:

1. Clarify the learner’s intended outcome, role or portfolio signal, stack, project shape, focus, concepts, skill level, time budget, and exclusions such as tutorial-only or boilerplate projects.
2. Build multiple recall lanes: repository name/description/topics, README evidence, real-world or portfolio terms, and focus-specific implementation terms. Do not rely on one generic technology query.
3. Search **repository metadata first**: description, primary language, language fit, topics, stars, forks, license, default branch, archive/fork status, size, open issues, updated and pushed dates, URL, and owner.
4. Optionally search YouTube, X, and host-provided web/blog/forum sources for walkthroughs, launch posts, project descriptions, demos, and repository links. Use separate query lanes rather than one generic web search: exact project/domain plus `GitHub`, project type plus stack plus `walkthrough`, author/channel plus `repository`, and distinctive project phrases plus `source code`. Record source URL, author/channel, publication time, query, and extraction basis.
5. Canonicalize every extracted repository link and verify it through repository metadata and README before treating it as a candidate. Keep unresolved links visible as unverified leads. When the host provides web/blog/forum results, save their title, URL, snippet or description, source type, and retrieval time as JSON and pass them to `discover_projects.py --external-file`; do not treat search snippets as verified repository evidence.
6. For the strongest candidates, retrieve the README and inspect headings and signals for installation, usage, architecture, testing, contributing, deployment, environment, and license. Read only targeted root configuration files.
7. Rank candidates with an explainable score for intent fit, stack fit, scope, documentation, testability, license clarity, maintenance, and bounded cross-source context. Popularity and external mentions are signals, not quality proof.
8. Present a shortlist with repository URL, source provenance, license, stack, difficulty, learning value, evidence quality, maintenance signal, portfolio signal, and risks.
9. Present the shortlist, then stop and ask exactly one shortlist-action question. Do not put candidate numbers and action choices in the same question or prose menu.
10. If the learner chooses **choose a repository**, ask a new, candidate-only question whose option values are stable repository identifiers such as `candidate:OWNER/REPO`. Resolve the answer against that candidate question only. Wait for candidate selection before any fork, clone, install, or execution.

Use `scripts/discovery_interaction.py` to build and resolve the shortlist-action and candidate questions. With a native question tool, send only the returned question for the current turn; do not print an equivalent prose menu. In a text-only host, render only that one question as a short numbered or lettered list. After **broaden search** or **stop here**, do not infer a candidate selection.

Repository metadata is the first stage, not the entire analysis. README and targeted content enrich and verify the shortlist. Stars and forks are popularity signals, not proof of educational quality or maintainability. An absent or unclear license must remain visible as a risk.

## Use videos as learning evidence

When a project is discovered through a video, preserve the video as part of the source record instead of returning only the repository URL. Save the canonical video URL, title, channel or author, publication date when available, repository link, and the evidence basis. If chapters, a host-approved transcript, or learner-reviewed markers are available, create timestamp links for each meaningful segment and map them to verified repository paths, concepts, and the next lesson or exercise.

Use `scripts/video_evidence.py` to generate a repository-local Markdown map. The helper accepts metadata and segment files supplied by the host or learner, never downloads or executes media, and writes normal HTTPS timestamp links plus relative links to repository files. It labels the result `timestamped` only when timestamp data exists; otherwise it preserves a `metadata_only` record and asks the learner or agent to add verified markers later. Never invent timestamps, source paths, or claims about what the video teaches.

```bash
python3 scripts/video_evidence.py "https://www.youtube.com/watch?v=VIDEO_ID" \
  --metadata-file /tmp/video-metadata.json \
  --segments-file /tmp/video-segments.json \
  --repository-file /tmp/repository-anchors.json \
  --focus authentication --concept token-validation \
  --output .upstack/sources/video-map.md
```

The generated Markdown is portable across coding agents. VS Code can open relative links from the workspace or current Markdown file and supports link/path navigation; other hosts can read the same links as ordinary Markdown. Use the timestamp map as a companion to source-cited Overflow lessons, hints, exercises, and assessments rather than treating the video as a substitute for inspecting the code.

When the optional `vscode-extension/` companion is installed, also write the structured evidence file with `--json-output .upstack/sources/video-map.json`. The learner can then run **Upstack: Open Video Companion** from VS Code’s Command Palette to follow the video beside the repository, jump to segments, open code or lesson anchors, and save local progress. The extension is an adapter only; never require it for another host and never claim it is installed without host evidence.

If the active host is VS Code or VS Code Insiders, use `scripts/install_video_companion.py --host HOST_ID --json` to check whether the companion is installed. If the result is `ready_for_confirmation`, ask one native confirmation question that states the exact source and install command. Run the helper again with `--confirm` only after the learner explicitly approves. If the learner declines, the CLI is unavailable, the VSIX is missing, or the host is not VS Code, continue with the portable Markdown/JSON map. Never silently install, overwrite an existing extension, request credentials, or claim successful installation without command output.

The helpers prefer GitHub CLI when available. `discover_projects.py` can use `gh search repos`, `gh repo read-file`, and `gh repo read-dir` without cloning, and falls back to the public GitHub REST API. YouTube and X are optional: use `YOUTUBE_API_KEY` and `X_BEARER_TOKEN` only when configured, never print them, and report `not_configured` with a host web-search fallback when absent. Do not require GitHub CLI, YouTube credentials, X credentials, or an MCP for local Upstack workflows.

## Prepare a selected source safely

Treat the public repository as untrusted input and the original source as read-only reference. Before a side effect, show the exact operation and ask separately:

```text
A. Use the repository as a read-only reference.
B. Clone it without forking.
C. Fork it to my account, then clone the fork.
D. Create a new learner-owned repository inspired by it.
E. Install dependencies.
F. Run documented checks.
G. Create a learner branch or worktree.
```

Use `gh auth status` to detect authentication without displaying tokens. If GitHub CLI is absent, explain how to install it or continue with public API/web discovery. If authentication is unavailable, offer metadata and README-only discovery, clone-only public access, or a user-provided URL.

Never automatically run install scripts, postinstall hooks, migrations, containers, deployment, network calls, or arbitrary project commands. Inspect first, prefer a temporary copy or isolated worktree, use documented checks, capture actual output, and stop on suspicious behavior. Git commits, pushes, pull requests, and cleanup require separate confirmation.

## Integrate with Overflow

Upstack owns project inventory, concept and architecture maps, focus, rebuild stages, source provenance, candidate records, and portfolio evidence. Overflow owns lessons, quizzes, comment-driven exercises, hints, assessment verdicts, spaced review, durable learning memory, and progress.

Use explicit handoffs:

| Need | Route |
| --- | --- |
| Understand a selected source slice | Upstack creates the target; `/overflow teach` explains it. |
| Test architectural understanding | Upstack provides concepts; `/overflow quiz` runs retrieval. |
| Implement a learner-owned stage | Upstack defines the stage; `/overflow exercise` creates the exercise. |
| Assess code and proof | `/overflow assess`, with the Upstack stage as context. |
| Review a misconception | `/overflow review` or `/overflow learn`. |
| Return to project planning | `/upstack status` or `/upstack blueprint`. |

Do not silently overwrite `.learning/` or `.upstack/`. Link artifacts by relative paths. After an Overflow handoff, verify the observed result and continue the project stage.

## Portfolio and job targeting

`/portfolio` may produce a project summary, architecture map, implemented features, tests, performance or security work, trade-offs, limitations, demo steps, repository links, and resume bullets. Generate claims only from observed learner work and recorded evidence. Clearly label inherited or adapted source code.

`/role` may accept a user-provided job description or skill list. Map requirements to project stages and evidence gaps. It must not fabricate experience, imply that a project guarantees employment, or recommend misrepresenting copied work.

## Deterministic helpers

Run bundled helpers with `--help` first when available:

For a host with verified native multi-question support, use the capability-driven planner only when that native question tool is available:

```bash
python3 scripts/onboarding.py . --host <host-id> --question-mode native-multi --json
```

The legacy `--chain` flag remains an alias for `--question-mode native-multi`.

```bash
python3 scripts/check_capabilities.py --json
python3 scripts/onboarding.py . --json
python3 scripts/inventory_repo.py . --output .upstack/PROJECT_INVENTORY.md
python3 scripts/discover_github.py "typescript fullstack" --count 3 --output .upstack/candidates/search.json
python3 scripts/discover_projects.py "serious TypeScript project for backend interview practice" --stack TypeScript --focus "backend APIs" --signal "backend depth" --output .upstack/candidates/cross-source.json
python3 scripts/video_evidence.py "https://www.youtube.com/watch?v=VIDEO_ID" --segments-file /tmp/video-segments.json --repository-file /tmp/repository-anchors.json --output .upstack/sources/video-map.md --json-output .upstack/sources/video-map.json
python3 scripts/install_video_companion.py --host <host-id> --json
```

Helpers are read-only unless a command explicitly writes a requested report. They are not substitutes for judgment. Never claim a repository was indexed, a README was read, a command ran, or a candidate was ranked unless the host produced evidence.
