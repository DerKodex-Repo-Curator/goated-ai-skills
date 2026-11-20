"""Ticket 065: a skill load, and a spawn-template read, count until the next compaction.

Like the other adapter tests, each drives the hook entry point with a
transcript in Claude Code's recorded shape (see `claude_code_adapter_support.py`).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from claude_code_adapter_support import (
    BRIEF,
    ROUTER,
    Session,
    decision,
    parse,
    reason,
)

DESIGN = "software-design-principles"
SKIP_DESIGN = f"goated-skip: {DESIGN}: one mechanical constant change"
SKIP_DOCS = "goated-skip: doc-sync: internal constant with no documented behavior"
CODING = "/opt/goated/skills/software-design-principles/references/coding.md"
RESETS = ("compact", "clear", "missing state")


def hold_line(output: dict) -> str:
    return reason(output).split("\n", 1)[0]


def stop(s: Session) -> dict:
    return parse(s.hook("Stop", stop_hook_active=False, last_assistant_message=""))


def commit(message: str) -> dict:
    return {"command": f'git add -A && git commit -m "{message}"'}


def code_edit(path: str, lines: int) -> dict:
    """An edit adding `lines` plain assignments, which trip no design-reads signal."""

    return {"file_path": path, "old_string": "pass",
            "new_string": "\n".join(f"total_{n} = {n}" for n in range(lines))}


class LoadsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._sessions = 0

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def session(self) -> Session:
        self._sessions += 1
        folder = self.root / f"s{self._sessions}"
        folder.mkdir()
        return Session(folder, session_id=f"session-{self._sessions}")

    def first_turn(self, *skills: str, route: str = "goated-route: direct",
                   prompt: str = "Start the export work.") -> Session:
        s = self.session()
        s.prompt(prompt)
        s.load(ROUTER)
        s.say(route)
        for skill in skills:
            s.load(skill)
        return s

    @staticmethod
    def later_turn(s: Session, route: str = "goated-route: continue",
                   prompt: str = "Carry on.") -> Session:
        """End the turn, as Claude Code's `Stop` does, and open a routed one."""

        stop(s)
        s.prompt(prompt)
        s.say(route)
        return s

    @staticmethod
    def reset(s: Session, how: str, route: str = "goated-route: direct") -> Session:
        """End the turn, lose the text of earlier turns (`compact`, `clear`) or
        the saved state, then open a routed turn."""

        stop(s)
        if how == "compact":
            s.compact()
        elif how == "clear":
            s.hook("SessionStart", source="clear")
        else:
            (s.config.state_dir / f"{s.session_id}.json").unlink()
        s.prompt("Next part.")
        s.load(ROUTER)
        s.say(route)
        return s


class LoadsCountInLaterTurnsTests(LoadsTestCase):
    """AC1: a load meets `pipeline`, `commit`, `design` and Docs in a later turn."""

    def test_pipeline(self) -> None:
        s = self.first_turn("tdd", route="goated-route: lightweight | requires: tdd")
        self.assertEqual(decision(s.call("Edit")), "pass")

        # A new task in a later turn: the earlier load still counts.
        self.later_turn(s, "goated-route: lightweight | requires: tdd", "Now fix the date parser.")
        self.assertEqual(decision(s.call("Edit")), "pass")

        # Near miss: a skill never loaded is still asked for, and only that one.
        self.later_turn(s, "goated-route: standard | requires: tdd, doc-sync", "Now the importer.")
        held = s.call("Edit")
        self.assertEqual(hold_line(held), "goated-hold: pipeline | strict")
        self.assertIn("`doc-sync`", reason(held))
        self.assertNotIn("`tdd`", reason(held))

    def test_commit(self) -> None:
        s = self.first_turn("commit-message")
        self.later_turn(s, prompt="Commit it.")

        # Near miss: the load counts, but the change read is still per turn.
        held = s.call("Bash", commit("Add CSV export"))
        self.assertEqual(hold_line(held), "goated-hold: commit | strict")
        self.assertIn("Read the change", reason(held))
        self.assertNotIn("Load the", reason(held))

        s.run("git diff")
        self.assertEqual(decision(s.call("Bash", commit("Add CSV export"))), "pass")

    def test_design(self) -> None:
        s = self.first_turn(DESIGN)
        self.later_turn(s)

        # The load counts in a later turn, so no load is asked for (Ticket 089:
        # no design-reads line either).
        self.assertEqual(decision(s.call("Edit", code_edit("src/export.py", 6))), "pass")

    def test_docs_item(self) -> None:
        s = self.first_turn("doc-sync")
        self.later_turn(s)
        s.say(SKIP_DESIGN)
        s.call("Edit", code_edit("src/export.py", 6))
        s.run("pytest -q")

        # Near miss: the change read is still per turn, but no load is asked for.
        held = stop(s)
        self.assertIn("- Docs: read the change itself after your last code change", held["reason"])
        self.assertNotIn("load `doc-sync`", held["reason"])

        s.run("git diff")
        self.assertEqual(stop(s), {})

    def test_a_skill_the_user_invoked_counts_in_a_later_turn(self) -> None:
        s = self.session()
        s.slash("commit-message")
        s.load(ROUTER)
        s.say("goated-route: direct")
        self.later_turn(s, prompt="Commit it.")
        s.run("git diff")

        self.assertEqual(decision(s.call("Bash", commit("Add CSV export"))), "pass")

    def test_a_failed_load_does_not_count_in_a_later_turn(self) -> None:
        s = self.first_turn()
        s.load("commit-message", success=False)
        self.later_turn(s, prompt="Commit it.")
        s.run("git diff")

        held = s.call("Bash", commit("Add CSV export"))
        self.assertIn("Load the `commit-message` skill", reason(held))

    def test_other_gates_that_ask_for_a_load(self) -> None:
        conflict = {"file_path": "src/app.py", "old_string": "<<<<<<< HEAD\na\n=======\nb\n>>>>>>> x",
                    "new_string": "a"}
        cases = (
            ("pr-description", lambda s: s.run("git diff"),
             lambda s: s.call("Bash", {"command": "gh pr create --title T --body B"})),
            ("resolving-merge-conflicts", lambda s: None, lambda s: s.call("Edit", conflict)),
            ("diagnose",
             lambda s: [s.run("pytest -q", success=False) for _ in range(2)],
             lambda s: s.call("Edit", {"file_path": "notes.md", "old_string": "a", "new_string": "b"})),
            ("code-security-review", lambda s: s.say(SKIP_DESIGN),
             lambda s: s.call("Edit", code_edit("src/auth.py", 2))),
        )
        for skill, prepare, act in cases:
            with self.subTest(skill=skill):
                # Near miss: without the earlier load, the same turn is held.
                s = self.first_turn()
                self.later_turn(s)
                prepare(s)
                self.assertEqual(decision(act(s)), "deny")

                s = self.first_turn(skill)
                self.later_turn(s)
                prepare(s)
                self.assertEqual(decision(act(s)), "pass")

    def test_a_resume_keeps_loads(self) -> None:
        s = self.first_turn("commit-message")
        s.hook("SessionStart", source="resume")
        self.later_turn(s, prompt="Commit it.")
        s.run("git diff")

        self.assertEqual(decision(s.call("Bash", commit("Add CSV export"))), "pass")


class ResetsAskForTheLoadAgainTests(LoadsTestCase):
    """AC2, AC3: after a compaction, a `/clear`, or with the state file
    missing, each hold asks for the load again."""

    def test_pipeline(self) -> None:
        route = "goated-route: lightweight | requires: tdd"
        for how in RESETS:
            with self.subTest(how=how):
                s = self.first_turn("tdd", route=route)
                self.reset(s, how, route)
                held = s.call("Edit")
                self.assertEqual(hold_line(held), "goated-hold: pipeline | strict")
                self.assertIn("`tdd`", reason(held))

    def test_commit(self) -> None:
        for how in RESETS:
            with self.subTest(how=how):
                s = self.first_turn("commit-message")
                self.reset(s, how)
                s.run("git diff")
                held = s.call("Bash", commit("Add CSV export"))
                self.assertIn("Load the `commit-message` skill", reason(held))

    def test_design(self) -> None:
        for how in RESETS:
            with self.subTest(how=how):
                s = self.first_turn(DESIGN)
                self.reset(s, how)
                held = s.call("Edit", code_edit("src/export.py", 6))
                self.assertEqual(hold_line(held), "goated-hold: design | justified-skip")
                self.assertIn(f"Load `{DESIGN}`", reason(held))

    def test_docs_item(self) -> None:
        for how in RESETS:
            with self.subTest(how=how):
                s = self.first_turn("doc-sync")
                self.reset(s, how)
                s.say(SKIP_DESIGN)
                s.call("Edit", code_edit("src/export.py", 6))
                s.run("pytest -q")
                s.run("git diff")
                self.assertIn("- Docs: load `doc-sync`", stop(s)["reason"])

    def test_spawn_template_read(self) -> None:
        for how in RESETS:
            with self.subTest(how=how):
                s = self.first_turn()
                s.brief_with_handoff()
                self.reset(s, how)
                held = s.spawn("a1", BRIEF)
                self.assertEqual(hold_line(held), "goated-hold: spawn | strict")
                self.assertIn("Load `handoff`", reason(held))


class CompactionBoundaryTests(LoadsTestCase):
    """A compaction drops earlier loads even when its `SessionStart` reset never
    ran, as when that hook failed open or the adapter was installed mid-session."""

    @staticmethod
    def compact_without_hook(s: Session) -> None:
        s._append({"type": "system", "subtype": "compact_boundary",
                   "content": "Conversation compacted"})
        s._append({"type": "user", "isCompactSummary": True,
                   "message": {"role": "user", "content": "Summary of earlier work."}})

    def test_a_load_before_the_boundary_does_not_count(self) -> None:
        s = self.first_turn("commit-message")
        stop(s)
        self.compact_without_hook(s)
        s.prompt("Commit it.")
        s.load(ROUTER)
        s.say("goated-route: direct")
        s.run("git diff")

        held = s.call("Bash", commit("Add CSV export"))
        self.assertIn("Load the `commit-message` skill", reason(held))

        # Near miss: a load after the boundary counts.
        s.load("commit-message")
        self.assertEqual(decision(s.call("Bash", commit("Add CSV export"))), "pass")

    def test_the_router_must_load_again_after_the_boundary(self) -> None:
        s = self.first_turn()
        stop(s)
        self.compact_without_hook(s)
        s.prompt("Next part.")
        s.say("goated-route: direct")

        self.assertEqual(hold_line(s.call("Edit")), "goated-hold: router-first | strict")
        s.load(ROUTER)
        self.assertEqual(decision(s.call("Edit")), "pass")


class UnreadableEditSizeTests(LoadsTestCase):
    """An edit whose added lines cannot be counted is not small (spec Constraints)."""

    UNREADABLE = {"file_path": "src/export.py", "old_string": "pass", "new_string": None}

    def test_it_meets_the_design_gate(self) -> None:
        s = self.first_turn()
        held = s.call("Edit", self.UNREADABLE)
        self.assertEqual(hold_line(held), "goated-hold: design | justified-skip")

        # Near miss: a counted one-line edit is small.
        self.assertEqual(decision(s.call("Edit", code_edit("src/export.py", 1))), "pass")

    def test_in_a_later_turn_it_raises_the_design_items(self) -> None:
        s = self.first_turn(DESIGN)
        self.later_turn(s)
        s.say(SKIP_DOCS)
        self.assertEqual(decision(s.call("Edit", self.UNREADABLE)), "pass")
        s.run("pytest -q")

        self.assertIn("- Design:", stop(s)["reason"])


class SubagentHoldTextTests(LoadsTestCase):
    """Inside a subagent a load must be in its current turn, and its holds say so."""

    def test_a_subagent_hold_asks_for_a_load_in_this_turn(self) -> None:
        s = self.session()
        s.prompt("Delegate the export work.")
        agent = s.subagent("a7")
        agent.prompt("Commit the export.", hook=False)
        held = agent.call("Bash", commit("Add export"), agent_id="a7",
                          agent_type="general-purpose")
        self.assertIn("with the Skill tool in this turn", reason(held))

        # Near miss: the main agent's hold does not, since an earlier load counts there.
        main = self.first_turn()
        self.assertNotIn("in this turn", reason(main.call("Bash", commit("Add export"))))


class PerTurnStaysPerTurnTests(LoadsTestCase):
    """AC4, AC5: lines, overrides and change reads still count only in their turn."""

    def test_a_typed_override_from_an_earlier_turn_clears_nothing(self) -> None:
        s = self.first_turn(prompt="Commit it, and skip commit-message.")
        self.assertEqual(decision(s.call("Bash", commit("Add CSV export"))), "pass")

        self.later_turn(s, prompt="Commit the rest.")
        self.assertEqual(hold_line(s.call("Bash", commit("Add the rest"))),
                         "goated-hold: commit | strict")

    def test_a_skip_routing_override_from_an_earlier_turn_clears_nothing(self) -> None:
        s = self.session()
        s.prompt("Fix the typo, and skip routing.")
        self.assertEqual(decision(s.call("Edit")), "pass")

        s.prompt("Now the next one.")
        self.assertEqual(hold_line(s.call("Edit")), "goated-hold: router-first | strict")

    def test_a_skip_line_from_an_earlier_turn_clears_nothing(self) -> None:
        s = self.first_turn()
        s.say(SKIP_DESIGN)
        self.assertEqual(decision(s.call("Edit", code_edit("src/a.py", 6))), "pass")

        self.later_turn(s)
        self.assertEqual(hold_line(s.call("Edit", code_edit("src/b.py", 6))),
                         "goated-hold: design | justified-skip")

    def test_a_change_read_from_an_earlier_turn_does_not_answer_a_later_change(self) -> None:
        notes = {"file_path": "notes.md", "old_string": "a", "new_string": "b"}
        s = self.first_turn("commit-message")
        s.call("Edit", notes)
        s.run("git diff")
        self.assertEqual(decision(s.call("Bash", commit("Add notes"))), "pass")

        self.later_turn(s, prompt="Fix the notes too.")
        s.call("Edit", notes)
        held = s.call("Bash", commit("Fix notes"))
        self.assertIn("Read the change before committing it", reason(held))
        s.run("git diff")
        self.assertEqual(decision(s.call("Bash", commit("Fix notes"))), "pass")


class DesignCloseoutTests(LoadsTestCase):
    """AC6: in a later turn the Design items follow the edits the `design` gate triggers on."""

    def later_designing(self) -> Session:
        s = self.first_turn(DESIGN)
        self.later_turn(s)
        s.say(SKIP_DOCS)
        return s

    def test_a_four_line_edit_raises_no_design_item(self) -> None:
        s = self.later_designing()
        self.assertEqual(decision(s.call("Edit", code_edit("src/export.py", 4))), "pass")
        s.run("pytest -q")

        self.assertEqual(stop(s), {})

    def test_a_twenty_line_non_test_edit_raises_it(self) -> None:
        s = self.later_designing()
        self.assertEqual(decision(s.call("Edit", code_edit("src/export.py", 20))), "pass")
        s.run("pytest -q")

        self.assertIn("- Design: read `software-design-principles/references/red-flags.md`",
                      stop(s)["reason"])

    def test_a_twenty_line_test_edit_raises_none(self) -> None:
        s = self.later_designing()
        s.read(CODING)
        self.assertEqual(decision(s.call("Edit", code_edit("tests/test_export.py", 20))), "pass")
        s.run("pytest -q")

        self.assertEqual(stop(s), {})

    def test_a_turn_that_loads_the_skill_keeps_the_items_for_small_edits(self) -> None:
        s = self.first_turn(DESIGN)
        s.say(SKIP_DOCS)
        s.call("Edit", code_edit("src/export.py", 4))
        s.run("pytest -q")

        self.assertIn("- Design:", stop(s)["reason"])


class SecurityCloseoutTests(LoadsTestCase):
    def test_a_load_in_an_earlier_turn_applies_the_security_item(self) -> None:
        s = self.first_turn("code-security-review")
        self.later_turn(s)
        s.say(SKIP_DOCS)
        s.load("verification-before-completion")  # A sensitive file needs verification (Ticket 069).
        self.assertEqual(decision(s.call("Edit", code_edit("src/auth.py", 2))), "pass")
        s.run("pytest -q")

        self.assertIn("- Security:", stop(s)["reason"])
        s.run("git diff")
        self.assertEqual(stop(s), {})

    def test_without_the_load_a_skipped_change_has_no_security_item(self) -> None:
        s = self.first_turn()
        self.later_turn(s)
        s.say(SKIP_DOCS)
        s.say("goated-skip: code-security-review: renames a local constant only")
        s.load("verification-before-completion")  # A sensitive file needs verification (Ticket 069).
        s.call("Edit", code_edit("src/auth.py", 2))
        s.run("pytest -q")

        self.assertEqual(stop(s), {})


class SpawnTemplateTests(LoadsTestCase):
    """AC7: a template read counts in a later turn; the content check still runs."""

    def test_a_template_read_in_an_earlier_turn_counts(self) -> None:
        s = self.first_turn()
        s.brief_with_handoff()
        self.later_turn(s)

        self.assertEqual(decision(s.spawn("a1", BRIEF)), "pass")
        held = s.spawn("a2", BRIEF.replace("## Done Means", "## Notes"))
        self.assertEqual(hold_line(held), "goated-hold: spawn | strict")
        self.assertIn("## Done Means", reason(held))

    def test_a_load_without_the_template_read_still_asks_for_the_read(self) -> None:
        s = self.first_turn("handoff")
        self.later_turn(s)

        held = s.spawn("a1", BRIEF)
        self.assertIn("spawn-brief.md", reason(held))
        self.assertNotIn("Load `handoff`", reason(held))


class SubagentTests(LoadsTestCase):
    """AC8: inside a subagent only its current turn counts."""

    def test_a_load_in_an_earlier_subagent_turn_does_not_count(self) -> None:
        s = self.session()
        s.prompt("Delegate the export work.")
        agent = s.subagent("a7")

        def sub_commit() -> dict:
            agent._tool_result(agent._tool_use("Bash", {"command": "git diff"}), "ok")
            return agent.call("Bash", commit("Add export"), agent_id="a7",
                              agent_type="general-purpose")

        agent.prompt("Load what you need.", hook=False)
        agent.load("commit-message")
        agent.prompt("Now commit.", hook=False)
        self.assertEqual(hold_line(sub_commit()), "goated-hold: commit | strict")

        # Near miss: a load in its current turn counts.
        agent.load("commit-message")
        self.assertEqual(decision(sub_commit()), "pass")


if __name__ == "__main__":
    unittest.main()
