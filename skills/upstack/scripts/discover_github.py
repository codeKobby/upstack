#!/usr/bin/env python3
"""Discover learning repositories using metadata first, then README and root-content signals.

This helper is read-only. It never clones, forks, installs dependencies, or executes
candidate code. It prefers the GitHub CLI, falls back to the public REST API, and
returns explainable candidate records for an agent to present to the learner.
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


API_VERSION = "2026-03-10"
ANSI_RE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
DEFAULT_COUNT = 3
MAX_COUNT = 5
ROOT_TARGETS = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "tsconfig.json",
    "vite.config.ts",
    "next.config.js",
    "README.md",
)


def _run(command: list[str], timeout: int = 20) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, "", str(exc)
    return completed.returncode, ANSI_RE.sub("", completed.stdout), ANSI_RE.sub("", completed.stderr)


def _gh_available() -> bool:
    return shutil.which("gh") is not None


def _gh_search(query: str, count: int) -> tuple[list[dict[str, Any]], str | None]:
    fields = "fullName,description,language,license,stargazersCount,forksCount,pushedAt,updatedAt,url,defaultBranch,isArchived,isFork,size,openIssuesCount"
    code, stdout, stderr = _run([
        "gh", "search", "repos", query,
        "--archived=false",
        "--include-forks=false",
        "--limit", str(count),
        "--json", fields,
    ])
    if code != 0:
        return [], stderr.strip() or "gh search repos failed"
    try:
        return json.loads(stdout), None
    except json.JSONDecodeError as exc:
        return [], f"could not parse gh search output: {exc}"


def _api_get(url: str) -> tuple[Any | None, str | None]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "upstack-repository-discovery",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read()
    except Exception as exc:  # noqa: BLE001 - surface transport failure in report
        return None, str(exc)
    try:
        return json.loads(body.decode("utf-8", errors="replace")), None
    except json.JSONDecodeError as exc:
        return None, f"could not parse GitHub API response: {exc}"


def _api_search(query: str, count: int) -> tuple[list[dict[str, Any]], str | None]:
    params = urllib.parse.urlencode({"q": f"{query} archived:false fork:false", "per_page": count})
    payload, error = _api_get(f"https://api.github.com/search/repositories?{params}")
    if error:
        return [], error
    if not isinstance(payload, dict):
        return [], "GitHub search returned an unexpected response"
    rows = []
    for item in payload.get("items", []):
        rows.append({
            "fullName": item.get("full_name"),
            "description": item.get("description"),
            "language": item.get("language"),
            "license": item.get("license"),
            "stargazersCount": item.get("stargazers_count", 0),
            "forksCount": item.get("forks_count", 0),
            "pushedAt": item.get("pushed_at"),
            "updatedAt": item.get("updated_at"),
            "url": item.get("html_url"),
            "defaultBranch": item.get("default_branch"),
            "isArchived": item.get("archived", False),
            "isFork": item.get("fork", False),
            "size": item.get("size", 0),
            "openIssuesCount": item.get("open_issues_count", 0),
            "topics": item.get("topics", []),
        })
    return rows, None


def _decode_content(value: str, encoding: str | None = None) -> str:
    if encoding == "base64":
        try:
            return base64.b64decode(value).decode("utf-8", errors="replace")
        except (ValueError, UnicodeDecodeError):
            return ""
    return value


def _gh_api_json(endpoint: str, headers: list[str] | None = None) -> tuple[Any | None, str | None]:
    command = ["gh", "api", endpoint]
    for header in headers or []:
        command.extend(["-H", header])
    code, stdout, stderr = _run(command)
    if code != 0:
        return None, stderr.strip() or f"could not read GitHub API endpoint {endpoint}"
    try:
        return json.loads(stdout), None
    except json.JSONDecodeError as exc:
        return None, f"could not parse GitHub API output for {endpoint}: {exc}"


def _gh_metadata_enrichment(full_name: str) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    detail, error = _gh_api_json(f"repos/{full_name}")
    if error:
        errors.append(f"metadata: {error}")
        detail = {}
    languages, error = _gh_api_json(f"repos/{full_name}/languages")
    if error:
        errors.append(f"languages: {error}")
        languages = {}
    topics, error = _gh_api_json(f"repos/{full_name}/topics", ["Accept: application/vnd.github+json"])
    if error:
        errors.append(f"topics: {error}")
        topics = {}
    if not isinstance(detail, dict):
        detail = {}
    if not isinstance(languages, dict):
        languages = {}
    if not isinstance(topics, dict):
        topics = {}
    return {
        "license": _license_name(detail.get("license")),
        "topics": topics.get("names", []),
        "languages": languages,
        "default_branch": detail.get("default_branch"),
        "homepage": detail.get("homepage"),
        "has_wiki": detail.get("has_wiki"),
        "has_issues": detail.get("has_issues"),
    }, errors


def _api_metadata_enrichment(full_name: str) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    detail, error = _api_get(f"https://api.github.com/repos/{full_name}")
    if error:
        errors.append(f"metadata: {error}")
        detail = {}
    languages, error = _api_get(f"https://api.github.com/repos/{full_name}/languages")
    if error:
        errors.append(f"languages: {error}")
        languages = {}
    if not isinstance(detail, dict):
        detail = {}
    if not isinstance(languages, dict):
        languages = {}
    return {
        "license": _license_name(detail.get("license")),
        "topics": detail.get("topics", []),
        "languages": languages,
        "default_branch": detail.get("default_branch"),
        "homepage": detail.get("homepage"),
        "has_wiki": detail.get("has_wiki"),
        "has_issues": detail.get("has_issues"),
    }, errors


def _gh_read_file(full_name: str, path: str) -> tuple[str, dict[str, Any], str | None]:
    code, stdout, stderr = _run([
        "gh", "repo", "read-file", path, "--repo", full_name,
        "--json", "content,encoding,size,gitSHA,downloadUrl,name,path",
    ])
    if code != 0:
        return "", {}, stderr.strip() or f"could not read {path}"
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return "", {}, f"could not parse gh read-file output: {exc}"
    content = _decode_content(str(payload.get("content", "")), payload.get("encoding"))
    return content, payload, None


def _api_readme(full_name: str) -> tuple[str, dict[str, Any], str | None]:
    payload, error = _api_get(f"https://api.github.com/repos/{full_name}/readme")
    if error:
        return "", {}, error
    if not isinstance(payload, dict):
        return "", {}, "README endpoint returned an unexpected response"
    content = _decode_content(str(payload.get("content", "")), payload.get("encoding"))
    return content, payload, None


def _gh_root_files(full_name: str) -> tuple[list[dict[str, Any]], str | None]:
    code, stdout, stderr = _run([
        "gh", "repo", "read-dir", "--repo", full_name,
        "--json", "name,path,type,size",
    ])
    if code != 0:
        return [], stderr.strip() or "could not read repository root"
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return [], f"could not parse gh read-dir output: {exc}"
    return payload if isinstance(payload, list) else [], None


def _api_root_files(full_name: str) -> tuple[list[dict[str, Any]], str | None]:
    payload, error = _api_get(f"https://api.github.com/repos/{full_name}/contents")
    if error:
        return [], error
    if not isinstance(payload, list):
        return [], "repository contents returned an unexpected response"
    return [{"name": item.get("name"), "path": item.get("path"), "type": item.get("type"), "size": item.get("size")} for item in payload], None


def _api_read_file(full_name: str, path: str) -> tuple[str, dict[str, Any], str | None]:
    encoded = urllib.parse.quote(path, safe="/")
    payload, error = _api_get(f"https://api.github.com/repos/{full_name}/contents/{encoded}")
    if error:
        return "", {}, error
    if not isinstance(payload, dict):
        return "", {}, "file contents returned an unexpected response"
    content = _decode_content(str(payload.get("content", "")).replace("\n", ""), payload.get("encoding"))
    return content, payload, None


def _license_name(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("spdx_id") or value.get("name") or value.get("key")
    return value if isinstance(value, str) else None


def _terms(text: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9+#.-]+", text.lower()) if len(term) > 2}


def _readme_signals(content: str) -> dict[str, Any]:
    lower = content.lower()
    headings = [line.lstrip("#").strip() for line in content.splitlines() if re.match(r"^#{1,6}\s+", line)]
    signals = {
        "installation": bool(re.search(r"\b(install|installation|setup|get started|getting started)\b", lower)),
        "usage": bool(re.search(r"\b(usage|quickstart|quick start|example|run it|how to use)\b", lower)),
        "testing": bool(re.search(r"\b(test|testing|tests|pytest|jest|vitest|playwright|cypress)\b", lower)),
        "architecture": bool(re.search(r"\b(architecture|design|structure|flow|diagram|internals)\b", lower)),
        "contributing": bool(re.search(r"\b(contribut|development|developing)\b", lower)),
        "deployment": bool(re.search(r"\b(deploy|deployment|production|docker|hosting)\b", lower)),
        "license": bool(re.search(r"\blicen[cs]e\b", lower)),
        "environment": bool(re.search(r"\b(environment|env|configuration|config)\b", lower)),
    }
    return {"characters": len(content), "headings": headings[:40], "signals": signals, "urls": len(re.findall(r"https?://[^)\s]+", content))}


def _recency_score(value: str | None) -> int:
    if not value:
        return 0
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return 0
    days = max(0, (datetime.now(timezone.utc) - date).days)
    if days <= 90:
        return 10
    if days <= 365:
        return 8
    if days <= 730:
        return 5
    if days <= 1460:
        return 2
    return 0


def _popularity_score(stars: int) -> int:
    if stars <= 0:
        return 0
    return min(10, max(1, int(math.log10(stars + 1) * 2)))


def _score_candidate(metadata: dict[str, Any], readme: dict[str, Any], root_files: list[dict[str, Any]], query: str) -> dict[str, Any]:
    description = metadata.get("description") or ""
    languages = {str(metadata.get("language") or "").lower()}
    corpus = _terms(" ".join([metadata.get("fullName") or "", description, str(metadata.get("language") or ""), " ".join(metadata.get("topics") or [])]))
    query_terms = _terms(query)
    overlap = len(query_terms & corpus) / max(1, len(query_terms))
    stack_fit = min(25, round(overlap * 25))
    readme_signals = readme.get("signals", {})
    documentation = min(20, sum(3 for key in ("installation", "usage", "architecture", "environment") if readme_signals.get(key)) + (2 if readme.get("characters", 0) >= 1200 else 0))
    file_names = {str(item.get("name") or "").lower() for item in root_files}
    testability = 15 if any("test" in name or "spec" in name for name in file_names) or readme_signals.get("testing") else 0
    testability += 5 if readme_signals.get("testing") and any(name in file_names for name in {"package.json", "pyproject.toml", "go.mod", "cargo.toml"}) else 0
    testability = min(20, testability)
    license_name = _license_name(metadata.get("license"))
    license_score = 10 if license_name and license_name.lower() not in {"unknown", "noassertion", "other"} else 3 if license_name else 0
    maintenance = _recency_score(metadata.get("pushedAt") or metadata.get("updatedAt"))
    popularity = _popularity_score(int(metadata.get("stargazersCount") or 0))
    total = min(100, stack_fit + documentation + testability + license_score + maintenance + popularity)
    reasons = []
    if stack_fit >= 15:
        reasons.append("metadata matches the requested stack or topic")
    if documentation >= 12:
        reasons.append("README provides usable setup, usage, architecture, or environment guidance")
    if testability >= 10:
        reasons.append("repository exposes testing signals")
    if maintenance >= 8:
        reasons.append("repository has recent activity")
    if license_score == 0:
        reasons.append("license is not visible in metadata")
    if not reasons:
        reasons.append("candidate requires closer inspection")
    return {
        "overall": total,
        "breakdown": {
            "stack_fit": stack_fit,
            "documentation": documentation,
            "testability": testability,
            "license_clarity": license_score,
            "maintenance": maintenance,
            "popularity_signal": popularity,
        },
        "reasons": reasons,
        "uncertainty": ["GitHub metadata and README signals are proxies, not proof of teaching quality", "difficulty still needs learner calibration and a staged scope"],
    }


def discover(query: str, count: int = DEFAULT_COUNT, backend: str = "auto") -> dict[str, Any]:
    count = max(1, min(MAX_COUNT, count))
    chosen_backend = backend
    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    if backend in {"auto", "gh"} and _gh_available():
        rows, error = _gh_search(query, count)
        chosen_backend = "gh"
        if error:
            errors.append(error)
    if not rows and backend in {"auto", "api"}:
        rows, error = _api_search(query, count)
        chosen_backend = "github-rest"
        if error:
            errors.append(error)
    if not rows and backend == "gh":
        errors.append("GitHub CLI was requested but returned no candidates")
    candidates: list[dict[str, Any]] = []
    for metadata in rows:
        full_name = metadata.get("fullName")
        if not full_name:
            continue
        readme_content = ""
        readme_meta: dict[str, Any] = {}
        root_files: list[dict[str, Any]] = []
        candidate_errors: list[str] = []
        if chosen_backend == "gh":
            enriched_metadata, metadata_errors = _gh_metadata_enrichment(full_name)
        else:
            enriched_metadata, metadata_errors = _api_metadata_enrichment(full_name)
        candidate_errors.extend(metadata_errors)
        metadata = {**metadata, **enriched_metadata}
        if chosen_backend == "gh":
            readme_content, readme_meta, error = _gh_read_file(full_name, "README.md")
            if error:
                candidate_errors.append(f"README: {error}")
            root_files, error = _gh_root_files(full_name)
            if error:
                candidate_errors.append(f"root: {error}")
        else:
            readme_content, readme_meta, error = _api_readme(full_name)
            if error:
                candidate_errors.append(f"README: {error}")
            root_files, error = _api_root_files(full_name)
            if error:
                candidate_errors.append(f"root: {error}")
        root_names = {str(item.get("name") or "") for item in root_files}
        targeted: dict[str, Any] = {}
        for target in ROOT_TARGETS:
            if target == "README.md" or target not in root_names:
                continue
            if chosen_backend == "gh":
                content, meta, error = _gh_read_file(full_name, target)
            else:
                content, meta, error = _api_read_file(full_name, target)
            if error:
                candidate_errors.append(f"{target}: {error}")
                continue
            targeted[target] = {"size": len(content), "metadata": meta, "signals": _target_signals(target, content)}
        readme = _readme_signals(readme_content)
        candidate = {
            "metadata": {
                **metadata,
                "license": _license_name(metadata.get("license")),
                "topics": metadata.get("topics", []),
                "languages": metadata.get("languages", {}),
            },
            "readme": {**readme, "metadata": {key: readme_meta.get(key) for key in ("name", "path", "size", "gitSHA", "downloadUrl") if key in readme_meta}},
            "root_files": root_files[:120],
            "targeted_files": targeted,
            "score": _score_candidate(metadata, readme, root_files, query),
            "errors": candidate_errors,
            "provenance": "GitHub repository metadata first; README and selected root files read without cloning",
        }
        candidates.append(candidate)
    candidates.sort(key=lambda item: item["score"]["overall"], reverse=True)
    return {
        "version": 1,
        "query": query,
        "requested_count": count,
        "backend": chosen_backend,
        "candidates": candidates,
        "errors": errors,
        "side_effects": [],
        "next_action": "present shortlist and ask the learner to choose; do not fork, clone, install, or execute automatically",
    }


def _target_signals(name: str, content: str) -> dict[str, Any]:
    lower = content.lower()
    signals: dict[str, Any] = {}
    if name == "package.json":
        try:
            data = json.loads(content)
            dependencies = {}
            dependencies.update(data.get("dependencies") or {})
            dependencies.update(data.get("devDependencies") or {})
            signals = {"scripts": sorted((data.get("scripts") or {}).keys())[:30], "dependencies": sorted(dependencies)[:60], "name": data.get("name")}
        except json.JSONDecodeError:
            signals = {"parse_error": True}
    elif name in {"pyproject.toml", "requirements.txt", "go.mod", "Cargo.toml", "pom.xml", "build.gradle", "build.gradle.kts"}:
        signals = {"dependency_mentions": [line.strip()[:160] for line in content.splitlines() if line.strip() and not line.lstrip().startswith(("#", "//"))][:30]}
    else:
        signals = {"keywords": [word for word in ("docker", "typescript", "react", "next", "test", "database", "api", "auth", "queue") if word in lower]}
    return signals


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="GitHub repository search query")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="number of candidates, 1-5 (default: 3)")
    parser.add_argument("--backend", choices=("auto", "gh", "api"), default="auto")
    parser.add_argument("--output", type=Path, help="write JSON report to a file")
    args = parser.parse_args()
    report = discover(args.query, args.count, args.backend)
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(rendered)
    return 0 if report["candidates"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
