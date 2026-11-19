"""Which `software-design-principles` references a project file edit requires.

This module owns the design-reads rules of the design-reads spec (R5),
stated in the enforcement contract ("Design Reference Signals"): which edits they
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

from .events import Call

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
# top-level ones; `export NAME=` is a shell variable, not one. `async` starts
# one only before `def`, `function` or `fn`, and Rust's or Zig's `pub`
# (`pub(crate)` and its forms too) only before a definition keyword, after any
# qualifiers, so `pub use x;` and `pub extern crate x;` re-export and define
# nothing.
PUB_QUALIFIERS = r'(?:(?:const|async|unsafe|default|inline|extern(?:\s+"[^"]*")?)\s+)*'
PUB_DEFINITION_KEYWORDS = r"(?!extern\s+crate\b)(?:fn|struct|enum|trait|type|const|static|mod|union|impl|extern|var)"
DEFINITION_START_RE = re.compile(
    r"^(?!export\s+\w+=)(?:export|def|class|function|func|fn|public|interface|struct"
    r"|enum|trait|impl|defmodule|async\s+(?:def|function|fn)"
    rf"|pub(?:\s*\([^)]*\))?\s+{PUB_QUALIFIERS}{PUB_DEFINITION_KEYWORDS})\b"
)
# Neither a string literal, such as the ABI in `extern "C"`, nor the path in a
# visibility such as `pub(in crate::x)` names the definition.
STRING_LITERAL_RE = re.compile(r'"[^"]*"')
PUB_VISIBILITY_RE = re.compile(r"^pub\s*\([^)]*\)")
GO_RECEIVER_RE = re.compile(r"^func\s*\([^)]*\)")
NAME_RE = re.compile(r"[A-Za-z_$][\w$]*")
NOT_NAMES = frozenset(
    "export default async def class function func fn pub crate super self public static final "
    "abstract sealed interface struct enum trait impl defmodule const let var type record void"
    " unsafe extern mod union inline"
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


# Test data beyond test files: anything under a `fixtures` or `__fixtures__`
# folder at any depth inside the project.
FIXTURE_PATH_RE = re.compile(r"(?:^|/)(?:fixtures|__fixtures__)/", re.IGNORECASE)


def is_test_data_path(project_path: str | None) -> bool:
    """Whether a file is test data, given its path inside the project as for
    `is_test_path`: a test file, or any file under a fixtures folder. It
    decides only whether a configuration file is judged; a code file under a
    fixtures folder is still code, and a test file only by `is_test_path`."""

    return is_test_path(project_path) or (
        project_path is not None and bool(FIXTURE_PATH_RE.search(project_path)))


def applies(path: str, *, is_code: bool, is_test_data: bool) -> bool:
    """Whether the design-reads rules apply to an edit of `path`: a code file,
    or a configuration file that is neither a lock file nor test data
    (`is_test_data_path`)."""

    return is_code or (is_config(path) and not is_test_data)


def required(path: str, edit: Call | None, *, is_code: bool, is_test: bool, small: bool,
             written_before: bool, other_code_files: int,
             cwd: str | None, test_edit: str | None = None) -> dict[str, str]:
    """The references a file write's signals select, each with why, in the
    skill's order. `edit` is the write, a `file_write` call, or None for a
    write whose text is unknown.

    `small`: the edit is too small for the `design` gate, adding too few
    lines or few enough comment-only ones (`actions._small_edit`), so no signal
    selects a reference by the kind of file or text it touches (see
    `_signals`). `written_before`: the turn already
    wrote this file. `other_code_files`: how many other non-test code files
    the turn has edited. A whole-file write is compared with the file on
    disk, a relative path taken from `cwd`, so only what it adds counts.
    `test_edit`: for a test file, why the edit designs a test, which selects
    `coding.md`, or None when it does not; the caller judges it by the
    registry's rule for test edits.
    """

    found = _signals(
        path, _Added(edit, path, cwd),
        new_file=is_code and creates_file(path, edit, written_before=written_before, cwd=cwd),
        is_code=is_code, is_test=is_test, small=small, test_edit=test_edit,
        code_files=other_code_files + 1 if is_code and not is_test else 0,
    )
    return {name: found[name] for name in REFERENCES if name in found}


def creates_file(path: str, edit: Call | None, *, written_before: bool, cwd: str | None) -> bool:
    """Whether a file write creates `path`: it writes the whole file, or is an
    edit that makes a missing file (`creates`), to a file no earlier write in
    the turn made (`written_before`) and that is not on disk, a relative path
    taken from `cwd`. A file a shell command made is on disk, so it is not."""

    if edit is None:
        return False
    makes = edit.whole_file or edit.creates
    return makes and not written_before and _disk_text(path, cwd) is None


def added_code(path: str, edit: Call | None, cwd: str | None) -> list[str]:
    """The code of each line a file write of `path` adds, as the design
    signals read it: comments and docstrings removed, "" for a comment line.
    A whole-file write is compared with the file on disk, a relative path
    taken from `cwd`."""

    return _Added(edit, path, cwd).code


class AddedLines(NamedTuple):
    """What a file write adds, as the reference signals read it: `code` as
    `added_code` gives it, and `in_strings`, the indices into `code` of the
    lines inside a string the write shows opening on an earlier line
    (`_read_lines`), whose words are text, not code."""

    code: list[str]
    in_strings: frozenset[int]


def added_lines(path: str, edit: Call | None, cwd: str | None) -> AddedLines:
    """`added_code`, with which of its lines are inside a multi-line string."""

    added = _Added(edit, path, cwd)
    return AddedLines(added.code, frozenset(added.in_strings))


def reference_read(path: str) -> str | None:
    """The reference file a read of `path` read, such as `errors.md`, or None."""

    path = path.replace("\\", "/").lower()
    for name in REFERENCES:
        suffix = SKILL_REFERENCES + name
        if path == suffix or path.endswith("/" + suffix):
            return name
    return None


def reads_in(calls) -> list[str]:
    """The references that finished file reads among `calls` read whole, in
    order (`Call.whole_read_path`). A shell command printing one does not
    count, as for the red flags."""

    return [
        name for call in calls
        if (path := call.whole_read_path()) and (name := reference_read(path)) is not None
    ]


class _Added:
    """What an edit adds, judged line by line against the text it replaces.

    `code` is the code part of each added line, with comments and docstrings
    removed; `in_strings` the indices into `code` of lines inside a
    multi-line string (`_read_lines`); `comment` whether any adds a comment or
    docstring; `definitions` the names of top-level definitions it adds, a
    definition whose name the old text already defined (a signature change)
    left out. Indentation alone does not make a line added. Text a write
    replaces without saying what (None) counts as empty, so all it adds is
    new; a whole-file write replaces the file on disk at `path`.
    """

    def __init__(self, edit: Call | None, path: str, cwd: str | None) -> None:
        self.code: list[str] = []
        self.in_strings: list[int] = []
        self.comment = False
        self.definitions: list[str] = []
        if edit is None:
            return
        extension = os.path.splitext(path)[1].lstrip(".").lower()
        on_disk = _disk_text(path, cwd) if edit.whole_file else None
        for removed, added in edit.edits:
            if added is not None:
                self._add((on_disk if edit.whole_file else removed) or "", added, extension)

    def _add(self, old: str, new: str, extension: str) -> None:
        old_lines = old.split("\n")
        kept = {line.strip() for line in old_lines}
        old_names = {_definition(read.code)
                     for read in _read_lines(old_lines, extension)} - {None}
        new_lines = new.split("\n")
        for line, read in zip(new_lines, _read_lines(new_lines, extension)):
            if not line.strip() or line.strip() in kept:
                continue
            if read.in_string:
                self.in_strings.append(len(self.code))
            part = read.code
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
# Comments that change what a tool does: a build or compile directive, a type
# checker's or linter's switch, an interpreter line, or a doctest. `comment_only`
# reads a comment whose text opens with one, its markers left out, as code.
DIRECTIVE_PREFIXES = ("//go:", "// +build", "@ts-", "eslint-", "# type:", "noqa", "pragma",
                      "pylint:", "#!", "/// <reference", ">>>")
_COMMENT_MARKS = "#/*\"' \t"
_DIRECTIVE_STARTS = tuple(prefix.lstrip(_COMMENT_MARKS) for prefix in DIRECTIVE_PREFIXES)


def comment_only(path: str, edit: Call) -> bool:
    """Whether a file write of `path` adds and removes only comments and
    docstrings: each text it replaces holds the same code lines, indentation
    included, as the text it writes. The comment syntax is the one
    `COMMENT_SYNTAX` gives the file's extension.

    It errs toward "a change": a file of another language, a whole-file
    write or an edit whose replaced text is unknown (they replace text this
    cannot see), a write with no edits, and any text it cannot read for
    certain (`_code_lines`) is not comment-only, nor is a text that ends with
    a block comment or docstring open where the text it replaces did not, or
    the reverse (`_open_block`): it comments out, or back in, the code after
    it. A directive comment (`DIRECTIVE_PREFIXES`) is code. These rules are
    stricter than `_Added`'s, which lean toward selecting a reference rather
    than toward finding no change.
    """

    syntax = COMMENT_SYNTAX.get(os.path.splitext(path)[1].lstrip(".").lower())
    if syntax is None or edit.whole_file:
        return False
    return bool(edit.edits) and all(
        removed is not None and added is not None
        and (code := _code_lines(removed, syntax)) is not None
        and code == _code_lines(added, syntax)
        and _open_block(removed, syntax) == _open_block(added, syntax)
        for removed, added in edit.edits
    )


def _open_block(text: str, syntax: _CommentSyntax) -> str | None:
    """The mark that would end a block comment or docstring `text` leaves
    open at its end, or None when it leaves none open. Meant for text
    `_code_lines` reads for certain."""

    closer = None
    for body in (line.strip() for line in text.split("\n")):
        if closer is not None:
            if closer in body:
                closer = None
        elif (close := _block_close(body, syntax)) is not None and close not in body[len(close):]:
            closer = close
    return closer


def _block_close(body: str, syntax: _CommentSyntax) -> str | None:
    """The mark that ends the block comment or docstring a stripped line
    `body` opens with, or None when it opens none."""

    if syntax.blocks and body.startswith("/*"):
        return "*/"
    if syntax.docstrings and body.startswith(DOCSTRING_QUOTES):
        return body[:3]
    return None


def _directive(comment: str) -> bool:
    """Whether a comment's text, its markers and leading space left out,
    opens with a directive (`DIRECTIVE_PREFIXES`)."""

    return comment.lstrip(_COMMENT_MARKS).startswith(_DIRECTIVE_STARTS)


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
    string that may span lines (`MULTILINE_STRING_MARKS`). A comment line, or
    a trailing comment, that is a directive (`_directive`) is code, kept whole.
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
            if _directive(body):
                lines.append(line.rstrip())
            continue
        close = _block_close(body, syntax)
        if close is not None:
            rest = body[len(close):]
            if not rest and close != "*/":
                return None
            if close not in rest:
                closer = close
            elif not rest.endswith(close) or rest.count(close) > 1:
                return None
            if _directive(body):
                lines.append(line.rstrip())
            continue
        if not body or body.startswith(syntax.line):
            if _directive(body):
                lines.append(line.rstrip())
            continue
        trailing = syntax.trailing.search(line)
        code = line[: trailing.start() + 1] if trailing else line
        if trailing and any(q in code for q in QUOTE_MARKS):
            return None
        if any(mark in code for mark in MULTILINE_STRING_MARKS):
            return None
        if trailing and _directive(line[trailing.end() - len(syntax.line):]):
            code = line
        lines.append(code.rstrip())
    return lines


def _signals(path: str, added: _Added, *, new_file: bool, is_code: bool, is_test: bool,
             small: bool, test_edit: str | None, code_files: int) -> dict[str, str]:
    """The references an edit's signals select, each with why. Only a code
    file (`is_code`) adds a public definition: a configuration key such as
    YAML's `class: foo` defines nothing.

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
    public = next((name for name in added.definitions if not name.startswith("_")),
                  None) if is_code else None
    if new_file or public is not None:
        why = "a new code file" if new_file else f'adds a public top-level definition ("{public}")'
        for name in ("process.md", "complexity-and-modules.md", "readability.md"):
            found[name] = why
    elif added.comment and not small:
        found["readability.md"] = "adds a comment or docstring"
    if not small and is_config(path):
        found["decoupling.md"] = "edits a configuration file"
    elif not small and code_files >= MANY_CODE_FILES:
        found["decoupling.md"] = f"the {_ordinal(code_files)} code file this turn edits, tests aside"
    if token := _first(ERROR_HANDLING_RE, added.code):
        found["errors.md"] = f'adds error handling ("{token}")'
    if token := _first(CONCURRENCY_RE, added.code):
        found["concurrency.md"] = f'adds concurrency ("{token}")'
    return found


class _Line(NamedTuple):
    """One line as `_read_lines` reads it: its `code`, and whether it is
    `in_string`, inside a string that opened on an earlier line."""

    code: str
    in_string: bool


class _OpenString(NamedTuple):
    """A string that spans lines: the `quote` that closes it, and the
    `marker` that opens code inside it (None when nothing does)."""

    quote: str
    marker: str | None


# Where a string that spans lines opens, by file extension: three quotes
# (Python) or a backtick (a JavaScript template literal) right after an `=`,
# a bracket, a `,` or `:`, or `return`/`yield`, as in `CONFIG = """` or
# `dedent('''`. Three quotes opening a line start a docstring, and a quote
# after other text may close a string that opened before the text shown, so
# neither opens one.
_AFTER_CODE = r"(?:[=(\[{,:]|\breturn|\byield)\s*"
STRING_OPENER_RE = {
    **{ext: re.compile(_AFTER_CODE + r"(?P<prefix>[rRbBuUfFtT]{0,2})(?P<quote>\"\"\"|''')")
       for ext in ("py", "pyi")},
    **{ext: re.compile(_AFTER_CODE + r"(?P<prefix>)(?P<quote>`)")
       for ext in ("js", "jsx", "mjs", "cjs", "ts", "tsx")},
}


def _read_lines(lines: list[str], extension: str) -> list[_Line]:
    """Each line's code, without comments or docstrings ("" for a comment or
    docstring line, the line up to a trailing comment otherwise), and whether
    it is inside a string the lines show opening (`STRING_OPENER_RE`, for a
    file of `extension`). The line that closes such a string is not inside
    it, nor is a line that may hold code in it (`{` in an `f` or `t`
    string, `${` in a template literal). A line holding both such code and
    the closing quote may hold a nested string, so no later line is read as
    inside one."""

    opener_re = STRING_OPENER_RE.get(extension)
    read, closer, string = [], None, None
    for line in lines:
        text = line.strip()
        if string is not None:
            closes = string.quote in text
            holds_code = string.marker is not None and string.marker in text
            if closes and holds_code:
                opener_re = None
            read.append(_Line("" if text.startswith(COMMENT_LINE_PREFIXES)
                              else INLINE_COMMENT_RE.sub("", line),
                              not closes and not holds_code))
            string = None if closes else string
            continue
        if closer is not None:
            read.append(_Line("", False))
            if closer in text:
                closer = None
            continue
        quote = next((q for q in DOCSTRING_QUOTES if text.startswith(q)), None)
        if quote is not None:
            closer = quote if text.count(quote) == 1 else None
            read.append(_Line("", False))
        elif text.startswith(COMMENT_LINE_PREFIXES):
            closer = "*/" if text.startswith("/*") and "*/" not in text else None
            read.append(_Line("", False))
        else:
            read.append(_Line(INLINE_COMMENT_RE.sub("", line), False))
            string = _opened_string(opener_re, line) if opener_re else None
    return read


def _opened_string(opener_re: re.Pattern, line: str) -> _OpenString | None:
    """The string `line` leaves open, by `opener_re`, or None: one whose
    closing quote is not later on the line."""

    for match in opener_re.finditer(line):
        quote = match.group("quote")
        if quote not in line[match.end():]:
            if quote == "`":
                return _OpenString(quote, "${")
            interpolates = any(letter in match.group("prefix") for letter in "fFtT")
            return _OpenString(quote, "{" if interpolates else None)
    return None


def _definition(part: str) -> str | None:
    """The name a top-level definition line defines, or None for any other line;
    an anonymous one (`export default function () {}`) is named by its keyword."""

    match = DEFINITION_START_RE.match(part)
    if match is None:
        return None
    rest = GO_RECEIVER_RE.sub("func", PUB_VISIBILITY_RE.sub("pub", part))
    rest = STRING_LITERAL_RE.sub(" ", rest)
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


def is_config(path: str) -> bool:
    """Whether `path` names a configuration file that is designed, not a lock file."""

    path = path.replace("\\", "/")
    return bool(CONFIG_PATH_RE.search(path)) and not LOCK_FILE_RE.search(path)


def _first(pattern: re.Pattern, lines: list[str]) -> str | None:
    return next((m.group(0) for line in lines if (m := pattern.search(line))), None)


def _ordinal(n: int) -> str:
    return {3: "third", 4: "fourth", 5: "fifth"}.get(n, f"{n}th")
