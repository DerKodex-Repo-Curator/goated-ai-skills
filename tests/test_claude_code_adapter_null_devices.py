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

    def test_the_same_redirect_in_powershell_is_no_write(self) -> None:
        passed = self.session.call("PowerShell", {"command": "echo x > nul"})
        self.assertEqual(decision(passed), "pass")


if __name__ == "__main__":
    unittest.main()
