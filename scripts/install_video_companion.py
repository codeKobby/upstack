#!/usr/bin/env python3
"""Plan and, only with explicit confirmation, install the Upstack VS Code companion."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

EXTENSION_ID = "codeKobby.upstack-video-companion"
DEFAULT_MARKETPLACE_ID = EXTENSION_ID
SUPPORTED_HOSTS = {"vscode", "vscode-insiders", "visual-studio-code", "code", "code-insiders"}


def _host_candidates(host: str) -> list[str]:
    normalized = (host or "").strip().lower()
    if normalized in {"vscode-insiders", "code-insiders"}:
        return ["code-insiders"]
    return ["code"]


def detect_host(explicit_host: str | None = None) -> dict[str, Any]:
    host = (explicit_host or os.environ.get("UPSTACK_HOST") or os.environ.get("CODING_AGENT") or "").strip().lower()
    vscode_signals = any(os.environ.get(name) for name in ("VSCODE_PID", "VSCODE_IPC_HOOK_CLI", "TERM_PROGRAM"))
    if host in SUPPORTED_HOSTS:
        host_id = "vscode-insiders" if host in {"vscode-insiders", "code"} and "insider" in host else "vscode"
        if host == "vscode-insiders":
            host_id = "vscode-insiders"
        return {"host": host_id, "detected": True, "signal": "explicit" if explicit_host or os.environ.get("UPSTACK_HOST") or os.environ.get("CODING_AGENT") else "environment", "cli": first_available_cli(host_id)}
    if vscode_signals:
        term = os.environ.get("TERM_PROGRAM", "").lower()
        host_id = "vscode-insiders" if "insider" in term else "vscode"
        return {"host": host_id, "detected": True, "signal": "vscode-environment", "cli": first_available_cli(host_id)}
    return {"host": host or "unknown", "detected": False, "signal": "none", "cli": None}


def first_available_cli(host: str) -> str | None:
    names = ["code-insiders", "code"] if host == "vscode-insiders" else ["code", "code-insiders"]
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def list_installed(cli: str | None) -> tuple[list[str], str | None]:
    if not cli:
        return [], "cli_unavailable"
    try:
        result = subprocess.run([cli, "--list-extensions"], capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], type(exc).__name__
    if result.returncode != 0:
        return [], f"cli_exit_{result.returncode}"
    return [line.strip() for line in result.stdout.splitlines() if line.strip()], None


def is_installed(extensions: list[str], extension_id: str = EXTENSION_ID) -> bool:
    target = extension_id.casefold()
    return any(value.casefold() == target for value in extensions)


def choose_source(vsix: str | None, marketplace_id: str, marketplace_available: bool) -> dict[str, Any]:
    if vsix:
        path = Path(vsix).expanduser().resolve()
        return {"kind": "vsix", "value": str(path), "exists": path.is_file(), "command_value": str(path)}
    if marketplace_available:
        return {"kind": "marketplace", "value": marketplace_id, "exists": None, "command_value": marketplace_id}
    return {"kind": "unavailable", "value": marketplace_id, "exists": False, "command_value": ""}


def build_plan(host: str | None = None, vsix: str | None = None, marketplace_id: str = DEFAULT_MARKETPLACE_ID, marketplace_available: bool = False) -> dict[str, Any]:
    detected = detect_host(host)
    source = choose_source(vsix, marketplace_id, marketplace_available)
    extensions, list_error = list_installed(detected.get("cli"))
    installed = is_installed(extensions, marketplace_id) if not list_error else False
    if not detected["detected"]:
        status = "unsupported_host"
        reason = "No VS Code host signal was found; keep using the portable video map."
    elif not detected.get("cli"):
        status = "cli_unavailable"
        reason = "VS Code is indicated, but its command-line launcher is unavailable. Install through the editor UI or provide a VSIX path."
    elif installed:
        status = "installed"
        reason = "The companion is already installed for this VS Code CLI."
    elif source["kind"] == "vsix" and not source["exists"]:
        status = "vsix_missing"
        reason = "The supplied VSIX path does not exist; do not attempt installation."
    elif source["kind"] == "unavailable":
        status = "marketplace_unavailable"
        reason = "The companion is not installed and is not yet available from the Marketplace. Provide a local VSIX path or continue with the portable video map."
    else:
        status = "ready_for_confirmation"
        reason = "The companion is not installed. Ask the learner for explicit confirmation before running the installation command."
    command = [detected["cli"], "--install-extension", source["command_value"]] if detected.get("cli") and status == "ready_for_confirmation" else []
    return {
        "extension_id": marketplace_id,
        "host": detected,
        "source": source,
        "installed": installed,
        "status": status,
        "reason": reason,
        "command": command,
        "requires_confirmation": status == "ready_for_confirmation",
        "portable_fallback": ".upstack/sources/video-map.md and .upstack/sources/video-map.json",
    }


def install(plan: dict[str, Any], confirmed: bool) -> dict[str, Any]:
    if plan["status"] != "ready_for_confirmation":
        return {**plan, "install_attempted": False, "install_result": "not_ready"}
    if not confirmed:
        return {**plan, "install_attempted": False, "install_result": "confirmation_required"}
    try:
        result = subprocess.run(plan["command"], capture_output=True, text=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {**plan, "install_attempted": True, "install_result": "error", "error": type(exc).__name__}
    return {
        **plan,
        "install_attempted": True,
        "install_result": "installed" if result.returncode == 0 else "failed",
        "exit_code": result.returncode,
        "stdout": result.stdout[-2000:],
        "stderr": result.stderr[-2000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan or explicitly install the optional Upstack Video Companion for VS Code")
    parser.add_argument("--host", help="host identifier; use vscode or vscode-insiders when known")
    parser.add_argument("--vsix", help="local VSIX path; otherwise use the Marketplace extension identifier")
    parser.add_argument("--marketplace-id", default=DEFAULT_MARKETPLACE_ID)
    parser.add_argument("--marketplace-available", action="store_true", help="use the Marketplace source only after publication has been verified")
    parser.add_argument("--confirm", action="store_true", help="explicitly authorize the local VS Code installation")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = install(build_plan(args.host, args.vsix, args.marketplace_id, args.marketplace_available), args.confirm)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["reason"])
        if result["command"]:
            print("Planned command: " + " ".join(result["command"]))
        if result.get("install_result"):
            print("Install result: " + result["install_result"])
    return 0 if result.get("install_result") not in {"failed", "error"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
