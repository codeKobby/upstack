from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / "scripts" / "inventory_repo.py").exists():
    ROOT = Path("/home/ubuntu/skills/upstack")
INVENTORY = ROOT / "scripts" / "inventory_repo.py"
DISCOVERY = ROOT / "scripts" / "discover_github.py"
DISCOVERY_INTERACTION = ROOT / "scripts" / "discovery_interaction.py"


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

    def test_discovery_interaction_separates_actions_from_candidate_selection(self):
        module = load_module("upstack_discovery_interaction", DISCOVERY_INTERACTION)
        report = {
            "candidates": [
                {"metadata": {"fullName": "owner/first", "description": "First project"}, "score": {"overall": 90}},
                {"metadata": {"fullName": "owner/second", "description": "Second project"}, "score": {"overall": 80}},
            ]
        }
        action_question = module.next_question(report)
        self.assertEqual(action_question["id"], "discovery_action")
        self.assertEqual([option["value"] for option in action_question["options"]], ["choose_candidate", "broaden_search", "finish"])
        self.assertEqual(module.resolve_answer(action_question, "2")["value"], "broaden_search")
        self.assertNotIn("owner/second", json.dumps(action_question))

        candidate_question = module.next_question(report, "choose_candidate")
        self.assertEqual(candidate_question["id"], "candidate_selection")
        self.assertEqual([option["value"] for option in candidate_question["options"]], ["candidate:owner/first", "candidate:owner/second"])
        self.assertEqual(module.resolve_answer(candidate_question, "2")["value"], "candidate:owner/second")
        with self.assertRaises(ValueError):
            module.resolve_answer(action_question, "candidate:owner/second")

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


class OnboardingTests(unittest.TestCase):
    def test_home_directory_is_not_treated_as_a_project(self):
        module = load_module("upstack_onboarding", ROOT / "scripts" / "onboarding.py")
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            project = home / "sample-app"
            project.mkdir()
            (project / "package.json").write_text("{}", encoding="utf-8")
            with patch.object(module.Path, "home", return_value=home):
                report = module.context(home)
            self.assertTrue(report["is_home"])
            self.assertFalse(report["is_project_context"])
            self.assertEqual(report["local_candidates"][0]["name"], "sample-app")
            first = module.next_question(report, {})
            self.assertEqual(first["id"], "goal")
            self.assertEqual(first["text"], "What would you like to accomplish first?")
            self.assertIn("Prepare for a technical interview", [item["label"] for item in first["options"]])
            self.assertIn("Learn how an existing project works", [item["label"] for item in first["options"]])

    def test_first_turn_defers_workspace_inspection(self):
        module = load_module("upstack_onboarding_deferred", ROOT / "scripts" / "onboarding.py")
        output = io.StringIO()
        with patch.object(module, "context", side_effect=AssertionError("context must be deferred")), patch.object(sys, "argv", ["onboarding.py", "/home/ubuntu"]), redirect_stdout(output):
            module.main()
        payload = json.loads(output.getvalue())
        self.assertTrue(payload["context"]["inspection_deferred"])
        self.assertEqual(payload["next_question"]["id"], "goal")

    def test_intent_is_asked_before_source_selection(self):
        module = load_module("upstack_onboarding_intent_first", ROOT / "scripts" / "onboarding.py")
        first = module.next_question(None, {})
        self.assertEqual(first["id"], "goal")
        self.assertEqual(first["text"], "What would you like to accomplish first?")
        self.assertEqual(module.next_question(None, {"goal": "rebuild"})["id"], "outcome_detail")
        self.assertEqual(module.next_question(None, {"goal": "interview"})["id"], "outcome_detail")

    def test_question_sequence_adapts_to_discovery_answers(self):
        module = load_module("upstack_onboarding_sequence", ROOT / "scripts" / "onboarding.py")
        report = module.context(Path.cwd())
        answers = {"goal": "rebuild"}
        self.assertEqual(module.next_question(report, answers)["id"], "outcome_detail")
        answers["outcome_detail"] = "existing"
        self.assertEqual(module.next_question(report, answers)["id"], "source")
        answers["source"] = "discover"
        self.assertEqual(module.next_question(report, answers)["id"], "source_detail")
        answers["source_detail"] = "frontend"
        self.assertEqual(module.next_question(report, answers)["id"], "focus")
        answers["focus"] = "frontend"
        self.assertEqual(module.next_question(report, answers)["id"], "time_budget")
        answers["time_budget"] = "1-2h"
        self.assertEqual(module.next_question(report, answers)["id"], "skill_profile")
        answers["skill_profile"] = "guided"
        self.assertEqual(module.next_question(report, answers)["id"], "mode")
        answers["mode"] = "coach"
        self.assertIsNone(module.next_question(report, answers))

    def test_known_project_skips_project_selection_question(self):
        module = load_module("upstack_onboarding_known", ROOT / "scripts" / "onboarding.py")
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            report = module.context(project)
            first = module.next_question(report, {})
            self.assertEqual(first["id"], "goal")
            self.assertEqual(first["text"], "What would you like to accomplish first?")
