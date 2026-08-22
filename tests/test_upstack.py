from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / "scripts" / "inventory_repo.py").exists():
    ROOT = Path("/home/ubuntu/skills/upstack")
INVENTORY = ROOT / "scripts" / "inventory_repo.py"
DISCOVERY = ROOT / "scripts" / "discover_github.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UpstackTests(unittest.TestCase):
    def test_inventory_reports_languages_manifests_readme_and_skips_generated_dirs(self):
        module = load_module("upstack_inventory", INVENTORY)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Demo\n\n## Install\n\n## Tests\n", encoding="utf-8")
            (root / "package.json").write_text(json.dumps({"name": "demo", "scripts": {"test": "vitest"}, "dependencies": {"react": "latest"}}), encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "main.tsx").write_text("export const App = () => null;\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "main.test.ts").write_text("test('works', () => {});\n", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "ignored.js").write_text("ignored", encoding="utf-8")
            report = module.inventory(root)
            self.assertEqual(report["manifests"]["files"][0]["path"], "package.json")
            self.assertEqual(report["languages"][0]["name"], "TypeScript/TSX")
            self.assertTrue(report["readme"]["present"])
            self.assertTrue(report["signals"]["has_tests"])
            self.assertNotIn("node_modules/ignored.js", report["source_files"])

    def test_discovery_enriches_metadata_with_readme_and_targeted_root_files(self):
        module = load_module("upstack_discovery", DISCOVERY)
        metadata = [{
            "fullName": "owner/demo",
            "description": "A TypeScript React API project",
            "language": "TypeScript",
            "license": {"spdx_id": "MIT"},
            "stargazersCount": 1200,
            "forksCount": 140,
            "pushedAt": "2026-08-01T00:00:00Z",
            "updatedAt": "2026-08-02T00:00:00Z",
            "url": "https://github.com/owner/demo",
            "defaultBranch": "main",
            "isArchived": False,
            "isFork": False,
            "size": 1200,
            "openIssuesCount": 2,
            "topics": ["react", "typescript"],
        }]
        root_files = [
            {"name": "package.json", "path": "package.json", "type": "file", "size": 200},
            {"name": "tests", "path": "tests", "type": "dir", "size": 0},
            {"name": "README.md", "path": "README.md", "type": "file", "size": 800},
        ]
        readme = "# Demo\n\n## Installation\n## Architecture\n## Testing\n## Usage\n"

        def fake_run(command, timeout=20):
            if command[:3] == ["gh", "search", "repos"]:
                return 0, json.dumps(metadata), ""
            if command[:3] == ["gh", "repo", "read-file"]:
                path = command[3]
                if path == "README.md":
                    return 0, json.dumps({"content": readme, "encoding": "utf-8", "size": len(readme), "gitSHA": "abc"}), ""
                return 0, json.dumps({"content": json.dumps({"scripts": {"test": "vitest"}}), "encoding": "utf-8", "size": 50}), ""
            if command[:3] == ["gh", "repo", "read-dir"]:
                return 0, json.dumps(root_files), ""
            raise AssertionError(f"unexpected command: {command}")

        def fake_api(endpoint, headers=None):
            if endpoint == "repos/owner/demo":
                return {"license": {"spdx_id": "MIT"}, "topics": ["react", "typescript"], "default_branch": "main"}, None
            if endpoint == "repos/owner/demo/languages":
                return {"TypeScript": 1000, "JavaScript": 200}, None
            if endpoint == "repos/owner/demo/topics":
                return {"names": ["react", "typescript"]}, None
            raise AssertionError(f"unexpected API endpoint: {endpoint}")

        with patch.object(module, "_gh_available", return_value=True), patch.object(module, "_run", side_effect=fake_run), patch.object(module, "_gh_api_json", side_effect=fake_api):
            report = module.discover("typescript react", count=3, backend="auto")
        self.assertEqual(report["backend"], "gh")
        self.assertEqual(len(report["candidates"]), 1)
        candidate = report["candidates"][0]
        self.assertEqual(candidate["metadata"]["fullName"], "owner/demo")
        self.assertTrue(candidate["readme"]["signals"]["architecture"])
        self.assertIn("package.json", candidate["targeted_files"])
        self.assertGreater(candidate["score"]["overall"], 0)
        self.assertEqual(report["side_effects"], [])

    def test_discovery_never_calls_fork_clone_or_install(self):
        module = load_module("upstack_discovery_side_effects", DISCOVERY)
        commands = []
        metadata = [{"fullName": "owner/demo", "description": "demo", "language": "Python", "license": None, "stargazersCount": 0, "forksCount": 0, "pushedAt": None, "updatedAt": None, "url": "https://github.com/owner/demo", "defaultBranch": "main", "isArchived": False, "isFork": False, "size": 1, "openIssuesCount": 0}]

        def fake_run(command, timeout=20):
            commands.append(command)
            if command[:3] == ["gh", "search", "repos"]:
                return 0, json.dumps(metadata), ""
            if command[:3] == ["gh", "repo", "read-file"]:
                return 0, json.dumps({"content": "# Demo", "encoding": "utf-8"}), ""
            if command[:3] == ["gh", "repo", "read-dir"]:
                return 0, "[]", ""
            return 1, "", "unexpected"

        with patch.object(module, "_gh_available", return_value=True), patch.object(module, "_run", side_effect=fake_run), patch.object(module, "_gh_api_json", return_value=({}, None)):
            module.discover("python", count=1, backend="gh")
        subcommands = [command[1:3] for command in commands if len(command) >= 3]
        self.assertNotIn(["repo", "fork"], subcommands)
        self.assertNotIn(["repo", "clone"], subcommands)
        self.assertFalse(any("install" in command for command in commands))


if __name__ == "__main__":
    unittest.main()


class CapabilityTests(unittest.TestCase):
    def test_capability_checker_reports_cli_without_exposing_token(self):
        module = load_module("upstack_capabilities", ROOT / "scripts" / "check_capabilities.py")
        with patch.object(module.shutil, "which", side_effect=lambda name: "/usr/bin/" + name if name in {"git", "gh", "curl"} else None), patch.object(module, "run", side_effect=[(0, "gh version 2.95.0\n", ""), (0, "  ✓ Logged in to github.com account learner\n", "token: secret-value\n")]):
            report = module.capability_report()
        self.assertTrue(report["github_cli"]["available"])
        self.assertTrue(report["github_cli"]["authenticated"])
        self.assertEqual(report["github_cli"]["account"], "learner")
        self.assertNotIn("secret-value", json.dumps(report))
