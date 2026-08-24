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

## Intent-driven cross-source sequence

Do not search from a vague technology keyword alone. First normalize the learner’s request into explicit criteria: intended outcome, role or portfolio signal, stack, project shape, focus, concepts, skill level, time budget, and exclusions such as tutorial-only or boilerplate projects. Preserve the original request and show the criteria used for search.

Generate multiple recall lanes rather than one generic query. At minimum use:

1. name, description, and topic matching for project identity;
2. README matching for architecture, testing, documentation, and setup evidence;
3. real-world or portfolio matching with tutorial, boilerplate, and todo exclusions when appropriate; and
4. a focus-specific implementation lane for the chosen feature, domain, or engineering signal.

Search GitHub through these lanes, collect a larger recall pool, deduplicate by canonical owner/repository, enrich only the strongest candidates, and rank them against the learner’s criteria. A high star count or a familiar project name must not outrank a smaller project with stronger scope, evidence, and learning fit.

Use optional context sources to discover projects that GitHub search misses:

| Source | Use | Access boundary |
| --- | --- | --- |
| YouTube | Find walkthroughs, build logs, launch demos, channel expertise, and repository links in descriptions. | Use the YouTube Data API when configured or a host-provided web search result. API results require an API key and quota; do not scrape around limits. |
| X | Find launch threads, author posts, project links, implementation notes, and recent discussions. | Use X Recent Search when configured; it covers recent posts, not the complete archive. Full-archive access has higher access requirements. |
| Web/blog/forum search | Find project pages, articles, demos, talks, and links from sources not indexed well by repository search. | Use the host’s web-search or web-retrieval capability, or accept a user/host-provided JSON result file. Search snippets are leads, not verification. |
| Package registries and demo pages | Confirm package identity, ecosystem usage, live demos, and related projects. | Treat registry and demo metadata as context; verify the actual source repository and license before selection. |

Extract repository URLs from external titles, descriptions, transcripts, posts, and articles, canonicalize them to repository roots, and then verify each link through GitHub or another repository host’s metadata and README. Keep every external item attached to its source URL, author/channel, publication time, query, retrieved time, and extraction basis. Unverified links remain visible as leads and must not be ranked as verified candidates.

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

When combining cross-source evidence, do not treat mentions as quality proof. Use external evidence as a bounded context signal: a relevant walkthrough or author thread can improve discoverability and explainability, but it cannot replace repository metadata, README evidence, license clarity, testability, or scope fit.

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
| Cross-source context | bounded modifier | Relevant verified external references, never a quality substitute |

Do not present the score without its breakdown. Include uncertainty such as missing license, unclear setup, no visible tests, oversized scope, external-service dependence, or weak source provenance. Difficulty is not identical to popularity and must be recalibrated against the learner’s skill vector.

A candidate summary should look like:

```text
candidate:owner/repo — 82/100
   Metadata: TypeScript; topics: api, react; 12.4k stars; MIT; pushed recently.
   README: setup, architecture, tests, and deployment sections found.
   Root signals: package scripts, CI, test directory, Docker configuration.
   Learning fit: strong for React/API integration; backend queueing is advanced.
   Risks: requires an external database and has a large deployment surface.
   Provenance: metadata + README SHA + targeted root files.
```

## Shortlist interaction contract

After rendering the candidate report, ask one question with only these actions: **choose a repository to explore**, **search for more candidates**, or **stop here**. Do not repeat those actions in prose when using a native question tool. During this action turn, label candidate rows with their full repository names or stable `candidate:OWNER/REPO` identifiers; do not number candidate rows, because action numbers and candidate numbers must never coexist in the same turn.

If the learner chooses **choose a repository to explore**, ask a separate second question containing only the enriched candidate repositories. Use stable values such as `candidate:OWNER/REPO`, not an unlabeled number that can be confused with an action choice. Numeric replies are scoped to the active question: `2` on the action question means **search for more candidates**; `2` on the candidate question means the second repository. Never accept a candidate number while the action question is active, and never interpret an action number as a candidate selection.

In a text-only host, render one short numbered or lettered list for the active question only. Do not add a second numbered list for candidates while the action question is active. In a native-question host, the native question output is the only user-facing prompt for that turn. Do not show a prose action menu followed by a native candidate question, or a prose candidate menu followed by a native action question.

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

## Video-backed project evidence

If an external result includes a video that explains, demonstrates, or builds the candidate repository, retain the video as a first-class source. Record its canonical URL, title, channel or author, publication date when available, repository link, and evidence basis. Prefer chapters, host-approved transcript segments, or learner-reviewed markers for timestamps. A timestamp link should use the video platform’s supported start-time format and should preserve the canonical video identity.

Use `scripts/video_evidence.py` to create `.upstack/sources/video-map.md`. Each segment may link to a verified repository-relative path, concept ID, and next lesson or exercise. Mark mappings as observed when directly anchored by the supplied segment and repository evidence; mark them inferred when matched by terms or agent analysis. Never invent timestamps, source paths, chapter titles, or claims that the video teaches a concept.

If no chapters, transcript, or reviewed markers are available, keep the video metadata and link but mark the source `metadata_only`. The learner or host can add a reviewed marker list later. Video downloads, transcript retrieval, media conversion, and external publication require explicit approval and are separate from read-only discovery.

Generated Markdown should use ordinary HTTPS timestamp links and safe relative repository links so VS Code can open them from the workspace or current Markdown file and other coding agents can still read them as portable text. A video is supporting evidence and a follow-along aid; it does not replace repository README, license, source, or test verification.

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
