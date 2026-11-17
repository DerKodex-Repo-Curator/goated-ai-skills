"""Which files code given to an interpreter inline writes, removes, or renames.

`writes(language, code)` reads the code that `python -c`, `node -e`,
`perl -e`, a heredoc on `python -`, and the like run (`shell.py` finds it)
for the calls in `WRITE_CALLS`, that language's one table. A call's file is
the string literal it names; a path built at run time (a variable, an
f-string, a concatenation, an interpolated string) cannot be read, so the
call is an unnamed write. Code with no such call writes nothing, as far as
the gates care. Like `shell.py` this is a lexical reading: a call spelled in
a string or comment still counts, and a write made through another program
(`subprocess`, `child_process`, `system`) or a dynamic call is not seen.
"""

from __future__ import annotations

import re
from typing import NamedTuple

# The interpreters whose inline code is read, by command name, with its language.
LANGUAGES = {
    "python": "python", "python3": "python", "py": "python",
    "node": "js", "deno": "js", "bun": "js", "perl": "perl", "ruby": "ruby",
}


class _Mode(NamedTuple):
    """An open call's mode argument: its position, its keyword name (Python's
    `mode=`, Ruby's `mode:`), and the pattern a mode that writes matches. A
    mode that is not a literal writes, unless `raw`: then the pattern is
    matched against the argument's text (`os.O_WRONLY | os.O_CREAT`). A call
    without the argument opens to read."""

    index: int
    keyword: str
    writes: re.Pattern
    raw: bool = False


class _Call(NamedTuple):
    """One write call. `pattern` matches its name, just before its arguments.
    `targets` are the positions of the arguments it writes, or `ALL` for
    every positional one; `names` are the keyword names of positions 0, 1, ….
    `receiver` says the file is also the object the method is called on:
    "any" for a method only a path has (`p.write_text()`), whose receiver is
    an unnamed file unless it is a `Path("…")`; "path" for a method other
    objects share (`.rename`, `.open`), which counts only on a `Path("…")`.
    `mode_in_path` says that, given only the arguments up to its mode, the
    call takes its mode as the leading signs of that last one, as Perl's
    two-argument `open(FH, ">PATH")` does."""

    pattern: re.Pattern
    targets: tuple[int, ...]
    names: tuple[str, ...] = ()
    mode: _Mode | None = None
    receiver: str = ""
    mode_in_path: bool = False


ALL = (-1,)
_PY_MODE = re.compile(r"[wax+]")
_JS_FLAGS = re.compile(r"^[wa]|\+")
_RUBY_MODE = re.compile(r"[wa+]")
_PERL_MODE = re.compile(r"^\+|>")
# A name that is not part of a longer one, in each language's spelling.
_JS_NAME_END = r"(?![\w$])"


def _call(pattern: str, targets: tuple[int, ...] = (0,), **fields) -> _Call:
    return _Call(re.compile(pattern), targets, **fields)


# Each language's write calls. A name other code also uses (`open`, `rm`,
# `rename`) counts only where its module, receiver, or mode says it writes.
WRITE_CALLS: dict[str, tuple[_Call, ...]] = {
    "python": (
        _call(r"(?<![\w.])(?:io\.|codecs\.)?open\b", names=("file", "mode"),
              mode=_Mode(1, "mode", _PY_MODE)),
        _call(r"\b(?:gzip|bz2|lzma)\.open\b", names=("filename", "mode"),
              mode=_Mode(1, "mode", _PY_MODE)),
        _call(r"\bos\.open\b", names=("path", "flags"),
              mode=_Mode(1, "flags", re.compile(r"O_(?:WRONLY|RDWR|CREAT|APPEND|TRUNC)"), raw=True)),
        _call(r"\bos\.(?:remove|unlink|rmdir|removedirs|truncate)\b", names=("path",)),
        _call(r"\bos\.(?:rename|renames|replace)\b", (0, 1), names=("src", "dst")),
        _call(r"\bshutil\.(?:copy|copy2|copyfile|copytree)\b", (1,), names=("src", "dst")),
        _call(r"\bshutil\.move\b", (0, 1), names=("src", "dst")),
        _call(r"\bshutil\.rmtree\b", names=("path",)),
        # A module's function of the same name (`os.unlink`) is matched above.
        _call(r"(?<!\bos)(?<!\bshutil)\.(?:write_text|write_bytes|unlink|touch|rmdir)\b", (),
              receiver="any"),
        _call(r"\.(?:rename|replace)\b", names=("target",), receiver="path"),
        _call(r"\.open\b", (), names=("mode",), mode=_Mode(0, "mode", _PY_MODE),
              receiver="path"),
    ),
    # Node's `fs` (and `fs/promises`), Deno, and Bun.
    "js": (
        _call(r"(?<![\w$])(?:writeFile|writeFileSync|appendFile|appendFileSync|createWriteStream"
              r"|unlinkSync|rmSync|rmdirSync|truncateSync)" + _JS_NAME_END),
        _call(r"\.(?:unlink|rm|rmdir|truncate)" + _JS_NAME_END),
        _call(r"(?<![\w$])renameSync" + _JS_NAME_END + r"|\.rename" + _JS_NAME_END, (0, 1)),
        _call(r"(?<![\w$])(?:copyFileSync|cpSync)" + _JS_NAME_END
              + r"|\.(?:copyFile|cp)" + _JS_NAME_END, (1,)),
        _call(r"(?<![\w$])openSync" + _JS_NAME_END + r"|\.open" + _JS_NAME_END,
              mode=_Mode(1, "", _JS_FLAGS)),
        _call(r"\bDeno\.(?:writeTextFile|writeFile|remove|create|truncate)(?:Sync)?" + _JS_NAME_END),
        _call(r"\bDeno\.rename(?:Sync)?" + _JS_NAME_END, (0, 1)),
        _call(r"\bDeno\.copyFile(?:Sync)?" + _JS_NAME_END, (1,)),
        _call(r"\bBun\.write" + _JS_NAME_END),
    ),
    # Parentheses are optional in Perl and Ruby (`unlink "a", "b"`).
    "perl": (
        _call(r"(?<![\w$@%&:>-])open\b", (2,), mode=_Mode(1, "", _PERL_MODE), mode_in_path=True),
        _call(r"(?<![\w$@%&:>-])(?:unlink|rmdir|(?:File::Path::)?(?:rmtree|remove_tree))\b", ALL),
        _call(r"(?<![\w$@%&:>-])rename\b", (0, 1)),
        _call(r"(?<![\w$@%&:>-])(?:File::Copy::)?(?:copy|cp)\b", (1,)),
        _call(r"(?<![\w$@%&:>-])(?:File::Copy::)?(?:move|mv)\b", (0, 1)),
    ),
    "ruby": (
        _call(r"\b(?:File|IO)\.(?:write|binwrite)\b"),
        _call(r"\bFile\.(?:open|new)\b", mode=_Mode(1, "mode", _RUBY_MODE)),
        _call(r"\bFile\.(?:delete|unlink)\b", ALL),
        _call(r"\bFile\.rename\b", (0, 1)),
        _call(r"\bFileUtils\.(?:rm_rf|rm_r|rm_f|rm|remove_file|remove_dir|remove_entry|remove"
              r"|rmdir|rmtree|touch)\b", ALL),
        _call(r"\bFileUtils\.(?:mv|move)\b", (0, 1)),
        _call(r"\bFileUtils\.(?:cp_r|cp|copy_file|copy|install)\b", (1,)),
    ),
}
_PARENS_OPTIONAL = frozenset({"perl", "ruby"})
_KEYWORD_RE = {
    "python": re.compile(r"^([A-Za-z_]\w*)\s*=(?!=)\s*(.*)$", re.DOTALL),
    "ruby": re.compile(r"^([A-Za-z_]\w*):\s+(.*)$", re.DOTALL),
}
# String literals that hold no run-time part, by language: the quote, and what
# in a double-quoted body would make it interpolate.
_LITERAL_RE = {
    "python": re.compile(r"^(?P<prefix>[rRbBuU]{0,2})(?P<q>'''|\"\"\"|'|\")(?P<body>.*)(?P=q)$",
                         re.DOTALL),
    "js": re.compile(r"^(?P<q>['\"`])(?P<body>.*)(?P=q)$", re.DOTALL),
    "perl": re.compile(r"^(?P<q>['\"])(?P<body>.*)(?P=q)$", re.DOTALL),
    "ruby": re.compile(r"^(?P<q>['\"])(?P<body>.*)(?P=q)$", re.DOTALL),
}
_INTERPOLATES = {"js": "${", "ruby": "#{"}
_PATH_RECEIVER_RE = re.compile(r"(?<![\w.])(?:pathlib\.)?(?:Pure(?:Posix|Windows)?)?Path\s*$")
# Where an argument list without parentheses ends, in Perl and Ruby.
_BARE_END_RE = re.compile(r"\s+(?:or|and|if|unless|do)\b|\|\||&&|[;\n{}]")


def writes(language: str, code: str, expanded: bool = False) -> tuple[list[str], bool]:
    """The files `code`, in `language` (a `LANGUAGES` value), writes, removes,
    or renames, in the order its calls appear, and whether some write call
    names its file only at run time. An unknown language writes nothing.

    `expanded` says the shell may have expanded the code before the
    interpreter got it (an argument, an unquoted heredoc), so a literal
    holding `$` or a backtick (`'$F'`, `'$(ls)'`) names a file only the
    shell knows: it is an unnamed write."""

    code = _resolve_aliases(language, code)
    found: list[tuple[int, list[str], bool]] = []
    for call in WRITE_CALLS.get(language, ()):
        for match in call.pattern.finditer(code):
            parsed = _arguments(code, match.end(), language)
            if parsed is None:
                continue
            files, unnamed = _call_writes(call, language, code, match.start(), *parsed)
            if expanded and any(map(_SHELL_EXPANDS_RE.search, files)):
                files, unnamed = [f for f in files if not _SHELL_EXPANDS_RE.search(f)], True
            if files or unnamed:
                found.append((match.start(), files, unnamed))
    found.sort(key=lambda item: item[0])
    return [f for _, files, _ in found for f in files], any(u for _, _, u in found)


_SHELL_EXPANDS_RE = re.compile(r"[$`]")
# The modules whose write calls the Python table names, as an import may rename them.
_PY_MODULES = r"(?:os|shutil|io|codecs|pathlib|gzip|bz2|lzma)"
_PY_IMPORT_AS_RE = re.compile(rf"\bimport\s+({_PY_MODULES})\s+as\s+(\w+)")
_PY_FROM_IMPORT_RE = re.compile(rf"\bfrom\s+({_PY_MODULES})\s+import\s+\(?([\w \t,]+)\)?")
_FS = r"""['"](?:node:)?fs(?:/promises)?['"]"""
# `const {a: b} = require('fs')` (group 1) and `import {a as b} from 'fs'` (group 2).
_JS_DESTRUCTURE_RE = re.compile(
    rf"\{{([^{{}}]*)\}}\s*=\s*(?:await\s+)?(?:require|import)\(\s*{_FS}\s*\)"
    rf"|\bimport\s*\{{([^{{}}]*)\}}\s*from\s*{_FS}"
)


def _resolve_aliases(language: str, code: str) -> str:
    """`code` with each name an import gave a write call's module or function
    spelled as the table knows it: after `import shutil as s`, `s.move(`
    reads `shutil.move(`; after `from os import remove`, `remove(` reads
    `os.remove(`; after `const {writeFileSync: w} = require('fs')`, `w(`
    reads `fs.writeFileSync(`. Other renamings (an assignment, `getattr`)
    are not followed."""

    renames: list[tuple[str, str]] = []  # (pattern, replacement)
    if language == "python":
        for module, alias in _PY_IMPORT_AS_RE.findall(code):
            renames.append((rf"(?<![\w.]){re.escape(alias)}\.", f"{module}."))
        for module, names in _PY_FROM_IMPORT_RE.findall(code):
            for name, alias in _imported(names, " as "):
                renames.append((rf"(?<![\w.]){re.escape(alias)}(?=\s*\()", f"{module}.{name}"))
    elif language == "js":
        for match in _JS_DESTRUCTURE_RE.finditer(code):
            required = match.group(1) is not None
            entries = match.group(1) if required else match.group(2)
            for name, alias in _imported(entries, ":" if required else " as "):
                renames.append((rf"(?<![\w$.]){re.escape(alias)}(?=\s*\()", f"fs.{name}"))
    for pattern, replacement in renames:
        code = re.sub(pattern, replacement, code)
    return code


def _imported(entries: str, separator: str) -> list[tuple[str, str]]:
    """Each (name, the name code calls it by) in an import list such as
    `remove as rm, rename` (`separator` " as ") or `writeFileSync: w` (":")."""

    pairs = []
    for entry in entries.split(","):
        name, _, alias = (part.strip() for part in entry.strip().partition(separator))
        if re.fullmatch(r"[\w$]+", name):
            pairs.append((name, alias if re.fullmatch(r"[\w$]+", alias) else name))
    return pairs


def _call_writes(call: _Call, language: str, code: str, start: int, positional: list[str],
                 keywords: dict[str, str]) -> tuple[list[str], bool]:
    """The literal files one matched call writes and whether it writes an unnamed one."""

    def argument(index: int) -> str | None:
        if index < len(positional):
            return positional[index]
        name = call.names[index] if index < len(call.names) else ""
        return keywords.get(name) if name else None

    receiver: str | None = None
    if call.receiver:
        receiver = _path_receiver(code, start, language)
        if receiver is None and call.receiver == "path":
            return [], False  # `.replace` on a string, `.open` on something else.
    if call.mode_in_path and call.mode and len(positional) == call.mode.index + 1:
        positional = [*positional[:-1], *_split_mode(positional[-1])]
    if call.mode is not None:
        mode = argument(call.mode.index)
        if mode is None and call.mode.keyword:
            mode = keywords.get(call.mode.keyword)
        if mode is None or not _mode_writes(call.mode, mode, language):
            return [], False

    texts = positional if call.targets == ALL else [argument(i) for i in call.targets]
    if call.receiver:
        texts = [receiver or "", *texts]  # "" for a receiver that is no `Path("…")`.
    files, unnamed = [], False
    for text in texts:
        if text is None:
            continue
        literal = _literal(text, language)
        if literal:
            files.append(literal)
        else:
            unnamed = True
    return files, unnamed


def _mode_writes(mode: _Mode, text: str, language: str) -> bool:
    if mode.raw:
        return bool(mode.writes.search(text))
    literal = _literal(text, language)
    return literal is None or bool(mode.writes.search(literal))


def _split_mode(text: str) -> list[str]:
    """Perl's two-argument `open(FH, ">PATH")` as its mode and path: the mode
    is the leading `<`, `>`, `>>`, or `+` signs of a quoted path."""

    match = re.match(r"^(['\"])\s*(\+?(?:<|>>|>)?)\s*(.*)\1$", text.strip(), re.DOTALL)
    if match is None:
        return ["'<'", text]  # A path in a variable opens to read.
    quote, sign, rest = match.groups()
    return [f"'{sign or '<'}'", f"{quote}{rest}{quote}"]


def _path_receiver(code: str, start: int, language: str) -> str | None:
    """The argument of the `Path(...)` a method at `start` is called on, or
    None when the receiver is anything else."""

    if language != "python":
        return None
    end = len(code[:start].rstrip())
    if not end or code[end - 1] != ")":
        return None
    depth, i = 0, end - 1
    while i >= 0:
        depth += {")": 1, "(": -1}.get(code[i], 0)
        if depth == 0:
            break
        i -= 1
    if i < 0 or not _PATH_RECEIVER_RE.search(code[:i]):
        return None
    parsed = _arguments(code, i, language)
    return parsed[0][0] if parsed and len(parsed[0]) == 1 else ""


def _literal(text: str, language: str) -> str | None:
    """The string `text` is, when it is one literal with no run-time part, else None."""

    match = _LITERAL_RE[language].match(text.strip())
    if match is None:
        return None
    body = match.group("body")
    quote = match.group("q")
    if len(quote) == 1 and quote in body.replace("\\" + quote, ""):
        return None  # Two literals with something between them: `'a' + b + 'c'`.
    if language == "python":
        prefix = match.group("prefix").lower()
        return body if "r" in prefix else body.replace("\\\\", "\\")
    if quote != "'" and (_INTERPOLATES.get(language, "") or "$") in body:
        return None
    if language == "perl" and quote == '"' and "@" in body:
        return None
    return body or None


def _arguments(code: str, i: int, language: str) -> tuple[list[str], dict[str, str]] | None:
    """The positional and keyword arguments of the call whose name ends at
    `i`, or None when no argument list follows (`f.open` read as a value).
    Without parentheses, in Perl or Ruby, the list runs to the end of
    the statement (`;`, a newline, `or die`, a block)."""

    j = i
    while j < len(code) and code[j] in " \t":
        j += 1
    if j < len(code) and code[j] == "(":
        body, closed = _balanced(code, j + 1, ")")
        if not closed:
            return None
    elif language in _PARENS_OPTIONAL and j > i and j < len(code) and code[j] not in ",;=)]}.\n":
        body = _balanced(code, j, "", stop=_BARE_END_RE)[0]
    else:
        return None
    positional, keywords = [], {}
    keyword_re = _KEYWORD_RE.get(language)
    for part in _split_top_level(body):
        if not part.strip():
            continue
        keyword = keyword_re.match(part.strip()) if keyword_re else None
        if keyword:
            keywords[keyword.group(1)] = keyword.group(2)
        else:
            positional.append(part)
    return positional, keywords


_CLOSERS = {"(": ")", "[": "]", "{": "}"}


def _balanced(code: str, i: int, close: str, stop: re.Pattern | None = None) -> tuple[str, bool]:
    """The text from `i` to the `close` bracket that balances (or, with
    `stop`, to the first top-level match of it), skipping quoted strings;
    and whether it ended there rather than at the end of the code."""

    stack: list[str] = []
    j = i
    while j < len(code):
        c = code[j]
        if c in "'\"`":
            j = _string_end(code, j)
            continue
        if not stack:
            if close and c == close:
                return code[i:j], True
            if stop is not None and stop.match(code, j):
                return code[i:j], True
        if c in _CLOSERS:
            stack.append(_CLOSERS[c])
        elif stack and c == stack[-1]:
            stack.pop()
        elif not stack and c in ")]}":
            return code[i:j], bool(stop)
        j += 1
    return code[i:], False


def _string_end(code: str, i: int) -> int:
    """The index just past the string literal opening at `i`."""

    quote = code[i]
    j = i + 1
    while j < len(code):
        if code[j] == "\\":
            j += 2
            continue
        if code[j] == quote:
            return j + 1
        j += 1
    return len(code)


def _split_top_level(body: str) -> list[str]:
    """`body` split at the commas outside brackets and strings."""

    parts, depth, start, j = [], 0, 0, 0
    while j < len(body):
        c = body[j]
        if c in "'\"`":
            j = _string_end(body, j)
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(body[start:j])
            start = j + 1
        j += 1
    parts.append(body[start:])
    return parts
