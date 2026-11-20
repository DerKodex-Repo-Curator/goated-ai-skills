"""Behavior tests for null devices per shell (Ticket 104, decision F1).

`nul` is the null device in PowerShell, but in a posix shell a redirect
into it writes a file named `nul`, so the core reads it as a write there,
and a hold it meets names `/dev/null` as the posix null device. Like the
other adapter tests, these drive the hook entry point (see
`claude_code_adapter_support.py`), with a direct look at `shell.analyze`.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from claude_code_adapter_support import ROUTER, Session, decision, parse, reason
from goated_core import shell
from goated_core.events import POSIX, POWERSHELL


class NullDeviceReadingTests(unittest.TestCase):
    def test_a_posix_redirect_into_nul_writes_a_file_named_nul(self) -> None:
        for command in ("echo x > nul", "echo x > NUL", "make 2>nul"):
            with self.subTest(command=command):
                result = shell.analyze(command, POSIX)
                self.assertTrue(result.writes)
                self.assertEqual([t.lower() for t in result.write_targets], ["nul"])

    def test_nul_stays_a_null_device_in_powershell(self) -> None:
        for command in ("echo x > nul", "echo x > NUL", "make 2>nul"):
            with self.subTest(command=command):
                self.assertFalse(shell.analyze(command, POWERSHELL).writes)

    def test_the_posix_null_device_writes_nothing(self) -> None:
        self.assertFalse(shell.analyze("echo x > /dev/null", POSIX).writes)


class NullDeviceHoldTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.session = Session(Path(self._tmp.name))
        self.session.prompt("Quiet the build.")
        self.session.load(ROUTER)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_a_posix_redirect_into_nul_is_held_and_names_dev_null(self) -> None:
        held = self.session.call("Bash", {"command": "echo x > nul"})
        self.assertEqual(decision(held), "deny")
        self.assertTrue(reason(held).startswith("goated-hold: route-line"))
        self.assertIn("/dev/null", reason(held))

    def test_the_nul_note_stands_for_the_part_that_made_a_write(self) -> None:
        held = reason(self.session.call("Bash", {"command": "echo x > nul"}))
        self.assertNotIn("no plain read because of", held)

    def test_the_same_redirect_in_powershell_is_no_write(self) -> None:
        passed = self.session.call("PowerShell", {"command": "echo x > nul"})
        self.assertEqual(decision(passed), "pass")


class ReadLookingWriteTests(unittest.TestCase):
    """A command made of read commands that is still held names what made it
    no plain read (round 6, R11)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.session = Session(Path(self._tmp.name))
        self.session.prompt("Look at the notes.")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_a_held_read_looking_command_names_the_part_that_made_it_a_write(self) -> None:
        for command, part in (
            ("cat notes.md > copy.md", 'the redirect into "copy.md"'),
            ("grep -n x notes.md &", "the background job (&)"),
            ("find . -name '*.md' -delete", 'the argument "-delete"'),
            ("sudo cat notes.md", '"sudo" before the command'),
            ("git branch -D old", '"git branch -D old"'),
        ):
            with self.subTest(command=command):
                held = reason(self.session.call("Bash", {"command": command}))
                self.assertIn(f"because of {part}", held)

    def test_a_command_that_does_not_look_like_a_read_names_no_part(self) -> None:
        held = reason(self.session.call("Bash", {"command": "python build.py"}))
        self.assertTrue(held.startswith("goated-hold: router-first"))
        self.assertNotIn("because of", held)

    def test_the_part_is_read_from_the_shell_analysis(self) -> None:
        self.assertEqual(shell.analyze("ls; cat a > b").write_part, 'the redirect into "b"')
        self.assertIsNone(shell.analyze("cat a").write_part)
        self.assertIsNone(shell.analyze("make > log").write_part)
        self.assertEqual(shell.analyze("echo `date`").write_part,
                         "a backtick, which this reading cannot follow as the shell does")


if __name__ == "__main__":
    unittest.main()
