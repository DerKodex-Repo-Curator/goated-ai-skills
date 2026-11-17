"""Behavior tests for the adapter's notices that never block (Ticket 073).

The retrospective notice follows a session's friction count: holds declined
by a skip line or left unanswered at the next typed prompt. The onboarding
notice names the onboarding skill for each agent file a project lacks, once
per project. Both drive the adapter's single hook entry point with synthetic
sessions in Claude Code's recorded shape (see `claude_code_adapter_support.py`).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from claude_code_adapter_support import ROUTER, Session, decision, parse

SECURITY = "code-security-review"
SENSITIVE_EDIT = {"file_path": "src/auth/login.py", "old_string": "a", "new_string": "b"}
RETROSPECTIVE = "`retrospective`"


def context_of(output: dict) -> str:
    return output.get("hookSpecificOutput", {}).get("additionalContext", "")


class NoticeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.session = Session(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()


class RetrospectiveNoticeTests(NoticeTestCase):
    def held_turn(self, prompt: str = "Change the login check.") -> dict:
        """One typed turn whose sensitive edit the security gate holds; returns
        the parsed output of the prompt that opened it."""

        s = self.session
        output = parse(s.prompt(prompt))
        s.load(ROUTER)
        s.say("goated-route: direct")
        self.assertEqual(decision(s.call("Edit", SENSITIVE_EDIT)), "deny")
        return output

    def assert_notice(self, output: dict) -> None:
        self.assertIn(RETROSPECTIVE, output.get("systemMessage", ""))
        self.assertIn(RETROSPECTIVE, context_of(output))

    def assert_no_notice(self, output: dict) -> None:
        self.assertNotIn(RETROSPECTIVE, output.get("systemMessage", ""))
        self.assertNotIn(RETROSPECTIVE, context_of(output))

    def test_three_unanswered_holds_bring_the_notice_once_at_the_next_prompt(self) -> None:
        for _ in range(3):
            self.assert_no_notice(self.held_turn())
        self.assert_notice(self.held_turn())
        # A fourth hold, and a fifth, bring no second notice.
        self.assert_no_notice(self.held_turn())
        self.assert_no_notice(parse(self.session.prompt("And the rest.")))

    def test_two_unanswered_holds_bring_none(self) -> None:
        self.held_turn()
        self.held_turn()
        self.assert_no_notice(parse(self.session.prompt("Carry on.")))

    def test_declined_holds_count_and_the_notice_waits_for_the_next_prompt(self) -> None:
        s = self.session
        for _ in range(3):
            self.held_turn()
            s.say(f"goated-skip: {SECURITY}: only a comment typo in the file")
            # The notice never blocks: the declined edit goes through.
            self.assertEqual(decision(s.call("Edit", SENSITIVE_EDIT)), "pass")
        self.assertNotIn(RETROSPECTIVE, parse(s.hook("Stop")).get("systemMessage", ""))
        self.assert_notice(parse(s.prompt("Next task.")))

    def test_a_hold_repeated_in_one_turn_counts_once(self) -> None:
        s = self.session
        self.held_turn()
        for _ in range(3):
            self.assertEqual(decision(s.call("Edit", SENSITIVE_EDIT)), "deny")
        self.held_turn()
        self.assert_no_notice(parse(s.prompt("Carry on.")))

    def test_holds_answered_by_a_load_do_not_count(self) -> None:
        s = self.session
        for _ in range(3):
            self.held_turn()
            s.load(SECURITY)
            self.assertEqual(decision(s.call("Edit", SENSITIVE_EDIT)), "pass")
            # A load counts until compaction, so the next turn holds again only after one.
            s.compact()
        self.assert_no_notice(parse(s.prompt("Next task.")))

    def test_a_hold_answered_by_a_read_does_not_count(self) -> None:
        s = self.session
        self.held_turn()
        self.held_turn()
        references = "D:\\goated\\skills\\software-design-principles\\references\\"
        new_code = {"file_path": "src/export.py", "content": "def export(rows):\n    return rows\n" * 4}
        s.prompt("Add the exporter.")
        s.say("goated-route: direct")
        s.load("software-design-principles")
        s.say("goated-design-reads: none: no condition holds here")
        self.assertEqual(decision(s.call("Write", new_code)), "deny")
        # The reads end the turn: no hook runs after them before the next prompt.
        for name in ("process.md", "complexity-and-modules.md", "readability.md"):
            s.read(references + name)
        # Two unanswered and one answered: the near miss of three.
        self.assert_no_notice(parse(s.prompt("Next task.")))

    def test_holds_a_typed_override_stands_down_do_not_count(self) -> None:
        s = self.session
        outputs = []
        for _ in range(3):
            self.held_turn()
            # The next prompt stands the open hold down, and holds nothing itself.
            outputs.append(parse(s.prompt(f"Skip {SECURITY}, it is a comment fix.")))
            s.say("goated-route: direct")
            self.assertEqual(decision(s.call("Edit", SENSITIVE_EDIT)), "pass")
        for output in outputs:
            self.assert_no_notice(output)

    def test_an_override_for_another_skill_stands_nothing_down(self) -> None:
        s = self.session
        outputs = []
        for _ in range(3):
            self.held_turn()
            outputs.append(parse(s.prompt("Skip tdd for this one.")))
        self.assert_notice(outputs[-1])


AGENT_FILES = {
    "AGENTS.md": "agent-instructions-integrator",
    "docs/agents/context-matrix.md": "context-matrix-map",
    "docs/agents/project-standards.md": "project-standards-calibration",
}


class OnboardingNoticeTests(NoticeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.project = self.session.project
        self.project.mkdir(parents=True)
        self.starts = 0

    def write(self, *paths: str) -> None:
        for path in paths:
            target = self.project / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# Notes\n", encoding="utf-8")

    def start(self) -> dict:
        """Start a new session in the project; return its parsed SessionStart output."""

        self.starts += 1
        session = Session(self.root, session_id=f"start-{self.starts}")
        return parse(session.hook("SessionStart", source="startup"))

    def onboarding_text(self, output: dict) -> str:
        """The onboarding sentence of a start's context, or "" when it has none."""

        context = context_of(output)
        return context if "onboarding" in context else ""

    def test_a_project_with_no_instruction_file_is_noticed_once(self) -> None:
        self.write("docs/agents/context-matrix.md", "docs/agents/project-standards.md")

        first = self.start()
        text = self.onboarding_text(first)
        self.assertIn("`agent-instructions-integrator`", text)
        self.assertIn("`AGENTS.md`", text)
        self.assertNotIn("`context-matrix-map`", text)
        self.assertNotIn("`project-standards-calibration`", text)
        self.assertIn("agent-instructions-integrator", first.get("systemMessage", ""))
        # A second session in the same project gets none.
        self.assertEqual(self.onboarding_text(self.start()), "")

    def test_a_project_with_all_three_files_gets_none(self) -> None:
        self.write(*AGENT_FILES)
        self.assertEqual(self.onboarding_text(self.start()), "")

    def test_claude_md_counts_as_the_instruction_file(self) -> None:
        self.write("CLAUDE.md", "docs/agents/context-matrix.md", "docs/agents/project-standards.md")
        self.assertEqual(self.onboarding_text(self.start()), "")

    def test_each_missing_file_names_its_skill(self) -> None:
        text = self.onboarding_text(self.start())
        for path, skill in AGENT_FILES.items():
            with self.subTest(path=path):
                self.assertIn(f"`{path}`", text)
                self.assertIn(f"`{skill}`", text)

    def test_a_file_going_missing_shows_the_notice_again_once(self) -> None:
        self.write("docs/agents/context-matrix.md", "docs/agents/project-standards.md")
        self.assertIn("agent-instructions-integrator", self.onboarding_text(self.start()))

        (self.project / "docs/agents/context-matrix.md").unlink()
        again = self.onboarding_text(self.start())
        self.assertIn("`context-matrix-map`", again)
        self.assertIn("`agent-instructions-integrator`", again)
        self.assertEqual(self.onboarding_text(self.start()), "")

    def test_a_file_added_back_brings_no_notice(self) -> None:
        self.write("docs/agents/project-standards.md")
        self.assertIn("context-matrix-map", self.onboarding_text(self.start()))

        self.write("docs/agents/context-matrix.md")
        self.assertEqual(self.onboarding_text(self.start()), "")

    def test_another_project_is_noticed_on_its_own(self) -> None:
        self.assertNotEqual(self.onboarding_text(self.start()), "")
        other = Session(self.root, session_id="elsewhere")
        other.cwd = self.root / "home" / "work" / "other"
        other.cwd.mkdir(parents=True)
        self.assertNotEqual(self.onboarding_text(parse(other.hook("SessionStart", source="startup"))), "")

    def test_notices_never_block_and_write_nothing_in_the_project(self) -> None:
        before = sorted(self.project.rglob("*"))
        output = self.start()
        self.assertNotEqual(self.onboarding_text(output), "")
        self.assertNotIn("decision", output)
        self.assertNotIn("permissionDecision", output.get("hookSpecificOutput", {}))
        # The retrospective notice reaches its prompt without blocking either.
        s = self.session
        for _ in range(4):
            s.prompt("Change the login check.")
            s.load(ROUTER)
            s.say("goated-route: direct")
            self.assertEqual(decision(s.call("Edit", SENSITIVE_EDIT)), "deny")
        self.assertNotIn("decision", parse(s.hook("Stop")))
        self.assertEqual(sorted(self.project.rglob("*")), before)
