"""Routing lets reads through (Ticket 055).

Before the router loads, `router-first` passes a shell command made only of
plainly read-only commands, as it passes Read and Grep. A spawn of a
read-only subagent type (`claude-code-guide`) passes the
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
    # Near misses of the review probes in HELD.
    ("Bash", "cat a 2>&1"),
    ("Bash", "cat a >&2"),
    ("Bash", "cat a 2>&-"),
    ("Bash", 'cat "a b"'),
    ("Bash", "find . -name b"),
    ("Bash", "git diff --stat"),
    ("Bash", "git log -p"),
    ("Bash", "tail -n 5 a.py"),
    ("PowerShell", "Get-Content a|Select-String x"),
    ("PowerShell", 'Get-Content "a.py"'),
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
    # Review probes: each passed the first version in a real shell, yet writes
    # or deletes a file.
    ("Bash", "cat a >&out.txt"),
    ("Bash", "cat a >& out.txt"),
    ("Bash", "cat a 1>&out.txt"),
    ("Bash", 'cat "$(touch x)"'),
    ("Bash", 'cat "a$(touch x)"'),
    ("Bash", 'cat <<< "$(touch x)"'),
    ("Bash", "cat <<< x"),
    ("Bash", "cat a ${x:=$(touch y)}"),
    ("Bash", 'cat "${x:-$(touch y)}"'),
    ("Bash", "cat $(( $(touch x) ))"),
    ("Bash", "cat $HOME/a"),
    ("Bash", r"find . -name b -del\ete"),
    ("Bash", r"find . -name a -fpr\int x"),
    ("Bash", r"git diff --out\put=x"),
    ("Bash", "git diff --ext-diff"),
    ("Bash", "git log -p --textconv"),
    ("Bash", "./cat a"),
    ("Bash", "./git status"),
    ("Bash", "cat.cmd a"),
    ("Bash", r"C:\evil\ls.bat"),
    ("Bash", "/bin/cat a"),
    ("PowerShell", 'Get-Content "$(Remove-Item b)"'),
    ("PowerShell", '$x = @"\n$(Remove-Item b)\n"@\nGet-Content a'),
    ("PowerShell", '@"\nb\n"@ | Get-Content'),
    ("PowerShell", r"Get-Content a\; Remove-Item b"),
    ("PowerShell", r'Get-Content "a\" ; Remove-Item b ; echo "\"'),
    ("PowerShell", "Get-Content a|Remove-Item"),
    ("PowerShell", "Get-Content a\rRemove-Item b"),
    ("PowerShell", "Get-Content a\x00"),
    ("PowerShell", r"Get-Content src\a.py"),
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

    def test_a_redirect_to_a_named_descriptor_writes_after_the_router_too(self) -> None:
        # `>&word` with a word that is not a number writes that file, as `&>` does.
        for command in ("cat a >&out.txt", "cat a >& out.txt", "cat a 1>&out.txt"):
            with self.subTest(command=command):
                s = self.fresh()
                s.load(ROUTER)
                held = s.call("Bash", {"command": command})
                self.assertEqual(hold_line(held), "goated-hold: route-line | strict")
        for command in ("cat a >&2", "cat a 2>&-"):
            with self.subTest(command=command):
                s = self.fresh()
                s.load(ROUTER)
                self.assertEqual(decision(s.call("Bash", {"command": command})), "pass")

    def test_the_hold_says_which_shell_reads_pass(self) -> None:
        held = reason(self.fresh().call("Bash", {"command": "pytest"}))
        self.assertIn("Reads stay free", held)
        self.assertIn("read-only", held)


class ReadOnlySpawnTests(ReadsTestCase):
    def test_read_only_subagents_pass_pipeline_and_spawn(self) -> None:
        for tool in ("Agent", "Task"):
            with self.subTest(tool=tool):
                s = self.routed()
                self.assertEqual(decision(s.call(tool, spawn("claude-code-guide"))), "pass")

    def test_other_subagents_are_still_held(self) -> None:
        # Explore and Plan keep Bash and PowerShell, and a subagent's own calls
        # meet no routing, so spawning one is not delegating reads.
        for kind in ("Explore", "Plan", "general-purpose", None, "Claude-Code-Guide"):
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
        tool_input = {"prompt": BRIEF, "subagent_type": "claude-code-guide"}
        held = s.call("mcp__ccd_session__start_session", tool_input)
        self.assertEqual(hold_line(held), "goated-hold: pipeline | strict")

    def test_a_read_only_spawn_still_needs_a_route_line(self) -> None:
        s = self.fresh()
        s.load(ROUTER)
        held = s.call("Agent", spawn("claude-code-guide"))
        self.assertEqual(hold_line(held), "goated-hold: route-line | strict")

    def test_a_read_only_spawn_still_needs_the_router(self) -> None:
        held = self.fresh().call("Agent", spawn("claude-code-guide"))
        self.assertEqual(hold_line(held), "goated-hold: router-first | strict")


if __name__ == "__main__":
    unittest.main()
