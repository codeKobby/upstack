#!/usr/bin/env python3
"""Inspect a local repository for Upstack without executing project code."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "vendor",
    "venv",
    ".venv",
    "env",
    ".env",
    "dist",
    "build",
    "coverage",
    ".next",
    ".nuxt",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".turbo",
    ".idea",
    ".vscode",
    ".learning",
    ".upstack",
}

MANIFESTS = {
    "package.json": "JavaScript/TypeScript package manifest",
    "pnpm-lock.yaml": "pnpm lockfile",
    "yarn.lock": "Yarn lockfile",
    "package-lock.json": "npm lockfile",
    "bun.lockb": "Bun lockfile",
    "pyproject.toml": "Python project manifest",
    "requirements.txt": "Python dependency file",
    "Pipfile": "Python dependency file",
    "go.mod": "Go module manifest",
    "Cargo.toml": "Rust package manifest",
    "pom.xml": "Maven project manifest",
    "build.gradle": "Gradle build file",
    "build.gradle.kts": "Gradle Kotlin build file",
    "composer.json": "PHP package manifest",
    "Gemfile": "Ruby dependency file",
    "mix.exs": "Elixir project manifest",
    "Dockerfile": "Docker build file",
    "docker-compose.yml": "Docker Compose file",
    "docker-compose.yaml": "Docker Compose file",
    "Makefile": "Make build file",
    "justfile": "Just task file",
    "terraform.tf": "Terraform configuration",
    "serverless.yml": "Serverless configuration",
    "vercel.json": "Vercel configuration",
    "vite.config.ts": "Vite configuration",
    "vite.config.js": "Vite configuration",
    "next.config.js": "Next.js configuration",
    "next.config.mjs": "Next.js configuration",
    "tsconfig.json": "TypeScript configuration",
    "pytest.ini": "Pytest configuration",
    "jest.config.js": "Jest configuration",
    "vitest.config.ts": "Vitest configuration",
}

EXTENSIONS = {
    ".js": "JavaScript",
    ".jsx": "JavaScript/JSX",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript/TSX",
    ".py": "Python",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".c": "C",
    ".h": "C/C++ header",
    ".cc": "C++",
    ".cpp": "C++",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".ex": "Elixir",
    ".exs": "Elixir",
    ".swift": "Swift",
    ".dart": "Dart",
    ".sh": "Shell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".vue": "Vue",
    ".svelte": "Svelte",
}

SOURCE_ROOT_NAMES = {"src", "app", "lib", "server", "client", "frontend", "backend", "cmd", "internal", "packages"}
TEST_TOKENS = ("test", "tests", "spec", "specs", "__tests__", "__test__", "fixtures")
README_NAMES = ("README.md", "README", "README.rst", "readme.md")


def _safe_read(path: Path, limit: int = 120_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _run_git(root: Path, args: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _walk_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative_parts = path.relative_to(root).parts
        if any(part in IGNORE_DIRS for part in relative_parts):
            continue
        try:
            if path.stat().st_size > 2_000_000:
                continue
        except OSError:
            continue
        files.append(path)
    return files


def _readme_report(root: Path, files: list[Path]) -> dict[str, Any]:
    readmes = [path for path in files if path.name in README_NAMES]
    if not readmes:
        return {"present": False, "files": [], "headings": [], "signals": {}, "urls": 0}
    path = sorted(readmes, key=lambda candidate: (len(candidate.parts), candidate.as_posix()))[0]
    content = _safe_read(path)
    headings = [line.lstrip("#").strip() for line in content.splitlines() if re.match(r"^#{1,6}\s+", line)]
    lower = content.lower()
    signals = {
        "installation": bool(re.search(r"\b(install|installation|setup|get started)\b", lower)),
        "usage": bool(re.search(r"\b(usage|quickstart|quick start|example|run it)\b", lower)),
        "testing": bool(re.search(r"\b(test|testing|pytest|jest|vitest|playwright|cypress)\b", lower)),
        "architecture": bool(re.search(r"\b(architecture|design|structure|flow|diagram)\b", lower)),
        "contributing": bool(re.search(r"\b(contribut|development|developing)\b", lower)),
        "deployment": bool(re.search(r"\b(deploy|deployment|production|docker)\b", lower)),
        "license": bool(re.search(r"\blicen[cs]e\b", lower)),
    }
    return {
        "present": True,
        "files": [path.relative_to(root).as_posix()],
        "headings": headings[:40],
        "signals": signals,
        "urls": len(re.findall(r"https?://[^)\s]+", content)),
        "characters": len(content),
        "sha_hint": _run_git(root, ["hash-object", str(path.relative_to(root))]),
    }


def _manifest_report(root: Path, files: list[Path]) -> dict[str, Any]:
    found: list[dict[str, Any]] = []
    for path in files:
        if path.relative_to(root).parts[:-1]:
            continue
        if path.name not in MANIFESTS:
            continue
        entry: dict[str, Any] = {"path": path.name, "kind": MANIFESTS[path.name]}
        content = _safe_read(path, 200_000)
        if path.name == "package.json":
            try:
                data = json.loads(content)
                entry["name"] = data.get("name")
                entry["scripts"] = sorted((data.get("scripts") or {}).keys())[:40]
                deps = {}
                deps.update(data.get("dependencies") or {})
                deps.update(data.get("devDependencies") or {})
                entry["dependencies"] = sorted(deps)[:80]
            except json.JSONDecodeError:
                entry["parse_error"] = True
        elif path.name == "pyproject.toml":
            entry["dependency_lines"] = [line.strip() for line in content.splitlines() if re.match(r"^[A-Za-z0-9_.-]+\s*[<>=!~]", line)][:40]
        else:
            entry["bytes"] = len(content.encode("utf-8"))
        found.append(entry)
    return {"files": found, "count": len(found)}


def _git_report(root: Path) -> dict[str, Any]:
    top = _run_git(root, ["rev-parse", "--show-toplevel"])
    if top is None:
        return {"is_repository": False}
    status = _run_git(root, ["status", "--short"])
    return {
        "is_repository": True,
        "top_level": top,
        "branch": _run_git(root, ["branch", "--show-current"]) or "detached-or-unknown",
        "head": _run_git(root, ["rev-parse", "HEAD"]),
        "default_branch_hint": _run_git(root, ["symbolic-ref", "refs/remotes/origin/HEAD"]),
        "remotes": _run_git(root, ["remote", "-v"]) or "",
        "dirty": bool(status),
        "dirty_paths": [line[3:] for line in (status or "").splitlines() if len(line) > 3][:100],
    }


def inventory(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    files = _walk_files(root)
    extension_counts = Counter(path.suffix.lower() for path in files if path.suffix)
    languages = Counter(EXTENSIONS[extension] for extension in extension_counts if extension in EXTENSIONS)
    source_files = []
    test_files = []
    for path in files:
        relative = path.relative_to(root).as_posix()
        lower_parts = {part.lower() for part in path.relative_to(root).parts}
        if path.suffix.lower() in EXTENSIONS and not any(token in lower_parts or token in path.stem.lower() for token in TEST_TOKENS):
            source_files.append(relative)
        if any(token in lower_parts or token in path.stem.lower() for token in TEST_TOKENS):
            test_files.append(relative)
    top_level_dirs = sorted({path.relative_to(root).parts[0] for path in files if len(path.relative_to(root).parts) > 1})
    source_roots = [name for name in top_level_dirs if name.lower() in SOURCE_ROOT_NAMES]
    signals = {
        "has_source": bool(source_files),
        "has_tests": bool(test_files),
        "has_readme": any(path.name in README_NAMES for path in files),
        "has_ci": any(".github/workflows" in path.relative_to(root).as_posix() for path in files),
        "has_container": any(path.name in {"Dockerfile", "docker-compose.yml", "docker-compose.yaml"} for path in files),
        "has_environment_example": any(path.name in {".env.example", ".env.sample", "env.example"} for path in files),
    }
    return {
        "version": 1,
        "root": str(root),
        "repository": {
            "name": root.name,
            "top_level_directories": top_level_dirs[:80],
            "source_roots": source_roots,
            "file_count": len(files),
            "source_file_count": len(source_files),
            "test_file_count": len(test_files),
        },
        "languages": [{"name": name, "files": count} for name, count in languages.most_common()],
        "extensions": [{"extension": extension or "[no extension]", "files": count} for extension, count in extension_counts.most_common(40)],
        "manifests": _manifest_report(root, files),
        "readme": _readme_report(root, files),
        "signals": signals,
        "source_files": source_files[:200],
        "test_files": test_files[:200],
        "git": _git_report(root),
        "provenance": "observed filesystem and read-only Git metadata; no project code executed",
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [f"# Project Inventory: {report['repository']['name']}", "", "> Generated by Upstack from observed repository files and read-only Git metadata. Project code was not executed.", "", "## Stack signals", ""]
    languages = report["languages"] or [{"name": "Unknown", "files": 0}]
    lines.append("| Language or file family | Files |")
    lines.append("| --- | ---: |")
    lines.extend(f"| {row['name']} | {row['files']} |" for row in languages)
    lines.extend(["", "## Repository shape", "", f"- Files indexed: **{report['repository']['file_count']}**", f"- Source-like files: **{report['repository']['source_file_count']}**", f"- Test-like files: **{report['repository']['test_file_count']}**", f"- Source roots: {', '.join(report['repository']['source_roots']) or 'not detected'}", ""])
    lines.extend(["## Manifests and configuration", "", "| Path | Kind | Details |", "| --- | --- | --- |"])
    for item in report["manifests"]["files"]:
        details = item.get("name") or ", ".join(item.get("scripts", [])[:8]) or "observed"
        lines.append(f"| `{item['path']}` | {item['kind']} | {details} |")
    if not report["manifests"]["files"]:
        lines.append("| — | No recognized root manifest | Unknown |")
    lines.extend(["", "## README signals", ""])
    readme = report["readme"]
    if readme["present"]:
        lines.append(f"README: `{readme['files'][0]}` ({readme['characters']} characters; {readme['urls']} URLs).")
        lines.append("")
        lines.append("| Signal | Observed |")
        lines.append("| --- | --- |")
        lines.extend(f"| {key} | {'yes' if value else 'no'} |" for key, value in readme["signals"].items())
        lines.extend(["", "Headings:", ""])
        lines.extend(f"- {heading}" for heading in readme["headings"][:20])
    else:
        lines.append("No README was detected in the indexed files.")
    lines.extend(["", "## Git context", "", f"- Repository: {'yes' if report['git']['is_repository'] else 'no'}"])
    if report["git"]["is_repository"]:
        lines.extend([f"- Branch: `{report['git']['branch']}`", f"- Dirty: {'yes' if report['git']['dirty'] else 'no'}"])
    lines.extend(["", "## Next analysis", "", "Use this inventory to choose a focus, build a concept map, and create a learner-calibrated blueprint. Treat unstated architecture, runtime behavior, and difficulty as unknown until verified from source, tests, or bounded execution.", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--output", type=Path, help="write Markdown inventory to this path")
    args = parser.parse_args()
    report = inventory(args.root)
    if args.output:
        args.output.write_text(_markdown(report), encoding="utf-8")
    if args.json or not args.output:
        print(json.dumps(report, indent=2))
    else:
        print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
