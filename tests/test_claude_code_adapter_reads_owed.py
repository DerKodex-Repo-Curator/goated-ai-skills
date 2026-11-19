"""Ticket 118: a design or registry read never refuses an edit.

An edit that `design`, `design-reads`, or `reference-reads` would hold for
reads alone lands at any size, and its references are owed: the closeout's
Reads item asks for them at a commit and at the turn's end. The turn's first
landed edit that owes a read carries one `reads_owed` notice listing them; a
later edit's notice names only references it newly adds. Each test drives the
Claude Code hook entry point with a transcript in Claude Code's recorded
shape (`claude_code_adapter_support.py`), so the owed reads cross the core's
saved state between hook calls.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from claude_code_adapter_support import (
    REPO_ROOT, ROUTER, Session, context, decision, owed_names, parse, reason,
)

DESIGN = "software-design-principles"
REFERENCES = f"/opt/goated/skills/{DESIGN}/references"
SOURCE = "src/export.py"
# A file the project already has, so each edit adds to it rather than creating it.
EXISTING = "def rows():\n    return []\n"
# A 3-line edit adding a public function.
PUBLIC_FUNCTION = {"file_path": SOURCE, "old_string": "def rows():\n",
                   "new_string": 'def total():\n    """Sum the rows."""\n    return 0\n'
                                 "def rows():\n"}
SKIP_LINE = f"goated-skip: {DESIGN}: a one-line placeholder with no design in it"


class ReadsOwedTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.session = Session(Path(self._tmp.name))
        self.session.config.registry_path = REPO_ROOT / "stack" / "goated-stack.yaml"
        (self.session.project / "src").mkdir(parents=True)
        (self.session.project / SOURCE).write_text(EXISTING, encoding="utf-8")
        self.session.prompt("Add the export total.")
        self.session.load(ROUTER)
        self.session.say("goated-route: direct")
        self.session.load(DESIGN)

    def stop(self) -> dict:
        return parse(self.session.hook("Stop", stop_hook_active=False,
                                       last_assistant_message=""))

    def test_a_three_line_public_function_lands_with_a_notice_naming_its_references(self) -> None:
        landed = self.session.call("Edit", PUBLIC_FUNCTION)
        self.assertEqual(decision(landed), "pass", reason(landed))
        self.assertTrue(owed_names(landed), context(landed))
        self.assertIn("Reads item", context(landed))

    def test_the_turn_end_is_held_by_the_reads_item_until_the_owed_references_are_read(self) -> None:
        references = owed_names(self.session.call("Edit", PUBLIC_FUNCTION))
        held = self.stop()
        self.assertEqual(held.get("decision"), "block")
        self.assertIn("- Reads: a write landed", held["reason"])
        for name in references:
            self.session.read(f"{REFERENCES}/{name}")
        self.session.read(SOURCE)
        self.assertNotIn("- Reads:", self.stop().get("reason", ""))

    def test_a_commit_is_held_by_the_reads_item_until_a_skip_line_declines_the_reads(self) -> None:
        self.session.call("Edit", PUBLIC_FUNCTION)
        self.session.load("commit-message")
        self.session.read(SOURCE)  # The commit gate's change read.
        commit = {"command": 'git commit -am "Add the export total"'}
        held = self.session.call("Bash", commit)
        self.assertIn("- Reads:", reason(held))
        self.session.say(SKIP_LINE)
        self.assertNotIn("- Reads:", reason(self.session.call("Bash", commit)))

    def test_four_edits_sent_in_one_message_all_land(self) -> None:
        edits = [("Edit", {"file_path": SOURCE, "old_string": "def rows():\n",
                           "new_string": f"def total_{n}():\n    return {n}\n\ndef rows():\n"})
                 for n in range(4)]
        outputs = self.session.parallel(edits)
        self.assertEqual([decision(output) for output in outputs], ["pass"] * 4,
                         [reason(output) for output in outputs])

    def test_a_reference_read_earlier_in_the_context_window_is_not_owed(self) -> None:
        self.session.read(f"{REFERENCES}/process.md")
        landed = self.session.call("Edit", PUBLIC_FUNCTION)
        self.assertTrue(owed_names(landed), context(landed))
        self.assertNotIn("process.md", owed_names(landed))

    def test_a_lasting_skip_made_at_the_reads_item_clears_the_next_turns_reads(self) -> None:
        self.session.call("Edit", PUBLIC_FUNCTION)
        self.session.say(SKIP_LINE)
        self.assertNotIn("- Reads:", self.stop().get("reason", ""))
        self.session.prompt("Add the export average too.")
        self.session.say("goated-route: continue")
        again = self.session.call("Edit", {**PUBLIC_FUNCTION, "new_string": PUBLIC_FUNCTION[
            "new_string"].replace("total", "average")})
        self.assertEqual(decision(again), "pass", reason(again))
        self.assertIn("through without a read of", context(again))
        self.assertNotIn("land before a read of", context(again))
        self.assertNotIn("- Reads:", self.stop().get("reason", ""))

    # Phase 2: one notice per turn.

    def test_a_second_edit_selecting_the_same_references_adds_no_notice_text(self) -> None:
        first = self.session.call("Edit", PUBLIC_FUNCTION)
        self.assertTrue(owed_names(first))
        second = self.session.call("Edit", {**PUBLIC_FUNCTION, "new_string": PUBLIC_FUNCTION[
            "new_string"].replace("total", "average")})
        self.assertEqual(decision(second), "pass", reason(second))
        self.assertEqual(context(second), "")

    def test_an_edit_selecting_a_new_reference_names_only_that_one(self) -> None:
        self.session.call("Edit", PUBLIC_FUNCTION)
        guarded = self.session.call("Edit", {**PUBLIC_FUNCTION, "new_string": (
            'def load():\n    """Load the rows."""\n    try:\n        return rows()\n'
            "    except OSError:\n        return []\ndef rows():\n")})
        self.assertEqual(decision(guarded), "pass", reason(guarded))
        self.assertEqual(owed_names(guarded), {"errors.md"}, context(guarded))

    def test_parallel_edits_owing_the_same_references_carry_one_notice(self) -> None:
        edits = [("Edit", {"file_path": SOURCE, "old_string": "def rows():\n",
                           "new_string": f"def total_{n}():\n    return {n}\n\ndef rows():\n"})
                 for n in range(4)]
        outputs = self.session.parallel(edits)
        self.assertTrue(owed_names(outputs[0]))
        self.assertEqual([context(output) for output in outputs[1:]], ["", "", ""])

    def test_edits_judged_at_once_each_keep_what_they_owe_and_share_one_notice(self) -> None:
        # Review of Ticket 118: hooks of one message run at the same moment, and
        # each saves the session state, so without a lock the last save drops
        # what the other edit owed.
        guarded = {"file_path": "src/other.py", "old_string": "def rows():\n", "new_string": (
            'def load():\n    """Load the rows."""\n    try:\n        return rows()\n'
            "    except OSError:\n        return []\ndef rows():\n")}
        for trial in range(3):
            with self.subTest(trial=trial):
                self.setUp()
                (self.session.project / "src" / "other.py").write_text(EXISTING, encoding="utf-8")
                outputs = self.session.parallel([("Edit", PUBLIC_FUNCTION), ("Edit", guarded)],
                                                concurrently=True)
                self.assertEqual([decision(o) for o in outputs], ["pass", "pass"])
                # Both public definitions select the same three; only one names them.
                listed = [owed_names(o) & {"process.md", "readability.md"} for o in outputs]
                self.assertEqual(sorted(map(bool, listed)), [False, True], listed)
                reads = self.stop()["reason"].split("- Reads:", 1)[1].split("\n- ", 1)[0]
                for name in ("process.md", "errors.md"):
                    self.assertIn(name, reads)

    def test_the_next_turn_names_its_references_again(self) -> None:
        # Owed reads end with their turn, so the next turn's notice names them afresh.
        self.session.call("Edit", PUBLIC_FUNCTION)
        self.session.prompt("Add the export average too.")
        self.session.say("goated-route: continue")
        again = self.session.call("Edit", PUBLIC_FUNCTION)
        self.assertTrue(owed_names(again), context(again))

    def test_the_design_gate_still_holds_a_first_change_until_the_skill_loads(self) -> None:
        (Path(self._tmp.name) / "fresh").mkdir()
        fresh = Session(Path(self._tmp.name) / "fresh")
        (fresh.project / "src").mkdir(parents=True)
        fresh.prompt("Add the export totals.")
        fresh.load(ROUTER)
        fresh.say("goated-route: direct")
        held = fresh.call("Write", {"file_path": SOURCE, "content": "".join(
            f"def total_{n}():\n    return {n}\n" for n in range(3))})
        self.assertEqual(reason(held).split("\n", 1)[0], "goated-hold: design | justified-skip")


if __name__ == "__main__":
    unittest.main()
