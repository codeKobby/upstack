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

Some coding agents provide a native question UI that can collect multiple questions before submission. Upstack uses that capability as an optional portable optimization for a short safe chain of answer-independent questions, such as focus followed by time budget. It does not chain intent into source selection, dependent outcome questions, focus into skill calibration, discovery actions into candidate selection, or any external-action approval. After answers are submitted, Upstack recomputes the next dependent question set. If chaining is unavailable or uncertain, it falls back to one question per call. OpenCode is one known example, but the workflow is not OpenCode-specific.

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

## Public project discovery

Upstack does not search from a single generic technology phrase. It first turns the learner’s request into criteria such as intended outcome, target role or portfolio signal, stack, project shape, focus, concepts, skill level, time budget, and exclusions such as tutorial-only or boilerplate projects. It then creates multiple search lanes for project identity, README evidence, real-world/portfolio fit, and the specific implementation focus.

GitHub remains the verification authority, searched through repository name/description/topics, README terms, language/topic filters, activity, license, issue, and scope signals. The default shortlist contains three repositories; use five for a broad search. Candidates are deduplicated, enriched, and ranked against the learner’s criteria rather than by stars alone.

Optional context search can use YouTube walkthroughs and descriptions, X launch threads and author posts, web/blog/forum results, package registries, and demo pages. These sources can reveal projects that GitHub search misses and often contain repository links. Upstack extracts and canonicalizes those links, verifies them through repository metadata and README evidence, and keeps the original source URL, author/channel, date, query, and extraction basis. An unverified link remains a lead, not a ranked candidate.

The default helper is:

```bash
python3 scripts/discover_projects.py "serious TypeScript project for backend interview practice" \
  --stack TypeScript --focus "backend APIs" --signal "backend depth" \
  --output .upstack/candidates/cross-source.json
```

YouTube and X are optional. They return a clear not-configured status unless `YOUTUBE_API_KEY` or `X_BEARER_TOKEN` is deliberately provided, and the host may instead supply web-search results through a JSON file. External mentions are bounded context signals, not proof of code quality, licensing, maintainability, or educational value.

### Video-backed projects

When a repository is found through a video, Upstack keeps both sources. It records the canonical video URL, title, channel or author, repository link, and evidence basis. If chapters, an approved transcript, or learner-reviewed markers are available, `scripts/video_evidence.py` generates `.upstack/sources/video-map.md` with clickable timestamp links, concept labels, and relative links to verified repository files. This lets the learner open a video segment, inspect the corresponding code, and request a source-cited lesson, hint, exercise, or assessment for that segment.

The Markdown map is portable across agents. VS Code supports relative Markdown links and workspace/file path navigation, while other coding agents can read the same links as ordinary Markdown. Upstack never invents timestamps or source anchors; without verified segment data it preserves a metadata-only video record and leaves timestamp enrichment for a later approved step.

For VS Code users, the repository includes an optional companion extension under [`vscode-extension/`](vscode-extension/). It opens a panel beside the code, embeds a recognized YouTube player when enabled, jumps to selected timestamps, highlights the active segment as playback advances, opens verified repository anchors, and stores local completion/current-segment state in `.upstack/sources/video-progress.json`. The extension is an adapter rather than a requirement: all other agents use the same Markdown and JSON maps.

The companion does not modify source code, download media, upload repository content, or invent mappings. It uses a restrictive webview policy, validates workspace-relative paths, and requires explicit learner interaction for progress writes. To enable it, install the extension through the normal VS Code extension workflow; the portable Upstack skill remains usable without it.

When Upstack detects a VS Code host, it can run `scripts/install_video_companion.py --host HOST_ID --json`. If a published Marketplace listing is verified, or the learner supplies an existing local VSIX, Upstack asks one explicit confirmation question containing the exact source and command. It installs only after approval. Until the companion is published to the Marketplace, the helper reports `marketplace_unavailable` when no VSIX is supplied and continues with the portable map instead of offering a dead Marketplace command.

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
python3 scripts/discover_projects.py "serious TypeScript project for backend interview practice" --stack TypeScript --focus "backend APIs" --signal "backend depth" --output /tmp/cross-source.json
python3 scripts/onboarding.py . --host <host-id> --question-mode native-multi --json
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
