"""Ticket 114: a large write lands past the read gates and reads after.

A write that `design-reads` or `reference-reads` would hold for reads alone,
adding thirty or more counted lines, is applied with a `reads_owed` notice,
and the closeout's Reads item then asks for the reads and a change read
after them. Each test drives the Claude Code hook entry point with a
transcript in Claude Code's recorded shape (`claude_code_adapter_support.py`),
so the owed reads also cross the core's saved state between hook calls.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from claude_code_adapter_support import REPO_ROOT, ROUTER, Session, decision, parse, reason

DESIGN = "software-design-principles"
DECOUPLING = f"/opt/goated/skills/{DESIGN}/references/decoupling.md"
SETTINGS = "config/export.json"


def settings(lines: int) -> dict:
    """A whole-file write of a settings file the gates count as `lines` lines."""

    keys = [f'  "key_{n:02d}": {n},' for n in range(lines - 3)]
    keys[-1] = keys[-1].rstrip(",")
    return {"file_path": SETTINGS, "content": "{\n" + "\n".join(keys) + "\n}\n"}


def context(output: dict) -> str:
    return output.get("hookSpecificOutput", {}).get("additionalContext", "")


def hold_line(output: dict) -> str:
    return reason(output).split("\n", 1)[0]


class LargeWriteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.session = Session(Path(self._tmp.name))
        self.session.config.registry_path = REPO_ROOT / "stack" / "goated-stack.yaml"
        self.session.prompt("Add the export settings.")
        self.session.load(ROUTER)
        self.session.say("goated-route: direct")
        self.session.load(DESIGN)

    def stop(self) -> dict:
        return parse(self.session.hook("Stop", stop_hook_active=False,
                                       last_assistant_message=""))

    def test_a_large_write_lands_and_the_stop_asks_for_its_read_then_a_change_read(self) -> None:
        landed = self.session.call("Write", settings(40))
        self.assertEqual(decision(landed), "pass", reason(landed))
        self.assertIn(f"`{DESIGN}/references/decoupling.md`", context(landed))
        self.assertIn("Reads item", context(landed))

        unread = self.stop()
        self.assertEqual(unread.get("decision"), "block")
        self.assertIn("- Reads: read each", unread["reason"])
        self.assertIn(f"`{DESIGN}/references/decoupling.md`", unread["reason"])

        self.session.read(DECOUPLING)
        unrevised = self.stop()
        self.assertIn("after reading the references it needed, and revise it", unrevised.get("reason", ""))

        self.session.read(SETTINGS)
        self.assertNotIn("decision", self.stop())

    def test_a_file_write_of_twenty_nine_lines_lands_too(self) -> None:
        # Ticket 118: a file edit lands at any size, owing its reads.
        landed = self.session.call("Write", settings(29))
        self.assertEqual(decision(landed), "pass", reason(landed))
        self.assertIn(f"`{DESIGN}/references/decoupling.md`", context(landed))

    def test_a_shell_write_keeps_the_thirty_line_floor(self) -> None:
        # Shell writes are out of Ticket 118's scope: one under thirty counted
        # lines is still held, and one of thirty or more lands owing its reads.
        for lines, held in ((29, True), (30, False)):
            with self.subTest(lines=lines):
                body = settings(lines + 1)["content"].rstrip("\n")
                output = self.session.call("Bash", {
                    "command": f"cat > {SETTINGS} <<'EOF'\n{body}\nEOF"})
                if held:
                    self.assertEqual(hold_line(output), "goated-hold: design-reads | justified-skip")
                else:
                    self.assertEqual(decision(output), "pass", reason(output))
                    self.assertIn("Reads item", context(output))

    def test_a_subagents_large_write_is_still_held(self) -> None:
        # Only the main agent keeps what a write owes, so a subagent's write cannot land.
        agent = self.session.subagent("a4")
        agent.prompt("Add the export settings.", hook=False)
        agent.load(DESIGN)
        held = agent.call("Write", settings(40), agent_id="a4", agent_type="general-purpose")
        self.assertEqual(hold_line(held), "goated-hold: design-reads | justified-skip")


if __name__ == "__main__":
    unittest.main()
