"""The Claude Code adapter's rule modules name nothing of Claude Code (Ticket 080).

ADR 0004 makes the event model the one seam: the rules read calls by kind and
turns as entries, and only the translation layer (`translation.py`), the
transcript reader (`transcript.py`), and the hook entry point (`hooks.py`)
know Claude Code's tool names, transcript fields, and hook fields. This check
reads each rule module's code, docstrings and comments aside, and fails on
any of those names in a string or an identifier.
"""

from __future__ import annotations

import ast
import re
import unittest

from claude_code_adapter_support import ADAPTER_DIR

PACKAGE = ADAPTER_DIR / "goated_adapter"
# The modules that know Claude Code, and the package's entry. Every other
# module holds rules or what they read (the event model, shell reading,
# markers, state) and moves to the shared core (Ticket 081).
HARNESS_MODULES = frozenset({
    "__init__.py", "hooks.py", "transcript.py", "translation.py",
    # Session-start notices: where Claude Code keeps instruction files and skills.
    "policy.py", "onboarding.py",
    # The adapter's saved session state: its override record is still bound to
    # Claude Code's `prompt_id` until the core owns session state (Ticket 081).
    "state.py",
})

# `Task`, the spawn tool's old name, is left out: it is also a brief heading.
TOOL_NAMES = frozenset({
    "Edit", "Write", "MultiEdit", "NotebookEdit", "Bash", "PowerShell", "Agent", "Skill",
    "Read", "Glob", "Grep", "WebFetch", "WebSearch", "claude-code-guide",
})
# Input fields only Claude Code's tools use; plain words such as `command`
# or `head` are also the event model's or git's.
INPUT_FIELDS = frozenset({
    "file_path", "notebook_path", "old_string", "new_string", "new_source", "subagent_type",
    "initiation", "proposal_id", "run_in_background", "remaining_plan", "target_branch",
    "source_branch",
})
TRANSCRIPT_FIELDS = frozenset({
    "toolUseResult", "agentId", "tool_use", "tool_result", "tool_use_id", "is_error",
    "isSidechain", "isMeta", "isCompactSummary", "promptId", "turnOrigin",
    "compact_boundary", "async_launched", "isAsync",
})
# Tags Claude Code puts in prompt text; the adapter removes them (ADR 0004).
PROMPT_TAGS = frozenset({
    "system-reminder", "pasted_content", "command-name", "task-notification", "agent-message",
    "cross-session-message", "local-command-stdout",
})
HOOK_FIELDS = frozenset({
    "hook_event_name", "tool_name", "tool_input", "tool_response", "transcript_path",
    "prompt_id", "agent_id", "last_assistant_message", "stop_hook_active",
    "PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit", "SessionStart",
    "permissionDecision", "additionalContext", "CLAUDE_PROJECT_DIR",
})
# Names a string may hold only as its whole value: inside text they are words.
VALUE_ONLY = INPUT_FIELDS | {"Edit", "Write", "Read", "Agent", "Skill", "Stop", "Grep", "Glob"}
# Names that are Claude Code's wherever a string holds them.
ANYWHERE = (TOOL_NAMES | TRANSCRIPT_FIELDS | PROMPT_TAGS | HOOK_FIELDS) - VALUE_ONLY
ANYWHERE_RE = re.compile(r"(?<![\w-])(?:%s)(?![\w-])" % "|".join(map(re.escape, sorted(ANYWHERE))))
# Identifiers that hold a tool call in Claude Code's shape.
IDENTIFIERS = frozenset({"tool_name", "tool_input", "tool_id", "tool_use_id", "tool_response"})


def rule_modules():
    return sorted(p for p in PACKAGE.glob("*.py") if p.name not in HARNESS_MODULES)


def findings(source: str) -> list[str]:
    """Each Claude Code name in the code of `source`, docstrings aside, as
    `line: name`, in the order the syntax tree is walked."""

    tree = ast.parse(source)
    docstrings = {
        id(node.body[0].value) for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstrings:
                continue
            names = ({node.value} & (VALUE_ONLY | ANYWHERE)) or set(ANYWHERE_RE.findall(node.value))
            if "mcp__" in node.value:
                names.add("mcp__")
            found += [f"{node.lineno}: {name}" for name in sorted(names)]
        else:
            name = (node.id if isinstance(node, ast.Name) else node.arg if isinstance(node, ast.arg)
                    else node.attr if isinstance(node, ast.Attribute) else None)
            if name in IDENTIFIERS:
                found.append(f"{node.lineno}: {name}")
    return found


class RulePurityTests(unittest.TestCase):
    def test_no_rule_module_names_a_claude_code_tool_or_field(self) -> None:
        modules = [p.name for p in rule_modules()]
        for expected in ("gates.py", "actions.py", "design_reads.py", "reference_reads.py",
                         "contracts.py", "overrides.py", "friction.py", "events.py"):
            self.assertIn(expected, modules)
        for path in rule_modules():
            with self.subTest(module=path.name):
                self.assertEqual(findings(path.read_text(encoding="utf-8")), [])

    def test_the_check_finds_each_kind_of_name(self) -> None:
        # One of each kind, so the check cannot pass by finding nothing.
        source = (
            'A = {"Edit": "file_path"}\n'
            'B = "toolUseResult"\n'
            'C = "the PreToolUse hook"\n'
            'D = "mcp__ccd_session__start_session"\n'
            'E = r"<pasted_content\\b"\n'
            'def f(tool_input): return call.tool_id\n'
        )
        self.assertEqual(
            sorted(found.split(": ")[1] for found in findings(source)),
            sorted(["Edit", "PreToolUse", "file_path", "mcp__", "pasted_content", "tool_id",
                    "tool_input", "toolUseResult"]),
        )

    def test_near_miss_docstrings_and_plain_words_pass(self) -> None:
        source = (
            '"""Reads a Write call\'s content, as Claude Code records it."""\n'
            'TEXT = "Write the message, then read the change and its edits."\n'
        )
        self.assertEqual(findings(source), [])


if __name__ == "__main__":
    unittest.main()
