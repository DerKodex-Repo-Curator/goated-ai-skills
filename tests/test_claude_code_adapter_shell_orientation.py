"""Whole shell prints orient a briefed session (Ticket 110, spec R1).

A finished, successful shell command whose plain file printer prints a file
whole counts as a whole read of that file toward the `pipeline` gate's three
distinct files: `cat`, or PowerShell's `Get-Content`, `gc` or `type` without
`-TotalCount`, `-Head`, `-First`, `-Tail` or `-Last`, its output not piped
into another command. Every other rule that asks for a whole read keeps
asking for a file read.
"""

from __future__ import annotations

import unittest

from claude_code_adapter_support import decision, owed_names
from goated_core import shell
from goated_core.events import POSIX, POWERSHELL
from test_claude_code_adapter_briefs import ORIENTATION, BriefTestCase, hold_line, reason
from test_claude_code_adapter_design_holds import (
    DEFINITION, DEFINITION_REFERENCES, DESIGN, REFERENCES, DesignTestCase, edit,
)
from test_claude_code_adapter_low_signal_routing import EDIT, PIPELINE, OrientationByReadsTests


class OrientedTestCase(BriefTestCase):
    """The orientation tests' setup and briefed session, without their tests:
    the orientation skill installed, not loaded."""

    def setUp(self) -> None:
        super().setUp()
        folder = self.session.config.home / ".claude" / "skills" / ORIENTATION
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")

    full_brief = OrientationByReadsTests.full_brief


class WholePrintTests(unittest.TestCase):
    """Which files a command prints whole, read by the core's shell reading."""

    def whole(self, command: str, kind: str = POSIX) -> list[str]:
        return shell.analyze(command, kind).whole_prints

    def test_cat_prints_each_file_it_names_whole(self) -> None:
        self.assertEqual(self.whole("cat a.md b.md c.md"), ["a.md", "b.md", "c.md"])
        self.assertEqual(self.whole("cat -n a.md"), ["a.md"])

    def test_get_content_and_its_aliases_print_whole_without_a_range(self) -> None:
        for command in ("Get-Content a.md", "gc a.md", "type a.md", "Get-Content -Path a.md -Raw",
                        "cat a.md"):
            with self.subTest(command=command):
                self.assertEqual(self.whole(command, POWERSHELL), ["a.md"])

    def test_a_range_parameter_prints_part(self) -> None:
        for parameter in ("-TotalCount 5", "-Head 5", "-First 5", "-Tail 5", "-Last 5",
                          "-totalcount:5"):
            with self.subTest(parameter=parameter):
                self.assertEqual(self.whole(f"Get-Content a.md {parameter}", POWERSHELL), [])
        # In PowerShell `cat` is Get-Content, so it takes the same range.
        self.assertEqual(self.whole("cat a.md -Tail 5", POWERSHELL), [])

    def test_partial_printers_and_other_commands_print_nothing_whole(self) -> None:
        # `type` in Bash describes commands, so it prints no file.
        for command in ("head a.md", "tail a.md", "sed -n 1,50p a.md", "grep x a.md",
                        "less a.md", "type a.md"):
            with self.subTest(command=command):
                self.assertEqual(self.whole(command), [])

    def test_a_print_piped_on_or_redirected_is_not_shown_whole(self) -> None:
        self.assertEqual(self.whole("cat a.md | head"), [])
        self.assertEqual(self.whole("cat a.md > b.md"), [])
        self.assertEqual(self.whole("Get-Content a.md | Select-Object -First 5", POWERSHELL), [])
        # A background job may still be printing when the command returns.
        self.assertEqual(self.whole("cat a.md &"), [])
        # Inside a substitution or group, the output is captured or may not run.
        self.assertEqual(self.whole("echo $(cat a.md)"), [])
        self.assertEqual(self.whole("if true; then cat a.md; fi"), [])
        # A stderr redirect leaves the print shown.
        self.assertEqual(self.whole("cat a.md 2>/dev/null"), ["a.md"])
        # The last command of a pipeline prints to the agent.
        self.assertEqual(self.whole("echo x | cat a.md"), ["a.md"])

    def test_a_print_counts_only_when_its_exit_status_is_the_commands(self) -> None:
        """A finished command's success proves a print only when nothing after
        it but `&&` (or a pipe after a later command) can set its exit status."""

        for command in ("cat a.md || true", "cat a.md; echo ok", "cat a.md; true",
                        "cat a.md\ntrue", "cat a.md && true || true"):
            with self.subTest(command=command):
                self.assertEqual(self.whole(command), [])
        self.assertEqual(self.whole("cat a.md && cat b.md"), ["a.md", "b.md"])
        self.assertEqual(self.whole("true; cat a.md"), ["a.md"])
        self.assertEqual(self.whole("cat a.md && git status | head"), ["a.md"])

    def test_option_values_are_not_files(self) -> None:
        for command in ("Get-Content a.md -ErrorAction SilentlyContinue", "gc a.md -EA 0",
                        "Get-Content a.md -WarningAction Ignore", "gc a.md -WA 0",
                        "Get-Content a.md -OutVariable out", "gc a.md -OV out",
                        "Get-Content a.md -ErrorVariable err", "gc a.md -EV err"):
            with self.subTest(command=command):
                self.assertEqual(self.whole(command, POWERSHELL), ["a.md"])

    def test_a_shortened_range_parameter_prints_part(self) -> None:
        for parameter in ("-Tot 5", "-T 5", "-Ta 5", "-He 5", "-Fir 5"):
            with self.subTest(parameter=parameter):
                self.assertEqual(self.whole(f"Get-Content a.md {parameter}", POWERSHELL), [])

    def test_a_word_the_shell_expands_names_no_one_file(self) -> None:
        for word in ("*.py", "src/?.py", "[ab].md", "$HOME/a.md", "~/a.md"):
            with self.subTest(word=word):
                self.assertEqual(self.whole(f"cat {word} c.md"), ["c.md"])
        self.assertEqual(self.whole("cat {a,b}.md"), [])

    def test_a_print_is_named_from_where_the_command_started(self) -> None:
        self.assertEqual(self.whole("cd ./src && cat a.py"), ["src/a.py"])
        self.assertEqual(self.whole("cat /abs/a.py"), ["/abs/a.py"])
        # From a folder the command left unknown, the file cannot be named:
        # a `cd` that may have failed, or a bare name Bash may find through CDPATH.
        self.assertEqual(self.whole("cd ./src; cat a.py"), [])
        self.assertEqual(self.whole("cd src && cat a.py"), [])


class ShellOrientationTests(OrientedTestCase):
    """Through the Claude Code hook, in a briefed `full` session with the
    orientation skill installed and not loaded."""

    def test_three_cats_of_distinct_files_meet_orientation(self) -> None:
        s = self.full_brief()
        for name in ("a.md", "b.md", "c.md"):
            s.run(f"cat {name}")

        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_one_cat_of_three_files_meets_orientation(self) -> None:
        s = self.full_brief()
        s.run("cat a.md b.md c.md")

        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_get_content_counts(self) -> None:
        s = self.full_brief()
        # After `;` only the last print's status is the command's.
        s.run("Get-Content a.md; Get-Content b.md; gc c.md", tool="PowerShell")
        s.run("Get-Content a.md", tool="PowerShell")
        self.assertEqual(hold_line(s.call("Edit", EDIT)), PIPELINE)

        s.run("type b.md", tool="PowerShell")
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_partial_prints_do_not_count(self) -> None:
        s = self.full_brief()
        s.run("cat a.md")
        for command in ("head b.md", "sed -n 1,50p b.md", "grep x b.md", "cat b.md | head"):
            s.run(command)
        s.run("Get-Content b.md -TotalCount 5", tool="PowerShell")

        self.assertEqual(hold_line(s.call("Edit", EDIT)), PIPELINE)
        s.run("Get-Content b.md", tool="PowerShell")
        self.assertEqual(hold_line(s.call("Edit", EDIT)), PIPELINE)
        s.run("cat c.md")
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_a_failed_command_does_not_count(self) -> None:
        s = self.full_brief()
        s.run("cat a.md b.md")
        s.run("cat c.md", success=False)

        self.assertEqual(hold_line(s.call("Edit", EDIT)), PIPELINE)

    def test_a_command_still_running_does_not_count(self) -> None:
        s = self.full_brief()
        s.run("cat a.md b.md")
        s.call("Bash", {"command": "cat c.md", "run_in_background": True},
               result="Command running in background with ID: b1")

        self.assertEqual(hold_line(s.call("Edit", EDIT)), PIPELINE)

    def test_a_print_and_a_read_of_one_file_count_once(self) -> None:
        s = self.full_brief()
        s.run("cat src/a.py")
        s.read(str(self.session.project / "src" / "a.py"))
        s.run("cat ./src/a.py")

        self.assertEqual(hold_line(s.call("Edit", EDIT)), PIPELINE)
        s.run("cat b.md")
        self.assertEqual(hold_line(s.call("Edit", EDIT)), PIPELINE)
        s.read(str(self.session.project / "c.md"))
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_the_hold_says_a_whole_shell_print_counts(self) -> None:
        s = self.full_brief()

        held = reason(s.call("Edit", EDIT))
        self.assertIn(f"loads `{ORIENTATION}`", held)
        self.assertIn("shell command that prints a file whole", held)


class ShellPrintsMeetNoReferenceTests(DesignTestCase):
    def test_a_shell_print_of_a_design_reference_does_not_count(self) -> None:
        s = self.routed()
        s.load(DESIGN)
        s.run("cat " + " ".join(REFERENCES + name for name in DEFINITION_REFERENCES))

        # The edit lands (Ticket 118), still owing every reference the print showed.
        landed = s.call("Edit", edit("src/export.py", DEFINITION))
        self.assertEqual(decision(landed), "pass")
        self.assertEqual(owed_names(landed), set(DEFINITION_REFERENCES))


if __name__ == "__main__":
    unittest.main()
