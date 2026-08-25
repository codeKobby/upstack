#!/usr/bin/env python3
"""Resolve package-manager evidence and safe selection plans for Upstack."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


MANAGERS = ("pnpm", "npm", "bun", "yarn")
LOCKFILES = {
    "pnpm": ("pnpm-lock.yaml",),
    "npm": ("package-lock.json", "npm-shrinkwrap.json"),
    "bun": ("bun.lock", "bun.lockb"),
    "yarn": ("yarn.lock",),
}
COMMANDS = {
    "pnpm": {"install": "pnpm install", "run": "pnpm run <script>", "exec": "pnpm exec <binary>"},
    "npm": {"install": "npm install", "run": "npm run <script>", "exec": "npm exec -- <binary>"},
    "bun": {"install": "bun install", "run": "bun run <script>", "exec": "bunx <binary>"},
    "yarn": {"install": "yarn install", "run": "yarn <script>", "exec": "yarn exec <binary>"},
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _manager_from_declaration(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.match(r"(pnpm|npm|bun|yarn)(?:@|$)", value.strip().lower())
    return match.group(1) if match else None


def _is_js_ts(root: Path, package_json: dict[str, Any], files: list[Path]) -> bool:
    if package_json:
        return True
    return any(path.suffix.lower() in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"} for path in files[:500])


def detect(root: str | Path) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    package_json_path = root / "package.json"
    package_json = _read_json(package_json_path) if package_json_path.is_file() else {}
    lockfiles: dict[str, list[str]] = {}
    for manager, names in LOCKFILES.items():
        found = [name for name in names if (root / name).is_file()]
        if found:
            lockfiles[manager] = found
    declared = _manager_from_declaration(package_json.get("packageManager"))
    if declared is None:
        declared = _manager_from_declaration(package_json.get("engines", {}).get("packageManager")) if isinstance(package_json.get("engines"), dict) else None
    evidence = []
    if declared:
        evidence.append({"manager": declared, "source": "package.json:packageManager"})
    for manager, files in lockfiles.items():
        for name in files:
            evidence.append({"manager": manager, "source": name})
    managers = sorted({item["manager"] for item in evidence}, key=MANAGERS.index)
    files = []
    try:
        files = [path for path in root.iterdir() if path.is_file() and path.name not in {"node_modules"}]
    except OSError:
        pass
    applicable = _is_js_ts(root, package_json, files)
    if len(managers) > 1:
        status = "conflict"
        detected = None
    elif len(managers) == 1:
        status = "detected"
        detected = managers[0]
    else:
        status = "not_detected"
        detected = None
    return {
        "root": str(root),
        "applicable": applicable,
        "status": status,
        "detected": detected,
        "declared": declared,
        "lockfiles": lockfiles,
        "evidence": evidence,
        "managers": managers,
        "recommended_for_new_js_ts": "pnpm",
        "provenance": "observed package.json and root lockfiles; no install or package command executed",
    }


def plan(root: str | Path, *, selected: str | None = None, new_project: bool = False) -> dict[str, Any]:
    report = detect(root)
    selected = selected.lower().strip() if isinstance(selected, str) else None
    if selected not in MANAGERS:
        selected = None
    detected = report["detected"]
    if selected and report["status"] == "conflict":
        status = "migration_confirmation_required"
        reason = f"The project has conflicting package-manager signals ({', '.join(report['managers'])}); selecting {selected} requires an explicit authoritative-manager and lockfile decision."
    elif selected and detected and selected != detected:
        status = "migration_confirmation_required"
        reason = f"The project currently has {detected} evidence; selecting {selected} would change package-manager files and commands."
    elif report["status"] == "conflict" and not selected:
        status = "choice_required"
        reason = "Multiple package-manager signals conflict; the learner must choose which manager is authoritative before dependency work."
    elif selected:
        status = "ready"
        reason = "The learner selected the package manager; preserve other manager files unless migration is separately confirmed." 
    elif detected:
        status = "preserve_detected"
        selected = detected
        reason = f"Preserve the detected {detected} manager for this existing project; do not rewrite its lockfile implicitly."
    elif new_project or report["applicable"]:
        status = "choice_required"
        reason = "No authoritative manager was detected; ask the learner, recommending pnpm for new JavaScript/TypeScript work."
    else:
        status = "not_applicable"
        reason = "No JavaScript/TypeScript package-manager evidence was detected."
    return {
        **report,
        "status": status,
        "selected": selected,
        "recommended": "pnpm" if (new_project or report["applicable"]) else None,
        "reason": reason,
        "commands": COMMANDS.get(selected or "pnpm"),
        "migration": status == "migration_confirmation_required",
        "install_confirmation_required": True if selected else False,
        "must_not": ["delete-lockfile-without-confirmation", "run-package-install-without-confirmation", "silently-migrate-manager", "mix-manager-commands-in-one-stage"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    parser.add_argument("--select", choices=MANAGERS)
    parser.add_argument("--new-project", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = plan(args.root, selected=args.select, new_project=args.new_project)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

