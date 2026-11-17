"""Routing lets reads through (Ticket 055).

Before the router loads, `router-first` passes a shell command made only of
plainly read-only commands, as it passes Read and Grep. A spawn of a
read-only subagent type (`Explore`, `Plan`, `claude-code-guide`) passes the
`pipeline` and `spawn` holds, but still needs the router and a route line.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from claude_code_adapter_support import BRIEF, ROUTER, Session, decision, reason

# Each passes before the router loads.
READS = [
    ("Bash", "cat a.py"),
    ("Bash", "git diff"),
    ("Bash", "grep -n x a.py | head"),
    ("PowerShell", "Get-Content a.py"),
    ("Bash", "head -n 20 a.py && tail a.py; wc -l a.py"),
    ("Bash", "ls -la src"),
    ("Bash", "rg -n 'a > b' src"),
    ("Bash", "find . -name '*.py'"),
    ("Bash", "git status --short"),
    ("Bash", "git log --oneline -5"),
    ("Bash", "git show HEAD:a.py"),
    ("Bash", "git -C sub diff --stat"),
    ("Bash", "grep -rn x src 2>/dev/null | wc -l"),
    ("PowerShell", "Get-ChildItem -Recurse src | Select-String -Pattern 'x'"),
    ("PowerShell", "gci src; gc a.py"),
    ("Bash", "cat 'a; rm b'"),
]

# Each is held before the router loads: the near misses of a read.
HELD = [
    ("Bash", "cat a > b"),
    ("Bash", "cat a >> b"),
    ("Bash", "find . -delete"),
    ("Bash", "find . -exec rm {} +"),
    ("Bash", "find . -execdir cat {} ;"),
    ("Bash", "find . -fprint out.txt"),
    ("Bash", "pytest"),
    ("Bash", "git push"),
    ("Bash", "git diff --output=patch.txt"),
    ("Bash", "git diff --output patch.txt"),
    ("Bash", "git -c core.pager=sh diff"),
    ("Bash", "git stash"),
    ("Bash", "cat $(make-it)"),
    ("Bash", "cat $(ls)"),
    ("Bash", "cat `ls`"),
    ("Bash", "cat <(ls)"),
    ("Bash", "grep -l x a.py | xargs rm"),
    ("Bash", "cat a.py | tee b.py"),
    ("Bash", "cat a.py | sh"),
    ("Bash", "(cat a.py)"),
    ("Bash", "cat a.py &"),
    ("Bash", "sudo cat a.py"),
    ("Bash", "X=1 cat a.py"),
    ("Bash", "rg --pre ./run.sh x"),
    ("Bash", "cat <<EOF\nhi\nEOF"),
    ("Bash", "make-it"),
    ("Bash", "python - <<'EOF'\nprint(1)\nEOF"),
    ("Bash", ""),
    ("PowerShell", "Get-Content a.py | Set-Content b.py"),
    ("PowerShell", "Get-Content a.py > b.py"),
    ("PowerShell", "Get-ChildItem | Remove-Item"),
    ("PowerShell", "Get-Content $(New-Item x)"),
    ("PowerShell", "gci | % { $_.Name }"),
]


def hold_line(output: dict) -> str:
    return reason(output).split("\n", 1)[0]


def spawn(subagent_type: str | None) -> dict:
    tool_input = {"prompt": BRIEF, "description": "Search the exporter"}
    if subagent_type is not None:
        tool_input["subagent_type"] = subagent_type
    return tool_input


class ReadsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._sessions = 0

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def fresh(self) -> Session:
        """A new session whose prompt has just been typed, router not loaded."""

        self._sessions += 1
        folder = self.root / f"s{self._sessions}"
        folder.mkdir()
        s = Session(folder, session_id=f"reads-{self._sessions}")
        s.prompt("What does the exporter do?")
        return s

    def routed(self) -> Session:
        s = self.fresh()
        s.load(ROUTER)
        s.say("goated-route: standard | requires: write-a-spec, spec-to-tickets")
        return s


class ShellReadsBeforeTheRouterTests(ReadsTestCase):
    def test_plainly_read_only_commands_pass_router_first(self) -> None:
        for tool, command in READS:
            with self.subTest(command=command):
                s = self.fresh()
                self.assertEqual(decision(s.call(tool, {"command": command})), "pass")

    def test_anything_else_is_held_by_router_first(self) -> None:
        for tool, command in HELD:
            with self.subTest(command=command):
                s = self.fresh()
                held = s.call(tool, {"command": command})
                self.assertEqual(hold_line(held), "goated-hold: router-first | strict")

    def test_once_the_router_loads_routing_behaves_as_before(self) -> None:
        s = self.fresh()
        s.load(ROUTER)
        self.assertEqual(decision(s.call("Bash", {"command": "cat a.py"})), "pass")
        self.assertEqual(decision(s.call("Bash", {"command": "pytest"})), "pass")
        held = s.call("Bash", {"command": "cat a > b"})
        self.assertEqual(hold_line(held), "goated-hold: route-line | strict")

    def test_the_hold_says_which_shell_reads_pass(self) -> None:
        held = reason(self.fresh().call("Bash", {"command": "pytest"}))
        self.assertIn("Reads stay free", held)
        self.assertIn("read-only", held)


class ReadOnlySpawnTests(ReadsTestCase):
    def test_read_only_subagents_pass_pipeline_and_spawn(self) -> None:
        for kind in ("Explore", "Plan", "claude-code-guide"):
            for tool in ("Agent", "Task"):
                with self.subTest(kind=kind, tool=tool):
                    s = self.routed()
                    self.assertEqual(decision(s.call(tool, spawn(kind))), "pass")

    def test_other_subagents_are_still_held(self) -> None:
        for kind in ("general-purpose", None, "explore", "Explorer"):
            with self.subTest(kind=kind):
                s = self.routed()
                held = s.call("Agent", spawn(kind))
                self.assertEqual(hold_line(held), "goated-hold: pipeline | strict")
                s.load("write-a-spec")
                s.load("spec-to-tickets")
                held = s.call("Agent", spawn(kind))
                self.assertEqual(hold_line(held), "goated-hold: spawn | strict")

    def test_side_sessions_are_unchanged(self) -> None:
        s = self.routed()
        tool_input = {"prompt": BRIEF, "subagent_type": "Explore"}
        held = s.call("mcp__ccd_session__start_session", tool_input)
        self.assertEqual(hold_line(held), "goated-hold: pipeline | strict")

    def test_a_read_only_spawn_still_needs_a_route_line(self) -> None:
        s = self.fresh()
        s.load(ROUTER)
        held = s.call("Agent", spawn("Explore"))
        self.assertEqual(hold_line(held), "goated-hold: route-line | strict")

    def test_a_read_only_spawn_still_needs_the_router(self) -> None:
        held = self.fresh().call("Agent", spawn("Explore"))
        self.assertEqual(hold_line(held), "goated-hold: router-first | strict")


if __name__ == "__main__":
    unittest.main()
