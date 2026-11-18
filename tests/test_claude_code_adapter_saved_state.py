"""Session state an adapter saved before the shared core keeps working (Ticket 081).

Before the core, the adapter keyed its override record by Claude Code's
`prompt_id` and, before Ticket 080, saved the session's last shell as its
tool name. The core keys the record by an opaque `prompt` and saves a shell
kind; the adapter upgrades older files as they load, so a session that
spans the upgrade is judged as before.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from claude_code_adapter_support import ROUTER, Session, decision, reason


def _save_old_state(s: Session, **fields) -> None:
    s.config.state_dir.mkdir(parents=True, exist_ok=True)
    (s.config.state_dir / f"{s.session_id}.json").write_text(json.dumps(fields), encoding="utf-8")


def _old_overrides(prompt_id: str) -> dict:
    return {"prompt_id": prompt_id, "routing": True, "skills": [], "commit_message": None,
            "phrases": ["skip routing"]}


class SavedStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.s = Session(Path(self._tmp.name))
        self.s.project.mkdir(parents=True)
        self.edit = {"file_path": str(self.s.project / "notes.md"), "old_string": "a",
                     "new_string": "b"}

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_an_override_saved_under_the_old_key_applies_to_its_prompt(self) -> None:
        self.s.prompt("Tidy the notes.", hook=False)
        _save_old_state(self.s, overrides=_old_overrides(self.s.prompt_id))

        self.assertEqual(decision(self.s.call("Edit", self.edit)), "pass")

    def test_an_override_saved_under_the_old_key_skips_another_prompt(self) -> None:
        # The near miss: the record names an earlier prompt.
        self.s.prompt("Tidy the notes.", hook=False)
        _save_old_state(self.s, overrides=_old_overrides("an-earlier-prompt"))

        self.assertIn("goated-hold: router-first", reason(self.s.call("Edit", self.edit)))

    def test_a_shell_saved_as_its_tool_name_names_that_tool_s_carrier(self) -> None:
        self.s.prompt("Tidy the notes.", hook=False)
        self.s.load(ROUTER)
        _save_old_state(self.s, shell="PowerShell", router_loaded=True)

        held = reason(self.s.call("Edit", self.edit))
        self.assertIn("goated-hold: route-line", held)
        self.assertIn("in the description of a PowerShell call", held)


if __name__ == "__main__":
    unittest.main()
