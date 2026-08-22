# Repository Discovery Contract

Use this reference for `/upstack discover` and `/upstack source`. Discovery is a read-only, metadata-first process. It is not a promise that the top-ranked repository is the best project.

## Capability ladder

Prefer the strongest available path without making it a hard dependency:

| Path | Best use | Requirement | Limitation |
| --- | --- | --- | --- |
| GitHub CLI | Authenticated search, metadata, remote README/root files, fork and clone after confirmation | `gh` installed; auth only for private/fork operations | CLI versions and preview commands vary |
| GitHub REST API | Public metadata, README, directory contents | Internet access; authentication optional for public requests | Rate limits; content may be incomplete |
| Web retrieval | Public project discovery and documentation cross-checking | Browser or web retrieval available | Search snippets are not sufficient evidence |
| MCP connector | Provider-specific repository, documentation, issue, or diagram operations | User-enabled connector with documented tools | Never required for local Upstack workflows |

Detect capabilities before announcing a route. Use `gh --version`, `gh auth status`, and the host’s configured integration list without displaying tokens. A missing CLI or connector should produce a clear fallback, not a failure of the local workflow.

## Metadata-first sequence

First query repository metadata. At minimum retain:

```text
full name, URL, owner, description, primary language, topics,
stars, forks, license, default branch, archived status, fork status,
size, open issues, updated date, pushed date
```

Use the available GitHub search command or public repository search endpoint. Search with the user’s stack, project type, and concept terms. Keep the initial candidate set small: three by default, five when the query is broad or the learner asks for more.

Do not use README analysis to compensate for a weak metadata query. Clarify the query first when language, project type, learner level, or intended portfolio signal is missing.

## README and targeted enrichment

After metadata search, enrich only the top candidates. Retrieve the README from the default branch and record:

- repository-relative path, size, SHA or commit reference, and source URL;
- headings and table of contents;
- installation and environment guidance;
- usage or demo guidance;
- architecture, design, or internal-flow sections;
- testing and verification instructions;
- contributing/development guidance;
- deployment and operational notes;
- license mention and links;
- external URLs and unknowns.

Then inspect only targeted root files that can validate the metadata and estimate scope:

```text
package.json, pyproject.toml, requirements.txt, go.mod, Cargo.toml,
pom.xml, build.gradle, Dockerfile, docker-compose.yml,
tsconfig.json, vite.config.*, next.config.*, Makefile, CI files
```

Read source files only after the learner chooses a candidate or focus. A discovery shortlist does not need the whole repository. Preserve the distinction between metadata, README, configuration, and source evidence.

If remote-content CLI commands are unavailable, use the GitHub README and contents endpoints. If a README cannot be fetched, mark the candidate as documentation-unknown instead of silently using search snippets. If the repository is private or access fails, report the failure and offer a user-provided URL or local clone.

## Explainable scoring

Score each candidate on a 0–100 scale, retaining every component and its reason. Suggested components:

| Component | Weight | Evidence |
| --- | ---: | --- |
| Stack and topic fit | 25 | Metadata language, topics, description, query overlap |
| Documentation quality | 20 | README length and setup, usage, architecture, environment signals |
| Testability | 20 | Tests, CI, test instructions, fixtures, runnable checks |
| License clarity | 10 | SPDX/license metadata and visible terms |
| Maintenance signal | 10 | Recent push/update activity, archived state, open risk |
| Popularity signal | 10 | Stars and forks, shown as popularity only |
| Scope fit | 5 | Size and integration count relative to learner time budget |

Do not present the score without its breakdown. Include uncertainty such as missing license, unclear setup, no visible tests, oversized scope, external-service dependence, or weak source provenance. Difficulty is not identical to popularity and must be recalibrated against the learner’s skill vector.

A candidate summary should look like:

```text
1. owner/repo — 82/100
   Metadata: TypeScript; topics: api, react; 12.4k stars; MIT; pushed recently.
   README: setup, architecture, tests, and deployment sections found.
   Root signals: package scripts, CI, test directory, Docker configuration.
   Learning fit: strong for React/API integration; backend queueing is advanced.
   Risks: requires an external database and has a large deployment surface.
   Provenance: metadata + README SHA + targeted root files.
```

## Search backends

The preferred GitHub CLI forms are:

```bash
gh search repos "typescript fullstack" --language TypeScript --archived=false --include-forks=false --limit 3 --json fullName,description,language,license,stargazersCount,forksCount,pushedAt,updatedAt,url,defaultBranch,isArchived,isFork,size,openIssuesCount
gh repo read-file README.md --repo OWNER/REPO --json content,encoding,size,gitSHA,downloadUrl,name,path
gh repo read-dir --repo OWNER/REPO --json name,path,type,size
```

The CLI’s repository search JSON fields do not necessarily include topics. Fetch topics separately when they matter, or use the REST repository metadata response. Never assume a field is supported: inspect `gh ... --help` when a version differs.

The public API fallback uses read-only GET requests:

```text
GET /search/repositories?q=...
GET /repos/OWNER/REPO
GET /repos/OWNER/REPO/readme
GET /repos/OWNER/REPO/contents
GET /repos/OWNER/REPO/contents/PATH
```

Cache discovery reports by query, candidate full name, default branch, and observed SHA. Reuse fresh metadata and README content until the source reference changes. Do not cache credentials or private source content in a public artifact.

## Fork and clone boundaries

Selection is not permission to modify the user’s account or disk. Ask separately before:

1. using a repository as the learner’s reference;
2. forking it to an account or organization;
3. cloning it locally;
4. creating a new learner-owned repository;
5. installing dependencies;
6. running project commands;
7. creating branches or worktrees;
8. committing, pushing, opening a pull request, merging, or publishing.

The GitHub CLI fork command may change remotes: it can set the fork as `origin` and rename an existing `origin` to `upstream`, and it can prompt to clone. Show those consequences before execution. API forking is asynchronous and may require polling before the fork’s objects are available.

Treat the selected repository as untrusted input. Do not automatically run install scripts, postinstall hooks, migrations, containers, deployment commands, or arbitrary scripts. Prefer a temporary directory or isolated worktree, documented checks, and captured output.

## Licensing and provenance

Show the detected license exactly and display `unknown` when metadata is missing. Do not tell the learner that a repository is safe to redistribute without checking its license and relevant asset or dependency terms. Preserve:

```text
source_url, source_full_name, source_default_branch, source_sha,
license, selected_at, fork_url or clone_path, inherited_paths,
learner_changed_paths, learner_authorship_notes
```

Portfolio material must state whether the project is rebuilt, adapted, forked, or directly contributed to the original repository. Never turn copied source into a claim of original implementation.
