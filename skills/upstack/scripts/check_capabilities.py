#!/usr/bin/env python3
"""Report optional local capabilities for Upstack without exposing secrets."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from typing import Any


def run(command: list[str], timeout: int = 8) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, "", str(exc)
    return completed.returncode, completed.stdout, completed.stderr


def capability_report() -> dict[str, Any]:
    git = shutil.which("git")
    gh = shutil.which("gh")
    curl = shutil.which("curl")
    report: dict[str, Any] = {
        "version": 1,
        "git": {"available": bool(git), "path": git},
        "github_cli": {"available": bool(gh), "path": gh, "authenticated": False, "account": None, "version": None},
        "public_api_fallback": {"available": bool(curl), "path": curl},
        "environment_hints": {
            "github_token_present": bool(os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")),
            "mcp_not_assumed": True,
        },
        "recommendation": "local inventory only",
    }
    if gh:
        version_code, version_out, _ = run(["gh", "--version"])
        if version_code == 0:
            report["github_cli"]["version"] = version_out.splitlines()[0] if version_out else None
        auth_code, auth_out, auth_err = run(["gh", "auth", "status"])
        report["github_cli"]["authenticated"] = auth_code == 0
        combined = (auth_out + "\n" + auth_err).splitlines()
        for line in combined:
            if "Logged in to github.com account " in line:
                account = line.split("Logged in to github.com account ", 1)[1].split(" ", 1)[0]
                report["github_cli"]["account"] = account.strip("'\"")
                break
    if report["github_cli"]["authenticated"]:
        report["recommendation"] = "use GitHub CLI for metadata, README/root reads, and confirmed authenticated actions"
    elif report["github_cli"]["available"] and report["public_api_fallback"]["available"]:
        report["recommendation"] = "use public API for read-only discovery; prompt for gh auth only for fork/private actions"
    elif report["public_api_fallback"]["available"]:
        report["recommendation"] = "use public API/web discovery; GitHub CLI is optional"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()
    report = capability_report()
    print(json.dumps(report, indent=2) if args.json else report["recommendation"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
