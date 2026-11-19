"""Ticket 113 (round 5, R2, decision K): design references follow what an
edit adds, not its raw line count.

- K1: a code edit adding fewer than five code lines and fewer than twenty
  comment lines selects no `readability.md` for its comment; the `design`
  gate keeps its size rule.
- K2: in an existing test file, added lines that only hold case data do not
  count toward the registry's `min_added_lines` for test files.

Each test drives the hook entry point with a transcript in Claude Code's
recorded shape (see `claude_code_adapter_support.py`).
"""

from __future__ import annotations

import unittest

from claude_code_adapter_support import decision, reason
from test_claude_code_adapter_design_holds import DESIGN, DesignTestCase, edit, hold_line
from test_claude_code_adapter_reference_reads import (
    CODING,
    TEST_DESIGN_PATH,
    TEST_FILE,
    ReferenceReadsTestCase,
)
# Imported as a module, so its test classes do not run again here.
import test_claude_code_adapter_reference_reads as reference_reads_tests


def code_and_comments(code: int, comments: int) -> str:
    """A Python edit adding `comments` comment lines, then `code` plain code lines."""

    return "\n".join([f"# why {n}" for n in range(comments)]
                     + [f"fix_{n} = {n}" for n in range(code)])


class CommentOnAShortCodeEdit(DesignTestCase):
    """K1: the comment of a short code edit selects no `readability.md`."""

    def held_for_readability(self, new: str, path: str = "src/export.py") -> bool:
        s = self.routed()
        s.load(DESIGN)
        output = s.call("Edit", edit(path, new))
        return decision(output) != "pass" and "references/readability.md" in reason(output)

    def test_three_code_lines_and_a_two_line_comment_select_no_readability(self) -> None:
        self.assertFalse(self.held_for_readability(code_and_comments(3, 2)))

    def test_five_code_lines_and_a_comment_select_readability(self) -> None:
        self.assertTrue(self.held_for_readability(code_and_comments(5, 1)))

    def test_three_code_lines_and_twenty_comment_lines_select_readability(self) -> None:
        self.assertTrue(self.held_for_readability(code_and_comments(3, 20)))

    def test_a_trailing_comment_leaves_its_line_a_code_line(self) -> None:
        new = "\n".join(f"fix_{n} = {n}  # why" for n in range(3))
        self.assertFalse(self.held_for_readability(new + "\n# one\n# two"))

    def test_a_new_public_definition_still_selects_readability(self) -> None:
        self.assertTrue(self.held_for_readability(
            "# Exports rows.\ndef export(rows):\n    return rows"))

    def test_a_file_whose_comment_syntax_is_unknown_is_judged_as_before(self) -> None:
        self.assertTrue(self.held_for_readability(
            "-- why\n-- more\nlocal a = 1\nlocal b = 2\nlocal c = 3", path="src/export.lua"))

    def test_the_same_edit_still_meets_the_design_gate_unloaded(self) -> None:
        s = self.routed()
        output = s.call("Edit", edit("src/export.py", code_and_comments(3, 2)))
        self.assertEqual(hold_line(output), "goated-hold: design | justified-skip")
        s.load(DESIGN)
        self.assertEqual(decision(s.call("Edit", edit("src/export.py", code_and_comments(3, 2)))),
                         "pass")


CASE_ROWS = [
    '    (1, "one", True),',
    "    (-2.5, 'neg', None),",
    '    pytest.param(3, "three", False, id="three"),',
    "    param(0x10, b\"hex\", id='hex'),  # a hex case",
    '    {"a": [1, 2], "b": null},',
    "    [],",
]


def case_data(count: int) -> list[str]:
    return [CASE_ROWS[n % len(CASE_ROWS)] for n in range(count)]


class NewCasesInAnExistingTest(ReferenceReadsTestCase):
    """K2: case-data lines in an existing test file do not count toward
    `min_added_lines`; a new test function, or a new test file, does."""

    required = reference_reads_tests.TestEditThresholds.required

    def added(self, lines: list[str], old: str = "pass") -> set[str]:
        return self.required("Edit", {"file_path": TEST_FILE, "old_string": old,
                                      "new_string": "\n".join(lines)})

    def test_24_case_data_lines_require_nothing(self) -> None:
        self.assertEqual(self.added(["CASES = ["] + case_data(24), old="CASES = ["), set())

    def test_24_lines_of_a_new_test_function_require_both(self) -> None:
        body = ["def test_totals():"] + [f"    assert total({n}) == {n}" for n in range(23)]
        self.assertEqual(self.added(body), {CODING, TEST_DESIGN_PATH})

    def test_case_data_creating_a_test_file_requires_both(self) -> None:
        content = "\n".join(["CASES = ["] + case_data(24) + ["]"]) + "\n"
        self.assertEqual(self.required("Write", {"file_path": TEST_FILE, "content": content}),
                         {CODING, TEST_DESIGN_PATH})

    def test_rows_that_call_code_still_count(self) -> None:
        rows = case_data(4) + [f"    (make({n}), {n})," for n in range(20)]
        self.assertEqual(self.added(rows), {CODING, TEST_DESIGN_PATH})

    def test_an_assignment_is_not_a_keyword_argument(self) -> None:
        self.assertEqual(self.added([f"expected_{n} = {n}" for n in range(20)]),
                         {CODING, TEST_DESIGN_PATH})

    def test_a_statement_of_literals_outside_brackets_still_counts(self) -> None:
        self.assertEqual(self.added([f"flag_{n}=True" for n in range(20)]),
                         {CODING, TEST_DESIGN_PATH})
        # The near miss: the same keyword arguments as rows of a call are case data.
        self.assertEqual(self.added([f"    flag_{n}=True," for n in range(20)]), set())

if __name__ == "__main__":
    unittest.main()
