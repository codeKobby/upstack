# Package-manager contract

Read this reference whenever Upstack is starting or modifying JavaScript/TypeScript work.

## Selection policy

For a new project, recommend **pnpm** and ask the learner to choose among pnpm, npm, Bun, Yarn, or another manager with a specified version. Do not treat the recommendation as an automatic selection. Store the selected manager in `.upstack/STATE.json` and `.upstack/PACKAGE_MANAGER.md`.

For an existing project, use the read-only `scripts/package_manager.py <path> --json` resolver. Treat evidence in this order, with one safety exception: a contradictory root signal is always surfaced as a conflict rather than silently overridden.

| Evidence | Meaning |
| --- | --- |
| `package.json:packageManager` | Strongest individual declaration when valid and recognized. |
| Matching root lockfile | Corroborates the declaration and identifies the operational lockfile. |
| Contradictory root lockfile | Conflict signal; requires learner choice even when a declaration exists. |
| Existing scripts and documentation | Supporting evidence; do not override a declaration or lockfile without learner input. |
| No evidence | Ask the learner and recommend pnpm for new JavaScript/TypeScript work. |

Recognized lockfiles are `pnpm-lock.yaml`, `package-lock.json` or `npm-shrinkwrap.json`, `bun.lock` or `bun.lockb`, and `yarn.lock`. A declaration plus a matching lockfile is detected safely; a declaration plus a different manager’s lockfile, or multiple manager lockfiles, is a conflict and requires a choice. Do not guess, delete a lockfile, or treat the declaration as permission to migrate.

## Existing projects

Preserve the detected manager by default. Use its command family consistently:

| Manager | Install | Run scripts | Execute a binary |
| --- | --- | --- | --- |
| pnpm | `pnpm install` | `pnpm run <script>` | `pnpm exec <binary>` |
| npm | `npm install` | `npm run <script>` | `npm exec -- <binary>` |
| Bun | `bun install` | `bun run <script>` | `bunx <binary>` |
| Yarn | `yarn install` | `yarn <script>` | `yarn exec <binary>` |

Never mix manager commands in one lesson or silently replace an existing lockfile.

## Migration boundary

If the learner chooses a manager different from the detected manager, stop before installation or file changes. Show the detected evidence, target manager, affected lockfiles, package scripts that may need changes, exact commands, and rollback or preservation plan. Ask a separate confirmation question. Only after confirmation may the agent modify package scripts, regenerate a lockfile, install dependencies, or update the project contract. Dependency installation remains a separate side-effect confirmation even when the manager itself is already selected.

## Lesson integration

Package management is part of the first setup lesson, but the agent should teach it rather than hide it. Explain what the package manager controls, why the project uses that manager, how lockfiles preserve reproducibility, and what command will run before executing it. The learner may choose another manager; record the decision and continue the curriculum without restarting onboarding.

## Provenance and limits

Detection is based on local files and is read-only. The resolver does not install packages, execute scripts, edit manifests, or inspect registry credentials. “Recommended” does not mean universally superior; compatibility with the existing project, workspace support, runtime choice, team convention, and learner preference may justify another manager.
