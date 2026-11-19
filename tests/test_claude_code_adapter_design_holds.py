"""Ticket 089: the design holds check no text the agent wrote.

The `design` gate asks for the `software-design-principles` load and the
references the edit's signals select, and for no design-reads line; the
closeout has no Design citations item; and a small fix after the red-flags
read asks only for a change read. Like the other adapter tests, each drives
the hook entry point with a transcript in Claude Code's recorded shape (see
`claude_code_adapter_support.py`).
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from claude_code_adapter_support import (
    ROUTER, Session, decision, next_turn, owed, owed_names, parse, reason,
)

DESIGN = "software-design-principles"
REFERENCES = "/opt/goated/skills/software-design-principles/references/"
RED_FLAGS = REFERENCES + "red-flags.md"
DOC_SKIP = "goated-skip: doc-sync: internal constant with no documented behavior"
# Six added lines that trip no design signal.
PLAIN = "\n".join(f"total_{n} = {n}" for n in range(6))
# A public top-level definition, which selects these three references.
DEFINITION = "def export(rows):\n" + "\n".join(f"    total_{n} = {n}" for n in range(5))
DEFINITION_REFERENCES = ("process.md", "complexity-and-modules.md", "readability.md")
LINES = (
    "goated-design-reads: differences.md",
    "goated-design-reads: none: renames one local variable",
    "goated-design-reads: references/process.md",
    "`goated-design-reads: errors.md, unknown-file.md`",
)


def edit(path: str, new: str, old: str = "pass") -> dict:
    return {"file_path": path, "old_string": old, "new_string": new}


def lines_of(count: int, start: int = 0) -> str:
    """`count` plain assignment lines, numbered from `start`."""

    return "\n".join(f"fix_{n} = {n}" for n in range(start, start + count))


def hold_line(output: dict) -> str:
    return reason(output).split("\n", 1)[0]


def stop(s: Session) -> dict:
    return parse(s.hook("Stop", stop_hook_active=False, last_assistant_message=""))


def design_items(output: dict) -> list[str]:
    return [line for line in str(output.get("reason", "")).split("\n") if line.startswith("- Design:")]


class DesignTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._sessions = 0

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def routed(self) -> Session:
        self._sessions += 1
        folder = self.root / f"s{self._sessions}"
        folder.mkdir()
        s = Session(folder, session_id=f"session-{self._sessions}")
        s.prompt("Do the task.")
        s.load(ROUTER)
        s.say("goated-route: direct")
        return s


class DesignGateTests(DesignTestCase):
    def test_a_first_substantial_edit_passes_with_the_skill_and_its_reads_and_no_line(self) -> None:
        s = self.routed()
        s.load(DESIGN)
        for name in DEFINITION_REFERENCES:
            s.read(REFERENCES + name)

        self.assertEqual(decision(s.call("Edit", edit("src/export.py", DEFINITION))), "pass")

        # The near miss: without the skill loaded, the same edit is held for the load.
        s = self.routed()
        for name in DEFINITION_REFERENCES:
            s.read(REFERENCES + name)
        held = s.call("Edit", edit("src/export.py", DEFINITION))
        self.assertEqual(hold_line(held), "goated-hold: design | justified-skip")
        self.assertIn(f"load `{DESIGN}`", reason(held))

    def test_an_unread_reference_is_owed_asking_for_the_read_and_no_line(self) -> None:
        s = self.routed()
        s.load(DESIGN)
        s.read(REFERENCES + "process.md")
        s.read(REFERENCES + "complexity-and-modules.md")

        # Since Ticket 118 the edit lands, and its notice asks for the read.
        landed = s.call("Edit", edit("src/export.py", DEFINITION))
        self.assertEqual(decision(landed), "pass")
        self.assertIn("the design gate let this write", owed(landed))
        self.assertEqual(owed_names(landed), {"readability.md"})
        self.assertNotIn("goated-design-reads", owed(landed))
        self.assertNotIn("design-reads line", owed(landed))

        # The near miss: once read, the same edit owes nothing, still with no line.
        s.read(REFERENCES + "readability.md")
        next_turn(s)  # A new turn, where an unread reference would be owed again.
        again = s.call("Edit", edit("src/export.py", DEFINITION))
        self.assertEqual((decision(again), owed(again)), ("pass", ""))

    def test_a_written_design_reads_line_changes_no_decision(self) -> None:
        def run(line: str | None) -> list[tuple[str, str]]:
            s = self.routed()
            s.load(DESIGN)
            if line is not None:
                s.say(line)
            outputs = [s.call("Edit", edit("src/export.py", PLAIN)),
                       s.call("Edit", edit("src/export.py", DEFINITION))]
            for name in DEFINITION_REFERENCES:
                s.read(REFERENCES + name)
            next_turn(s)  # A new turn, where an unread reference would be owed again.
            outputs.append(s.call("Edit", edit("src/export.py", DEFINITION)))
            return [(decision(o), reason(o), owed_names(o)) for o in outputs]

        without = run(None)
        # The baseline: every edit lands, and only the definition before its
        # reads owes them (Ticket 118).
        self.assertEqual(without, [("pass", "", set()), ("pass", "", set(DEFINITION_REFERENCES)),
                                   ("pass", "", set())])
        for line in LINES:
            with self.subTest(line=line):
                self.assertEqual(run(line), without)


class DesignCloseoutTests(DesignTestCase):
    def designed(self) -> Session:
        """A turn that loaded the skill, made an edit requiring errors.md, and proved it."""

        s = self.routed()
        s.load(DESIGN)
        s.read(REFERENCES + "errors.md")
        new = "try:\n    total = load()\nexcept OSError:\n    raise\n" + lines_of(2)
        self.assertEqual(decision(s.call("Edit", edit("src/export.py", new))), "pass")
        s.run("pytest -q")
        s.say(DOC_SKIP)
        return s

    def test_a_closeout_after_design_edits_lists_no_citations_item(self) -> None:
        s = self.designed()
        s.read(RED_FLAGS)
        s.run("git diff")

        self.assertEqual(stop(s), {})

    def test_the_red_flags_item_alone_remains_without_a_citation_ask(self) -> None:
        # The near miss: with no red-flags read, the Design item is the red-flags one only.
        held = stop(self.designed())

        items = design_items(held)
        self.assertEqual(len(items), 1, held)
        self.assertIn("red-flags.md", items[0])
        self.assertNotIn("cite", held["reason"])
        self.assertNotIn("file#id", held["reason"])


class RedFlagsRereadTests(DesignTestCase):
    def scanned(self) -> Session:
        """A designed turn whose closeout is met: red flags read, then the change read."""

        s = self.routed()
        s.load(DESIGN)
        self.assertEqual(decision(s.call("Edit", edit("src/export.py", PLAIN))), "pass")
        s.run("pytest -q")
        s.say(DOC_SKIP)
        s.read(RED_FLAGS)
        s.run("git diff")
        self.assertEqual(stop(s), {})
        return s

    def fix(self, s: Session, lines: int, start: int = 0) -> None:
        self.assertEqual(decision(s.call("Edit", edit("src/export.py", lines_of(lines, start)))), "pass")
        s.run("pytest -q")

    def test_a_two_line_fix_asks_only_for_a_change_read(self) -> None:
        s = self.scanned()
        self.fix(s, 2)

        items = design_items(stop(s))
        self.assertEqual(len(items), 1, items)
        self.assertNotIn("red-flags.md", items[0])
        self.assertIn("read the change itself", items[0])
        s.run("git diff")
        self.assertEqual(stop(s), {})

    def test_a_six_line_fix_asks_for_the_red_flags_read_again(self) -> None:
        s = self.scanned()
        self.fix(s, 6)
        s.run("git diff")

        items = design_items(stop(s))
        self.assertEqual(len(items), 1, items)
        self.assertIn("red-flags.md", items[0])
        s.read(RED_FLAGS)
        s.run("git diff")
        self.assertEqual(stop(s), {})

    def test_three_two_line_fixes_ask_for_the_red_flags_read_again(self) -> None:
        s = self.scanned()
        for start in (0, 2, 4):
            self.fix(s, 2, start)
            s.run("git diff")

        items = design_items(stop(s))
        self.assertEqual(len(items), 1, items)
        self.assertIn("red-flags.md", items[0])

    def test_comment_only_changes_do_not_count_toward_the_five_lines(self) -> None:
        s = self.scanned()
        self.fix(s, 2)
        comments = "\n".join(f"# note {n}" for n in range(8))
        self.assertEqual(decision(s.call("Edit", edit("src/export.py", comments, old="# old"))), "pass")
        s.run("pytest -q")
        s.run("git diff")

        self.assertEqual(stop(s), {})

    def test_a_red_flags_read_before_any_designed_change_covers_no_later_fix(self) -> None:
        # Lead review of 089: a read with no designed change before it scanned nothing.
        s = self.routed()
        s.load(DESIGN)
        s.say(DOC_SKIP)
        s.read(RED_FLAGS)
        self.fix(s, 2)
        s.run("git diff")

        items = design_items(stop(s))
        self.assertEqual(len(items), 1, items)
        self.assertIn("red-flags.md", items[0])

        # The near miss: a designed change of five lines before the read lets it cover the fix.
        s = self.routed()
        s.load(DESIGN)
        s.say(DOC_SKIP)
        self.fix(s, 5, start=10)
        s.read(RED_FLAGS)
        self.fix(s, 2)
        s.run("git diff")
        self.assertEqual(stop(s), {})

    def test_a_fix_with_no_red_flags_read_in_the_turn_still_asks_for_it(self) -> None:
        # The rule needs an earlier red-flags read in the same turn.
        s = self.routed()
        s.load(DESIGN)
        self.assertEqual(decision(s.call("Edit", edit("src/export.py", PLAIN))), "pass")
        self.fix(s, 2)
        s.say(DOC_SKIP)
        s.run("git diff")

        items = design_items(stop(s))
        self.assertEqual(len(items), 1, items)
        self.assertIn("red-flags.md", items[0])


def comment_edit(count: int) -> dict:
    """A comment-only edit of a Python file adding `count` lines."""

    return edit("src/export.py", "\n".join(f"# note {n}" for n in range(count - 1)) + "\npass")


class ShortCommentEditTests(DesignTestCase):
    """Round 4, R3: a comment-only edit adding fewer than 20 lines is no
    substantial change, selects no reference by its comment, and is no code
    change the Design item counts; one of 20 lines is judged as before."""

    def finish(self, s: Session) -> list[str]:
        s.run("pytest -q")
        s.say(DOC_SKIP)
        return design_items(stop(s))

    def test_a_19_line_comment_edit_meets_no_design_hold(self) -> None:
        s = self.routed()
        self.assertEqual(decision(s.call("Edit", comment_edit(19))), "pass")

        # The near miss: 20 lines are a substantial change, held for the load.
        s = self.routed()
        self.assertEqual(hold_line(s.call("Edit", comment_edit(20))),
                         "goated-hold: design | justified-skip")

    def test_a_19_line_comment_edit_selects_no_reference_and_no_design_item(self) -> None:
        s = self.routed()
        s.load(DESIGN)
        self.assertEqual(decision(s.call("Edit", comment_edit(19))), "pass")
        self.assertEqual(self.finish(s), [])

        # The near miss: 20 lines are substantial, so the Design item counts
        # them; their 19 comment lines are too few for `readability.md`, and
        # 20 comment lines ask for it (round 5, K1).
        s = self.routed()
        s.load(DESIGN)
        self.assertEqual(owed(s.call("Edit", comment_edit(20))), "")
        landed = s.call("Edit", comment_edit(21))
        self.assertEqual(decision(landed), "pass")
        self.assertEqual(owed_names(landed), {"readability.md"})
        s.read(REFERENCES + "readability.md")
        next_turn(s)  # A new turn, where an unread reference would be owed again.
        self.assertEqual(owed(s.call("Edit", comment_edit(21))), "")
        self.assertEqual(len(self.finish(s)), 1)

    def test_a_19_line_comment_edit_in_a_later_turn_meets_no_design_item(self) -> None:
        s = self.routed()
        s.load(DESIGN)
        s.say("goated-skip: doc-sync: nothing changed yet")
        stop(s)
        s.prompt("Explain the totals in comments.")
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Edit", comment_edit(19))), "pass")
        self.assertEqual(self.finish(s), [])


if __name__ == "__main__":
    unittest.main()
