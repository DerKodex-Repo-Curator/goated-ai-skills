"""Ticket 095: every hold a call would meet arrives in one message.

Each test drives the hook entry point with a transcript in Claude Code's
recorded shape (see `claude_code_adapter_support.py`). A joint message keeps
each hold's own `goated-hold: <gate> | <kind>` line, in the order the gates
fire, and gives each shared paragraph once.
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from claude_code_adapter_support import (
    BRIEF,
    REPO_ROOT,
    ROUTER,
    Session,
    decision,
    parse,
    reason,
)

REGISTRY = REPO_ROOT / "stack" / "goated-stack.yaml"
SKILLS = "/opt/goated/skills"
CODING = f"{SKILLS}/software-design-principles/references/coding.md"
MOCKING = f"{SKILLS}/tdd/references/mocking-and-seams.md"
TEST_DESIGN = f"{SKILLS}/tdd/references/test-design.md"
TEST_FILE = "tests/test_export.py"
HOLD_LINE = re.compile(r"^goated-hold: ([a-z-]+) \| ([a-z-]+)$", re.MULTILINE)
FULL_ADVICE = "may not be seen"
CHANGE_READ = "print its diff with a git diff or git show command"
SKIP_DIAGNOSE = "goated-skip: diagnose: the failing check's cause is already known"


def hold_lines(output: dict) -> list[tuple[str, str]]:
    return HOLD_LINE.findall(reason(output))


def gates_of(output: dict) -> list[str]:
    return [gate for gate, _ in hold_lines(output)]


def mocking_edit(*extra: str) -> dict:
    lines = ["client = MagicMock()", *extra, *(f"assert total_{n} == {n}" for n in range(30))]
    return {"file_path": TEST_FILE, "old_string": "pass", "new_string": "\n".join(lines)}


class SessionCase(unittest.TestCase):
    """Sessions routed `direct` in a temporary folder, with this repo's registry."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def session(self, name: str = "s", route: str = "goated-route: direct") -> Session:
        folder = self.root / name
        folder.mkdir()
        s = Session(folder)
        s.config.registry_path = REGISTRY
        s.prompt("Add CSV export.")
        s.load(ROUTER)
        s.say(route)
        return s

    def three_gate_session(self) -> Session:
        """A turn where a test edit meets design-reads, reference-reads and repeated-failure."""

        s = self.session("three")
        s.load("software-design-principles")
        s.load("tdd")
        s.run("pytest -q", success=False)
        s.run("pytest -q", success=False)
        return s


class JointHoldTests(SessionCase):
    """R1: one message carries every hold a call meets, in today's order."""

    def test_a_test_edit_meeting_three_gates_is_held_once_with_all_three(self) -> None:
        s = self.three_gate_session()
        held = s.call("Edit", mocking_edit())
        self.assertEqual(decision(held), "deny")
        self.assertEqual(gates_of(held), ["design-reads", "reference-reads", "repeated-failure"])
        self.assertTrue(reason(held).startswith("goated-hold: design-reads | justified-skip\n"))

    def test_clearing_all_three_lets_the_retry_pass(self) -> None:
        s = self.three_gate_session()
        s.call("Edit", mocking_edit())
        s.read(CODING)
        s.read(MOCKING)
        s.read(TEST_DESIGN)
        s.say(SKIP_DIAGNOSE)
        self.assertEqual(decision(s.call("Edit", mocking_edit())), "pass")

    def test_a_gate_already_met_is_left_out_of_the_joint_message(self) -> None:
        # Near miss: diagnose skipped, so repeated-failure passes and two holds remain.
        s = self.three_gate_session()
        s.say(SKIP_DIAGNOSE)
        held = s.call("Edit", mocking_edit())
        self.assertEqual(gates_of(held), ["design-reads", "reference-reads"])

    def test_a_spawn_meeting_pipeline_and_spawn_is_held_once_with_both(self) -> None:
        s = self.session("spawn", "goated-route: standard | requires: tdd")
        held = s.call("Agent", {"prompt": BRIEF})
        self.assertEqual(hold_lines(held), [("pipeline", "strict"), ("spawn", "strict")])
        # Near miss: with the route's skill loaded, only the spawn hold is left.
        s.load("tdd")
        self.assertEqual(hold_lines(s.call("Agent", {"prompt": BRIEF})), [("spawn", "strict")])

    def test_routing_holds_still_come_one_at_a_time(self) -> None:
        # The route line is the router's output, so route-line waits for router-first.
        folder = self.root / "unrouted"
        folder.mkdir()
        s = Session(folder)
        s.prompt("Add CSV export.")
        self.assertEqual(gates_of(s.call("Edit", {"file_path": "notes.md", "old_string": "a",
                                                  "new_string": "b"})), ["router-first"])


class SharedTextTests(SessionCase):
    """R3: a paragraph several holds or closeout items share appears once in a message."""

    def test_holds_sharing_the_unseen_line_advice_carry_it_once(self) -> None:
        text = reason(self.three_gate_session().call("Edit", mocking_edit()))
        self.assertEqual(text.count(FULL_ADVICE), 1, text)
        # Each hold keeps its own typed way out.
        for way_out in ("skip software-design-principles", "skip diagnose"):
            self.assertIn(f"`{way_out}`", text)

    def changed_and_loaded(self, name: str) -> Session:
        s = self.session(name)
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.call("Write", {"file_path": "src/export.py", "content": "rate = 1\n"})
        s.load("commit-message")
        s.load("pr-description")
        return s

    def test_a_commit_and_pull_request_sharing_the_change_read_carry_it_once(self) -> None:
        s = self.changed_and_loaded("commit-pr")
        held = s.call("Bash", {"command": 'git commit -m "Add export" && gh pr create '
                                          '--title "Add export" --body "Adds it."'})
        self.assertEqual(gates_of(held), ["commit", "pull-request"])
        text = reason(held)
        self.assertEqual(text.count(CHANGE_READ), 1, text)
        self.assertEqual(text.count("rerun any steps chained before it"), 1, text)
        # Near miss: the commit alone still carries both in full.
        alone = reason(self.changed_and_loaded("alone").call(
            "Bash", {"command": 'git commit -m "Add export"'}))
        self.assertIn(CHANGE_READ, alone)
        self.assertIn("rerun any steps chained before it", alone)

    def test_closeout_items_sharing_the_change_read_carry_it_once(self) -> None:
        s = self.session("closeout")
        s.load("software-design-principles")
        s.load("doc-sync")
        s.read(CODING)
        s.call("Edit", {"file_path": "src/export.py", "old_string": "pass",
                        "new_string": "\n".join(f"total_{n} = {n}" for n in range(6))})
        s.run("pytest -q")
        text = stop_reason(s)
        self.assertIn("- Docs:", text)
        self.assertIn("- Design:", text)
        self.assertEqual(text.count(CHANGE_READ), 1, text)


def stop_reason(s: Session) -> str:
    return parse(s.hook("Stop", stop_hook_active=False, last_assistant_message="")).get("reason", "")


class ShortRepeatTests(SessionCase):
    """R3: a gate's second or later hold in a turn is short; the next turn is full again."""

    def closeout_turn(self, name: str) -> Session:
        s = self.session(name)
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.call("Write", {"file_path": "src/export.py", "content": "rate = 1\n"})
        return s

    def test_a_second_stop_hold_lists_only_the_unmet_items_short(self) -> None:
        s = self.closeout_turn("stop")
        first = stop_reason(s)
        self.assertIn("- Proof:", first)
        self.assertIn("- Docs:", first)
        s.run("pytest -q")  # Meets the Proof item.
        second = stop_reason(s)
        self.assertTrue(second.startswith("goated-hold: closeout | justified-skip\n"), second)
        self.assertIn("Still unmet", second)
        self.assertNotIn("- Proof:", second)
        self.assertIn("- Docs:", second)
        self.assertIn("`goated-skip: doc-sync: <reason>`", second)
        self.assertLess(len(second), len(first))
        # The next turn's first hold is full again.
        s.prompt("Also add JSON export.")
        s.say("goated-route: direct")
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.call("Write", {"file_path": "src/export.py", "content": "rate = 2\n"})
        third = stop_reason(s)
        self.assertNotIn("Still unmet", third)
        self.assertIn("- Proof:", third)

    def test_with_the_marker_unwritable_each_hold_is_full(self) -> None:
        s = self.closeout_turn("unwritable")
        (s.config.state_dir / "turn-markers").write_text("", encoding="utf-8")
        first, second = stop_reason(s), stop_reason(s)
        self.assertEqual(first, second)
        self.assertNotIn("Still unmet", second)
        self.assertIn(FULL_ADVICE, reason(s.call("Write", {"file_path": "src/auth.py",
                                                           "content": "key = 1\n"})))

    def test_advice_and_two_gates_claim_apart_in_one_turn(self) -> None:
        s = self.session("purposes")
        auth = {"file_path": "src/auth.py", "content": "key = 1\n"}
        conflict = {"file_path": "notes.md", "old_string": "<<<<<<< HEAD\na\n=======\nb\n>>>>>>> x\n",
                    "new_string": "b\n"}
        security_1 = reason(s.call("Write", auth))
        self.assertIn(FULL_ADVICE, security_1)
        security_2 = reason(s.call("Write", auth))
        conflict_1 = reason(s.call("Edit", conflict))
        conflict_2 = reason(s.call("Edit", conflict))
        self.assertNotIn("Still unmet", security_1)
        self.assertIn("Still unmet", security_2)
        self.assertNotIn("Still unmet", conflict_1)
        self.assertIn("Still unmet", conflict_2)
        for later in (security_2, conflict_1, conflict_2):
            self.assertNotIn(FULL_ADVICE, later)
        self.assertIn("`skip code-security-review`", security_2)
        self.assertIn("`skip resolving-merge-conflicts`", conflict_2)
        # Neither claim erased the other: the security gate is still short.
        self.assertIn("Still unmet", reason(s.call("Write", auth)))
        # The next turn starts with every form full again.
        s.prompt("Next change.")
        s.say("goated-route: direct")
        again = reason(s.call("Write", auth))
        self.assertIn(FULL_ADVICE, again)
        self.assertNotIn("Still unmet", again)
        self.assertNotIn("Still unmet", reason(s.call("Edit", conflict)))


class CarrierTests(SessionCase):
    """R4: a hold a line can clear, on a call with no line field, names a carrier."""

    AUTH = {"file_path": "src/auth.py", "content": "key = 1\n"}
    BASH_CARRIER = "a Bash call with the command true"
    POWERSHELL_CARRIER = "a PowerShell call with the command $null"

    def test_an_edit_hold_names_the_bash_carrier_in_a_bash_session(self) -> None:
        s = self.session("bash")
        s.run("ls")
        text = reason(s.call("Write", self.AUTH))
        self.assertIn(self.BASH_CARRIER, text)
        self.assertNotIn(self.POWERSHELL_CARRIER, text)

    def test_an_edit_hold_names_the_powershell_carrier_in_a_powershell_session(self) -> None:
        s = self.session("powershell")
        s.run("Get-ChildItem", tool="PowerShell")
        text = reason(s.call("Write", self.AUTH))
        self.assertIn(self.POWERSHELL_CARRIER, text)
        self.assertNotIn(self.BASH_CARRIER, text)

    def test_a_call_with_a_line_field_or_a_strict_hold_names_no_carrier(self) -> None:
        s = self.session("fields")
        s.run("ls")
        # Near misses: a shell call has a description, and a strict hold takes no line.
        self.assertNotIn("command true", reason(s.call("Bash", {
            "command": "python - <<'EOF'\nopen(\"src/export.py\", \"w\").write(text)\nEOF"})))
        self.assertNotIn("command true", reason(s.call("Agent", {"prompt": BRIEF})))

    def test_each_carrier_passes_before_and_after_the_router_loads_and_carries_the_line(self) -> None:
        for tool, command in (("Bash", "true"), ("PowerShell", "$null")):
            with self.subTest(tool=tool):
                folder = self.root / tool
                folder.mkdir()
                s = Session(folder)
                s.prompt("Harden the login check.")
                carrier = {"command": command, "description": "goated-route: direct"}
                self.assertEqual(decision(s.call(tool, carrier)), "pass")
                s.load(ROUTER)
                skip = {"command": command, "description":
                        "goated-skip: code-security-review: constant with no trust boundary"}
                self.assertEqual(decision(s.call(tool, skip)), "pass")
                self.assertEqual(decision(s.call("Write", self.AUTH)), "pass")


if __name__ == "__main__":
    unittest.main()
