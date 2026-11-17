"""Which `software-design-principles` references a code edit requires.

This module owns the signal table of the design-reads spec (R5), documented in
the adapter README ("Design references"): each reference with what in an edit
selects it. `red-flags.md` is not here; the closeout requires it on every
change. `differences.md` has no signal: only a design-reads line names it.

Signals are deliberately loose word and shape matches on the lines an edit
adds, so they over-select rather than miss; a reference read counts until the
next compaction, which bounds the cost.
"""

from __future__ import annotations

import re

SKILL_REFERENCES = "software-design-principles/references/"
# The references a design-reads line can require, in the skill's order.
REFERENCES = (
    "process.md", "complexity-and-modules.md", "decoupling.md", "readability.md",
    "errors.md", "coding.md", "concurrency.md", "differences.md",
)
# A turn that has edited this many code files needs `decoupling.md`.
MANY_CODE_FILES = 3

# A definition at the start of a line, with no indentation, as most languages
# write top-level ones.
TOP_LEVEL_DEFINITION_RE = re.compile(
    r"^(?:export|(?:async\s+)?def|class|(?:async\s+)?function|func|(?:pub(?:\([^)]*\))?\s+)?fn"
    r"|public|interface|struct|enum|trait|impl|defmodule)\b"
)
# A comment or docstring opening a line, or a trailing comment after two spaces
# (one space before `//` is Python's floor division).
COMMENT_RE = re.compile(r"^\s*(?:#(?:\s|$)|//|/\*|\*(?:\s|/|$)|\"\"\"|'''|--\s|<!--)|\S {2,}(?:#|//) ")
ERROR_HANDLING_RE = re.compile(r"\b(?:try|except|catch|raise|throw|finally|defer)\b|\bwith\s+open\b")
CONCURRENCY_RE = re.compile(
    r"\b(?:threading|R?Lock|Mutex|asyncio|synchronized)\b|\bPromise\.all|\bAtomic\w*|\bgo\s+func\b"
)
CONFIG_PATH_RE = re.compile(
    r"\.(?:ya?ml|toml|json|env)$|(?:^|/)\.env(?:\.[^/]*)?$|(?:^|/)settings\.[^/]+$", re.IGNORECASE
)


def reference_read(path: str) -> str | None:
    """The reference file a Read of `path` read, such as `errors.md`, or None."""

    path = path.replace("\\", "/").lower()
    for name in REFERENCES:
        suffix = SKILL_REFERENCES + name
        if path == suffix or path.endswith("/" + suffix):
            return name
    return None


def is_config(path: str) -> bool:
    return bool(CONFIG_PATH_RE.search(path.replace("\\", "/")))


def detect(path: str, added: list[str], *, new_file: bool, test_file: bool,
           code_files: int) -> dict[str, str]:
    """The references an edit selects, each with the signal that selected it.

    `path` is the edited file; `added` the lines the edit adds (not those it
    keeps as context); `new_file` whether it creates a code file; `test_file`
    whether it is a test file, by the closeout's rule; `code_files` how many
    distinct code files the turn has edited, this one included, or 0 when the
    file is not code.
    """

    found: dict[str, str] = {}
    definition = next((m.group(0) for line in added if (m := TOP_LEVEL_DEFINITION_RE.match(line))), None)
    if new_file or definition:
        why = "a new code file" if new_file else f'adds a top-level definition ("{definition}")'
        found["process.md"] = found["complexity-and-modules.md"] = why
    if is_config(path):
        found["decoupling.md"] = "edits a configuration file"
    elif code_files >= MANY_CODE_FILES:
        found["decoupling.md"] = f"the {_ordinal(code_files)} code file this turn edits"
    if definition:
        found["readability.md"] = f'adds a top-level definition ("{definition}")'
    elif any(COMMENT_RE.search(line) for line in added):
        found["readability.md"] = "adds a comment or docstring"
    if token := _first(ERROR_HANDLING_RE, added):
        found["errors.md"] = f'adds error handling ("{token}")'
    if test_file:
        found["coding.md"] = "edits a test file"
    if token := _first(CONCURRENCY_RE, added):
        found["concurrency.md"] = f'adds concurrency ("{token}")'
    return {name: found[name] for name in REFERENCES if name in found}


def _first(pattern: re.Pattern, lines: list[str]) -> str | None:
    return next((m.group(0) for line in lines if (m := pattern.search(line))), None)


def _ordinal(n: int) -> str:
    return {3: "third", 4: "fourth", 5: "fifth"}.get(n, f"{n}th")


def reads_in(calls) -> list[str]:
    """The references that finished Read calls among `calls` read, in order."""

    return [
        name for call in calls
        if call.name == "Read" and call.ok
        and (name := reference_read(str(call.input.get("file_path") or ""))) is not None
    ]
