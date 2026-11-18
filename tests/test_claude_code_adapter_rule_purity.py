"""The shared core names nothing of Claude Code (Tickets 080 and 081).

ADR 0004 makes the event model the one seam: the rules, in the core at
`adapters/core/`, read calls by kind and turns as entries, and only the
Claude Code adapter's translation layer (`translation.py`), transcript
reader (`transcript.py`), and hook entry point (`hooks.py`) know Claude
Code's tool names, transcript fields, and hook fields. This check reads each
core module's code, docstrings and comments aside, and fails on any of those
names in a string or an identifier, on prose that names a tool ("the Edit
tool"), and on a path into Claude Code's own folder. It also fails on an
import of anything but the standard library and the core itself.

The names come from the harness modules themselves: every distinctive name
in their strings, so a name the translation learns is checked at once, plus
the names below that the translation does not read yet.
"""

from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path

from claude_code_adapter_support import ADAPTER_DIR, REPO_ROOT

PACKAGE = ADAPTER_DIR / "goated_adapter"
CORE_DIR = REPO_ROOT / "adapters" / "core"
CORE_PACKAGE = "goated_core"
# The Claude Code modules that know Claude Code, whose names make the denylist.
TRANSLATING_MODULES = ("translation.py", "transcript.py", "hooks.py")

# A distinctive name: snake_case, camelCase, a compound like `PreToolUse`, or
# an MCP tool name. A plain word such as `command` or `head` is also the
# event model's or git's, so it is never taken from the harness modules.
DISTINCTIVE_RE = re.compile(
    r"^(?:[a-z]+(?:_[a-z]+)+|[a-z]+(?:[A-Z][a-z]+)+|[A-Z][a-z]+(?:[A-Z][a-z]+)+|mcp__\w+)$")
# Distinctive names the harness modules hold that are also the event
# model's own or the adapter's settings, which the rules may use.
SHARED = frozenset({
    "agent_id", "line_text", "starts_session", "session_id", "prompt_ids", "project_dir",
    "state_dir", "skill_namespaces", "lag_wait_seconds", "registry_path", "registry_named",
    "own_initiative", "task_notification",
})
# Claude Code names the translation does not read yet.
MORE_NAMES = frozenset({
    "hookSpecificOutput", "systemMessage", "SubagentStop", "SubagentStart", "queued_command",
    "host_synthetic", "attachment", "edit_mode", "cell_id", "TodoWrite", "ExitPlanMode",
    "WebFetch", "WebSearch", "claude-code-guide", "system-reminder", "pasted_content",
    "command-name", "task-notification", "agent-message", "cross-session-message",
    "local-command-stdout",
})
# Claude Code's one-word tool names. Inside text they are words, so a
# string counts only when it is one of them, or names one as "the X tool".
# `Task`, the spawn tool's old name, is left out: it is also a brief heading.
TOOL_WORDS = frozenset({
    "Edit", "Write", "Read", "Bash", "Agent", "Skill", "Stop", "Glob", "Grep",
})
TOOL_PROSE_RE = re.compile(r"\bthe ([A-Z][A-Za-z]+) tool\b")
CLAUDE_FOLDER_RE = re.compile(r"(?:^|[/\\~])\.claude\b")


def _strings(tree: ast.AST) -> list[ast.Constant]:
    """Every string constant of `tree` that is not a docstring."""

    docstrings = {
        id(node.body[0].value) for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }
    return [node for node in ast.walk(tree) if isinstance(node, ast.Constant)
            and isinstance(node.value, str) and id(node) not in docstrings]


def harness_names() -> frozenset[str]:
    """The distinctive names in the translating modules' strings, the shared
    ones aside, with `MORE_NAMES`."""

    names = set(MORE_NAMES)
    for module in TRANSLATING_MODULES:
        tree = ast.parse((PACKAGE / module).read_text(encoding="utf-8"))
        names |= {node.value for node in _strings(tree) if DISTINCTIVE_RE.match(node.value)}
    return frozenset(names - SHARED)


def findings(source: str, names: frozenset[str], allowed: frozenset[str] = frozenset()) -> list[str]:
    """Each Claude Code name in the code of `source`, docstrings aside, as
    `line: name`, in the order the syntax tree is walked."""

    anywhere = re.compile(r"(?<![\w-])(?:%s)(?![\w-])" % "|".join(map(re.escape, sorted(names))))
    tree = ast.parse(source)
    strings = {id(node) for node in _strings(tree)}
    found = []
    for node in ast.walk(tree):
        if id(node) in strings:
            text = node.value
            hits = set(anywhere.findall(text)) | ({text} & TOOL_WORDS)
            hits |= set(TOOL_PROSE_RE.findall(text))
            if "mcp__" in text:
                hits.add("mcp__")
            if CLAUDE_FOLDER_RE.search(text):
                hits.add(".claude")
            found += [f"{node.lineno}: {name}" for name in sorted(hits - allowed)]
        else:
            name = (node.id if isinstance(node, ast.Name) else node.arg if isinstance(node, ast.arg)
                    else node.attr if isinstance(node, ast.Attribute) else None)
            if name in names and name not in allowed:
                found.append(f"{node.lineno}: {name}")
    return found


def core_modules() -> list[Path]:
    """Every Python file of the core: its package and the command beside it."""

    return sorted(CORE_DIR.rglob("*.py"))


def foreign_imports(source: str) -> list[str]:
    """Each import in `source` of anything but the standard library and the
    core package, as `line: module`."""

    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules = [node.module]
        else:
            continue
        found += [f"{node.lineno}: {module}" for module in modules
                  if module.split(".")[0] not in sys.stdlib_module_names | {CORE_PACKAGE}]
    return found


class RulePurityTests(unittest.TestCase):
    def test_no_core_module_names_a_claude_code_tool_or_field(self) -> None:
        names = harness_names()
        modules = [p.name for p in core_modules()]
        for expected in ("gates.py", "actions.py", "design_reads.py", "reference_reads.py",
                         "contracts.py", "overrides.py", "friction.py", "events.py", "state.py",
                         "wording.py", "judge.py", "request.py", "goated_judge.py"):
            self.assertIn(expected, modules)
        for path in core_modules():
            with self.subTest(module=path.name):
                self.assertEqual(findings(path.read_text(encoding="utf-8"), names), [])

    def test_the_core_imports_only_the_standard_library_and_itself(self) -> None:
        for path in core_modules():
            with self.subTest(module=path.name):
                self.assertEqual(foreign_imports(path.read_text(encoding="utf-8")), [])

    def test_the_import_check_finds_an_adapter_import(self) -> None:
        source = ("import json\nfrom goated_core import gates\nfrom . import events\n"
                  "from goated_adapter import translation\nimport yaml\n")
        self.assertEqual(foreign_imports(source), ["4: goated_adapter", "5: yaml"])

    def test_the_denylist_holds_the_translation_s_names(self) -> None:
        # Taken from the harness modules, not typed here.
        names = harness_names()
        for name in ("file_path", "old_string", "tool_use_id", "toolUseResult", "PreToolUse",
                     "MultiEdit", "permissionDecision", "mcp__ccd_session__start_session",
                     "hookSpecificOutput", "edit_mode"):
            self.assertIn(name, names)
        self.assertFalse(names & {"command", "head", "agent_id", "line_text"})

    def test_the_check_finds_each_kind_of_name(self) -> None:
        # One of each kind, so the check cannot pass by finding nothing.
        source = (
            'A = {"Edit": "file_path"}\n'
            'B = "toolUseResult"\n'
            'C = "the PreToolUse hook"\n'
            'D = "mcp__ccd_session__start_session"\n'
            'E = r"<pasted_content\\b"\n'
            'F = "Use the Write tool here."\n'
            'G = "~/.claude/settings.json"\n'
            'H = {"hookSpecificOutput": {}, "systemMessage": ""}\n'
            'def f(tool_input, file_path, old_string): return call.tool_use_id\n'
        )
        self.assertEqual(
            sorted(found.split(": ")[1] for found in findings(source, harness_names())),
            sorted([".claude", "Edit", "PreToolUse", "Write", "file_path", "file_path",
                    "hookSpecificOutput", "mcp__", "mcp__ccd_session__start_session",
                    "old_string", "pasted_content",
                    "systemMessage", "tool_input", "tool_use_id", "toolUseResult"]),
        )

    def test_near_miss_docstrings_plain_words_and_allowed_names_pass(self) -> None:
        source = (
            '"""Reads a Write call\'s content, as the Edit tool records it in ~/.claude."""\n'
            'TEXT = "Write the message, then read the change and its edits."\n'
            'WORDS = "the command, its head and base, a tool to run"\n'
            'KEY = "prompt_id"\n'
            'FOLDER = "docs/claude.md"\n'
        )
        self.assertEqual(findings(source, harness_names(), frozenset({"prompt_id"})), [])


if __name__ == "__main__":
    unittest.main()
