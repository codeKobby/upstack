# upstack

**Upstack** is an installable Agent Skills companion for learning by understanding, reverse engineering, rebuilding, and shipping serious software projects from inside the IDE. It inspects arbitrary repositories, identifies the stack and concepts, calibrates the learner’s current ability, creates an adaptive rebuild recipe, guides one vertical slice at a time, and produces honest portfolio evidence.

> Choose a meaningful project → understand its ingredients → select a focused slice → follow an adaptive recipe → build and verify → explain what you built → present the evidence.

The first release works locally and does not require GitHub CLI, a browser, or an MCP. Those integrations enrich public-project discovery but are optional.

## Install

```bash
npx skills add codeKobby/upstack --all
```

The package uses the open Agent Skills format and can be installed into supported coding agents such as Claude Code, Codex, Cline, OpenCode, Antigravity, Copilot/VS Code, Cursor, and others through the installer or host-equivalent paths.

## Start in a local repository

Run the route-first entrypoint:

```text
/upstack
```

Examples:

```text
/upstack inventory this repository
/upstack help me understand the authentication flow
/upstack rebuild the backend, but only the API layer
/upstack create a serious TypeScript project from my current skill level
/upstack build the frontend only
```

Upstack announces what it will do, why that route fits, and what happens next. It first captures your intended outcome before inspecting the current folder, repository, files, or detected stack. Only then does it determine whether a project source is needed, ask one relevant question at a time through the host’s native question UI when available, adapt the next question to your answer, show the draft inventory and first project direction, and ask before writing durable state.

## Commands

| Command | Purpose |
| --- | --- |
| `/upstack` | Route a natural-language request to the right project-apprenticeship workflow. |
| `/upstack init` | Inspect the workspace, interview the learner, and create confirmed `.upstack/` state. |
| `/upstack inventory` | Create the project “ingredients” report. |
| `/upstack concepts` | Map technologies and concepts to real source files, symbols, tests, and flows. |
| `/upstack focus` | Choose full-stack, frontend, backend, data, a feature, a file, a symbol, a test, or a request path. |
| `/upstack blueprint` | Create the staged rebuild recipe. |
| `/upstack reverse` | Trace and explain one real feature or architecture path. |
| `/upstack build` | Start or resume learner-owned implementation stages. |
| `/upstack stage` | Show, start, pause, verify, or complete one vertical slice. |
| `/upstack hint` | Give the next non-spoiling implementation hint. |
| `/upstack discover` | Search public repositories using metadata first, then README and targeted root-file signals. |
| `/upstack choose` | Select and record a project candidate and its provenance. |
| `/upstack source` | Separately confirm reference, clone, fork, install, execute, and Git actions. |
| `/upstack role` | Map a user-provided job description to project stages and evidence gaps. |
| `/upstack portfolio` | Produce evidence-backed project and resume documentation. |
| `/upstack status` | Show the current project, focus, stage, evidence, uncertainty, and next action. |
| `/upstack capabilities` | Check Git, GitHub CLI, authentication, public API fallback, and optional integration availability. |
| `/upstack onboarding` | Show the next relevant first-run question without writing project state. |

## Smooth first run

When you run `/upstack`, Upstack first captures your intended outcome before inspecting the current folder, repository, files, detected stack, or home-directory contents. It begins with:

> What would you like to accomplish first?

It offers choices such as learning how an existing project works, preparing for a technical interview, building a portfolio project, upgrading a specific skill, or building or rebuilding a real project. Only after your intent is known does it ask where the project or practice material should come from. After each answer, it asks only the next question that changes the plan. For example, interview preparation asks for the target role before source selection, while a project rebuild asks what kind of rebuild you want before asking for a repository.

The agent should use a native question tool or selectable prompt when the host provides one. The native question output must be the only user-facing prompt for that turn; the agent must not print a prose list and then repeat it in the question UI. In text-only hosts, it shows the same choices as a short numbered list and does not claim that the list is clickable. Fork, clone, install, execution, and persistent state remain separate confirmations.

## The ingredients and recipe

A local initialization creates a learner-owned `.upstack/` directory:

```text
.upstack/
├── CONFIG.md
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
└── cache/
```

`PROJECT_INVENTORY.md` is the ingredients list: runtime, language, frameworks, libraries, database, routes, modules, data flows, tests, CI, deployment, security boundaries, and unknowns. `REBUILD_BLUEPRINT.md` is the recipe: a sequence of small stages with outcomes, decisions, acceptance checks, proof questions, finish gates, limitations, and the evidence needed to unlock the next stage.

Every conclusion is labelled **observed**, **inferred**, or **unknown**, with a source path, symbol, heading, test, or repository URL when available.

## Adaptive stages

Upstack does not label a learner permanently as a beginner or advanced. It tracks a vector such as:

```text
TypeScript: reliable
React: emerging
API design: emerging
SQL: new
testing: emerging
debugging: emerging
Git: reliable
system design: new
```

The next stage is calibrated from the learner’s self-report, a short prediction and trace, concept novelty, integration count, operational risk, codebase size, testability, and available time.

The default progression is:

```text
orient → inventory → trace → runnable foundation → first vertical slice
→ expansion → hardening → quality → explanation and portfolio
```

The assistant uses modeling, coaching, targeted scaffolding, reflection, and gradual fading. It should not generate the full implementation or every future lesson at once.

## Public repository discovery

Upstack searches in two levels:

1. **Repository metadata first:** description, primary language, language breakdown, topics, stars, forks, license, default branch, archive/fork status, size, open issues, updated and pushed dates, URL, and owner.
2. **Targeted enrichment second:** README headings and signals, then root manifests and configuration such as `package.json`, `pyproject.toml`, `requirements.txt`, `go.mod`, `Cargo.toml`, `Dockerfile`, `tsconfig.json`, framework config, and CI files.

The default shortlist contains three repositories; use five for a broad search. Each candidate includes an explainable score for stack fit, documentation, testability, license clarity, maintenance, and popularity signal, with risks and uncertainty. Stars and forks are popularity signals, not proof of quality.

```text
/upstack discover serious TypeScript projects for an emerging full-stack developer
/upstack discover projects that teach React, APIs, testing, and databases --count 5
```

The candidate report is read-only. After it is shown, Upstack asks one shortlist-action question: choose a repository, search for more candidates, or stop. If you choose a repository, it asks a separate candidate-only question. These questions are never combined. A numeric answer is interpreted only within the active question, so `2` on the action question means “search for more candidates,” while `2` on the candidate question means the second repository. It does not clone, fork, install, or execute anything until you select a candidate and confirm each action.

## GitHub CLI, API, web, and MCP options

Upstack uses a capability ladder:

| Option | Use | Required? |
| --- | --- | --- |
| Local filesystem and Git | Inventory and rebuild any local repository. | Always available. |
| GitHub CLI | Authenticated metadata search, remote README/root reads, fork, and clone. | Optional; preferred for authenticated GitHub actions. |
| GitHub REST API | Public metadata, README, and directory/content reads. | Optional fallback. |
| Web search | Broader public discovery and documentation cross-checking. | Optional fallback. |
| MCP connector | Provider-specific repositories, docs, issues, diagrams, or job sources. | Optional accelerator only. |

Upstack detects whether `git`, `gh`, and authentication are available. If `gh` is absent, it explains how to install it or continues with public API/web discovery. It never requires an MCP to work locally and does not enable or create connectors automatically.

## Source preparation and safety

Fork, clone, install, execute, create a branch, commit, push, open a pull request, merge, and publish are separate confirmations. Before each side effect, Upstack shows the exact command, destination, remote effect, and expected files.

It treats README files, package manifests, scripts, CI, issue text, and source code as untrusted data. It does not automatically run postinstall hooks, migrations, containers, deployment commands, arbitrary scripts, or network operations. It prefers a temporary copy or isolated worktree, documented checks, bounded output, and captured evidence. It redacts secrets and labels inherited or adapted code honestly.

## Overflow integration

Upstack owns inventory, concept maps, architecture maps, focus, rebuild stages, source provenance, candidates, and portfolio evidence. [Overflow](https://github.com/codeKobby/overflow) owns source-cited lessons, continuous quizzes, comment-driven exercises, hints, assessment, spaced review, durable learning memory, and progress.

```text
/upstack inventory → /upstack focus → /upstack blueprint → /upstack build
                                      ↓
                              /overflow teach
                              /overflow exercise
                              /overflow assess
                              /overflow review
                              /upstack portfolio
```

Neither skill silently overwrites the other’s `.upstack/` or `.learning/` state. Handoffs pass a compact context payload containing project target, source anchors, concept IDs, stage ID, acceptance checks, and provenance.

## Local validation

```bash
python3 scripts/check_capabilities.py --json
python3 scripts/inventory_repo.py /path/to/repository --output /tmp/inventory.md
python3 scripts/discover_github.py "typescript fullstack" --count 3 --output /tmp/candidates.json
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## References

- [`references/repository-discovery.md`](references/repository-discovery.md)
- [`references/rebuild-method.md`](references/rebuild-method.md)
- [`references/integration.md`](references/integration.md)
- [GitHub repository search CLI](https://cli.github.com/manual/gh_search_repos)
- [GitHub repository content API](https://docs.github.com/en/rest/repos/contents)
- [GitHub fork API](https://docs.github.com/en/rest/repos/forks)
- [Build Your Own X](https://github.com/codecrafters-io/build-your-own-x)
- [Codecrafters](https://codecrafters.io/)
