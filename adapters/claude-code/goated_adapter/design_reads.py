"""Which `software-design-principles` references a project file edit requires.

This module owns the design-reads rules of the design-reads spec (R5),
documented in the adapter README ("Design references"): which edits they
apply to, what an edit adds, and each reference with what in an edit selects
it, close to the skill's own "Read now" conditions. `red-flags.md` is not
here; the closeout requires it on every change. `differences.md` has no
signal, so no edit requires it: the registry declares it advisory.

Signals are word and shape matches on the code an edit adds, so they lean
toward selecting; a reference read counts until the next compaction, which
bounds the cost. What is code is the action gates' rule (`actions.is_code`);
what is a test file is this module's (`is_test_path`), which the closeout
shares. Callers pass both answers.
"""

from __future__ import annotations

import os
import re
from typing import NamedTuple

SKILL_REFERENCES = "software-design-principles/references/"
# The design references whose reads count, in the skill's order.
REFERENCES = (
    "process.md", "complexity-and-modules.md", "decoupling.md", "readability.md",
    "errors.md", "coding.md", "concurrency.md", "differences.md",
)
# The non-test code file a turn edits that makes the edit a change across files.
MANY_CODE_FILES = 3
# A file on disk larger than this is not compared: all of a Write's text counts as added.
MAX_COMPARED_BYTES = 2 * 1024 * 1024

# A definition at a line start, with no indentation, as most languages write
# top-level ones; `export NAME=` is a shell variable, not one.
DEFINITION_START_RE = re.compile(
    r"^(?!export\s+\w+=)(?:export|async|def|class|function|func|fn|pub|public|interface|struct"
    r"|enum|trait|impl|defmodule)\b"
)
GO_RECEIVER_RE = re.compile(r"^func\s*\([^)]*\)")
NAME_RE = re.compile(r"[A-Za-z_$][\w$]*")
NOT_NAMES = frozenset(
    "export default async def class function func fn pub crate super self public static final "
    "abstract sealed interface struct enum trait impl defmodule const let var type record void"
    .split()
)
# A whole line of comment, as the lines a code check skips.
COMMENT_LINE_PREFIXES = ("#", "//", "/*", "*", "-- ", "<!--")
DOCSTRING_QUOTES = ('"""', "'''")
# A trailing comment after code: two spaces before it, since one space before
# `//` is Python's floor division.
TRAILING_COMMENT_RE = re.compile(r"\S {2,}(?:#|//) ")
INLINE_COMMENT_RE = re.compile(r"\s+(?:#|//)\s.*$")
ERROR_HANDLING_RE = re.compile(r"\b(?:try|except|catch|raise|throw|finally|defer)\b|\bwith\s+open\b")
CONCURRENCY_RE = re.compile(
    r"\b(?:threading|R?Lock|Mutex|asyncio|synchronized)\b|\bPromise\.all|\bAtomic\w*|\bgo\s+func\b"
)
CONFIG_PATH_RE = re.compile(
    r"\.(?:ya?ml|toml|json|env)$|(?:^|/)\.env(?:\.[^/]*)?$|(?:^|/)settings\.[^/]+$", re.IGNORECASE
)
# Lock files are written by tools, not designed.
LOCK_FILE_RE = re.compile(r"(?:^|/)(?:[^/]*[-.]lock\.(?:json|ya?ml|toml)|npm-shrinkwrap\.json)$",
                          re.IGNORECASE)


# A test file, by its path inside the project: under a `tests`, `test`, or
# `__tests__` folder at any depth, or a top-level `spec` folder (a `spec`
# folder deeper down is as often source, such as a parser for one); or named
# as runners collect tests, which makes `test_runner.py` one too.
TEST_PATH_RE = re.compile(
    r"(?:^|/)(?:tests?|__tests__)/|^spec/"
    r"|(?:^|/)test_[^/]*$|_(?:test|spec)\.[^/.]+$|\.(?:test|spec)\.[^/.]+$",
    re.IGNORECASE,
)


def is_test_path(project_path: str | None) -> bool:
    """Whether a file is a test file, given its path inside the project with
    `/` separators. None, a file whose place in the project is unknown, is not
    one, so it meets every gate a code file meets."""

    return project_path is not None and bool(TEST_PATH_RE.search(project_path))


def applies(path: str, *, is_code: bool, is_test: bool) -> bool:
    """Whether the design-reads rules apply to an edit of `path`: a code file,
    or a configuration file that is neither a lock file nor test data."""

    return is_code or (_is_config(path) and not is_test)


def required(path: str, tool_input: dict, *, is_code: bool, is_test: bool, small: bool,
             written_before: bool, other_code_files: int,
             cwd: str | None, test_edit: str | None = None) -> dict[str, str]:
    """The references an edit's signals select, each with why, in the skill's order.

    `small`: the edit adds too few lines for the `design` gate, so no signal
    selects a reference by the kind of file or text it touches (see
    `_signals`). `written_before`: the turn already
    wrote this file. `other_code_files`: how many other non-test code files
    the turn has edited. A Write is compared with the file on disk, a
    relative path taken from `cwd`, so only what it adds counts.
    `test_edit`: for a test file, why the edit designs a test, which selects
    `coding.md`, or None when it does not; the caller judges it by the
    registry's rule for test edits.
    """

    on_disk = _disk_text(path, cwd) if "content" in tool_input else None
    found = _signals(
        path, _Added(tool_input, on_disk),
        new_file=is_code and creates_file(path, tool_input, written_before=written_before, cwd=cwd),
        is_test=is_test, small=small, test_edit=test_edit,
        code_files=other_code_files + 1 if is_code and not is_test else 0,
    )
    return {name: found[name] for name in REFERENCES if name in found}


def creates_file(path: str, tool_input: dict, *, written_before: bool, cwd: str | None) -> bool:
    """Whether an edit creates `path`: a Write to a file no earlier write in
    the turn made (`written_before`) and that is not on disk, a relative
    path taken from `cwd`."""

    return "content" in tool_input and not written_before and _disk_text(path, cwd) is None


def added_code(path: str, tool_input: dict, cwd: str | None) -> list[str]:
    """The code of each line an edit of `path` adds, as the design signals
    read it: comments and docstrings removed, "" for a comment line. A Write
    is compared with the file on disk, a relative path taken from `cwd`."""

    on_disk = _disk_text(path, cwd) if "content" in tool_input else None
    return _Added(tool_input, on_disk).code


def reference_read(path: str) -> str | None:
    """The reference file a Read of `path` read, such as `errors.md`, or None."""

    path = path.replace("\\", "/").lower()
    for name in REFERENCES:
        suffix = SKILL_REFERENCES + name
        if path == suffix or path.endswith("/" + suffix):
            return name
    return None


def reads_in(calls) -> list[str]:
    """The references that finished Read calls among `calls` read, in order.
    A shell command printing one does not count, as for the red flags."""

    return [
        name for call in calls
        if call.name == "Read" and call.ok
        and (name := reference_read(str(call.input.get("file_path") or ""))) is not None
    ]


class _Added:
    """What an edit adds, judged line by line against the text it replaces.

    `lines` are the added lines as written; `code` the code part of each, with
    comments and docstrings removed; `comment` whether any adds a comment or
    docstring; `definitions` the names of top-level definitions it adds, a
    definition whose name the old text already defined (a signature change)
    left out. Indentation alone does not make a line added.
    """

    def __init__(self, tool_input: dict, on_disk: str | None) -> None:
        pairs = [(on_disk, tool_input.get("content")), (None, tool_input.get("new_source")),
                 (tool_input.get("old_string"), tool_input.get("new_string"))]
        edits = tool_input.get("edits")
        if isinstance(edits, list):
            pairs += [(e.get("old_string"), e.get("new_string")) for e in edits if isinstance(e, dict)]
        self.code: list[str] = []
        self.comment = False
        self.definitions: list[str] = []
        for old, new in pairs:
            if isinstance(new, str):
                self._add(old if isinstance(old, str) else "", new)

    def _add(self, old: str, new: str) -> None:
        old_lines = old.split("\n")
        kept = {line.strip() for line in old_lines}
        old_names = {_definition(part) for part in _code_parts(old_lines)} - {None}
        new_lines = new.split("\n")
        for line, part in zip(new_lines, _code_parts(new_lines)):
            if not line.strip() or line.strip() in kept:
                continue
            self.code.append(part)
            self.comment = self.comment or not part.strip() or bool(TRAILING_COMMENT_RE.search(line))
            name = _definition(part)
            if name is not None and name not in old_names:
                self.definitions.append(name)


class _CommentSyntax(NamedTuple):
    """How a language writes comments, as `comment_only` reads them: the
    marker of a line comment, a trailing comment after code (two or more
    spaces, then the marker), whether `/* */` blocks exist, and whether
    three-quote docstrings do."""

    line: str
    trailing: re.Pattern
    blocks: bool
    docstrings: bool


_HASH = _CommentSyntax("#", re.compile(r"\S {2,}#"), blocks=False, docstrings=False)
_SLASH = _CommentSyntax("//", re.compile(r"\S {2,}//"), blocks=True, docstrings=False)
# The languages `comment_only` reads, by file extension. Any other file has no
# comment syntax it knows, so no edit of it is comment-only.
COMMENT_SYNTAX = {
    **{ext: _HASH for ext in ("rb", "sh", "bash", "zsh", "pl", "r", "ps1", "psm1")},
    **{ext: _HASH._replace(docstrings=True) for ext in ("py", "pyi")},
    **{ext: _SLASH for ext in ("c", "h", "cc", "cpp", "cxx", "hpp", "cs", "java", "js", "jsx",
                               "mjs", "cjs", "ts", "tsx", "go", "rs", "swift", "kt", "kts",
                               "scala", "dart")},
}
# Code holding one of these may open a string that spans lines, whose lines
# could look like comments, so `comment_only` cannot read the text after it.
MULTILINE_STRING_MARKS = ('"""', "'''", "`")
QUOTE_MARKS = ('"', "'", "`")


def comment_only(path: str, tool_input: dict) -> bool:
    """Whether an edit of `path` adds and removes only comments and docstrings:
    each text it replaces holds the same code lines, indentation included, as
    the text it writes. The comment syntax is the one `COMMENT_SYNTAX` gives
    the file's extension.

    It errs toward "a change": a file of another language, a Write or a
    notebook edit (they replace text this cannot see), an input with no old
    and new text, and any text it cannot read for certain (`_code_lines`) is
    not comment-only. These rules are stricter than `_Added`'s, which lean
    toward selecting a reference rather than toward finding no change.
    """

    syntax = COMMENT_SYNTAX.get(os.path.splitext(path)[1].lstrip(".").lower())
    if syntax is None or "content" in tool_input or "new_source" in tool_input:
        return False
    pairs = [(tool_input["old_string"], tool_input.get("new_string"))] if "old_string" in tool_input else []
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        pairs += [(e.get("old_string"), e.get("new_string")) if isinstance(e, dict) else (None, None)
                  for e in edits]
    return bool(pairs) and all(
        isinstance(old, str) and isinstance(new, str)
        and (code := _code_lines(old, syntax)) is not None and code == _code_lines(new, syntax)
        for old, new in pairs
    )


def _code_lines(text: str, syntax: _CommentSyntax) -> list[str] | None:
    """The code lines of `text`, comments, docstrings, and blank lines left out
    and trailing space removed; None when it cannot be read for certain.

    A comment is a whole line opening with the line marker, a `/* */` block
    (where the language has them) with nothing after its close, a docstring
    opening a line with three quotes (where the language has them) with
    nothing after its close, or a trailing comment after two or more spaces
    with no quote before it. Uncertain: a block or docstring with code after
    its close, a lone three-quote line (opening or closing, a fragment cannot
    say), and code holding a quote before a trailing comment or a mark of a
    string that may span lines (`MULTILINE_STRING_MARKS`).
    """

    lines: list[str] = []
    closer = None  # The mark that ends the block comment or docstring being read.
    for line in text.split("\n"):
        body = line.strip()
        if closer is not None:
            if closer in body:
                if not body.endswith(closer) or body.count(closer) > 1:
                    return None
                closer = None
            continue
        opener = ("/*" if syntax.blocks and body.startswith("/*") else
                  body[:3] if syntax.docstrings and body.startswith(DOCSTRING_QUOTES) else None)
        if opener is not None:
            close = "*/" if opener == "/*" else opener
            rest = body[len(opener):]
            if not rest and opener != "/*":
                return None
            if close not in rest:
                closer = close
            elif not rest.endswith(close) or rest.count(close) > 1:
                return None
            continue
        if not body or body.startswith(syntax.line):
            continue
        trailing = syntax.trailing.search(line)
        code = line[: trailing.start() + 1] if trailing else line
        if trailing and any(q in code for q in QUOTE_MARKS):
            return None
        if any(mark in code for mark in MULTILINE_STRING_MARKS):
            return None
        lines.append(code.rstrip())
    return lines


def _signals(path: str, added: _Added, *, new_file: bool, is_test: bool, small: bool,
             test_edit: str | None, code_files: int) -> dict[str, str]:
    """The references an edit's signals select, each with why.

    A test file selects `coding.md` only when the edit designs a test
    (`test_edit`, the registry's rule). Otherwise a small edit selects none
    by the kind of file or text it touches: a configuration file, the third
    code file, or an added comment (the skill's small-edit rule). Signals
    read from the added code apply at any size: a new code file or public
    definition, error handling, and concurrency.
    """

    if is_test:
        # Test code needs the reasoning on tests, not on interfaces or errors.
        return {"coding.md": test_edit} if test_edit else {}
    found: dict[str, str] = {}
    public = next((name for name in added.definitions if not name.startswith("_")), None)
    if new_file or public is not None:
        why = "a new code file" if new_file else f'adds a public top-level definition ("{public}")'
        for name in ("process.md", "complexity-and-modules.md", "readability.md"):
            found[name] = why
    elif added.comment and not small:
        found["readability.md"] = "adds a comment or docstring"
    if not small and _is_config(path):
        found["decoupling.md"] = "edits a configuration file"
    elif not small and code_files >= MANY_CODE_FILES:
        found["decoupling.md"] = f"the {_ordinal(code_files)} code file this turn edits, tests aside"
    if token := _first(ERROR_HANDLING_RE, added.code):
        found["errors.md"] = f'adds error handling ("{token}")'
    if token := _first(CONCURRENCY_RE, added.code):
        found["concurrency.md"] = f'adds concurrency ("{token}")'
    return found


def _code_parts(lines: list[str]) -> list[str]:
    """Each line's code, without comments or docstrings: "" for a comment or
    docstring line, the line up to a trailing comment otherwise."""

    parts, closer = [], None
    for line in lines:
        text = line.strip()
        if closer is not None:
            parts.append("")
            if closer in text:
                closer = None
            continue
        quote = next((q for q in DOCSTRING_QUOTES if text.startswith(q)), None)
        if quote is not None:
            closer = quote if text.count(quote) == 1 else None
            parts.append("")
        elif text.startswith(COMMENT_LINE_PREFIXES):
            closer = "*/" if text.startswith("/*") and "*/" not in text else None
            parts.append("")
        else:
            parts.append(INLINE_COMMENT_RE.sub("", line))
    return parts


def _definition(part: str) -> str | None:
    """The name a top-level definition line defines, or None for any other line;
    an anonymous one (`export default function () {}`) is named by its keyword."""

    match = DEFINITION_START_RE.match(part)
    if match is None:
        return None
    rest = GO_RECEIVER_RE.sub("func", part)
    return next((n for n in NAME_RE.findall(rest) if n not in NOT_NAMES), match.group(0))


def _disk_text(path: str, cwd: str | None) -> str | None:
    """The text of `path` on disk, or None when no such file exists. A file that
    exists but cannot be read or is too large reads as "", so all of a Write
    over it counts as added."""

    full = path if os.path.isabs(path) or cwd is None else os.path.join(cwd, path)
    if not os.path.isfile(full):
        return None
    try:
        if os.path.getsize(full) > MAX_COMPARED_BYTES:
            return ""
        with open(full, encoding="utf-8", errors="replace") as stream:
            return stream.read()
    except OSError:
        return ""


def _is_config(path: str) -> bool:
    path = path.replace("\\", "/")
    return bool(CONFIG_PATH_RE.search(path)) and not LOCK_FILE_RE.search(path)


def _first(pattern: re.Pattern, lines: list[str]) -> str | None:
    return next((m.group(0) for line in lines if (m := pattern.search(line))), None)


def _ordinal(n: int) -> str:
    return {3: "third", 4: "fourth", 5: "fifth"}.get(n, f"{n}th")
