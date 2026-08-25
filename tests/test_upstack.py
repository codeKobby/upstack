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
sys.path.insert(0, str(ROOT / "scripts"))
INVENTORY = ROOT / "scripts" / "inventory_repo.py"
DISCOVERY = ROOT / "scripts" / "discover_github.py"
DISCOVERY_INTERACTION = ROOT / "scripts" / "discovery_interaction.py"
DISCOVERY_PROJECTS = ROOT / "scripts" / "discover_projects.py"
HOST_MATRIX = ROOT / "compatibility" / "hosts.json"
VIDEO_EVIDENCE = ROOT / "scripts" / "video_evidence.py"
INSTALL_COMPANION = ROOT / "scripts" / "install_video_companion.py"
UI_DESIGN = ROOT / "scripts" / "ui_design.py"
INTERVIEW_PREP = ROOT / "scripts" / "interview_prep.py"
LESSON_PLAN = ROOT / "scripts" / "lesson_plan.py"
PROJECT_STATE = ROOT / "scripts" / "project_state.py"
TUTOR = ROOT / "scripts" / "tutor.py"
SESSION_HANDOFF = ROOT / "scripts" / "session_handoff.py"
PACKAGE_MANAGER = ROOT / "scripts" / "package_manager.py"
COMMAND_ROUTER = ROOT / "scripts" / "command_router.py"
VSCODE_EXTENSION = ROOT / "vscode-extension"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UpstackTests(unittest.TestCase):
    def test_project_state_help_is_context_independent(self):
        module = load_module("upstack_project_state_help", PROJECT_STATE)
        with tempfile.TemporaryDirectory() as directory:
            skill_path = Path(directory) / ".agents" / "skills" / "upstack"
            skill_path.mkdir(parents=True)
            (skill_path / "SKILL.md").write_text("---\nname: upstack\n---\n", encoding="utf-8")
            result = module.command_gate(skill_path, "help")
            self.assertEqual(result["status"], "help_available")
            self.assertEqual(result["detection"], "not_applicable")
            self.assertIsNone(result["project_root"])
            self.assertEqual(result["next_action"], "show_upstack_help")

    def test_command_router_namespaces_help_and_bypasses_project_resolution(self):
        module = load_module("upstack_command_router_help", COMMAND_ROUTER)
        with tempfile.TemporaryDirectory() as directory:
            result = module.route(Path(directory), "help")
            self.assertEqual(result["status"], "help_available")
            self.assertEqual(result["action"], "show_help")
            self.assertIsNone(result["dispatch"])
            self.assertIn("use-generic-/help", result["must_not"])
            alias = module.route(Path(directory), "upstack-help")
            self.assertEqual(alias["normalized_command"], "help")
            self.assertEqual(alias["action"], "show_help")

    def test_command_router_automatically_dispatches_known_project_next_action(self):
        module = load_module("upstack_command_router_known", COMMAND_ROUTER)
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "ai-workflow"
            state_dir = project / ".upstack"
            (state_dir / "lessons").mkdir(parents=True)
            (project / "package.json").write_text("{}", encoding="utf-8")
            (state_dir / "PROJECT.json").write_text(json.dumps({"project_id": "router-id", "root": str(project), "name": "ai-workflow"}), encoding="utf-8")
            (state_dir / "STATE.json").write_text(json.dumps({"project_id": "router-id", "mode": "guided-lesson", "current_stage": 2, "completed_stages": [1], "next_action": "resume_current_lesson", "current_lesson": {"id": "stage-02-foundation", "status": "active", "path": str(state_dir / "lessons" / "CURRENT_LESSON.md")}, "pointers": {"project_root": str(project)}}), encoding="utf-8")
            (state_dir / "lessons" / "CURRENT_LESSON.md").write_text("# Foundation", encoding="utf-8")
            result = module.route(project, "upstack")
            self.assertEqual(result["status"], "known_project")
            self.assertFalse(result["onboarding"])
            self.assertEqual(result["action"], "resume_current_lesson")
            self.assertEqual(result["lesson_identifier"], "stage-02-foundation")
            self.assertEqual(result["dispatch"]["helper"], "scripts/tutor.py")

    def test_command_router_preserves_unknown_request_for_onboarding(self):
        module = load_module("upstack_command_router_unknown", COMMAND_ROUTER)
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "package.json").write_text("{}", encoding="utf-8")
            result = module.route(project, "lesson", ["day-one"])
            self.assertEqual(result["status"], "onboarding_required")
            self.assertTrue(result["onboarding"])
            self.assertEqual(result["requested_command"], "lesson")
            self.assertEqual(result["arguments"], ["day-one"])

    def test_inventory_reports_languages_manifests_readme_and_skips_generated_dirs(self):
        module = load_module("upstack_inventory", INVENTORY)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("# Demo\n\n## Install\n\n## Tests\n", encoding="utf-8")
            (root / "package.json").write_text(json.dumps({"name": "demo", "packageManager": "pnpm@10.0.0", "scripts": {"test": "vitest"}, "dependencies": {"react": "latest"}}), encoding="utf-8")
            (root / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
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
            self.assertEqual(report["package_manager"]["detected"], "pnpm")
            self.assertEqual(report["package_manager"]["status"], "detected")
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
            "project_mode": "clone",
            "destination": "clone-local",
            "destination_path": "/tmp/upstack-chain-clone",
            "destination_confirmed": "confirmed",
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
        self.assertEqual(matrix["version"], "1.12.0")
        self.assertIn("project_root", matrix["project_tracking"]["state_pointers"])

        self.assertIn("current_lesson", matrix["project_tracking"]["state_pointers"])
        self.assertEqual(matrix["project_tracking"]["history"], ".upstack/HISTORY.jsonl")
        self.assertIn("continue", matrix["project_tracking"]["commands"])
        self.assertIn("resume", matrix["project_tracking"]["commands"])
        self.assertIn("help", matrix["project_tracking"]["commands"])
        self.assertIn("upstack-help", matrix["project_tracking"]["commands"])
        self.assertEqual(matrix["project_tracking"]["help_aliases"], ["/upstack help", "upstack-help"])
        self.assertEqual(matrix["project_tracking"]["automatic_dispatch"], "route-on-every-invocation-before-workflow")

        self.assertIn(".upstack/design/WIREFRAME.md", matrix["design_policy"]["portable_artifacts"])
        self.assertEqual(matrix["design_policy"]["stitch"], "offer-only-when-verified-callable")
        self.assertEqual(matrix["design_policy"]["remote_writes"], "explicit-confirmation-required")
        self.assertTrue(matrix["interview_policy"]["requirements_first"])
        self.assertIn("self-report-plus-small-diagnostics", matrix["interview_policy"]["skill_profile"])
        self.assertIn("markdown", matrix["interview_policy"]["output_modes"])

    def test_verified_native_multi_capability_is_host_neutral(self):
        module = load_module("upstack_onboarding_host_neutral", ROOT / "scripts" / "onboarding.py")
        answers = {"goal": "rebuild", "outcome_detail": "existing", "project_mode": "clone", "destination": "clone-local", "destination_path": "/tmp/upstack-host-neutral-clone", "destination_confirmed": "confirmed", "source": "discover", "source_detail": "frontend"}
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
        mode_plan = module.question_plan(None, {"goal": "rebuild", "outcome_detail": "existing"}, host="opencode")
        self.assertEqual([item["id"] for item in mode_plan["questions"]], ["project_mode"])
        destination_plan = module.question_plan(None, {"goal": "rebuild", "outcome_detail": "existing", "project_mode": "clone"}, host="opencode")
        self.assertEqual([item["id"] for item in destination_plan["questions"]], ["destination"])

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
        self.assertEqual(module.next_question(report, answers)["id"], "project_mode")
        answers["project_mode"] = "clone"
        self.assertEqual(module.next_question(report, answers)["id"], "destination")
        answers["destination"] = "clone-local"
        self.assertEqual(module.next_question(report, answers)["id"], "destination_path")
        answers["destination_path"] = "/tmp/upstack-sequence-clone"
        self.assertEqual(module.next_question(report, answers)["id"], "destination_confirmation")
        answers["destination_confirmed"] = "confirmed"
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

    def test_scratch_route_requires_destination_brief_and_design_before_focus(self):
        module = load_module("upstack_onboarding_scratch", ROOT / "scripts" / "onboarding.py")
        report = module.intent_context()
        answers = {"goal": "rebuild", "outcome_detail": "new"}
        self.assertEqual(module.next_question(report, answers)["id"], "project_mode")
        answers["project_mode"] = "scratch"
        self.assertEqual(module.next_question(report, answers)["id"], "destination")
        answers["destination"] = "new-local"
        self.assertEqual(module.next_question(report, answers)["id"], "destination_path")
        answers["destination_path"] = "/tmp/upstack-scratch-project"
        answers["destination_confirmed"] = "confirmed"
        self.assertEqual(module.next_question(report, answers)["id"], "project_brief")
        answers["project_brief"] = "custom"
        self.assertEqual(module.next_question(report, answers)["id"], "ui_design")
        answers["ui_design"] = "portable"
        self.assertEqual(module.next_question(report, answers)["id"], "fresh_start_mode")
        answers["fresh_start_mode"] = "guided-lesson"
        self.assertEqual(module.next_question(report, answers)["id"], "package_manager")
        answers["package_manager"] = "pnpm"
        self.assertEqual(module.next_question(report, answers)["id"], "focus")

    def test_fresh_start_lesson_plan_maps_curriculum_and_requires_learner_evidence(self):
        module = load_module("upstack_lesson_plan", LESSON_PLAN)
        plan = module.build_plan({"name": "Focus Board", "problem": "Help learners track one project slice."}, {"level": "working"})
        self.assertEqual(plan["mode"], "guided-lesson")
        self.assertEqual(plan["default_behavior"], "teach_then_learner_attempt_then_verify_then_feedback_then_unlock")
        self.assertEqual(len(plan["stages"]), 6)
        self.assertEqual(plan["stages"][0]["status"], "current")
        self.assertEqual(plan["stages"][1]["status"], "locked")
        self.assertIn("learner attempt", plan["progression_gate"]["required_before_unlock"])
        self.assertIn("generate every lesson at once", plan["agent_boundary"]["must_not_do"])
        self.assertEqual(module.resolve_lesson(plan, "upstack-fresh-start-core")["status"], "curriculum")
        self.assertEqual(module.resolve_lesson(plan, "stage-03-vertical-slice")["stage"], 3)
        self.assertEqual(module.resolve_lesson(plan, "day 2")["stage"], 2)
        self.assertEqual(module.resolve_lesson(plan, "day two")["stage"], 2)
        self.assertEqual(module.resolve_lesson(plan, "day-two")["stage"], 2)
        self.assertEqual(module.resolve_lesson(plan, "vertical slice")["stage"], 3)
        self.assertEqual(module.resolve_lesson(plan, "not-a-lesson")["status"], "not_found")
        lesson = module.current_lesson(plan, 1)
        self.assertEqual(lesson["status"], "current")
        self.assertTrue(lesson["lesson_flow"])
        self.assertTrue(lesson["learner_submission"]["preserve_original"])
        with tempfile.TemporaryDirectory() as directory:
            written = module.write_artifacts(plan, Path(directory))
            self.assertTrue(Path(written["blueprint"]).exists())
            self.assertTrue(Path(written["current_lesson"]).exists())
            self.assertTrue(Path(written["progress"]).exists())

    def test_package_manager_resolver_prefers_pnpm_for_new_projects_and_detects_conflicts(self):
        module = load_module("upstack_package_manager", PACKAGE_MANAGER)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"name": "demo"}), encoding="utf-8")
            new_plan = module.plan(root, new_project=True)
            self.assertEqual(new_plan["status"], "choice_required")
            self.assertEqual(new_plan["recommended"], "pnpm")
            self.assertIn("pnpm install", new_plan["commands"]["install"])
            (root / "package-lock.json").write_text("{}", encoding="utf-8")
            (root / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
            conflict = module.plan(root)
            self.assertEqual(conflict["status"], "choice_required")
            self.assertEqual(conflict["detected"], None)
            self.assertEqual(set(conflict["managers"]), {"pnpm", "npm"})

    def test_onboarding_asks_existing_manager_then_migration_confirmation(self):
        module = load_module("upstack_onboarding_package_manager", ROOT / "scripts" / "onboarding.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"name": "existing", "packageManager": "npm@11.0.0"}), encoding="utf-8")
            (root / "package-lock.json").write_text("{}", encoding="utf-8")
            answers = {"goal": "understand", "outcome_detail": "architecture", "project_mode": "study", "destination": "source-adjacent", "source": "current"}
            first = module.next_question(module.context(root), answers)
            self.assertEqual(first["id"], "package_manager")
            answers["package_manager"] = "pnpm"
            migration = module.next_question(module.context(root), answers)
            self.assertEqual(migration["id"], "package_manager_migration_confirmation")
            self.assertIn("npm", migration["text"])
            self.assertIn("pnpm", migration["text"])

    def test_package_manager_migration_requires_separate_confirmation(self):
        module = load_module("upstack_package_manager_migration", PACKAGE_MANAGER)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(json.dumps({"packageManager": "npm@11.0.0"}), encoding="utf-8")
            (root / "package-lock.json").write_text("{}", encoding="utf-8")
            migration = module.plan(root, selected="pnpm")
            self.assertEqual(migration["status"], "migration_confirmation_required")
            self.assertTrue(migration["migration"])
            self.assertIn("delete-lockfile-without-confirmation", migration["must_not"])

    def test_project_state_gate_requires_onboarding_for_unknown_project_and_resumes_known_project(self):
        module = load_module("upstack_project_state", PROJECT_STATE)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "known-project"
            root.mkdir()
            (root / "package.json").write_text("{}", encoding="utf-8")
            unknown = module.command_gate(root, "lesson")
            self.assertEqual(unknown["status"], "onboarding_required")
            self.assertFalse(unknown["command_allowed"])
            no_resume = module.command_gate(root, "continue")
            self.assertEqual(no_resume["status"], "resume_unavailable")
            self.assertEqual(no_resume["next_action"], "offer_initialize_or_choose_existing_project")
            state_dir = root / ".upstack"
            state_dir.mkdir()
            project = {"project_id": "local-test-id", "root": str(root), "name": "Known Project"}
            state = {"project_id": "local-test-id", "project": {"name": "Known Project"}, "mode": "guided-lesson", "current_stage": 2, "completed_stages": [1], "last_action": "stage_completed", "next_action": "resume_current_lesson", "onboarding": {"status": "initialized"}}
            (state_dir / "PROJECT.json").write_text(json.dumps(project), encoding="utf-8")
            (state_dir / "STATE.json").write_text(json.dumps(state), encoding="utf-8")
            known = module.command_gate(root / "src", "hint")
            self.assertEqual(known["status"], "known_project")
            self.assertTrue(known["resume_required"])
            self.assertEqual(known["state"]["current_stage"], 2)
            self.assertEqual(known["project_id"], "local-test-id")
            for command in ["upstack", "init", "inventory", "concepts", "focus", "blueprint", "reverse", "build", "stage", "curriculum", "lesson", "hint", "assess", "discover", "choose", "source", "role", "portfolio", "status", "update", "continue", "resume"]:
                gated = module.command_gate(root / "src", command)
                self.assertEqual(gated["status"], "known_project", command)
                self.assertTrue(gated["resume_required"], command)

    def test_project_state_recovers_from_project_local_installed_skill_path(self):
        module = load_module("upstack_project_state_skill_path", PROJECT_STATE)
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "ai-workflow"
            skill = project / ".agents" / "skills" / "upstack"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: upstack\n---\n", encoding="utf-8")
            state_dir = project / ".upstack"
            state_dir.mkdir()
            (project / "package.json").write_text("{}", encoding="utf-8")
            (state_dir / "PROJECT.json").write_text(json.dumps({"project_id": "workflow-id", "root": str(project), "name": "ai-workflow"}), encoding="utf-8")
            (state_dir / "STATE.json").write_text(json.dumps({"project_id": "workflow-id", "mode": "guided-lesson", "current_stage": 3, "completed_stages": [1, 2], "next_action": "record_current_lesson_evidence", "pointers": {"project_root": str(project)}}), encoding="utf-8")
            gate = module.command_gate(skill, "lesson")
            self.assertEqual(gate["status"], "known_project")
            self.assertEqual(Path(gate["project_root"]), project.resolve())
            self.assertEqual(gate["skill_resource_path"], str(skill.resolve()))
            self.assertEqual(gate["resume_context"]["project_root"], str(project.resolve()))
            self.assertEqual(gate["resume_context"]["next_action"], "record_current_lesson_evidence")
            onboarding = load_module("upstack_onboarding_skill_path_resume", ROOT / "scripts" / "onboarding.py")
            context = onboarding.context(skill)
            self.assertTrue(context["known_upstack_project"])
            self.assertEqual(context["project_root"], str(project.resolve()))
            resume_plan = onboarding.question_plan(context, {}, host="opencode")
            self.assertEqual(resume_plan["mode"], "resume-known-project")
            self.assertEqual(resume_plan["questions"], [])

    def test_global_installed_skill_path_is_not_a_project(self):
        module = load_module("upstack_project_state_global_skill", PROJECT_STATE)
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            skill = home / ".agents" / "skills" / "upstack"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: upstack\n---\n", encoding="utf-8")
            with patch.object(module.Path, "home", return_value=home):
                root, detection = module.resolve_project_root(skill)
            self.assertIsNone(root)
            self.assertEqual(detection, "installed_skill_path")

    def test_onboarding_context_reports_known_project_state(self):
        module = load_module("upstack_onboarding_state_context", ROOT / "scripts" / "onboarding.py")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text("{}", encoding="utf-8")
            state_dir = root / ".upstack"
            state_dir.mkdir()
            state = {"project_id": "context-test-id", "mode": "guided-lesson", "current_stage": 3, "completed_stages": [1, 2], "last_action": "stage_completed", "next_action": "resume_current_lesson", "updated_at": "2026-08-25T00:00:00+00:00"}
            (state_dir / "STATE.json").write_text(json.dumps(state), encoding="utf-8")
            context = module.context(root)
            self.assertTrue(context["known_upstack_project"])
            self.assertEqual(context["persisted_state"]["current_stage"], 3)
            self.assertEqual(context["persisted_state"]["next_action"], "resume_current_lesson")

    def test_onboarding_cli_continue_without_state_does_not_start_intent(self):
        module = load_module("upstack_onboarding_cli_continue_unknown", ROOT / "scripts" / "onboarding.py")
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "package.json").write_text("{}", encoding="utf-8")
            with patch.object(sys, "argv", ["onboarding.py", str(project), "--command", "continue", "--host", "opencode", "--json"]):
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(module.main(), 0)
            payload = json.loads(output.getvalue())
            self.assertFalse(payload["context"]["known_upstack_project"])
            self.assertEqual(payload["question_plan"]["mode"], "resume-unavailable")
            self.assertEqual(payload["question_plan"]["questions"], [])
            self.assertTrue(payload["question_plan"]["resume_unavailable"])

    def test_onboarding_cli_continue_bypasses_intent_for_known_project(self):
        module = load_module("upstack_onboarding_cli_continue", ROOT / "scripts" / "onboarding.py")
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            state_dir = project / ".upstack"
            state_dir.mkdir()
            (project / "package.json").write_text("{}", encoding="utf-8")
            state = {"project_id": "cli-continue-id", "mode": "guided-lesson", "current_stage": 1, "next_action": "resume_current_lesson", "pointers": {"project_root": str(project)}, "current_lesson": {"id": "stage-01-orient", "status": "active"}}
            (state_dir / "STATE.json").write_text(json.dumps(state), encoding="utf-8")
            with patch.object(sys, "argv", ["onboarding.py", str(project), "--command", "continue", "--host", "opencode", "--json"]):
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(module.main(), 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["context"]["known_upstack_project"], True)
            self.assertEqual(payload["question_plan"]["mode"], "resume-known-project")
            self.assertEqual(payload["question_plan"]["command"], "continue")
            self.assertEqual(payload["question_plan"]["questions"], [])

    def test_known_project_onboarding_returns_resume_plan_without_questions(self):
        module = load_module("upstack_onboarding_resume_plan", ROOT / "scripts" / "onboarding.py")
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "package.json").write_text("{}", encoding="utf-8")
            state_dir = project / ".upstack"
            state_dir.mkdir()
            state = {"project_id": "resume-test-id", "mode": "guided-lesson", "current_stage": 2, "completed_stages": [1], "next_action": "record_current_lesson_evidence", "current_lesson": {"id": "stage-02-foundation", "status": "active"}, "pointers": {"project_root": str(project), "curriculum": {"id": "upstack-fresh-start-core"}, "current_lesson": {"id": "stage-02-foundation", "status": "active"}, "design": {"mode": "stitch-mcp", "status": "available_after_confirmation"}, "history_file": str(state_dir / "HISTORY.jsonl")}, "history": [{"event": "lesson_requested"}]}
            (state_dir / "STATE.json").write_text(json.dumps(state), encoding="utf-8")
            context = module.context(project)
            self.assertTrue(context["known_upstack_project"])
            self.assertIsNone(module.next_question(context, {}))
            plan = module.question_plan(context, {}, host="opencode")
            self.assertEqual(plan["mode"], "resume-known-project")
            self.assertEqual(plan["questions"], [])
            self.assertEqual(plan["resume_context"]["current_lesson"]["id"], "stage-02-foundation")
            continue_plan = module.question_plan(context, {}, host="opencode", command="continue")
            self.assertEqual(continue_plan["command"], "continue")
            self.assertEqual(continue_plan["questions"], [])
            self.assertEqual(plan["resume_context"]["design"]["mode"], "stitch-mcp")

    def test_live_session_handoff_requires_confirmation_and_preserves_project_progress(self):
        module = load_module("upstack_session_handoff", SESSION_HANDOFF)
        state_module = load_module("upstack_session_handoff_state", PROJECT_STATE)
        tutor = load_module("upstack_session_handoff_tutor", TUTOR)
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            destination = workspace / "agent-flow"
            brief = {"name": "Agent Flow", "problem": "Learn orchestration by building slices."}
            tutor.initialize_project(destination, brief, {"level": "new"}, workspace=workspace, onboarding_answers={"goal": "skill-upgrade", "project_mode": "scratch", "ui_design": "stitch-mcp", "stitch_status": "available_after_confirmation", "stitch_project_id": "stitch-project-1"}, confirm=True)
            request = {"reason": "Learner clarified that the project must be lesson-led and curriculum-first.", "changes": {"project_mode": "scratch", "teaching_mode": "guided-lesson", "lesson_generation": "explicit-identifier-only"}, "resume_command": "resume_current_curriculum"}
            prepared = module.prepare_handoff(destination, request)
            self.assertEqual(prepared["status"], "confirmation_required")
            self.assertFalse(prepared["write_performed"])
            self.assertFalse((destination / ".upstack" / "SESSION_HANDOFF.json").exists())
            not_confirmed = module.apply_handoff(destination, request, confirm=False)
            self.assertEqual(not_confirmed["status"], "confirmation_required")
            applied = module.apply_handoff(destination, request, confirm=True)
            self.assertEqual(applied["status"], "applied")
            self.assertTrue(applied["write_performed"])
            self.assertTrue((destination / ".upstack" / "SESSION_HANDOFF.json").exists())
            self.assertTrue((destination / ".upstack" / "SESSION_HANDOFF.md").exists())
            self.assertEqual(applied["state"]["active_directive"]["changes"]["teaching_mode"], "guided-lesson")
            self.assertEqual(applied["state"]["next_action"], "resume_current_curriculum")
            gate = state_module.command_gate(destination, "lesson")
            self.assertEqual(gate["status"], "known_project")
            self.assertEqual(gate["active_directive"]["request_id"], applied["request"]["request_id"])
            self.assertEqual(gate["state"]["history_count"], 2)
            self.assertEqual(gate["resume_context"]["project_root"], str(destination.resolve()))

    def test_live_session_handoff_without_state_stays_session_only(self):
        module = load_module("upstack_session_handoff_draft", SESSION_HANDOFF)
        with tempfile.TemporaryDirectory() as directory:
            result = module.prepare_handoff(Path(directory), {"changes": {"teaching_mode": "guided-lesson"}})
            self.assertEqual(result["status"], "session_only_pending")
            self.assertFalse(result["write_performed"])
            self.assertFalse((Path(directory) / ".upstack").exists())
            tutor = load_module("upstack_session_handoff_draft_tutor", TUTOR)
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            destination = workspace / "new-project"
            directive = result["request"]
            created = tutor.initialize_project(destination, {"name": "New Project", "problem": "Learn by building."}, {}, workspace=workspace, active_directive=directive, confirm=True)
            self.assertEqual(created["state"]["last_action"], "initialized_with_live_directive")
            self.assertEqual(created["state"]["active_directive"]["request_id"], directive["request_id"])

    def test_project_state_gate_rejects_ambiguous_broad_workspace(self):
        module = load_module("upstack_project_state_broad", PROJECT_STATE)
        with tempfile.TemporaryDirectory() as directory:
            broad = Path(directory)
            result = module.command_gate(broad, "build")
            self.assertEqual(result["status"], "project_selection_required")
            self.assertFalse(result["command_allowed"])
            self.assertEqual(result["next_action"], "ask_for_explicit_project_path_or_start_onboarding")

    def test_tutor_persists_identity_resumes_and_only_unlocks_complete_evidence(self):
        module = load_module("upstack_tutor", TUTOR)
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "workspace"
            workspace.mkdir()
            destination = workspace / "agent-flow"
            brief = {"name": "Agent Flow", "problem": "Teach orchestration through a usable project."}
            needs_confirmation = module.initialize_project(destination, brief, {"level": "new"}, workspace=workspace, confirm=False)
            self.assertEqual(needs_confirmation["status"], "confirmation_required")
            created = module.initialize_project(destination, brief, {"level": "new"}, workspace=workspace, onboarding_answers={"project_mode": "scratch", "package_manager": "pnpm"}, confirm=True)
            self.assertEqual(created["status"], "initialized")
            self.assertTrue((destination / ".upstack" / "PROJECT.json").exists())
            self.assertTrue((destination / ".upstack" / "STATE.json").exists())
            self.assertTrue((destination / ".upstack" / "lessons" / "CURRICULUM.md").exists())
            self.assertTrue((destination / ".upstack" / "PACKAGE_MANAGER.md").exists())
            self.assertTrue((destination / ".upstack" / "HISTORY.jsonl").exists())
            self.assertEqual(created["state"]["package_manager"], "pnpm")
            self.assertEqual(created["state"]["pointers"]["project_root"], str(destination.resolve()))
            self.assertEqual(created["state"]["pointers"]["destination"], str(destination.resolve()))
            self.assertEqual(created["state"]["pointers"]["curriculum"]["id"], "upstack-fresh-start-core")
            self.assertEqual(created["state"]["current_lesson"]["status"], "not_generated")
            self.assertFalse((destination / ".upstack" / "lessons" / "CURRENT_LESSON.md").exists())
            self.assertEqual(created["state"]["current_stage"], 1)
            resumed = module.resume_project(destination)
            self.assertEqual(resumed["status"], "resumed")
            self.assertEqual(resumed["lesson"]["sequence"], 1)
            self.assertEqual(module.resume_project(destination, "day 1")["status"], "resumed")
            self.assertEqual(module.resume_project(destination, "stage-02-foundation")["status"], "locked")
            requested = module.resume_project(destination, "day one", write=True)
            self.assertTrue(requested["write_performed"])
            self.assertTrue((destination / ".upstack" / "lessons" / "CURRENT_LESSON.md").exists())
            self.assertEqual(requested["state"]["next_action"], "record_current_lesson_evidence")
            self.assertEqual(requested["state"]["current_lesson"]["id"], "stage-01-orient")
            self.assertEqual(requested["state"]["current_lesson"]["status"], "active")
            self.assertGreaterEqual(len(requested["state"]["history"]), 2)
            self.assertGreaterEqual(len((destination / ".upstack" / "HISTORY.jsonl").read_text(encoding="utf-8").splitlines()), 2)
            partial = module.record_evidence(destination, 1, {"attempt": "code", "verification": "passed"}, write=True)
            self.assertEqual(partial["status"], "evidence_incomplete")
            self.assertFalse(partial["unlocked"])
            self.assertEqual(partial["state"]["current_stage"], 1)
            complete = module.record_evidence(destination, 1, {"attempt": "code", "verification": "passed", "explanation": "I can explain it", "feedback": "reviewed"}, write=True)
            self.assertEqual(complete["status"], "ready_to_unlock")
            self.assertTrue(complete["unlocked"])
            self.assertEqual(complete["state"]["current_stage"], 2)
            progress = json.loads((destination / ".upstack" / "lessons" / "progress.json").read_text(encoding="utf-8"))
            self.assertEqual(progress["completed_stages"], [1])
            curriculum = module.resolve_lesson(json.loads((destination / ".upstack" / "lessons" / "plan.json").read_text(encoding="utf-8")), "day 2")
            self.assertEqual(curriculum["stage"], 2)
            already = module.initialize_project(destination, brief, confirm=True)
            self.assertEqual(already["status"], "already_initialized")
            self.assertTrue(already["resume"])

    def test_broad_workspace_requires_exact_destination_and_confirmation(self):
        module = load_module("upstack_onboarding_destination", ROOT / "scripts" / "onboarding.py")
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            answers = {"goal": "rebuild", "outcome_detail": "new", "project_mode": "scratch", "destination": "new-local"}
            self.assertEqual(module.next_question(module.context(workspace), answers)["id"], "destination_path")
            rejected = module.validate_destination(workspace, workspace)
            self.assertFalse(rejected["valid"])
            self.assertEqual(rejected["status"], "same_as_broad_workspace")
            target = workspace / "focus-board"
            accepted = module.validate_destination(target, workspace)
            self.assertTrue(accepted["valid"])
            self.assertEqual(accepted["status"], "new_folder_under_existing_parent")
            answers["destination_path"] = str(target)
            self.assertEqual(module.next_question(module.context(workspace), answers)["id"], "destination_confirmation")
            answers["destination_confirmed"] = "confirmed"
            self.assertEqual(module.next_question(module.context(workspace), answers)["id"], "project_brief")
            self.assertFalse(target.exists())

    def test_scratch_route_exposes_stitch_only_when_capability_is_verified(self):
        module = load_module("upstack_onboarding_design_capability", ROOT / "scripts" / "onboarding.py")
        answers = {"goal": "rebuild", "outcome_detail": "new", "project_mode": "scratch", "destination": "new-local", "destination_path": "/tmp/upstack-scratch-design", "destination_confirmed": "confirmed", "project_brief": "custom"}
        without = module.next_question({"design_tools": []}, answers)
        self.assertNotIn("stitch-mcp", [item["value"] for item in without["options"]])
        with_stitch = module.next_question({"design_tools": ["stitch-mcp"]}, answers)
        self.assertIn("stitch-mcp", [item["value"] for item in with_stitch["options"]])

    def test_interview_route_collects_requirements_and_skill_profile_before_source(self):
        module = load_module("upstack_onboarding_interview", ROOT / "scripts" / "onboarding.py")
        answers = {"goal": "interview", "outcome_detail": "backend"}
        self.assertEqual(module.next_question(None, answers)["id"], "job_requirements")
        answers["job_requirements"] = "paste"
        self.assertEqual(module.next_question(None, answers)["id"], "self_assessment")
        answers["self_assessment"] = "working"
        self.assertEqual(module.next_question(None, answers)["id"], "project_mode")

    def test_interview_planner_separates_self_report_and_demonstrated_skill(self):
        module = load_module("upstack_interview_profile", INTERVIEW_PREP)
        profile = module.build_skill_profile(
            {"level": "working", "dimensions": [{"name": "backend", "level": "working"}, {"name": "testing", "level": "new"}]},
            [{"dimension": "backend", "type": "explain", "score": 2.8, "observation": "Explained request validation and one failure case."}],
        )
        backend = next(item for item in profile["dimensions"] if item["name"] == "backend")
        self.assertEqual(profile["calibration_status"], "evidence_calibrated")
        self.assertEqual(backend["self_reported_level"], "working")
        self.assertEqual(backend["demonstrated_level"], "reliable")
        self.assertEqual(backend["status"], "demonstrated")
        self.assertEqual(len(backend["evidence"]), 1)

    def test_interview_planner_labels_reported_patterns_and_derives_questions_from_requirements(self):
        module = load_module("upstack_interview_plan", INTERVIEW_PREP)
        job = {"title": "Backend Engineer", "company": "ExampleCo", "level": "mid-level", "requirements": ["Design reliable APIs", "Python and SQL", "testing and debugging"], "ai_policy": "No AI during live interviews"}
        sources = [{"id": "candidate-report-1", "source_type": "candidate_report", "role": "Backend Engineer", "level": "mid-level", "url": "https://example.test/report", "questions": ["Design a rate limiter"]}]
        plan = module.build_plan(job, sources, self_assessment={"level": "working"})
        self.assertEqual(plan["skill_profile"]["initial_hypothesis"], "emerging")
        self.assertEqual(plan["evidence"][0]["evidence_class"], "high_confidence_public_pattern")
        self.assertTrue(any(item["prediction_status"] == "reported_pattern_not_guarantee" for item in plan["question_bank"]))
        self.assertTrue(any(item["prediction_status"] == "derived_from_supplied_requirements_not_guarantee" for item in plan["question_bank"]))
        self.assertEqual(plan["practice_policy"]["ai_policy"], "No AI during live interviews")
        self.assertEqual(plan["blueprint"][0]["id"], "stage-01-role-map")
        self.assertEqual(len(plan["diagnostic_plan"]), 3)
        with tempfile.TemporaryDirectory() as directory:
            written = module.write_artifacts(plan, Path(directory))
            self.assertIn("profile", written)
            profile_text = Path(written["profile"]).read_text(encoding="utf-8")
            self.assertIn("Learner Skill and Knowledge Profile", profile_text)
            self.assertIn("backend", profile_text)
            self.assertTrue(Path(written["requirements"]).exists())
            self.assertTrue(Path(written["question_bank"]).exists())

    def test_interview_feedback_preserves_attempt_and_requires_reasoned_correction(self):
        module = load_module("upstack_interview_feedback", INTERVIEW_PREP)
        question = {"id": "q-1", "prompt": "Design an API", "category": "system_design", "evidence_class": "verified_requirement"}
        contract = module.build_feedback_contract(question, {"answer": "I would use a database.", "language": "text"}, "both")
        self.assertTrue(contract["attempt_preserved"])
        self.assertEqual(contract["output_mode"], "both")
        self.assertIn("first_incorrect_assumption_or_step", contract["required_feedback"])
        self.assertIn("trade_offs_and_when_each_approach_is_better", contract["required_feedback"])
        self.assertIn("one_nearby_follow_up_for_transfer", contract["required_feedback"])

    def test_ui_design_helper_keeps_markdown_fallback_and_gates_remote_writes(self):
        module = load_module("upstack_ui_design", UI_DESIGN)
        brief = {
            "name": "Focus Board",
            "problem": "Help learners track one project slice.",
            "audience": "Developers learning by building.",
            "primary_action": "Open the next stage",
            "screens": [{"name": "Home", "goal": "Choose a stage", "elements": ["Stage list", "Progress", "Open stage"]}],
        }
        portable = module.build_design_plan(brief, mode="portable")
        self.assertEqual(portable["workflow"]["curriculum_scope"], "map_the_complete_project_before_teaching")
        self.assertEqual(portable["workflow"]["lesson_delivery"], "generate_one_current_stage_at_a_time")
        self.assertEqual(portable["integration"]["status"], "not_required")
        self.assertFalse(portable["integration"]["remote_write"])
        self.assertIn("# Focus Board — Wireframe", module.render_wireframe_markdown(portable))
        unavailable = module.build_design_plan(brief, mode="stitch-mcp")
        self.assertEqual(unavailable["integration"]["status"], "unavailable_use_portable_fallback")
        self.assertTrue(any(path.endswith("/WIREFRAME.md") for path in unavailable["integration"]["portable_fallback"]))
        available = module.build_design_plan(brief, mode="stitch-mcp", design_capabilities=["stitch-mcp"])
        self.assertEqual(available["integration"]["status"], "available_after_confirmation")
        self.assertTrue(available["integration"]["requires_confirmation"])
        self.assertEqual(available["side_effects"], [])

    def test_known_project_skips_project_selection_question(self):
        module = load_module("upstack_onboarding_known", ROOT / "scripts" / "onboarding.py")
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
            report = module.context(project)
            first = module.next_question(report, {})
            self.assertEqual(first["id"], "goal")
            self.assertEqual(first["text"], "What would you like to accomplish first?")
