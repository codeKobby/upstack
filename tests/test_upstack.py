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
DISCOVERY_PROJECTS = ROOT / "scripts" / "discover_projects.py"
HOST_MATRIX = ROOT / "compatibility" / "hosts.json"
VIDEO_EVIDENCE = ROOT / "scripts" / "video_evidence.py"
INSTALL_COMPANION = ROOT / "scripts" / "install_video_companion.py"
VSCODE_EXTENSION = ROOT / "vscode-extension"


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

    def test_cross_source_query_lanes_are_diverse_and_qualified(self):
        module = load_module("upstack_discover_projects_lanes", DISCOVERY_PROJECTS)
        lanes = module.build_query_lanes(
            "build a serious Instagram-style app for interview practice",
            stack=["TypeScript", "Next.js"],
            project_type="web application",
            focus="backend APIs",
            concepts=["authentication", "testing"],
            level="guided",
            signal="backend depth",
        )
        self.assertGreaterEqual(len(lanes), 3)
        self.assertEqual(len(lanes), len(set(lanes)))
        self.assertTrue(any("in:name,description,topics" in lane for lane in lanes))
        self.assertTrue(any("in:readme" in lane for lane in lanes))
        self.assertTrue(any("-tutorial" in lane for lane in lanes))

    def test_cross_source_links_match_verified_github_candidates(self):
        module = load_module("upstack_discover_projects_links", DISCOVERY_PROJECTS)
        candidate = {
            "metadata": {"fullName": "owner/demo", "description": "A serious TypeScript API project", "topics": ["typescript", "api"]},
            "readme": {"headings": ["Architecture", "Testing"]},
            "score": {"overall": 70},
        }
        with tempfile.TemporaryDirectory() as directory:
            external_file = Path(directory) / "external.json"
            external_file.write_text(json.dumps({"results": [
                {"source": "youtube", "url": "https://youtube.com/watch?v=demo", "title": "Build owner/demo", "description": "Walkthrough https://github.com/owner/demo/blob/main/README.md"},
                {"source": "x", "url": "https://x.com/dev/status/1", "text": "Launch thread for https://github.com/owner/demo"},
            ]}), encoding="utf-8")
            with patch.object(module, "github_discover", return_value={"candidates": [candidate], "errors": []}):
                report = module.discover_projects("TypeScript API project", sources=["github"], external_file=external_file, count=3)
        self.assertEqual(len(report["candidates"]), 1)
        matched = report["candidates"][0]
        self.assertEqual(matched["metadata"]["fullName"], "owner/demo")
        self.assertEqual(len(matched["external_evidence"]), 2)
        self.assertGreaterEqual(matched["score"]["cross_source_evidence"], 2)
        self.assertEqual(report["side_effects"], [])
        self.assertEqual(report["unverified_repository_links"], [])

    def test_youtube_and_x_results_normalize_links_and_metadata(self):
        module = load_module("upstack_discover_projects_social", DISCOVERY_PROJECTS)

        def fake_request(url, headers=None):
            if "googleapis.com/youtube" in url:
                return {"items": [{"id": {"videoId": "abc"}, "snippet": {"title": "Build demo", "description": "Code: https://github.com/owner/demo", "publishedAt": "2026-08-20T00:00:00Z", "channelTitle": "Builder"}}]}, None
            if "api.x.com" in url:
                return {"data": [{"id": "123", "text": "Launch https://github.com/owner/demo", "created_at": "2026-08-21T00:00:00Z", "author_id": "7"}], "includes": {"users": [{"id": "7", "username": "builder"}]}}, None
            raise AssertionError(url)

        with patch.object(module, "_request_url", side_effect=fake_request):
            youtube, youtube_status = module.search_youtube("demo", api_key="youtube-secret", limit=1)
            posts, x_status = module.search_x("demo", bearer_token="x-secret", limit=10)
        self.assertEqual(youtube_status["status"], "ok")
        self.assertEqual(x_status["status"], "ok")
        self.assertEqual(youtube[0]["repository_links"], ["https://github.com/owner/demo"])
        self.assertEqual(posts[0]["repository_links"], ["https://github.com/owner/demo"])
        self.assertNotIn("youtube-secret", json.dumps(youtube))
        self.assertNotIn("x-secret", json.dumps(posts))

    def test_optional_sources_report_clear_not_configured_status(self):
        module = load_module("upstack_discover_projects_optional", DISCOVERY_PROJECTS)
        with patch.dict(module.os.environ, {}, clear=True):
            report = module.discover_projects("React project", sources=["youtube", "x"], count=3)
        statuses = {item["source"]: item for item in report["sources"]}
        self.assertEqual(statuses["youtube"]["status"], "not_configured")
        self.assertEqual(statuses["x"]["status"], "not_configured")
        self.assertEqual(report["candidates"], [])
        self.assertEqual(report["side_effects"], [])

    def test_repository_link_extraction_canonicalizes_paths_and_git_suffix(self):
        module = load_module("upstack_discover_projects_extract", DISCOVERY_PROJECTS)
        links = module.extract_repository_links("See https://github.com/owner/demo/blob/main/src/app.tsx and https://gitlab.com/team/tool.git")
        self.assertEqual(links, ["https://github.com/owner/demo", "https://gitlab.com/team/tool"])

    def test_companion_installer_requires_confirmation_and_has_fallback(self):
        module = load_module("upstack_install_video_companion", INSTALL_COMPANION)
        unsupported = module.build_plan(host="unknown-agent")
        self.assertEqual(unsupported["status"], "unsupported_host")
        self.assertFalse(unsupported["requires_confirmation"])
        self.assertIn("video-map.md", unsupported["portable_fallback"])
        with tempfile.NamedTemporaryFile(suffix=".vsix") as handle:
            with patch.object(module.shutil, "which", return_value="/usr/bin/code"):
                plan = module.build_plan(host="vscode", vsix=handle.name)
            self.assertEqual(plan["status"], "ready_for_confirmation")
            self.assertTrue(plan["requires_confirmation"])
            with patch.object(module.shutil, "which", return_value="/usr/bin/code"):
                marketplace_plan = module.build_plan(host="vscode", marketplace_available=False)
            self.assertEqual(marketplace_plan["status"], "marketplace_unavailable")
            self.assertFalse(marketplace_plan["requires_confirmation"])
            declined = module.install(plan, confirmed=False)
            self.assertEqual(declined["install_result"], "confirmation_required")
            self.assertFalse(declined["install_attempted"])

    def test_vscode_companion_manifest_and_security_contract(self):
        manifest = json.loads((VSCODE_EXTENSION / "package.json").read_text(encoding="utf-8"))
        extension = (VSCODE_EXTENSION / "src" / "extension.ts").read_text(encoding="utf-8")
        self.assertEqual(manifest["name"], "upstack-video-companion")
        commands = {item["command"] for item in manifest["contributes"]["commands"]}
        self.assertEqual(commands, {"upstackVideo.open", "upstackVideo.generateMap"})
        self.assertIn("upstackVideo.videoMap", manifest["contributes"]["configuration"]["properties"])
        self.assertIn("youtube-nocookie.com", extension)
        self.assertIn("Content-Security-Policy", extension)
        self.assertIn("isInsideWorkspace", extension)
        self.assertIn("video-progress.json", extension)
        self.assertNotIn("workspace.fs.writeFile", extension)
        self.assertNotIn("executeCommand", extension)

    def test_video_evidence_builds_timestamped_repository_map(self):
        module = load_module("upstack_video_evidence", VIDEO_EVIDENCE)
        evidence = module.build_evidence(
            {"url": "https://youtu.be/demo123", "title": "Build the API", "channel": "Builder"},
            segments=[
                {"start": "1:02", "title": "Authentication", "summary": "Wire the auth flow", "repository_paths": ["src/auth.ts"], "lesson_path": ".upstack/lessons/auth.md", "concepts": ["tokens"]},
                {"start": 0, "title": "Setup", "summary": "Create the app"},
            ],
            repository={"full_name": "owner/demo", "url": "https://github.com/owner/demo", "paths": ["src/auth.ts", "src/app.ts"]},
            focus=["authentication"],
            concepts=["tokens"],
            query="build a TypeScript API",
        )
        self.assertEqual(evidence["status"], "timestamped")
        self.assertEqual([item["timestamp"] for item in evidence["segments"]], ["00:00", "01:02"])
        self.assertEqual(evidence["segments"][1]["timestamp_url"], "https://www.youtube.com/watch?v=demo123&t=62s")
        self.assertEqual(evidence["segments"][1]["repository_paths"], ["src/auth.ts"])
        markdown = module.render_markdown(evidence)
        self.assertIn("[01:02](https://www.youtube.com/watch?v=demo123&t=62s)", markdown)
        self.assertIn("[`src/auth.ts`](../../src/auth.ts)", markdown)
        self.assertIn("[`.upstack/lessons/auth.md`](../../.upstack/lessons/auth.md)", markdown)
        self.assertIn("https://github.com/owner/demo", markdown)
        self.assertEqual(evidence["side_effects"], [])

    def test_video_evidence_keeps_metadata_only_when_timestamps_are_missing(self):
        module = load_module("upstack_video_metadata_only", VIDEO_EVIDENCE)
        evidence = module.build_evidence({"url": "https://www.youtube.com/watch?v=demo123", "title": "Demo"})
        self.assertEqual(evidence["status"], "metadata_only")
        self.assertEqual(evidence["segments"], [])
        markdown = module.render_markdown(evidence)
        self.assertIn("No verified chapter or transcript timestamps were supplied", markdown)
        self.assertIn("https://www.youtube.com/watch?v=demo123", markdown)

    def test_video_timestamp_parsing_accepts_clock_and_unit_forms(self):
        module = load_module("upstack_video_timestamp_parsing", VIDEO_EVIDENCE)
        self.assertEqual(module.parse_seconds("01:02"), 62)
        self.assertEqual(module.parse_seconds("1h 2m 3s"), 3723)
        self.assertEqual(module.parse_seconds(45), 45)
        self.assertEqual(module.format_seconds(3723), "01:02:03")

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
        self.assertEqual([item["id"] for item in payload["question_plan"]["questions"]], ["goal"])
        self.assertEqual(payload["question_plan"]["delivery"]["required_action"], "invoke_native_question_tool_if_callable")
        self.assertEqual(payload["question_plan"]["delivery"]["send_only"], "questions")

    def test_intent_is_asked_before_source_selection(self):
        module = load_module("upstack_onboarding_intent_first", ROOT / "scripts" / "onboarding.py")
        first = module.next_question(None, {})
        self.assertEqual(first["id"], "goal")
        self.assertEqual(first["text"], "What would you like to accomplish first?")
        self.assertEqual(module.next_question(None, {"goal": "rebuild"})["id"], "outcome_detail")
        self.assertEqual(module.next_question(None, {"goal": "interview"})["id"], "outcome_detail")

    def test_opencode_chains_only_answer_independent_questions(self):
        module = load_module("upstack_onboarding_chain", ROOT / "scripts" / "onboarding.py")
        answers = {
            "goal": "rebuild",
            "outcome_detail": "existing",
            "source": "discover",
            "source_detail": "frontend",
        }
        plan = module.question_plan(None, answers, host="opencode")
        self.assertEqual(plan["mode"], "native-multi-question-when-safe")
        self.assertEqual([item["id"] for item in plan["questions"]], ["focus", "time_budget"])
        self.assertNotIn("skill_profile", [item["id"] for item in plan["questions"]])
        self.assertNotIn("source", [item["id"] for item in plan["questions"]])

    def test_host_matrix_declares_capability_neutral_question_policy(self):
        matrix = json.loads(HOST_MATRIX.read_text(encoding="utf-8"))
        self.assertEqual(matrix["question_policy"]["default"], "single-question")
        self.assertIn("native-host-capability-is-verified", matrix["question_policy"]["multi_question"])
        self.assertIn("HOST_ID", matrix["question_policy"]["planner"])
        self.assertEqual(matrix["hosts"][0]["id"], "claude-code")

    def test_verified_native_multi_capability_is_host_neutral(self):
        module = load_module("upstack_onboarding_host_neutral", ROOT / "scripts" / "onboarding.py")
        answers = {"goal": "rebuild", "outcome_detail": "existing", "source": "discover", "source_detail": "frontend"}
        plan = module.question_plan(None, answers, host="claude-code", question_mode="native-multi")
        self.assertEqual(plan["mode"], "native-multi-question-when-safe")
        self.assertEqual([item["id"] for item in plan["questions"]], ["focus", "time_budget"])

    def test_unknown_host_defaults_to_single_question(self):
        module = load_module("upstack_onboarding_unknown_host", ROOT / "scripts" / "onboarding.py")
        plan = module.question_plan(None, {}, host="some-agent", question_mode="auto")
        self.assertEqual(plan["mode"], "native-single-question-or-text-fallback")
        self.assertEqual([item["id"] for item in plan["questions"]], ["goal"])

    def test_opencode_does_not_chain_intent_or_discovery_source_questions(self):
        module = load_module("upstack_onboarding_chain_boundaries", ROOT / "scripts" / "onboarding.py")
        intent_plan = module.question_plan(None, {}, host="opencode")
        self.assertEqual([item["id"] for item in intent_plan["questions"]], ["goal"])
        source_plan = module.question_plan(None, {"goal": "rebuild", "outcome_detail": "existing"}, host="opencode")
        self.assertEqual([item["id"] for item in source_plan["questions"]], ["source"])

    def test_generic_host_keeps_one_question_fallback(self):
        module = load_module("upstack_onboarding_generic_plan", ROOT / "scripts" / "onboarding.py")
        plan = module.question_plan(None, {}, host="generic")
        self.assertEqual(plan["mode"], "native-single-question-or-text-fallback")
        self.assertEqual([item["id"] for item in plan["questions"]], ["goal"])
        self.assertEqual(plan["delivery"]["native_tool"], "discover_from_current_host_tools")
        self.assertTrue(plan["delivery"]["prose_prompt_allowed"])

    def test_native_host_plan_requires_tool_invocation_without_duplicate_prose(self):
        module = load_module("upstack_onboarding_native_delivery", ROOT / "scripts" / "onboarding.py")
        plan = module.question_plan(None, {}, host="opencode")
        self.assertEqual(plan["delivery"]["native_tool"], "question")
        self.assertFalse(plan["delivery"]["prose_prompt_allowed"])
        self.assertEqual(plan["delivery"]["send_only"], "questions")
        self.assertIn("print-question-specification-as-prompt", plan["delivery"]["must_not"])
        self.assertIn("simulate-native-tool", plan["delivery"]["must_not"])

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
