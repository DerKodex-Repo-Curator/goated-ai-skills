"""Which `software-design-principles` references a project file edit requires.

This module owns the design-reads rules of the design-reads spec (R5),
documented in the adapter README ("Design references"): which edits they
apply to, what an edit adds, and each reference with what in an edit selects
it, close to the skill's own "Read now" conditions. `red-flags.md` is not
here; the closeout requires it on every change. `differences.md` has no
signal: only a design-reads line names it.

Signals are word and shape matches on the code an edit adds, so they lean
toward selecting; a reference read counts until the next compaction, which
bounds the cost. What is code is the action gates' rule (`actions.is_code`);
what is a test file is this module's (`is_test_path`), which the closeout
shares. Callers pass both answers.

It also owns what the closeout's citation item reads (spec R6): each
reference's section ids, from the installed skill's own files, and the
citations a text makes.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

SKILL_REFERENCES = "software-design-principles/references/"
# The references a design-reads line can require, in the skill's order.
REFERENCES = (
    "process.md", "complexity-and-modules.md", "decoupling.md", "readability.md",
    "errors.md", "coding.md", "concurrency.md", "differences.md",
)
# Named in a design-reads line, it requires nothing here: the closeout requires it.
CLOSEOUT_REFERENCE = "red-flags.md"
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
# A section id, declared on its own line in a reference file before its heading.
SECTION_ID_RE = re.compile(r"^<!-- id: #([a-z0-9]+(?:-[a-z0-9]+)*) -->[ \t]*$", re.MULTILINE)
HEADING_RE = re.compile(r"^(#{2,3}) ", re.MULTILINE)
# A citation, `errors.md#crash-early`, bare or after a path such as `references/`.
CITATION_RE = re.compile(r"(?<![\w.-])([a-z0-9]+(?:-[a-z0-9]+)*\.md)#([a-z0-9]+(?:-[a-z0-9]+)*)")
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


def required(path: str, tool_input: dict, *, is_code: bool, is_test: bool,
             written_before: bool, other_code_files: int, declared: list[str],
             cwd: str | None) -> dict[str, str]:
    """The references an edit requires, each with why, in the skill's order.

    They are those its signals select plus the known ones in `declared`, the
    turn's design-reads files. `written_before`: the turn already wrote this
    file. `other_code_files`: how many other non-test code files the turn has
    edited. A Write is compared with the file on disk, a relative path taken
    from `cwd`, so only what it adds counts.
    """

    on_disk = _disk_text(path, cwd) if "content" in tool_input else None
    found = _signals(
        path, _Added(tool_input, on_disk),
        new_file=is_code and "content" in tool_input and not written_before and on_disk is None,
        is_test=is_test,
        code_files=other_code_files + 1 if is_code and not is_test else 0,
    )
    for name in declared:
        if name in REFERENCES:
            found[name] = "named in your design-reads line"
    return {name: found[name] for name in REFERENCES if name in found}


def section_ids(skill_folder: Path | None) -> dict[str, tuple[str, ...]]:
    """Each design reference's section ids, in file order, from the
    `<!-- id: #name -->` comments in `skill_folder`'s reference files.

    An id whose `##` heading groups `###` sections, such as `#errors`, names
    a part of the file, not a section, so it is left out, as the skill's
    Section Index leaves it out. A reference whose file cannot be read, or
    that declares no section, is left out, so its citation is not required.
    """

    ids: dict[str, tuple[str, ...]] = {}
    if skill_folder is None:
        return ids
    for name in REFERENCES:
        try:
            text = (skill_folder / "references" / name).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        found = tuple(
            match.group(1) for match in SECTION_ID_RE.finditer(text)
            if not _groups_sections(text, match.end())
        )
        if found:
            ids[name] = found
    return ids


def citations(texts: list[str]) -> set[str]:
    """The sections `texts` cite, each as `file#id`, such as `errors.md#crash-early`."""

    return {f"{name}#{section}" for text in texts for name, section in CITATION_RE.findall(text)}


def unknown(declared: list[str]) -> list[str]:
    """The files a design-reads line names that are not design references."""

    return [name for name in declared if name not in REFERENCES and name != CLOSEOUT_REFERENCE]


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


def _groups_sections(text: str, at: int) -> bool:
    """Whether the first heading after `at` is a `##` with a `###` under it."""

    heading = HEADING_RE.search(text, at)
    if heading is None or heading.group(1) != "##":
        return False
    following = HEADING_RE.search(text, heading.end())
    return following is not None and following.group(1) == "###"


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


def _signals(path: str, added: _Added, *, new_file: bool, is_test: bool,
             code_files: int) -> dict[str, str]:
    if is_test:
        # Test code needs the reasoning on tests, not on interfaces or errors.
        return {"coding.md": "edits a test file"}
    found: dict[str, str] = {}
    public = next((name for name in added.definitions if not name.startswith("_")), None)
    if new_file or public is not None:
        why = "a new code file" if new_file else f'adds a public top-level definition ("{public}")'
        for name in ("process.md", "complexity-and-modules.md", "readability.md"):
            found[name] = why
    elif added.comment:
        found["readability.md"] = "adds a comment or docstring"
    if _is_config(path):
        found["decoupling.md"] = "edits a configuration file"
    elif code_files >= MANY_CODE_FILES:
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
