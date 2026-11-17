"""Behavior tests for the opt-in Claude Code adapter's routing gates.

Each test drives the adapter's single hook entry point with hook inputs and a
transcript written in Claude Code's recorded shape (see
`claude_code_adapter_support.py`).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from claude_code_adapter_support import (
    ADAPTER_DIR,
    BRIEF,
    REPO_ROOT,
    ROUTER,
    Config,
    Session,
    decision,
    parse,
    reason,
    run_hook,
)

MARKER_FIXTURES = REPO_ROOT / "stack" / "fixtures" / "markers" / "lines.yaml"
DESIGN_READS_FIXTURES = MARKER_FIXTURES.with_name("design-reads.yaml")
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

    def test_an_unchanged_retry_of_router_first_never_passes(self) -> None:
        s = self.session
        s.prompt("Fix the flaky export test.")

        for _ in range(3):
            held = s.call("Bash")
            self.assertEqual(decision(held), "deny")
        self.assertIn("skip routing", reason(held))

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

    def test_continue_in_a_session_with_no_task_starts_one_without_required_skills(
        self,
    ) -> None:
        s = self.session
        s.prompt(
            "Background (from the session that started this one): the export work "
            "begun there continues here.",
            origin=None,
            turnOrigin="host_synthetic",
        )
        s.load(ROUTER)
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Edit")), "pass")

        s.prompt("Also cover the empty file.")
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_continue_in_a_new_sessions_second_turn_starts_a_task(self) -> None:
        s = self.session
        s.hook("SessionStart", source="startup")
        s.prompt(
            "Background (from the session that started this one): read the brief.",
            origin=None,
            turnOrigin="host_synthetic",
        )
        s.read("brief.md")

        s.prompt("Go ahead with it.")
        s.load(ROUTER)
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_a_task_started_by_continue_gives_way_to_a_full_route(self) -> None:
        s = self.routed_session()
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Edit")), "pass")

        s.prompt("Now add the importer.")
        s.say("goated-route: lightweight | requires: tdd")
        held = s.call("Edit")
        self.assertEqual(decision(held), "deny")
        self.assertTrue(reason(held).startswith("goated-hold: pipeline | strict"))

    def test_continue_after_a_state_reset_is_still_held(self) -> None:
        s = self.routed_session()
        s.say("goated-route: lightweight | requires: tdd")
        self.assertEqual(decision(s.call("Edit")), "deny")

        s.prompt("Go on.")
        s.load(ROUTER)
        s.say("goated-route: continue")
        (s.config.state_dir / "session-1.json").write_text("{not json")
        held = s.call("Edit")
        self.assertEqual(decision(held), "deny")
        self.assertTrue(reason(held).startswith("goated-hold: route-line | strict"))
        self.assertIn("reset", reason(held))
        self.assertEqual(decision(s.call("Edit")), "deny")

        s.say("goated-route: lightweight | requires: tdd")
        s.load("tdd")
        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_continue_after_the_state_file_went_missing_is_still_held(self) -> None:
        s = self.routed_session()
        s.say("goated-route: lightweight | requires: tdd")
        self.assertEqual(decision(s.call("Edit")), "deny")

        (s.config.state_dir / "session-1.json").unlink()
        s.prompt("Go on.")
        s.load(ROUTER)
        s.say("goated-route: continue")
        held = s.call("Edit")
        self.assertEqual(decision(held), "deny")
        self.assertTrue(reason(held).startswith("goated-hold: route-line | strict"))
        self.assertIn("missing", reason(held))

        s.prompt("Still going.")
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Edit")), "deny")

    def test_a_missing_state_file_in_the_first_turn_still_lets_continue_start_a_task(
        self,
    ) -> None:
        s = self.routed_session()
        s.say("goated-route: continue")
        (s.config.state_dir / "session-1.json").unlink()

        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_continue_after_a_route_in_the_same_turn_keeps_its_skills(self) -> None:
        s = self.routed_session()
        s.say("goated-route: lightweight | requires: tdd")
        s.say("goated-route: continue")

        held = s.call("Edit")
        self.assertEqual(decision(held), "deny")
        self.assertIn("`tdd`", reason(held))

    def test_continue_after_a_route_in_the_same_turn_replaces_the_old_task(self) -> None:
        s = self.routed_session()
        s.say("goated-route: direct")
        self.assertEqual(decision(s.call("Edit")), "pass")

        s.prompt("Now the importer, test first.")
        s.say("goated-route: lightweight | requires: tdd")
        s.say("goated-route: continue")
        held = s.call("Edit")
        self.assertEqual(decision(held), "deny")
        self.assertIn("`tdd`", reason(held))

    def test_continue_as_the_first_route_after_compaction_starts_a_task(self) -> None:
        s = self.routed_session()
        self.assertEqual(decision(s.call("Bash")), "pass")

        s.compact()
        s.load(ROUTER)
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Edit")), "pass")

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
        self.assertTrue(reason(held).startswith("goated-hold: pipeline | strict"))
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

    def test_a_skip_line_never_passes_a_routing_hold(self) -> None:
        s = self.session
        s.prompt("Tidy the README.")
        s.say("goated-skip: using-goated-ai-skills: this is a one line typo fix")
        self.assertEqual(decision(s.call("Bash")), "deny")

        s.load(ROUTER)
        s.say("goated-route: lightweight | requires: doc-sync")
        s.say("goated-skip: doc-sync: only the README itself changes here")
        held = s.call("Edit")
        self.assertEqual(decision(held), "deny")
        self.assertTrue(reason(held).startswith("goated-hold: pipeline | strict"))
        self.assertIn("corrected route line", reason(held))

    def test_a_corrected_route_line_drops_a_required_skill(self) -> None:
        s = self.start("goated-route: standard | requires: tdd, doc-sync")
        s.load("tdd")
        self.assertEqual(decision(s.call("Edit")), "deny")

        s.say("doc-sync does not apply after all.\n\ngoated-route: standard | requires: tdd")
        s.load("tdd")
        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_an_unchanged_retry_of_a_pipeline_hold_never_passes(self) -> None:
        s = self.start("goated-route: standard | requires: tdd")

        for _ in range(3):
            self.assertEqual(decision(s.call("Edit")), "deny")

    def test_a_load_earlier_in_the_turn_counts_for_the_task_it_starts(self) -> None:
        s = self.session
        s.prompt("Add CSV export.")
        s.load(ROUTER)
        s.load("tdd")
        s.say("goated-route: lightweight | requires: tdd")

        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_a_load_in_an_earlier_turn_does_not_count(self) -> None:
        s = self.session
        s.prompt("Read up on the exporter first.")
        s.load(ROUTER)
        self.assertEqual(decision(s.call("Bash")), "pass")
        s.load("tdd")

        s.prompt("Now add CSV export.")
        s.say("goated-route: lightweight | requires: tdd")
        held = s.call("Edit")
        self.assertEqual(decision(held), "deny")
        self.assertIn("earlier turn", reason(held))

    def test_a_load_before_an_earlier_tasks_route_line_does_not_count(self) -> None:
        s = self.session
        s.prompt("Add CSV export.")
        s.load(ROUTER)
        s.load("tdd")
        s.say("goated-route: lightweight | requires: tdd")
        self.assertEqual(decision(s.call("Edit")), "pass")

        s.say("A separate change now.\n\ngoated-route: lightweight | requires: tdd")
        held = s.call("Edit")
        self.assertEqual(decision(held), "deny")
        self.assertIn("another task's route line", reason(held))
        s.load("tdd")
        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_a_load_after_an_earlier_tasks_route_line_counts_for_the_next(self) -> None:
        s = self.start("goated-route: direct")
        s.load("tdd")
        s.say("This needs tests after all.\n\ngoated-route: lightweight | requires: tdd")

        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_a_corrected_route_line_keeps_loads_made_before_the_first(self) -> None:
        s = self.session
        s.prompt("Add CSV export.")
        s.load(ROUTER)
        s.load("tdd")
        s.say("goated-route: standard | requires: tdd, doc-sync")
        self.assertEqual(decision(s.call("Edit")), "deny")
        s.say("doc-sync does not apply.\n\ngoated-route: lightweight | requires: tdd")

        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_a_shell_write_between_route_lines_starts_another_task(self) -> None:
        s = self.session
        s.prompt("Add CSV export.")
        s.load(ROUTER)
        s.load("tdd")
        s.say("goated-route: direct")
        s.run("echo done > notes.txt")
        s.say("Next, the importer.\n\ngoated-route: lightweight | requires: tdd")

        held = s.call("Edit")
        self.assertEqual(decision(held), "deny")
        self.assertIn("`tdd`", reason(held))

    def test_a_failed_shell_write_between_route_lines_still_starts_another_task(
        self,
    ) -> None:
        s = self.session
        s.prompt("Add CSV export.")
        s.load(ROUTER)
        s.load("tdd")
        s.say("goated-route: direct")
        s.run("echo done > notes.txt && false", success=False)
        s.say("Next, the importer.\n\ngoated-route: lightweight | requires: tdd")

        held = s.call("Edit")
        self.assertEqual(decision(held), "deny")
        self.assertIn("`tdd`", reason(held))

    def test_a_held_shell_write_between_route_lines_does_not_split_the_task(self) -> None:
        s = self.session
        s.prompt("Add CSV export.")
        s.load(ROUTER)
        s.load("tdd")
        s.say("goated-route: standard | requires: tdd, doc-sync")
        self.assertEqual(decision(s.call("Bash", {"command": "echo x > out.csv"})), "deny")
        s.say("doc-sync does not apply.\n\ngoated-route: lightweight | requires: tdd")

        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_a_load_before_another_tasks_correction_does_not_count(self) -> None:
        s = self.session
        s.prompt("Add CSV export.")
        s.load(ROUTER)
        s.say("goated-route: standard | requires: tdd, doc-sync")
        s.load("tdd")
        s.say("Only a typo after all.\n\ngoated-route: direct")
        self.assertEqual(decision(s.call("Edit")), "pass")

        s.say("Now the importer.\n\ngoated-route: lightweight | requires: tdd")
        held = s.call("Edit")
        self.assertEqual(decision(held), "deny")
        self.assertIn("`tdd`", reason(held))

    def test_a_load_after_another_tasks_last_route_line_counts(self) -> None:
        s = self.start("goated-route: direct")
        self.assertEqual(decision(s.call("Edit")), "pass")
        s.load("tdd")
        s.say("Now the importer.\n\ngoated-route: lightweight | requires: tdd")

        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_a_skill_the_user_invoked_with_a_slash_command_counts(self) -> None:
        s = self.session
        s.slash("tdd", "add the CSV export")
        s.load(ROUTER)
        s.say("goated-route: lightweight | requires: tdd")

        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_a_skill_from_another_namespace_does_not_count(self) -> None:
        s = self.start("goated-route: lightweight | requires: tdd")
        s.load("someplugin:tdd")
        self.assertEqual(decision(s.call("Edit")), "deny")

    def test_a_configured_goated_namespace_counts(self) -> None:
        s = self.session
        s.config = Config(
            state_dir=s.config.state_dir,
            home=s.config.home,
            lag_wait_seconds=0.0,
            skill_namespaces=("goated",),
        )
        s.prompt("Add CSV export.")
        s.load("goated:using-goated-ai-skills")
        s.say("goated-route: lightweight | requires: tdd")
        s.load("goated:tdd")
        self.assertEqual(decision(s.call("Edit")), "pass")


class UnseenLineAdviceTests(AdapterTestCase):
    """The unseen-line advice is given in full on a turn's first hold that carries
    it; later ones in that turn give one sentence and keep the typed override."""

    FULL = "may not be seen"
    SHORT = "call's description or a Skill call's args"
    AUTH = {"file_path": "src/auth.py", "content": "x = 1\n"}

    def route_line_hold(self) -> dict:
        s = self.session
        s.prompt("Harden the login check.")
        s.load(ROUTER)
        return s.call("Edit")

    def test_a_turns_first_hold_with_the_advice_gives_it_in_full(self) -> None:
        s = self.session
        s.prompt("Harden the login check.")
        # Near miss: an earlier hold in the turn that carries no advice does not
        # count as having shown it.
        first = s.call("Edit")
        self.assertTrue(reason(first).startswith("goated-hold: router-first"))
        s.load(ROUTER)

        held = s.call("Edit")
        self.assertTrue(reason(held).startswith("goated-hold: route-line | strict\n"))
        self.assertIn(self.FULL, reason(held))
        self.assertIn("description field of a shell or agent call, or in a Skill call's args",
                      reason(held))
        self.assertIn("`skip routing`", reason(held))

    def test_a_later_hold_in_the_turn_gives_one_sentence_and_the_override(self) -> None:
        s = self.session
        self.assertIn(self.FULL, reason(self.route_line_hold()))
        s.say("goated-route: direct")

        held = reason(s.call("Write", self.AUTH))
        self.assertTrue(held.startswith("goated-hold: security | justified-skip\n"))
        self.assertNotIn(self.FULL, held)
        self.assertIn(self.SHORT, held)
        self.assertIn("`skip code-security-review`", held)
        self.assertIn("This edit was not applied.", held)

    def test_advice_text_in_a_call_that_was_not_held_does_not_count_as_shown(self) -> None:
        # Near miss for the short form: only this adapter's held results count.
        s = self.session
        s.prompt("Harden the login check.")
        s.load(ROUTER)
        s.say("goated-route: direct")
        s.call("Bash", {"command": "cat README.md"},
               result="A route line in reply text may not be seen: Claude Code records ...")

        held = reason(s.call("Write", self.AUTH))
        self.assertTrue(held.startswith("goated-hold: security"))
        self.assertIn(self.FULL, held)

    def test_the_next_turn_gives_the_full_advice_again(self) -> None:
        s = self.session
        self.route_line_hold()
        s.say("goated-route: direct")
        self.assertNotIn(self.FULL, reason(s.call("Write", self.AUTH)))

        s.prompt("Also harden the logout check.")
        s.say("goated-route: direct")
        again = reason(s.call("Write", self.AUTH))
        self.assertTrue(again.startswith("goated-hold: security"))
        self.assertIn(self.FULL, again)
        # Near miss: the new turn's own second such hold is short again.
        self.assertNotIn(self.FULL, reason(s.call("Write", self.AUTH)))

    def test_a_hold_that_never_carried_the_advice_is_unchanged(self) -> None:
        commit = {"command": 'git commit -m "Harden login"'}
        (self.root / "fresh").mkdir()
        fresh = Session(self.root / "fresh")
        fresh.prompt("Harden the login check.")
        fresh.load(ROUTER)
        fresh.say("goated-route: direct")
        alone = reason(fresh.call("Bash", commit))
        self.assertTrue(alone.startswith("goated-hold: commit | strict\n"))

        s = self.session
        self.route_line_hold()
        s.say("goated-route: direct")
        self.assertEqual(reason(s.call("Bash", commit)), alone)
        # Near miss: a hold that carries the advice, later in the same turn, is shortened.
        self.assertNotIn(self.FULL, reason(s.call("Write", self.AUTH)))


    def held_in_parallel(self, session: Session, count: int = 4) -> list[str]:
        """Route-line holds on `count` edits made in one message, judged at once."""

        session.prompt("Harden the login check.")
        session.load(ROUTER)
        outputs = session.parallel([("Edit", {}) for _ in range(count)], concurrently=True)
        self.assertEqual([decision(o) for o in outputs], ["deny"] * count)
        return [reason(o) for o in outputs]

    def test_of_four_parallel_holds_exactly_one_gives_the_full_advice(self) -> None:
        held = self.held_in_parallel(self.session)
        self.assertEqual(sum(self.FULL in text for text in held), 1, held)
        for text in held:
            self.assertTrue(text.startswith("goated-hold: route-line | strict\n"), text)
            self.assertIn("`skip routing`", text)
            if self.FULL not in text:
                self.assertIn(self.SHORT, text)
        # Near miss: another session's parallel holds, sharing the state folder,
        # give their own full advice once.
        (self.root / "other").mkdir()
        other = Session(self.root / "other", session_id="session-2")
        other.config = self.session.config
        self.assertEqual(sum(self.FULL in text for text in self.held_in_parallel(other)), 1)

    def test_a_hold_after_parallel_holds_gives_one_sentence_and_the_override(self) -> None:
        s = self.session
        self.held_in_parallel(s)
        s.say("goated-route: direct")
        held = reason(s.call("Write", self.AUTH))
        self.assertTrue(held.startswith("goated-hold: security | justified-skip\n"), held)
        self.assertNotIn(self.FULL, held)
        self.assertIn(self.SHORT, held)
        self.assertIn("`skip code-security-review`", held)
        # Near miss: the next turn's first such hold gives the full text again.
        s.prompt("Also harden the logout check.")
        s.say("goated-route: direct")
        self.assertIn(self.FULL, reason(s.call("Write", self.AUTH)))

    def test_with_the_marker_folder_unwritable_each_hold_gives_the_full_advice(self) -> None:
        s = self.session
        # A file where the marker folder belongs: no marker can be made or read.
        s.config.state_dir.mkdir(parents=True, exist_ok=True)
        (s.config.state_dir / "turn-markers").write_text("", encoding="utf-8")
        s.prompt("Harden the login check.")
        s.load(ROUTER)
        outputs = s.parallel([("Edit", {}) for _ in range(4)], concurrently=True)
        outputs.append(s.call("Edit"))
        for output in outputs:
            self.assertEqual(decision(output), "deny")
            self.assertIn(self.FULL, reason(output))
            # No hook fails open; parallel saves of session state may warn on
            # Windows (README "Known Limits"), which is not this marker.
            self.assertNotIn("allowed without checks", output.get("systemMessage", ""))
        # Near miss: with the folder back, the turn's next such hold claims it
        # and the one after is short.
        (s.config.state_dir / "turn-markers").unlink()
        self.assertIn(self.FULL, reason(s.call("Edit")))
        self.assertNotIn(self.FULL, reason(s.call("Edit")))

    def test_a_hold_without_the_advice_does_not_claim_the_turns_full_advice(self) -> None:
        s = self.session
        s.prompt("Harden the login check.")
        s.load(ROUTER)
        s.say("goated-route: direct")
        commit = {"command": 'git commit -m "Harden login"'}
        alone = reason(s.call("Bash", commit))
        self.assertTrue(alone.startswith("goated-hold: commit | strict\n"), alone)
        self.assertNotIn(self.FULL, alone)
        self.assertNotIn(self.SHORT, alone)
        # Near miss: the advice-carrying hold that follows still gives it in full.
        self.assertIn(self.FULL, reason(s.call("Write", self.AUTH)))

    def subagent_holds(self, agent_id: str, count: int = 2) -> list[str]:
        """Security holds on `count` writes in a new subagent's turn."""

        agent = self.session.subagent(agent_id)
        agent.prompt("Harden the login check.", hook=False)
        return [
            reason(agent.call("Write", self.AUTH, agent_id=agent_id, agent_type="general-purpose"))
            for _ in range(count)
        ]

    def test_a_subagents_first_hold_gives_the_full_advice_and_later_ones_one_sentence(self) -> None:
        self.session.prompt("Delegate the login work.")
        first, later = self.subagent_holds("a1")
        self.assertTrue(first.startswith("goated-hold: security | justified-skip\n"), first)
        self.assertIn(self.FULL, first)
        self.assertNotIn(self.FULL, later)
        self.assertIn(self.SHORT, later)
        self.assertIn("`skip code-security-review`", later)
        # Near miss: another subagent of the same session gives its own full
        # advice once, and the parent's turn still has its own.
        other_first, other_later = self.subagent_holds("a2")
        self.assertIn(self.FULL, other_first)
        self.assertNotIn(self.FULL, other_later)
        s = self.session
        s.load(ROUTER)
        self.assertIn(self.FULL, reason(s.call("Edit")))

    def test_clearing_the_session_drops_its_advice_marker(self) -> None:
        s = self.session
        self.route_line_hold()
        self.subagent_holds("a1", count=1)
        markers = s.config.state_dir / "turn-markers"
        self.assertEqual(len(list(markers.iterdir())), 2)
        s.hook("SessionStart", source="clear")
        self.assertEqual(list(markers.iterdir()), [])


class SpawnTests(AdapterTestCase):
    SPAWN_TOOLS = (
        "Agent",
        "mcp__ccd_session__start_session",
        "mcp__ccd_session__hand_off_to_session",
    )

    def test_spawning_is_held_like_a_write(self) -> None:
        for tool in self.SPAWN_TOOLS:
            with self.subTest(tool=tool):
                (self.root / tool).mkdir()
                s = Session(self.root / tool, session_id=f"spawn-{tool}")
                brief = {"prompt": BRIEF, "remaining_plan": BRIEF}
                s.prompt("Delegate the export work.")
                self.assertEqual(decision(s.call(tool, brief)), "deny")
                s.load(ROUTER)
                self.assertEqual(decision(s.call(tool, brief)), "deny")
                s.say("goated-route: standard | requires: tdd")
                held = s.call(tool, brief)
                self.assertTrue(reason(held).startswith("goated-hold: pipeline"))
                s.load("tdd")
                s.brief_with_handoff()
                self.assertEqual(decision(s.call(tool, brief)), "pass")

    def test_the_settings_snippet_matches_every_gated_tool(self) -> None:
        from goated_adapter import actions, gates

        snippet = json.loads((ADAPTER_DIR / "settings.snippet.json").read_text(encoding="utf-8"))
        matcher = snippet["hooks"]["PreToolUse"][0]["matcher"]
        names = [*gates.GATED_TOOLS, *actions.SPAWN_BRIEF_FIELDS, *actions.FILE_WRITE_TOOLS,
                 "mcp__github__create_pull_request", "mcp__gitlab__create_merge_request",
                 "mcp__github__push_files", "mcp__github__create_or_update_file",
                 "mcp__git__git_commit"]
        for name in names:
            self.assertTrue(re.fullmatch(matcher, name), name)
            self.assertTrue(name in gates.GATED_TOOLS or actions.is_action_tool(name), name)
        self.assertIsNone(re.fullmatch(matcher, "Read"))
        self.assertEqual(
            set(snippet["hooks"]), {"SessionStart", "UserPromptSubmit", "PreToolUse", "Stop"}
        )
        for entries in snippet["hooks"].values():
            self.assertEqual(entries[0]["hooks"][0]["args"], ["<adapter-dir>/goated_hook.py"])


class SessionCardTests(AdapterTestCase):
    """A start_session card runs nothing until the user starts it (spec R7)."""

    START = "mcp__ccd_session__start_session"
    CARD = {"title": "Audit the exporter", "initiation": "own_initiative", "prompt": BRIEF}
    OFFER = {"title": "Audit the exporter", "initiation": "offer"}

    def test_a_proposal_card_passes_routing_and_meets_the_spawn_hold(self) -> None:
        s = self.session
        s.prompt("Fix the flaky export test.")

        held = s.call(self.START, self.CARD)
        self.assertTrue(reason(held).startswith("goated-hold: spawn | strict"), reason(held))
        s.brief_with_handoff()
        self.assertEqual(decision(s.call(self.START, self.CARD)), "pass")
        # Near miss: the same brief started now is a spawn, held by router-first.
        started = s.call(self.START, {**self.CARD, "initiation": "user_asked"})
        self.assertTrue(reason(started).startswith("goated-hold: router-first"))

    def test_a_proposal_card_passes_route_line_and_pipeline(self) -> None:
        s = self.session
        s.prompt("Fix the flaky export test.")
        s.load(ROUTER)
        s.brief_with_handoff()

        self.assertEqual(decision(s.call(self.START, self.CARD)), "pass")
        # Near miss: an Agent spawn with the same brief needs the route line.
        self.assertTrue(reason(s.call("Agent", {"prompt": BRIEF})).startswith("goated-hold: route-line"))

        s.say("goated-route: standard | requires: tdd")
        self.assertEqual(decision(s.call(self.START, self.CARD)), "pass")
        # Near miss: the Agent spawn is held by pipeline.
        self.assertTrue(reason(s.call("Agent", {"prompt": BRIEF})).startswith("goated-hold: pipeline"))

    def test_an_offer_card_passes_every_hold(self) -> None:
        s = self.session
        s.prompt("Fix the flaky export test.")

        self.assertEqual(decision(s.call(self.START, self.OFFER)), "pass")
        # Near miss: an offer that starts a saved proposal starts a session.
        held = s.call(self.START, {**self.OFFER, "proposal_id": "p-1"})
        self.assertTrue(reason(held).startswith("goated-hold: router-first"))

    def test_starts_and_unknown_initiations_are_held_as_spawns(self) -> None:
        cases = {
            "user_asked": {**self.CARD, "initiation": "user_asked"},
            "no initiation": {"title": "Audit", "prompt": BRIEF},
            "unknown initiation": {**self.CARD, "initiation": "later"},
            "saved proposal": {"proposal_id": "p-1", "initiation": "own_initiative"},
            "saved proposal, empty id": {**self.CARD, "proposal_id": ""},
            # Not a string, so not a card: it meets the gates rather than failing open.
            "list initiation": {**self.CARD, "initiation": ["offer"]},
            "dict initiation": {**self.CARD, "initiation": {"kind": "offer"}},
        }
        for name, tool_input in cases.items():
            with self.subTest(case=name):
                (self.root / name).mkdir()
                s = Session(self.root / name, session_id=f"card-{name}")
                s.prompt("Fix the flaky export test.")
                held = s.call(self.START, tool_input)
                self.assertTrue(reason(held).startswith("goated-hold: router-first"), name)

    def test_hand_off_to_session_is_unchanged(self) -> None:
        s = self.session
        s.prompt("Fix the flaky export test.")
        hand_off = {"title": "Audit", "initiation": "own_initiative", "remaining_plan": BRIEF}

        held = s.call("mcp__ccd_session__hand_off_to_session", hand_off)
        self.assertTrue(reason(held).startswith("goated-hold: router-first"))
        # Near miss: the same fields on start_session make a card.
        card = {**hand_off, "prompt": BRIEF}
        self.assertFalse(reason(s.call(self.START, card)).startswith("goated-hold: router-first"))

    def test_a_card_between_route_lines_does_not_start_a_new_task(self) -> None:
        s = self.session
        s.prompt("Fix the flaky export test.")
        s.load(ROUTER)
        s.load("tdd")
        s.say("goated-route: standard | requires: tdd")
        s.call(self.START, self.OFFER)
        s.say("goated-route: standard | requires: tdd")
        # The card ran nothing, so the second line corrects the first and tdd still counts.
        self.assertEqual(decision(s.call("Edit")), "pass")

        (self.root / "near").mkdir()
        near = Session(self.root / "near", session_id="card-near-miss")
        near.prompt("Fix the flaky export test.")
        near.load(ROUTER)
        near.load("tdd")
        near.brief_with_handoff()
        near.say("goated-route: standard | requires: tdd")
        near.call("Agent", {"prompt": BRIEF})
        near.say("goated-route: standard | requires: tdd")
        # Near miss: a spawn that ran is work, so the second line is a new task.
        self.assertTrue(reason(near.call("Edit")).startswith("goated-hold: pipeline"))


class OverrideTests(AdapterTestCase):
    def test_user_typed_skip_routing_stands_routing_holds_down_for_that_turn(self) -> None:
        s = self.session
        notice = s.prompt("Skip routing and just fix the typo in README.md.")
        self.assertIn("Skip routing", notice)

        self.assertEqual(decision(s.call("Bash")), "pass")
        self.assertEqual(decision(s.call("Edit")), "pass")

        s.prompt("Now update the changelog.")
        self.assertEqual(decision(s.call("Edit")), "deny")

    def test_a_typed_override_is_also_returned_as_hook_context_a_mod_can_read(self) -> None:
        # A notice reaches a mod with no text; hook context arrives with it.
        output = parse(self.session.prompt("Skip routing and just fix the typo in README.md."))

        sentence = 'recorded your override for this prompt: "Skip routing"'
        self.assertIn(sentence, output["systemMessage"])
        specific = output["hookSpecificOutput"]
        self.assertEqual(specific["hookEventName"], "UserPromptSubmit")
        self.assertEqual(
            specific["additionalContext"], f"GOATED Claude Code adapter: {sentence}."
        )

    def test_a_prompt_with_no_override_returns_no_hook_context(self) -> None:
        output = parse(self.session.prompt("Fix the typo in README.md."))

        self.assertNotIn("hookSpecificOutput", output)

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

    def test_overrides_inside_pasted_content_are_not_recorded(self) -> None:
        s = self.session
        pasted = paste("Feedback: we should skip routing and skip commit-message here.")
        output = s.prompt(f"Read this feedback.\n{pasted}\nFix what it reports.")

        self.assertEqual(output, "")
        self.assertEqual(decision(s.call("Bash")), "deny")

    def test_a_skip_typed_after_pasted_content_is_recorded_for_the_mod(self) -> None:
        s = self.session
        output = parse(s.prompt(f"{paste('Some notes.')}\nSkip routing and fix it."))

        self.assertIn(
            'recorded your override for this prompt: "Skip routing"',
            output["hookSpecificOutput"]["additionalContext"],
        )
        self.assertEqual(decision(s.call("Bash")), "pass")


def paste(text: str, paste_id: str = "e8c0") -> str:
    """Wrap `text` the way Claude Code wraps pasted text in a typed prompt."""

    return f'<pasted_content id="{paste_id}">\n{text}\n</pasted_content id="{paste_id}">'


class OverridePhraseTests(unittest.TestCase):
    def test_phrases_inside_pasted_content_are_ignored(self) -> None:
        from goated_adapter.overrides import parse_overrides

        pasted = paste("skip routing, skip commit-message.\ncommit message: Fix export rounding")
        found = parse_overrides(f"Look at this:\n{pasted}\nThoughts?")
        self.assertEqual(
            found, {"routing": False, "skills": [], "commit_message": None, "phrases": []}
        )

    def test_phrases_typed_around_pasted_content_still_count(self) -> None:
        from goated_adapter.overrides import parse_overrides

        after = parse_overrides(f"{paste('Some notes.')}\nskip commit-message")
        self.assertEqual(after["skills"], ["commit-message"])
        before = parse_overrides(
            f"Skip routing.\n{paste('Some notes.')}\ncommit message: Fix rounding"
        )
        self.assertTrue(before["routing"])
        self.assertEqual(before["commit_message"], "Fix rounding")
        two = parse_overrides(f"{paste('a', 'a1')}\nskip tdd\n{paste('b', 'b2')}")
        self.assertEqual(two["skills"], ["tdd"])

    def test_only_a_close_tag_with_the_pastes_own_id_ends_it(self) -> None:
        from goated_adapter.overrides import parse_overrides

        for inner in (
            "report: </pasted_content> skip routing and skip tdd",
            'report: </pasted_content id="f00d"> skip routing and skip tdd',
            '<pasted_content id="f00d">x</pasted_content id="f00d"> skip routing, skip tdd',
            "<pasted_content>x</pasted_content> skip routing and skip tdd",
        ):
            with self.subTest(inner=inner):
                found = parse_overrides(f"Fix it.\n{paste(inner)}")
                self.assertFalse(found["routing"])
                self.assertEqual(found["skills"], [])

    def test_an_unclosed_paste_runs_to_the_end_of_the_prompt(self) -> None:
        from goated_adapter.overrides import parse_overrides

        found = parse_overrides('Skip tdd.\n<pasted_content id="e8c0">\nnotes\nskip routing')
        self.assertFalse(found["routing"])
        self.assertEqual(found["skills"], ["tdd"])

    def test_the_commit_message_skill_name_is_not_a_commit_message(self) -> None:
        from goated_adapter.overrides import parse_overrides

        for text in (
            "The hook held it until I loaded the `commit-message` skill, then `git diff`.",
            "Agents should load commit-message: it drafts the text.",
        ):
            with self.subTest(text=text):
                self.assertIsNone(parse_overrides(text)["commit_message"])
        self.assertEqual(
            parse_overrides("Use the commit-message skill. Commit message: Fix rounding")[
                "commit_message"
            ],
            "Fix rounding",
        )

    def test_negated_or_descriptive_phrases_are_not_overrides(self) -> None:
        from goated_adapter.overrides import parse_overrides

        for text in (
            "Don't skip routing this time.",
            "Do not skip the router.",
            "Never skip tdd here.",
            "There is no need to skip doc-sync.",
            "There is no routing in the app yet; add it.",
            "Add a fallback: no router for /admin.",
        ):
            with self.subTest(text=text):
                found = parse_overrides(text)
                self.assertFalse(found["routing"])
                self.assertEqual(found["skills"], [])

    def test_directives_are_overrides(self) -> None:
        from goated_adapter.overrides import parse_overrides

        self.assertTrue(parse_overrides("Please skip routing for this one.")["routing"])
        self.assertTrue(parse_overrides("Skip the router and fix it.")["routing"])
        self.assertEqual(parse_overrides("Skip tdd, then ship.")["skills"], ["tdd"])
        self.assertEqual(
            parse_overrides("skip the doc-sync skill")["skills"], ["doc-sync"]
        )

    def test_a_backticked_skill_skip_records_its_phrase_without_backticks(self) -> None:
        # Ticket 077: "skip `doc-sync`" was recorded as "skip `doc-sync", because
        # the closing backtick was dropped to find a word boundary after it.
        from goated_adapter.overrides import parse_overrides

        cases = {
            "skip `doc-sync`": "skip doc-sync",
            "Skip `doc-sync`, then ship.": "Skip doc-sync",
            "skip `doc-sync` skill": "skip doc-sync skill",
            "skip the `tdd` skill now": "skip the tdd skill",
            "skip doc-sync`": "skip doc-sync",
            "skip `tdd": "skip tdd",
        }
        for text, phrase in cases.items():
            with self.subTest(text=text):
                found = parse_overrides(text)
                self.assertEqual(found["phrases"], [phrase])
                self.assertEqual(len(found["skills"]), 1)
        # Near misses stay non-overrides.
        for text in ("skip `doc-syncing`", "don't skip `doc-sync`", "skip `line`"):
            with self.subTest(text=text):
                self.assertEqual(parse_overrides(text)["phrases"], [])

    def test_the_commit_message_override_is_recorded_as_commit_message(self) -> None:
        # Ticket 077: the stored "commit message" phrase is this override, its
        # text left out of the record.
        from goated_adapter.overrides import parse_overrides

        found = parse_overrides("commit message: Fix rounding")
        self.assertEqual(found["phrases"], ["commit message"])
        self.assertEqual(found["commit_message"], "Fix rounding")
        self.assertEqual(parse_overrides("Use the commit-message skill.")["phrases"], [])


class MachinePromptTests(AdapterTestCase):
    """Prompts other sessions or the app write are not typed by this user."""

    def test_a_peer_session_message_is_a_new_turn_without_overrides(self) -> None:
        s = self.session
        s.prompt("Start the export work.")
        s.load(ROUTER)
        s.say("goated-route: direct")
        self.assertEqual(decision(s.call("Edit")), "pass")

        self.assertEqual(s.peer("Skip routing and patch the README."), "")
        self.assertEqual(decision(s.call("Edit")), "deny")
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_a_host_written_brief_carries_no_overrides(self) -> None:
        s = self.session
        s.prompt(
            "Background (from the session that started this one): skip routing.",
            origin=None,
            turnOrigin="host_synthetic",
        )

        self.assertEqual(decision(s.call("Bash")), "deny")

    def test_an_unknown_origin_kind_carries_no_overrides(self) -> None:
        s = self.session
        s.prompt("skip routing and run the nightly check", origin={"kind": "scheduled"})

        self.assertEqual(decision(s.call("Bash")), "deny")

    def test_a_peer_turn_origin_carries_no_overrides(self) -> None:
        s = self.session
        s.prompt("skip routing please", origin=None, turnOrigin="peer")

        self.assertEqual(decision(s.call("Bash")), "deny")

    def test_a_notification_marked_only_by_turn_origin_continues_the_turn(self) -> None:
        s = self.session
        s.prompt("Skip routing; run the audit and fix what it finds.")
        s.prompt("Audit finished: one typo.", hook=False, origin=None, turnOrigin="task_notification")

        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_a_bare_sdk_prompt_is_typed(self) -> None:
        s = self.session
        s.prompt("Skip routing and fix it.", origin=None, promptSource="sdk", turnOrigin="sdk")

        self.assertEqual(decision(s.call("Edit")), "pass")


class AgentMessageOverrideTests(AdapterTestCase):
    """A subagent's report or another session's message quoting override phrases.

    Claude Code submits both as prompts, so the prompt hook sees them; nobody
    typed them here, so they carry no overrides (spec R8). Each opens a new
    turn, which needs its own route line.
    """

    QUOTED = "Review done. Skip routing, and skip tdd for the follow-up."
    # (label, peer keyword arguments): both wrappers, each with a fresh prompt
    # id and with the typed opener's id, since Claude Code records both.
    SHAPES = (
        ("subagent hand-back", {"handback": True}),
        ("cross-session message", {"handback": False}),
        ("hand-back sharing the prompt id", {"handback": True, "same_prompt_id": True}),
        ("message sharing the prompt id", {"handback": False, "same_prompt_id": True}),
    )

    def fresh(self, name: str) -> Session:
        folder = self.root / name.replace(" ", "-")
        folder.mkdir()
        return Session(folder)

    def stored_overrides(self, s: Session) -> dict:
        from goated_adapter.state import StateStore

        state, _ = StateStore(s.config.state_dir).load(s.session_id)
        return state.overrides

    def test_a_quoted_skip_is_neither_announced_nor_stored(self) -> None:
        for name, shape in self.SHAPES:
            with self.subTest(name):
                s = self.fresh(name)
                s.prompt("Start the export work.")

                self.assertEqual(s.peer(self.QUOTED, **shape), "")
                stored = self.stored_overrides(s)
                self.assertFalse(stored.get("routing"))
                self.assertEqual(stored.get("skills", []), [])
                self.assertEqual(stored.get("phrases", []), [])

    def test_holds_a_typed_skip_would_clear_still_hold(self) -> None:
        for name, shape in self.SHAPES:
            with self.subTest(name):
                s = self.fresh(name)
                s.prompt("Start the export work.")
                s.peer(self.QUOTED, **shape)

                self.assertEqual(decision(s.call("Bash")), "deny")
                s.load(ROUTER)
                s.say("goated-route: standard | requires: tdd")
                self.assertEqual(decision(s.call("Edit")), "deny")

    def test_the_same_words_typed_are_announced_and_applied(self) -> None:
        s = self.session
        notice = parse(s.prompt(self.QUOTED))["systemMessage"]
        self.assertIn('recorded your override for this prompt: "Skip routing", "skip tdd"', notice)

        self.assertEqual(decision(s.call("Bash")), "pass")
        s.load(ROUTER)
        s.say("goated-route: standard | requires: tdd")
        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_a_typed_override_does_not_cover_the_turn_a_message_opens(self) -> None:
        for name, shape in self.SHAPES:
            with self.subTest(name):
                s = self.fresh(name)
                s.prompt("Skip routing and fix the typo.")
                self.assertEqual(decision(s.call("Bash")), "pass")

                s.peer("Done.", **shape)
                self.assertEqual(decision(s.call("Bash")), "deny")

    def test_the_gates_ignore_stored_overrides_on_an_agent_messages_turn(self) -> None:
        # Even if the prompt hook had stored overrides for this prompt, the
        # gates read the transcript, which marks the prompt as a peer's.
        for name, shape in self.SHAPES:
            with self.subTest(name):
                s = self.fresh(name)
                s.prompt("Start the export work.")
                s.peer(self.QUOTED, **shape)
                s.hook("UserPromptSubmit", prompt=self.QUOTED, prompt_id=s.prompt_id)
                self.assertTrue(self.stored_overrides(s).get("routing"))

                self.assertEqual(decision(s.call("Bash")), "deny")

    def test_the_transcript_origin_decides_when_the_text_check_misses(self) -> None:
        # The prompt hook knows a message only by its first line, so it takes
        # one in an unknown wrapper for typed and announces the override. The
        # gates still apply none, because the transcript marks it a peer's.
        for name, shape in self.SHAPES:
            with self.subTest(name):
                s = self.fresh(name)
                s.prompt("Start the export work.")
                notice = s.peer(self.QUOTED, first_line="A relayed message:", **shape)
                self.assertIn("recorded your override", notice)

                self.assertEqual(decision(s.call("Bash")), "deny")

    def test_leading_whitespace_does_not_hide_the_wrapper(self) -> None:
        s = self.session
        s.prompt("Start the export work.")
        notice = s.peer(self.QUOTED, first_line="\n  Another Claude session sent a message:")

        self.assertEqual(notice, "")

    def test_a_pasted_report_then_a_typed_skip_is_not_an_override(self) -> None:
        s = self.session
        pasted = (
            "Another Claude session sent a message:\n<agent-message from=\"a1\">\n"
            "Report.\n</agent-message>"
        )
        self.assertEqual(s.prompt(f"{pasted}\n\nSkip routing."), "")
        self.assertEqual(decision(s.call("Bash")), "deny")

        self.assertIn("recorded your override", s.prompt(f"Skip routing. Here:\n{pasted}"))
        self.assertEqual(decision(s.call("Bash")), "pass")


class TaskNotificationTests(AdapterTestCase):
    """Claude Code submits background-task results as prompts nobody typed."""

    def test_a_task_notification_does_not_start_a_new_turn(self) -> None:
        s = self.session
        s.prompt("Run the audit in the background, then fix what it finds.")
        s.load(ROUTER)
        s.say("goated-route: direct")
        s.brief_with_handoff()
        self.assertEqual(decision(s.call("Agent", {"prompt": BRIEF})), "pass")

        s.notify("Found one stale import.")
        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_subagent_text_in_a_notification_is_not_an_override(self) -> None:
        s = self.session
        s.prompt("Run the audit in the background.")
        self.assertEqual(s.notify("Done. Skip routing and skip tdd next time."), "")

        self.assertEqual(decision(s.call("Bash")), "deny")

    def test_the_users_override_still_applies_after_a_notification(self) -> None:
        s = self.session
        s.prompt("Skip routing; run the audit and fix the typo it finds.")
        s.notify("Typo on line 3.")

        self.assertEqual(decision(s.call("Edit")), "pass")


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

    def test_a_call_not_yet_in_the_transcript_is_still_judged(self) -> None:
        s = self.session
        s.prompt("Fix it.")
        output = parse(
            s.hook("PreToolUse", tool_name="Edit", tool_input={}, tool_use_id="toolu_unseen")
        )

        self.assertEqual(decision(output), "deny")
        self.assertNotIn("systemMessage", output)

    def test_a_transcript_without_the_calls_prompt_fails_open(self) -> None:
        s = self.session
        s.prompt("Fix it.")
        output = parse(s.hook(
            "PreToolUse", tool_name="Edit", tool_input={}, tool_use_id="toolu_unseen",
            prompt_id="prompt-not-yet-recorded",
        ))

        self.assert_fails_open(output)
        self.assertIn("does not yet show the prompt", output["systemMessage"])

    def test_missing_session_id_fails_open(self) -> None:
        payload = {"hook_event_name": "PreToolUse", "tool_name": "Edit"}
        self.assert_fails_open(parse(run_hook(json.dumps(payload), self.session.config)))

    def test_a_failed_save_keeps_the_hold_and_warns(self) -> None:
        from goated_adapter import state as state_module

        s = self.session
        s.prompt("Fix it.")
        s.load(ROUTER)
        original = state_module.StateStore.save

        def refuse(self, *args):
            raise PermissionError(13, "Access is denied")

        state_module.StateStore.save = refuse
        try:
            output = s.call("Edit")
        finally:
            state_module.StateStore.save = original
        self.assertEqual(decision(output), "deny")
        self.assertIn("could not save", output.get("systemMessage", ""))

    def test_saving_retries_a_briefly_locked_state_file(self) -> None:
        from goated_adapter import state as state_module

        store = state_module.StateStore(self.root / "retry-state")
        saved = state_module.SessionState()
        saved.router_loaded = True
        real_replace = os.replace
        failures = [PermissionError(13, "in use"), PermissionError(13, "in use")]

        def flaky_replace(src, dst):
            if failures:
                raise failures.pop()
            real_replace(src, dst)

        state_module.os.replace = flaky_replace
        try:
            store.save("s1", saved)
        finally:
            state_module.os.replace = real_replace
        loaded, warning = store.load("s1")
        self.assertIsNone(warning)
        self.assertTrue(loaded.router_loaded)

    def test_state_with_the_wrong_shape_resets_and_re_holds(self) -> None:
        s = self.session
        s.prompt("Fix it.")
        s.load(ROUTER)
        s.say("goated-route: lightweight | requires: tdd")
        self.assertEqual(decision(s.call("Edit")), "deny")
        s.prompt("Go on.")
        s.load(ROUTER)
        s.say("goated-route: continue")
        s.config.state_dir.mkdir(parents=True, exist_ok=True)
        for bad in (
            {"router_loaded": True, "task": {"route": [], "started_turn": "x"}},
            {"router_loaded": True, "task": {"route": {"form": "route"}, "started_turn": "x"}},
            {"router_loaded": True, "overrides": ["skip"]},
            {"router_loaded": "yes"},
        ):
            with self.subTest(bad=bad):
                (s.config.state_dir / "session-1.json").write_text(json.dumps(bad))
                first = s.call("Edit")
                self.assertIn("was reset", first.get("systemMessage", ""))
                self.assertEqual(decision(first), "deny")
                second = s.call("Edit")
                self.assertNotIn("allowed without checks", second.get("systemMessage", ""))

    def test_a_long_run_of_unseen_turns_does_not_fail_open_forever(self) -> None:
        from goated_adapter import transcript

        limits = transcript.MAX_BYTES, transcript.BLOCK_SIZE
        transcript.MAX_BYTES, transcript.BLOCK_SIZE = 8 * 1024, 1024
        try:
            s = self.session
            s.prompt("Task one.")
            s.load(ROUTER)
            s.say("goated-route: direct")
            self.assertEqual(decision(s.call("Edit")), "pass")
            s.prompt("Explain the module.")
            for index in range(6):
                tool_use_id = s._tool_use("Read", {"file_path": f"f{index}"})
                s._tool_result(tool_use_id, "x" * 3000)

            s.prompt("Now change it.")
            third = s.call("Edit")
            self.assertEqual(decision(third), "deny")
            self.assertNotIn("systemMessage", third)
            s.say("goated-route: continue")
            self.assertEqual(decision(s.call("Edit")), "pass")
        finally:
            transcript.MAX_BYTES, transcript.BLOCK_SIZE = limits

    def test_a_current_turn_larger_than_the_limit_fails_open(self) -> None:
        from goated_adapter import transcript

        limits = transcript.MAX_BYTES, transcript.BLOCK_SIZE
        transcript.MAX_BYTES, transcript.BLOCK_SIZE = 8 * 1024, 1024
        try:
            s = self.session
            s.prompt("Do a lot.")
            for index in range(6):
                tool_use_id = s._tool_use("Read", {"file_path": f"f{index}"})
                s._tool_result(tool_use_id, "x" * 3000)
            self.assert_fails_open(s.call("Edit"))
        finally:
            transcript.MAX_BYTES, transcript.BLOCK_SIZE = limits

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
        held = s.call("Edit")
        self.assertEqual(decision(held), "deny")
        self.assertIn("`tdd`", reason(held))
        s.load("tdd")
        self.assertEqual(decision(s.call("Edit")), "pass")

    def trial_session_compacted(self) -> Session:
        """The Ticket 033 trial shape: a task needing `commit-message`, a
        `continue` turn, then a new prompt that an auto-compaction followed
        before the reply."""

        s = self.session
        s.prompt("Close ticket 040.")
        s.load(ROUTER)
        s.say("goated-route: standard | requires: commit-message")
        s.load("commit-message")
        self.assertEqual(decision(s.call("Edit")), "pass")
        s.prompt("Push main.")
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Edit")), "pass")
        s.prompt("I found a real bug when the model loads skills.")
        s.compact()
        return s

    def test_direct_after_compaction_and_continue_clears_the_earlier_pipeline(
        self,
    ) -> None:
        s = self.trial_session_compacted()
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Bash")), "deny")
        s.load(ROUTER)
        for _ in range(2):
            held = s.call("Edit")
            self.assertTrue(reason(held).startswith("goated-hold: pipeline | strict"))
            self.assertIn("`commit-message`", reason(held))

        s.say("goated-route: direct")
        self.assertEqual(decision(s.call("Edit")), "pass")

    def test_the_route_carries_over_a_compaction_into_a_later_continue_turn(
        self,
    ) -> None:
        s = self.trial_session_compacted()
        s.load(ROUTER)
        s.say("Summary read; picking the work back up.")
        s.hook("Stop")
        s.prompt("Carry on.")
        s.say("goated-route: continue")
        held = s.call("Edit")
        self.assertIn("`commit-message`", reason(held))
        s.load("commit-message")
        self.assertEqual(decision(s.call("Edit")), "pass")


class SharedPolicyNoticeTests(AdapterTestCase):
    POLICY = "# GOATED Integrated Stack Policy\n\nApply this shared policy.\n"

    def setUp(self) -> None:
        super().setUp()
        self.router_skill = self.root / "home" / ".claude" / "skills" / ROUTER
        self.router_skill.mkdir(parents=True)
        (self.router_skill / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")

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

    def test_unc_and_outside_imports_are_not_opened(self) -> None:
        from goated_adapter import policy

        project = self.session.project
        project.mkdir(parents=True)
        outside = self.root / "elsewhere"
        outside.mkdir()
        (outside / "policy.md").write_text(self.POLICY, encoding="utf-8")
        (project / "CLAUDE.md").write_text(
            "@\\\\attacker-host\\share\\policy.md\n@//attacker-host/share/policy.md\n"
            f"@{outside / 'policy.md'}\n",
            encoding="utf-8",
        )
        opened: list[str] = []
        real_read = policy._read

        def spy(path):
            opened.append(str(path))
            return real_read(path)

        policy._read = spy
        try:
            self.assertFalse(policy.shared_policy_loaded(project, self.root / "home"))
        finally:
            policy._read = real_read
        self.assertFalse(any("attacker-host" in path for path in opened), opened)
        self.assertFalse(any("elsewhere" in path for path in opened), opened)

    def test_an_import_through_a_link_is_not_opened(self) -> None:
        from goated_adapter import policy

        project = self.session.project
        project.mkdir(parents=True)
        outside = self.root / "elsewhere"
        outside.mkdir()
        (outside / "policy.md").write_text(self.POLICY, encoding="utf-8")
        link = project / "linked"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("this platform does not allow creating symlinks here")
        (project / "CLAUDE.md").write_text("@linked/policy.md\n", encoding="utf-8")

        try:
            self.assertFalse(policy.shared_policy_loaded(project, self.root / "home"))
        finally:
            # Remove the link itself before the temporary folder is cleaned:
            # on Windows, Python 3.11's rmtree does not treat a directory link
            # as a link. `rmdir` removes a Windows directory link without
            # following it; elsewhere a link is removed with `unlink`.
            if os.name == "nt":
                os.rmdir(link)
            else:
                os.unlink(link)
        self.assertTrue((outside / "policy.md").exists())

    def test_missing_router_skill_is_warned_about_at_session_start(self) -> None:
        (self.router_skill / "SKILL.md").unlink()

        output = self.start()
        self.assertIn("could not find", output["systemMessage"])
        self.assertIn("using-goated-ai-skills", output["systemMessage"])
        self.assertIn("skip routing", output["systemMessage"])

    def test_router_skill_in_the_project_is_found(self) -> None:
        (self.router_skill / "SKILL.md").unlink()
        project_skill = self.session.project / ".claude" / "skills" / ROUTER
        project_skill.mkdir(parents=True)
        (project_skill / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")

        output = self.start()
        self.assertNotIn("could not find", output.get("systemMessage", ""))

    def test_policy_imported_from_claude_md_is_detected(self) -> None:
        project = self.session.project
        (project / "goated").mkdir(parents=True)
        (project / "goated" / "policy.md").write_text(self.POLICY, encoding="utf-8")
        (project / "CLAUDE.md").write_text("@goated/policy.md\n", encoding="utf-8")

        self.assertEqual(self.start(), {})


class StateFolderDefaultTests(unittest.TestCase):
    def config_with(self, env: dict) -> Config:
        clean = {k: v for k, v in os.environ.items() if k not in {"GOATED_ADAPTER_STATE_DIR", "XDG_STATE_HOME"}}
        clean.update(env)
        with mock.patch.dict(os.environ, clean, clear=True):
            return Config.from_environment()

    def test_an_explicit_state_folder_wins(self) -> None:
        config = self.config_with({"GOATED_ADAPTER_STATE_DIR": "/custom/state"})
        self.assertEqual(config.state_dir, Path("/custom/state"))

    @unittest.skipIf(os.name == "nt", "POSIX default")
    def test_posix_default_is_per_user_and_outside_shared_tmp(self) -> None:
        self.assertEqual(
            self.config_with({"XDG_STATE_HOME": "/xdg/state"}).state_dir,
            Path("/xdg/state/goated-claude-code-adapter"),
        )
        default = self.config_with({}).state_dir
        self.assertEqual(default, Path.home() / ".local" / "state" / "goated-claude-code-adapter")

    @unittest.skipUnless(os.name == "nt", "Windows default")
    def test_windows_default_is_the_per_user_temp_folder(self) -> None:
        config = self.config_with({"TEMP": "C:/Temp/u"})
        self.assertEqual(config.state_dir, Path("C:/Temp/u/goated-claude-code-adapter"))


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

    def test_adapter_parser_agrees_with_the_design_reads_fixtures(self) -> None:
        from goated_adapter import markers

        data = yaml.safe_load(DESIGN_READS_FIXTURES.read_text(encoding="utf-8"))
        for case in data["design_reads_lines"]["valid"]:
            self.assertEqual(markers.parse_design_reads_line(case["line"]), case["expect"], case["line"])
        for case in data["design_reads_lines"]["invalid"]:
            self.assertIsNone(markers.parse_design_reads_line(case["line"]), case["line"])
        for reply in data["design_reads_replies"]:
            parsed = markers.parse_reply(reply["text"])
            self.assertEqual(
                {
                    "files": markers.declared_files(parsed.design_reads),
                    "lines": parsed.design_reads,
                    "malformed": parsed.malformed_design_reads,
                },
                reply["expect"],
                reply["identifier"],
            )
            # Design-reads lines stay out of the route and skip lines' malformed list.
            self.assertFalse(any("design-reads" in line.lower() for line in parsed.malformed))


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
