"""Ticket 098: the adapter's gaps against the enforcement contract, closed.

- (b) `design` and `design-reads` judge a shell write that puts new text
  into a project code or configuration file: a redirect, heredoc, `tee`,
  `Set-Content`, `Out-File`, or `Add-Content` (the maintainer's choice). A
  heredoc counts its body lines; text the command does not show counts as
  five or more. Copies, moves, restores, and `sed -i` add no text designed
  in the command, so they stay unjudged, and a write naming no file meets
  no design hold.

Gap (a), orientation by whole reads only, is tested beside the other
orientation tests in `test_claude_code_adapter_low_signal_routing.py`, and
gap (c), a subagent's commit closeout, beside the commit closeout tests in
`test_claude_code_adapter_actions.py`.
"""

from __future__ import annotations

import unittest

from claude_code_adapter_support import decision, owed, reason
from test_claude_code_adapter_design_holds import DESIGN, REFERENCES, DesignTestCase, hold_line

DESIGN_HOLD = "goated-hold: design | justified-skip"
DESIGN_READS_HOLD = "goated-hold: design-reads | justified-skip"


def heredoc(path: str, lines: int) -> str:
    body = "\n".join(f"total_{n} = {n}" for n in range(lines))
    return f"cat > {path} <<'EOF'\n{body}\nEOF"


class ShellWriteDesignTests(DesignTestCase):
    def test_a_heredoc_of_six_code_lines_waits_for_design_principles(self) -> None:
        s = self.routed()

        held = s.run(heredoc("src/export.py", 6))
        self.assertEqual(hold_line(held), DESIGN_HOLD)
        self.assertIn(f"load `{DESIGN}`", reason(held))
        self.assertIn("This command was not run.", reason(held))

        s.load(DESIGN)
        self.assertEqual(decision(s.run(heredoc("src/export.py", 6))), "pass")

    def test_a_heredoc_counts_its_body_lines(self) -> None:
        s = self.routed()

        self.assertEqual(decision(s.run(heredoc("src/export.py", 4))), "pass")
        self.assertEqual(hold_line(s.run(heredoc("src/export.py", 5))), DESIGN_HOLD)

    def test_text_the_command_does_not_show_counts_as_five_lines(self) -> None:
        for command, tool in (("python gen.py > src/export.py", "Bash"),
                              ("python gen.py | tee src/export.py", "Bash"),
                              ("Get-Content gen.txt | Out-File src/export.py", "PowerShell")):
            with self.subTest(command=command):
                held = self.routed().run(command, tool=tool)
                self.assertEqual(hold_line(held), DESIGN_HOLD)

    def test_a_shown_value_counts_its_lines(self) -> None:
        s = self.routed()

        self.assertEqual(decision(s.run('echo "total = 1" > src/export.py')), "pass")
        command = "Set-Content -Path src/export.py -Value 'total = 1'"
        self.assertEqual(decision(s.run(command, tool="PowerShell")), "pass")

    def test_copies_moves_restores_and_in_place_edits_stay_unjudged(self) -> None:
        for command in ("cp gen/export.py src/export.py", "mv old.py src/export.py",
                        "git checkout -- src/export.py", "sed -i 's/a/b/' src/export.py",
                        "git apply fix.patch"):
            with self.subTest(command=command):
                self.assertEqual(decision(self.routed().run(command)), "pass")

    def test_a_shell_write_to_a_test_file_or_docs_meets_no_design_hold(self) -> None:
        for path in ("tests/test_export.py", "docs/export.md"):
            with self.subTest(path=path):
                s = self.routed()
                self.assertEqual(decision(s.run(heredoc(path, 8))), "pass")
                s.load(DESIGN)
                self.assertEqual(decision(s.run(heredoc(path, 8))), "pass")

    def test_a_shell_write_to_a_configuration_file_waits_for_its_reference(self) -> None:
        s = self.routed()
        s.load(DESIGN)

        held = s.run(heredoc("config/export.yaml", 6))
        self.assertEqual(hold_line(held), DESIGN_READS_HOLD)
        self.assertIn("references/decoupling.md` (edits a configuration file)", reason(held))
        self.assertIn('"export.yaml"', reason(held))

        s.read(REFERENCES + "decoupling.md")
        self.assertEqual(decision(s.run(heredoc("config/export.yaml", 6))), "pass")

    def test_a_positional_value_after_a_named_path_is_shown_text(self) -> None:
        # Review B1: with -Path named, the first positional argument is the value.
        command = "Set-Content -Path src/export.py 'total = 1'"
        self.assertEqual(decision(self.routed().run(command, tool="PowerShell")), "pass")

    def test_a_value_that_expands_is_text_the_command_does_not_show(self) -> None:
        # Review B2: a variable, a command substitution, or a subexpression.
        for command, tool in (
                ("$code = Get-Content gen.py -Raw; Set-Content src/export.py -Value $code",
                 "PowerShell"),
                ("Set-Content src/export.py -Value (Get-Content gen.py -Raw)", "PowerShell"),
                ('echo "$(cat gen.py)" > src/export.py', "Bash"),
                ('CODE=$(python gen.py); echo "$CODE" > src/export.py', "Bash"),
                ("cat > src/export.py <<EOF\n$(cat gen.py)\nEOF", "Bash")):
            with self.subTest(command=command):
                held = self.routed().run(command, tool=tool)
                self.assertEqual(hold_line(held), DESIGN_HOLD)

    def test_two_spellings_of_one_file_add_up(self) -> None:
        # Review B3: four lines and four more to the same file are eight.
        for command, tool in (
                (heredoc("src/export.py", 4) + "\n"
                 + heredoc("./src/export.py", 4).replace(" > ", " >> "), "Bash"),
                ("Set-Content src\\export.py -Value @'\na\nb\nc\nd\n'@\n"
                 "Add-Content src/export.py -Value @'\ne\nf\ng\nh\n'@", "PowerShell")):
            with self.subTest(command=command):
                held = self.routed().run(command, tool=tool)
                self.assertEqual(hold_line(held), DESIGN_HOLD)

    def test_shown_text_piped_into_cat_or_a_quoted_string_counts_its_lines(self) -> None:
        # Review B4 and B6.
        for command, tool in (("echo 'total = 1' | cat > src/export.py", "Bash"),
                              ("'x' | Out-File src/export.py", "PowerShell"),
                              ("'x' | Tee-Object src/export.py", "PowerShell")):
            with self.subTest(command=command):
                self.assertEqual(decision(self.routed().run(command, tool=tool)), "pass")

    def test_new_item_with_a_value_writes_text(self) -> None:
        # Review B11: the lead's decision, in the spirit of the maintainer's rule.
        six = "New-Item -ItemType File src/export.py -Value @'\na\nb\nc\nd\ne\nf\n'@"
        self.assertEqual(hold_line(self.routed().run(six, tool="PowerShell")), DESIGN_HOLD)
        one = "New-Item -ItemType File src/export.py -Value 'total = 1'"
        self.assertEqual(decision(self.routed().run(one, tool="PowerShell")), "pass")
        # The near miss: New-Item with no value writes no text.
        bare = "New-Item -ItemType File src/export.py"
        self.assertEqual(decision(self.routed().run(bare, tool="PowerShell")), "pass")

    def test_a_shell_write_is_the_turns_first_substantial_change(self) -> None:
        # Review B9: a later edit after a substantial heredoc meets design-reads,
        # and since Ticket 118 lands owing its reads under that gate's name.
        s = self.routed()
        s.load(DESIGN)
        s.run(heredoc("src/a.py", 6))

        definition = "def export(rows):\n" + "\n".join(f"    total_{n} = {n}" for n in range(5))
        landed = s.call("Edit", {"file_path": "src/b.py", "old_string": "pass",
                                 "new_string": definition})
        self.assertEqual(decision(landed), "pass")
        self.assertIn("the design-reads gate let this write", owed(landed))

    def test_shell_written_files_count_toward_the_third_code_file(self) -> None:
        # Review B8 and item 11, both ways round.
        plain = "\n".join(f"total_{n} = {n}" for n in range(6))
        s = self.routed()
        s.load(DESIGN)
        s.run(heredoc("src/a.py", 6))
        s.run(heredoc("src/b.py", 6))
        landed = s.call("Edit", {"file_path": "src/c.py", "old_string": "pass", "new_string": plain})
        self.assertEqual(decision(landed), "pass")
        self.assertIn("the design-reads gate let this write", owed(landed))
        self.assertIn("the third code file this turn edits", owed(landed))

        # A short shell write still meets the hold itself.
        s = self.routed()
        s.load(DESIGN)
        for name in ("a", "b"):
            s.call("Edit", {"file_path": f"src/{name}.py", "old_string": "pass", "new_string": plain})
        held = s.run(heredoc("src/c.py", 6))
        self.assertEqual(hold_line(held), DESIGN_READS_HOLD)
        self.assertIn("the third code file this turn edits", reason(held))

        # The near miss: a third file by copy adds no text, so it is not judged.
        self.assertEqual(decision(s.run("cp src/a.py src/d.py")), "pass")

    def test_a_script_write_stays_with_the_scripted_edit_gate(self) -> None:
        held = self.routed().run("python - <<'EOF'\nopen('src/export.py', 'w').write(text)\nEOF")
        self.assertEqual(hold_line(held), "goated-hold: scripted-edit | justified-skip")
        self.assertNotIn("goated-hold: design", reason(held))


if __name__ == "__main__":
    unittest.main()
