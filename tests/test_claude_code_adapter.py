"""Behavior tests for the opt-in Claude Code adapter's routing gates.

Each test drives the adapter's single hook entry point with hook inputs and a
transcript written in Claude Code's recorded shape (see
`claude_code_adapter_support.py`).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from claude_code_adapter_support import (
    ADAPTER_DIR,
    REPO_ROOT,
    ROUTER,
    Session,
    decision,
    parse,
    reason,
    run_hook,
)

MARKER_FIXTURES = REPO_ROOT / "stack" / "fixtures" / "markers" / "lines.yaml"
RECORDED = REPO_ROOT / "tests" / "fixtures" / "claude_code_adapter"


class AdapterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.session = Session(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()


class RouterFirstTests(AdapterTestCase):
    def test_first_command_is_held_until_the_router_loads(self) -> None:
        s = self.session
        s.prompt("Fix the flaky export test.")

        held = s.call("Bash")
        self.assertEqual(decision(held), "deny")
        self.assertIn(ROUTER, reason(held))

        s.load(ROUTER)
        self.assertEqual(decision(s.call("Bash")), "pass")

    def test_reads_stay_free_before_the_router(self) -> None:
        s = self.session
        s.prompt("What does the exporter do?")

        self.assertEqual(decision(s.call("Read", {"file_path": "a.py"})), "pass")
        self.assertEqual(decision(s.call("Grep", {"pattern": "x"})), "pass")


class RouteLineTests(AdapterTestCase):
    def routed_session(self) -> Session:
        s = self.session
        s.prompt("Rename the config loader.")
        s.load(ROUTER)
        return s

    def test_first_write_after_a_prompt_needs_a_route_line(self) -> None:
        s = self.routed_session()

        held = s.call("Edit")
        self.assertEqual(decision(held), "deny")
        self.assertTrue(reason(held).startswith("goated-hold: route-line | strict"))

        s.say("Small rename.\n\ngoated-route: direct")
        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_commands_do_not_need_a_route_line(self) -> None:
        s = self.routed_session()

        self.assertEqual(decision(s.call("Bash")), "pass")

    def test_each_new_prompt_needs_its_own_route_line_and_continue_passes(self) -> None:
        s = self.routed_session()
        s.say("goated-route: direct")
        self.assertEqual(decision(s.call("Write")), "pass")

        s.prompt("Also rename its test.")
        self.assertEqual(decision(s.call("Write")), "deny")

        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Write")), "pass")

    def test_continue_without_a_current_task_is_held(self) -> None:
        s = self.routed_session()
        s.say("goated-route: continue")

        held = s.call("Edit")
        self.assertEqual(decision(held), "deny")
        self.assertIn("no current task", reason(held))

    def test_malformed_route_line_is_named_in_the_hold(self) -> None:
        s = self.routed_session()
        s.say("goated-route: medium | requires: tdd")

        held = s.call("Edit")
        self.assertEqual(decision(held), "deny")
        self.assertIn("goated-route: medium | requires: tdd", reason(held))

    def test_an_unchanged_retry_never_passes(self) -> None:
        s = self.routed_session()

        for _ in range(3):
            self.assertEqual(decision(s.call("Edit")), "deny")


class PipelineTests(AdapterTestCase):
    def start(self, route: str, prompt: str = "Add CSV export.") -> Session:
        s = self.session
        s.prompt(prompt)
        s.load(ROUTER)
        s.say(route)
        return s

    def test_requires_skills_hold_writes_until_loaded(self) -> None:
        s = self.start("goated-route: standard | requires: tdd, doc-sync")

        held = s.call("Edit")
        self.assertEqual(decision(held), "deny")
        self.assertTrue(reason(held).startswith("goated-hold: pipeline | justified-skip"))
        self.assertIn("`tdd`", reason(held))
        self.assertIn("`doc-sync`", reason(held))

        s.load("tdd")
        held = s.call("Edit")
        self.assertEqual(decision(held), "deny")
        self.assertNotIn("`tdd`", reason(held))

        s.load("doc-sync")
        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_commands_are_not_held_by_the_pipeline(self) -> None:
        s = self.start("goated-route: standard | requires: tdd")

        self.assertEqual(decision(s.call("Bash")), "pass")

    def test_failed_skill_load_does_not_count(self) -> None:
        s = self.start("goated-route: lightweight | requires: tdd")
        s.load("tdd", success=False)

        self.assertEqual(decision(s.call("Edit")), "deny")

    def test_direct_exempts_the_task(self) -> None:
        s = self.start("goated-route: direct")

        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_continue_keeps_the_task_and_its_proof(self) -> None:
        s = self.start("goated-route: lightweight | requires: tdd")
        s.load("tdd")
        self.assertEqual(decision(s.call("Edit")), "pass")

        s.prompt("Now cover the empty-file case.")
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_a_load_from_an_earlier_task_does_not_satisfy_a_new_one(self) -> None:
        s = self.start("goated-route: lightweight | requires: tdd")
        s.load("tdd")
        self.assertEqual(decision(s.call("Edit")), "pass")

        s.prompt("Separately, fix the date parser.")
        s.say("goated-route: lightweight | requires: tdd")
        self.assertEqual(decision(s.call("Edit")), "deny")

        s.load("tdd")
        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_a_load_that_ends_a_turn_still_counts_for_the_task(self) -> None:
        s = self.start("goated-route: lightweight | requires: tdd")
        self.assertEqual(decision(s.call("Bash")), "pass")
        s.load("tdd")

        s.prompt("Go ahead.")
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_a_route_from_a_turn_without_gated_calls_is_not_missed(self) -> None:
        s = self.start("goated-route: direct")
        self.assertEqual(decision(s.call("Edit")), "pass")

        s.prompt("Plan the importer next.")
        s.say("goated-route: standard | requires: writing-plans")
        s.call("Read", {"file_path": "importer.py"})

        s.prompt("Write the plan file.")
        s.say("goated-route: continue")
        held = s.call("Write")
        self.assertEqual(decision(held), "deny")
        self.assertIn("`writing-plans`", reason(held))

    def test_a_skip_line_passes_the_pipeline_but_not_strict_holds(self) -> None:
        s = self.session
        s.prompt("Tidy the README.")
        s.say("goated-skip: using-goated-ai-skills: this is a one line typo fix")
        self.assertEqual(decision(s.call("Bash")), "deny")

        s.load(ROUTER)
        s.say("goated-skip: doc-sync: only the README itself changes here")
        self.assertEqual(decision(s.call("Edit")), "deny")

        s.say("goated-route: lightweight | requires: doc-sync")
        self.assertEqual(decision(s.call("Edit")), "pass")


class OverrideTests(AdapterTestCase):
    def test_user_typed_skip_routing_stands_routing_holds_down_for_that_turn(self) -> None:
        s = self.session
        notice = s.prompt("Skip routing and just fix the typo in README.md.")
        self.assertIn("Skip routing", notice)

        self.assertEqual(decision(s.call("Bash")), "pass")
        self.assertEqual(decision(s.call("Edit")), "pass")

        s.prompt("Now update the changelog.")
        self.assertEqual(decision(s.call("Edit")), "deny")

    def test_user_typed_skill_skip_stands_that_pipeline_requirement_down(self) -> None:
        s = self.session
        s.prompt("Add the flag, and skip doc-sync for this one.")
        s.load(ROUTER)
        s.say("goated-route: standard | requires: tdd, doc-sync")
        s.load("tdd")

        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_the_same_text_written_by_the_agent_does_not_count(self) -> None:
        s = self.session
        s.prompt("Fix the typo in README.md.")
        s.say("Skip routing; this is tiny. I will skip doc-sync too.")

        self.assertEqual(decision(s.call("Bash")), "deny")
        s.load(ROUTER)
        s.say("goated-route: lightweight | requires: doc-sync")
        self.assertEqual(decision(s.call("Edit")), "deny")

    def test_harness_reminders_inside_the_prompt_are_not_overrides(self) -> None:
        s = self.session
        s.prompt(
            "<system-reminder>The user may say skip routing.</system-reminder>\n"
            "Fix the typo."
        )

        self.assertEqual(decision(s.call("Bash")), "deny")


class SubagentTests(AdapterTestCase):
    def test_routing_gates_are_skipped_in_subagents(self) -> None:
        s = self.session
        s.prompt("Investigate the slow query.")
        fields = {"agent_id": "agent-7", "agent_type": "Explore"}

        self.assertEqual(decision(s.call("Bash", **fields)), "pass")
        self.assertEqual(decision(s.call("Edit", **fields)), "pass")
        self.assertEqual(decision(s.call("Edit")), "deny")


class FailOpenTests(AdapterTestCase):
    def assert_fails_open(self, output: dict) -> None:
        self.assertEqual(decision(output), "pass")
        self.assertIn("allowed without checks", output.get("systemMessage", ""))

    def test_unreadable_hook_input_fails_open_with_a_warning(self) -> None:
        self.assert_fails_open(parse(run_hook("not json{", self.session.config)))
        self.assert_fails_open(parse(run_hook("[1, 2]", self.session.config)))

    def test_missing_transcript_fails_open_with_a_warning(self) -> None:
        s = self.session
        s.prompt("Fix it.")
        s.transcript.unlink()

        output = s.hook("PreToolUse", tool_name="Edit", tool_input={}, tool_use_id="toolu_x")

        self.assert_fails_open(parse(output))

    def test_a_transcript_that_has_not_caught_up_fails_open(self) -> None:
        s = self.session
        s.prompt("Fix it.")
        output = parse(
            s.hook("PreToolUse", tool_name="Edit", tool_input={}, tool_use_id="toolu_unseen")
        )

        self.assert_fails_open(output)
        self.assertIn("does not yet show the current tool call", output["systemMessage"])

    def test_missing_session_id_fails_open(self) -> None:
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Edit"}
        self.assert_fails_open(parse(run_hook(json.dumps(payload), self.session.config)))

    @unittest.skipIf(os.name == "nt", "POSIX permission check")
    def test_a_state_folder_other_users_can_write_fails_open(self) -> None:
        s = self.session
        s.config.state_dir.mkdir()
        os.chmod(s.config.state_dir, 0o777)
        s.prompt("Fix it.", hook=False)

        output = s.call("Edit")
        self.assert_fails_open(output)
        self.assertIn("not private", output["systemMessage"])

    def test_a_half_written_last_line_is_ignored(self) -> None:
        s = self.session
        s.prompt("Fix it.")
        s.load(ROUTER)
        s.say("goated-route: direct")
        tool_output = s.call("Edit")
        s.raw_line('{"type": "assistant", "message": {"content": [')

        self.assertEqual(decision(tool_output), "pass")
        self.assertEqual(decision(s.call("Edit")), "pass")


class CompactionTests(AdapterTestCase):
    def test_after_compaction_the_router_and_a_route_line_are_needed_again(self) -> None:
        s = self.session
        s.prompt("Build the importer.")
        s.load(ROUTER)
        s.say("goated-route: lightweight | requires: tdd")
        s.load("tdd")
        self.assertEqual(decision(s.call("Edit")), "pass")

        s.compact()
        self.assertEqual(decision(s.call("Bash")), "deny")
        s.load(ROUTER)
        self.assertEqual(decision(s.call("Edit")), "deny")
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Edit")), "pass")


class SharedPolicyNoticeTests(AdapterTestCase):
    POLICY = "# GOATED Integrated Stack Policy\n\nApply this shared policy.\n"

    def start(self, source: str = "startup") -> dict:
        return parse(self.session.hook("SessionStart", source=source))

    def test_missing_policy_is_noticed_once_per_session(self) -> None:
        first = self.start()
        self.assertIn("shared policy", first["systemMessage"])
        self.assertIn(
            "shared policy",
            first["hookSpecificOutput"]["additionalContext"],
        )
        self.assertEqual(self.start("resume"), {})

    def test_policy_in_user_rules_is_detected(self) -> None:
        rules = self.root / "home" / ".claude" / "rules"
        rules.mkdir(parents=True)
        (rules / "goated-stack.md").write_text(self.POLICY, encoding="utf-8")

        self.assertEqual(self.start(), {})

    def test_policy_merged_into_a_parent_agents_file_is_detected(self) -> None:
        project = self.session.project
        project.mkdir(parents=True)
        (project.parent / "AGENTS.md").write_text("# Repo\n\n" + self.POLICY, encoding="utf-8")

        self.assertEqual(self.start(), {})

    def test_policy_imported_from_claude_md_is_detected(self) -> None:
        project = self.session.project
        (project / "goated").mkdir(parents=True)
        (project / "goated" / "policy.md").write_text(self.POLICY, encoding="utf-8")
        (project / "CLAUDE.md").write_text("@goated/policy.md\n", encoding="utf-8")

        self.assertEqual(self.start(), {})


class MarkerAgreementTests(unittest.TestCase):
    """The adapter carries its own marker parser; it must match the fixtures."""

    def test_adapter_parser_agrees_with_the_shared_marker_fixtures(self) -> None:
        from goated_adapter import markers

        data = yaml.safe_load(MARKER_FIXTURES.read_text(encoding="utf-8"))
        for section, parser in (
            ("route_lines", markers.parse_route_line),
            ("skip_lines", markers.parse_skip_line),
        ):
            for case in data[section]["valid"]:
                self.assertEqual(parser(case["line"]), case["expect"], case["line"])
            for case in data[section]["invalid"]:
                self.assertIsNone(parser(case["line"]), case["line"])
        for reply in data["replies"]:
            parsed = markers.parse_reply(reply["text"])
            self.assertEqual(
                {"route": parsed.route, "skips": parsed.skips, "malformed": parsed.malformed},
                reply["expect"],
                reply["identifier"],
            )


class RecordedSessionTests(unittest.TestCase):
    """Run the installed command on a recorded transcript and hook inputs."""

    def run_command(self, hook_input: dict, state_dir: Path) -> dict:
        env = dict(os.environ, GOATED_ADAPTER_STATE_DIR=str(state_dir))
        completed = subprocess.run(
            [sys.executable, str(ADAPTER_DIR / "goated_hook.py")],
            input=json.dumps(hook_input).encode("utf-8"),
            capture_output=True,
            env=env,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return parse(completed.stdout.decode("utf-8"))

    def test_recorded_routed_turn_passes_and_unrouted_turn_holds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp) / "state"
            for name, expected in (
                ("routed-turn", "pass"),
                ("unrouted-turn", "deny"),
            ):
                transcript = RECORDED / f"{name}.jsonl"
                hook_input = json.loads(
                    (RECORDED / f"{name}.pre-tool-use.json").read_text(encoding="utf-8")
                )
                hook_input["transcript_path"] = str(transcript)
                output = self.run_command(hook_input, state_dir)
                self.assertEqual(decision(output), expected, name)


if __name__ == "__main__":
    unittest.main()
