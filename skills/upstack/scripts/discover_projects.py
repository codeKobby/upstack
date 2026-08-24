"""Discover project candidates across GitHub and optional public context sources.

GitHub remains the verification authority for repository metadata. YouTube and X
are optional context sources that can reveal project names, launch threads,
walkthroughs, and repository links. They never authorize cloning, forking,
installation, execution, or publication.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from discover_github import discover as github_discover
except ModuleNotFoundError:  # pragma: no cover - supports loading from another directory
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from discover_github import discover as github_discover


DEFAULT_SOURCES = ("github", "youtube", "x")
MAX_EXTERNAL_RESULTS = 20
REPO_URL_RE = re.compile(
    r"https?://(?P<host>(?:www\.)?(?:github\.com|gitlab\.com|codeberg\.org))/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)(?P<path>/[^\s<>)\]}]*)?",
    re.IGNORECASE,
)
TOKEN_RE = re.compile(r"[a-z0-9+#.-]{3,}", re.IGNORECASE)


def _terms(value: str) -> set[str]:
    return {token.casefold() for token in TOKEN_RE.findall(value or "")}


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        clean = " ".join(value.split()).strip()
        key = clean.casefold()
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def _criteria_text(request: str, stack: list[str], project_type: str, focus: str, concepts: list[str], level: str, signal: str) -> str:
    return " ".join(_unique([request, " ".join(stack), project_type, focus, " ".join(concepts), level, signal]))


def build_query_lanes(
    request: str,
    *,
    stack: list[str] | None = None,
    project_type: str = "",
    focus: str = "",
    concepts: list[str] | None = None,
    level: str = "",
    signal: str = "",
) -> list[str]:
    """Create diverse, intent-specific GitHub recall lanes instead of one generic query."""
    stack = stack or []
    concepts = concepts or []
    base = _criteria_text(request, stack, project_type, focus, concepts, level, signal)
    if not base:
        base = "serious software project"
    educational = "architecture tests documentation"
    scope = "production real-world portfolio" if signal or project_type else "real-world"
    lanes = [
        f"{base} in:name,description,topics",
        f"{base} in:readme {educational}",
        f"{base} {scope} -tutorial -boilerplate -todo",
        f"{base} {focus or 'feature'} implementation case-study",
    ]
    return _unique(lanes)


def _request_url(url: str, headers: dict[str, str] | None = None) -> tuple[Any | None, str | None]:
    request = urllib.request.Request(url, headers=headers or {"User-Agent": "upstack-project-discovery"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read()
    except Exception as exc:  # noqa: BLE001 - report transport failures as source status
        return None, str(exc)
    try:
        return json.loads(payload.decode("utf-8", errors="replace")), None
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON response: {exc}"


def canonical_repository_url(url: str) -> str | None:
    """Canonicalize a public GitHub/GitLab/Codeberg link to its repository root."""
    match = REPO_URL_RE.search(url or "")
    if not match:
        return None
    host = match.group("host").lower().removeprefix("www.")
    owner = match.group("owner")
    repo = match.group("repo").removesuffix(".git")
    return f"https://{host}/{owner}/{repo}"


def repository_key(url: str) -> str | None:
    canonical = canonical_repository_url(url)
    if not canonical:
        return None
    return canonical.removeprefix("https://").casefold()


def extract_repository_links(text: str) -> list[str]:
    return _unique([canonical_repository_url(match.group(0)) or "" for match in REPO_URL_RE.finditer(text or "")])


def _external_record(source: str, *, url: str, title: str, text: str, published_at: str | None = None, author: str | None = None) -> dict[str, Any]:
    combined = f"{title}\n{text}"
    return {
        "source": source,
        "url": url,
        "title": title,
        "text": text,
        "published_at": published_at,
        "author": author,
        "repository_links": extract_repository_links(combined),
        "provenance": {"source": source, "url": url, "retrieved_by": "optional public source search"},
    }


def search_youtube(query: str, *, api_key: str | None = None, limit: int = 10) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Search YouTube when YOUTUBE_API_KEY is configured; otherwise return a clear fallback."""
    api_key = api_key or os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        return [], {"source": "youtube", "status": "not_configured", "message": "Set YOUTUBE_API_KEY or use host web search; no YouTube request was made."}
    params = urllib.parse.urlencode({"part": "snippet", "q": query, "type": "video", "order": "relevance", "maxResults": min(50, max(1, limit)), "key": api_key})
    payload, error = _request_url(f"https://www.googleapis.com/youtube/v3/search?{params}")
    if error:
        return [], {"source": "youtube", "status": "error", "message": error}
    records: list[dict[str, Any]] = []
    for item in (payload or {}).get("items", []) if isinstance(payload, dict) else []:
        snippet = item.get("snippet") or {}
        video_id = (item.get("id") or {}).get("videoId")
        if not video_id:
            continue
        records.append(_external_record(
            "youtube",
            url=f"https://www.youtube.com/watch?v={video_id}",
            title=str(snippet.get("title") or ""),
            text=str(snippet.get("description") or ""),
            published_at=snippet.get("publishedAt"),
            author=snippet.get("channelTitle"),
        ))
    return records, {"source": "youtube", "status": "ok", "count": len(records), "query": query}


def search_x(query: str, *, bearer_token: str | None = None, limit: int = 10) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Search recent X posts when X_BEARER_TOKEN is configured."""
    bearer_token = bearer_token or os.environ.get("X_BEARER_TOKEN")
    if not bearer_token:
        return [], {"source": "x", "status": "not_configured", "message": "Set X_BEARER_TOKEN or use host web search; no X request was made."}
    params = urllib.parse.urlencode({
        "query": f"{query} -is:retweet",
        "max_results": min(100, max(10, limit)),
        "tweet.fields": "created_at,author_id,lang,public_metrics",
        "expansions": "author_id",
        "user.fields": "username,name",
    })
    payload, error = _request_url(
        f"https://api.x.com/2/tweets/search/recent?{params}",
        headers={"Authorization": f"Bearer {bearer_token}", "User-Agent": "upstack-project-discovery"},
    )
    if error:
        return [], {"source": "x", "status": "error", "message": error}
    users = {str(user.get("id")): user for user in (payload or {}).get("includes", {}).get("users", [])} if isinstance(payload, dict) else {}
    records: list[dict[str, Any]] = []
    for item in (payload or {}).get("data", []) if isinstance(payload, dict) else []:
        author = users.get(str(item.get("author_id")), {})
        username = author.get("username")
        records.append(_external_record(
            "x",
            url=f"https://x.com/{username}/status/{item.get('id')}" if username else f"https://x.com/i/web/status/{item.get('id')}",
            title=f"@{username}" if username else "X post",
            text=str(item.get("text") or ""),
            published_at=item.get("created_at"),
            author=username,
        ))
    return records, {"source": "x", "status": "ok", "count": len(records), "query": query, "coverage": "recent search only"}


def load_external_results(path: Path) -> list[dict[str, Any]]:
    """Load host-collected web/blog/forum results without fetching arbitrary pages."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("results", payload.get("items", payload)) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("external results must be a JSON list or an object with results/items")
    records: list[dict[str, Any]] = []
    for row in rows[:MAX_EXTERNAL_RESULTS]:
        if not isinstance(row, dict) or not row.get("url"):
            continue
        records.append(_external_record(
            str(row.get("source") or "web"),
            url=str(row.get("url")),
            title=str(row.get("title") or ""),
            text=str(row.get("text") or row.get("description") or row.get("snippet") or ""),
            published_at=row.get("published_at") or row.get("publishedAt"),
            author=row.get("author") or row.get("channel") or row.get("username"),
        ))
    return records


def _candidate_full_name(candidate: dict[str, Any]) -> str:
    metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else candidate
    return str(metadata.get("fullName") or metadata.get("full_name") or "").strip()


def _candidate_corpus(candidate: dict[str, Any]) -> str:
    metadata = candidate.get("metadata") if isinstance(candidate.get("metadata"), dict) else candidate
    readme = candidate.get("readme") if isinstance(candidate.get("readme"), dict) else {}
    return " ".join([
        str(metadata.get("fullName") or ""),
        str(metadata.get("description") or ""),
        " ".join(str(item) for item in metadata.get("topics") or []),
        " ".join(str(item) for item in readme.get("headings") or []),
    ])


def _rerank_candidate(candidate: dict[str, Any], criteria: str, external: list[dict[str, Any]], matched_lanes: list[str]) -> dict[str, Any]:
    base_score = candidate.get("score") if isinstance(candidate.get("score"), dict) else {}
    base_overall = int(base_score.get("overall") or 0)
    criteria_terms = _terms(criteria)
    corpus_terms = _terms(_candidate_corpus(candidate))
    intent_fit = round(100 * len(criteria_terms & corpus_terms) / max(1, len(criteria_terms)))
    evidence_count = len(external)
    source_count = len({item.get("source") for item in external})
    educational_noise = len(_terms(_candidate_corpus(candidate)) & {"tutorial", "boilerplate", "todo", "starter"})
    evidence_boost = min(12, evidence_count * 3 + max(0, source_count - 1) * 3)
    noise_penalty = min(10, educational_noise * 3)
    overall = max(0, min(100, round(base_overall * 0.55 + intent_fit * 0.33 + evidence_boost - noise_penalty)))
    score = {
        **base_score,
        "base_overall": base_overall,
        "overall": overall,
        "intent_fit": intent_fit,
        "cross_source_evidence": evidence_count,
        "cross_source_count": source_count,
        "noise_penalty": noise_penalty,
        "matched_lanes": matched_lanes,
    }
    updated = dict(candidate)
    updated["score"] = score
    updated["external_evidence"] = external
    updated["discovery"] = {
        "matched_lanes": matched_lanes,
        "source_count": source_count + (1 if base_overall else 0),
        "match_basis": "structured intent criteria, repository metadata/README signals, and optional external project references",
    }
    return updated


def discover_projects(
    request: str,
    *,
    count: int = 5,
    backend: str = "auto",
    sources: list[str] | None = None,
    stack: list[str] | None = None,
    project_type: str = "",
    focus: str = "",
    concepts: list[str] | None = None,
    level: str = "",
    signal: str = "",
    external_file: Path | None = None,
) -> dict[str, Any]:
    sources = sources or list(DEFAULT_SOURCES)
    stack = stack or []
    concepts = concepts or []
    criteria = _criteria_text(request, stack, project_type, focus, concepts, level, signal)
    lanes = build_query_lanes(request, stack=stack, project_type=project_type, focus=focus, concepts=concepts, level=level, signal=signal)
    statuses: list[dict[str, Any]] = []
    external: list[dict[str, Any]] = []
    if "youtube" in sources:
        records, status = search_youtube(criteria, limit=max(5, count * 2))
        external.extend(records)
        statuses.append(status)
    if "x" in sources:
        records, status = search_x(criteria, limit=max(10, count * 2))
        external.extend(records)
        statuses.append(status)
    if external_file:
        try:
            external.extend(load_external_results(external_file))
            statuses.append({"source": "external_file", "status": "ok", "count": len(external)})
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            statuses.append({"source": "external_file", "status": "error", "message": str(exc)})
    candidates_by_key: dict[str, dict[str, Any]] = {}
    lanes_by_key: defaultdict[str, list[str]] = defaultdict(list)
    errors: list[str] = []
    if "github" in sources:
        for lane in lanes:
            report = github_discover(lane, count=min(5, max(3, count)), backend=backend)
            errors.extend(report.get("errors") or [])
            for candidate in report.get("candidates") or []:
                key = _candidate_full_name(candidate).casefold()
                if not key:
                    continue
                lanes_by_key[key].append(lane)
                existing = candidates_by_key.get(key)
                if existing is None or int((candidate.get("score") or {}).get("overall") or 0) > int((existing.get("score") or {}).get("overall") or 0):
                    candidates_by_key[key] = candidate
    linked_by_key: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for evidence in external:
        for link in evidence.get("repository_links") or []:
            key = repository_key(link)
            if key:
                linked_by_key[key].append(evidence)
    # Verify GitHub links found outside GitHub search, but keep the external source trace.
    for key, evidence in list(linked_by_key.items())[:8]:
        if key.startswith("github.com/") and key not in candidates_by_key:
            full_name = key.removeprefix("github.com/")
            report = github_discover(f"repo:{full_name}", count=1, backend=backend)
            errors.extend(report.get("errors") or [])
            for candidate in report.get("candidates") or []:
                candidate_key = _candidate_full_name(candidate).casefold()
                if candidate_key:
                    candidates_by_key[candidate_key] = candidate
                    lanes_by_key[candidate_key].append(f"linked:{full_name}")
    ranked = []
    for key, candidate in candidates_by_key.items():
        evidence = linked_by_key.get(f"github.com/{key}", []) + linked_by_key.get(key, [])
        ranked.append(_rerank_candidate(candidate, criteria, evidence, _unique(lanes_by_key[key])))
    ranked.sort(key=lambda item: (int((item.get("score") or {}).get("overall") or 0), int((item.get("score") or {}).get("base_overall") or 0)), reverse=True)
    verified_repository_keys = {f"github.com/{key}" for key in candidates_by_key}
    unverified_links = sorted({link for item in external for link in item.get("repository_links") or [] if repository_key(link) not in verified_repository_keys})
    statuses.insert(0, {"source": "github", "status": "ok" if "github" in sources and ranked else "no_candidates" if "github" in sources else "not_requested", "query_lanes": lanes, "candidate_pool": len(candidates_by_key)})
    return {
        "version": 1,
        "request": request,
        "criteria": {"stack": stack, "project_type": project_type, "focus": focus, "concepts": concepts, "level": level, "portfolio_signal": signal},
        "query_lanes": lanes,
        "sources": statuses,
        "candidates": ranked[: max(1, min(10, count))],
        "external_evidence": external[:MAX_EXTERNAL_RESULTS],
        "unverified_repository_links": unverified_links,
        "errors": _unique(errors),
        "side_effects": [],
        "next_action": "present candidates with source provenance; ask the learner to choose before any clone, fork, install, execution, or publication",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", help="natural-language project goal or search request")
    parser.add_argument("--count", type=int, default=5, help="number of ranked candidates to return (default: 5)")
    parser.add_argument("--backend", choices=("auto", "gh", "api"), default="auto")
    parser.add_argument("--source", action="append", choices=("github", "youtube", "x"), help="source to use; repeat for multiple sources")
    parser.add_argument("--stack", action="append", default=[], help="technology or runtime criterion; repeatable")
    parser.add_argument("--project-type", default="", help="project shape such as web app, API, CLI, or systems project")
    parser.add_argument("--focus", default="", help="first learning/build focus")
    parser.add_argument("--concept", action="append", default=[], help="concept criterion; repeatable")
    parser.add_argument("--level", default="", help="learner level or stage size signal")
    parser.add_argument("--signal", default="", help="desired portfolio or interview signal")
    parser.add_argument("--external-file", type=Path, help="JSON results collected by host web/blog/forum search")
    parser.add_argument("--output", type=Path, help="write the JSON report to a file")
    args = parser.parse_args()
    report = discover_projects(args.request, count=args.count, backend=args.backend, sources=args.source, stack=args.stack, project_type=args.project_type, focus=args.focus, concepts=args.concept, level=args.level, signal=args.signal, external_file=args.external_file)
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(rendered)
    return 0 if report["candidates"] or report["external_evidence"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
