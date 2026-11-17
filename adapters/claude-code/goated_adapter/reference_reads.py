"""Which skill references an edit requires, as the installed registry declares them.

The registry (`stack/goated-stack.yaml` in a GOATED distribution) lists each
skill's reference files, each with a signal that makes its read required or
an advisory reason (registry reference reads spec, R1, R2). This module owns
how the adapter reads those declarations and how it judges the signal kinds
observed at one write (Tickets 067 and 068):

- `edit-adds-pattern`: the code an edit adds matches a pattern the registry
  names (`PATTERNS`), in a file of the given kind if one is given;
- `edit-of-file-kind`: an edit of a file of that kind adds at least
  `min_added_lines` lines, or, with `new_file: true`, creates the file. The
  design gate judges a test edit for `coding.md` by the same signal
  (`file_kind_signal`), so the registry owns one rule for both (Ticket 090);
- `write-under-path`: the file written is under that folder of the project;
- `gate-fires`: the named gate's condition holds at the write, whether or not
  that gate holds it (its skill may be loaded);
- `sensitive-category-count`: the write is to a security-sensitive file, and
  the turn's sensitive changes, this one included, span at least
  `min_categories` categories.

The caller observes the facts (`Edit`); this module decides which references
they select. `existing-rule` references keep their own gates, and
`spawn-with-brief` is not judged here. A reference of these kinds added to the
registry later is enforced with no change here, as long as its pattern, file
kind, and gate are ones the adapter observes.

The adapter uses only the standard library, so `load` reads the block-style
YAML subset the registry is written in, and raises `RegistryUnreadable` for a
registry it cannot find, read, or parse; the gate then asks for nothing (spec
Constraints). The validator checks that this reader and a full YAML parser
agree on the source registry.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

# The signal kinds judged on the code a write adds; they apply to code files only.
EDIT_KINDS = ("edit-adds-pattern", "edit-of-file-kind")
# The gates a `gate-fires` signal can name: the ones whose condition the adapter
# observes at a write (`Edit.gates`). The schema allows any gate, so
# `validate_skills.py` rejects a registry entry naming another.
OBSERVED_GATES = frozenset({"repeated-failure"})
MAX_REGISTRY_BYTES = 1024 * 1024


class Pattern(NamedTuple):
    """A named pattern of the registry's `reference_patterns`, as the code an
    edit adds can match it: `label` says what a match is, in a hold's words."""

    label: str
    regex: re.Pattern


# The mock pattern matches at a word start, so `dispatch` holds no patch; the
# wait pattern also inside a word (`asyncio.sleep`, `MAX_RETRIES`), though
# `retrieve` holds no retry. A word that only starts like one (`patches`,
# `spyglass`), or one in a string, still selects, since a read once per
# context window costs little.
PATTERNS = {
    "mock-or-patch": Pattern("a mock or patch", re.compile(
        r"\b(?:[Mm]ock|[Pp]atch|[Ss]tub|[Ss]py|[Ff]ake|monkeypatch|sinon)"
        r"|[a-z0-9_]Mock\b|\b(?:jest|vi)\.fn\b"
    )),
    "sleep-retry-or-timeout": Pattern("a sleep, retry, poll, or timeout", re.compile(
        r"(?i:\w*(?:sleep|timeout)|\w*retr(?:y|ies|ied|ying))"
        # `poll` and `wait for` end a word, or a part of one before an
        # underscore or a capital: `poll_interval`, `waitForSelector`.
        r"|(?:(?i:\w*poll(?:s|ed|ing|er)?)|(?i:\bwait_?for))(?=_|[A-Z]|\b)"
        r"|\bsetInterval\b"
    )),
}
# The file kinds a signal can name: "test" is a code file at a test path.
FILE_KINDS = ("test",)
# A Read of `<skill>/references/<file>`: the skill folder's name and the file's.
REFERENCE_PATH_RE = re.compile(
    r"(?:^|/)([a-z0-9]+(?:-[a-z0-9]+)*)/references/([a-z0-9]+(?:-[a-z0-9]+)*\.md)$"
)


class RegistryUnreadable(Exception):
    """The registry cannot be used: `missing` when no file is at its path,
    else it could not be read or is not the registry's shape. The message
    says why."""

    def __init__(self, why: str, missing: bool = False) -> None:
        super().__init__(why)
        self.missing = missing


class Reference(NamedTuple):
    """One reference file the registry declares with a signal: its skill, its
    file name under the skill's `references/`, and the signal as written
    (`{"kind": "edit-adds-pattern", "pattern": "mock-or-patch"}`)."""

    skill: str
    file: str
    signal: dict

    @property
    def path(self) -> str:
        """The file's path under the skill folder, as a hold names it and a read
        is recorded: `tdd/references/mocking-and-seams.md`."""

        return f"{self.skill}/references/{self.file}"


class Edit(NamedTuple):
    """What the signals read of one write and the turn before it.

    `is_code` and `is_test` say whether the file is a code file and a test
    file. `added_code` is the code of each line the write adds
    (`design_reads.added_code`): the non-blank lines the text it replaces, or
    the file on disk for a Write, did not hold, indentation aside; empty when
    unknown, as for a shell write. `new_file` says the write creates the file
    (`design_reads.creates_file`). `project_paths` are the file's paths below
    each project root that holds it, with `/` separators; empty when its place
    is unknown. `gates` names the gates whose condition holds at this write
    (`repeated-failure`). `categories` are the security-sensitive categories
    the turn's changes span, this write's included, when this write is to a
    sensitive file; else empty."""

    is_code: bool
    is_test: bool
    added_code: list[str]
    project_paths: tuple[str, ...] = ()
    gates: frozenset[str] = frozenset()
    categories: frozenset[str] = frozenset()
    new_file: bool = False


def load(path: Path | None) -> tuple[Reference, ...]:
    """Every reference the registry at `path` declares with a signal, in
    registry order; () for None. Raises `RegistryUnreadable` for a missing
    file, one that cannot be read or is too large, or one whose text is not
    the registry's shape."""

    if path is None:
        return ()
    path = Path(path)
    if not path.exists():
        raise RegistryUnreadable("no file is there", missing=True)
    try:
        if path.stat().st_size > MAX_REGISTRY_BYTES:
            raise RegistryUnreadable("it is too large")
        return tuple(_declared(_parse_yaml(path.read_text(encoding="utf-8"))))
    except (OSError, UnicodeDecodeError) as exc:
        raise RegistryUnreadable(f"it could not be read ({type(exc).__name__})") from exc
    except ValueError as exc:
        raise RegistryUnreadable(f"it does not parse: {exc}") from exc


def selected(references, edit: Edit) -> list[tuple[Reference, str]]:
    """The references among `references` whose signal `edit` fires, each with
    what selected it, in the given order. A signal of a kind not judged here,
    or naming a pattern, file kind, or gate this module is not told of,
    selects nothing."""

    found = []
    for reference in references:
        why = fires(reference.signal, edit)
        if why is not None:
            found.append((reference, why))
    return found


def file_kind_signal(references, file_kind: str) -> dict | None:
    """The first `edit-of-file-kind` signal among `references` for files of
    `file_kind`, such as `tdd`'s for `test-design.md`, or None. Another gate
    judges its own edits of that kind by it (`fires`), whether or not the
    declaring skill is loaded; `validate_skills.py` refuses a source registry
    declaring two for test files, so "first" never picks between rules."""

    return next((r.signal for r in references if r.signal.get("kind") == "edit-of-file-kind"
                 and r.signal.get("file_kind") == file_kind), None)


def reads_in(calls) -> list[str]:
    """The skill references, as `Reference.path`, that finished Read calls
    among `calls` read whole, in order (`Call.whole_read_path`). A shell
    command printing one does not count."""

    found = []
    for call in calls:
        path = call.whole_read_path()
        match = path and REFERENCE_PATH_RE.search(path.replace("\\", "/").lower())
        if match:
            found.append(f"{match.group(1)}/references/{match.group(2)}")
    return found


def fires(signal: dict, edit: Edit) -> str | None:
    """What makes `signal` fire for `edit`, in a hold's words, or None."""

    kind = signal.get("kind")
    if kind in EDIT_KINDS:
        return _edit_fires(signal, edit) if edit.is_code else None
    if kind == "write-under-path":
        # The registry's folder ends in `/`, so `docs/specs.md` is not under
        # `docs/specs/`. Case is ignored, as Windows ignores it.
        folder = signal.get("path")
        under = folder is not None and any(
            p.lower().startswith(folder.lower()) for p in edit.project_paths)
        return f'a write under "{folder}"' if under else None
    if kind == "gate-fires":
        gate = signal.get("gate")
        return f"a write while the {gate} gate's condition holds" if gate in edit.gates else None
    if kind == "sensitive-category-count":
        least, spanned = signal.get("min_categories", 1), sorted(edit.categories)
        if not spanned or len(spanned) < least:
            return None
        return (f"a security-sensitive write, the turn's changes spanning {len(spanned)} "
                f"categories ({', '.join(spanned)}), {least} or more")
    return None


def _edit_fires(signal: dict, edit: Edit) -> str | None:
    """What makes an edit-kind `signal` fire for code-file `edit`, or None."""

    kind, file_kind = signal.get("kind"), signal.get("file_kind")
    if file_kind is not None and (file_kind not in FILE_KINDS or not edit.is_test):
        return None
    in_file = f" to a {file_kind} file" if file_kind else ""
    if kind == "edit-adds-pattern":
        pattern = PATTERNS.get(signal.get("pattern"))
        token = pattern and next(
            (_word_at(code, m) for code in edit.added_code if (m := pattern.regex.search(code))),
            None)
        if token is None:
            return None
        return f'adds {pattern.label} ("{token}"){in_file}, the registry\'s {signal["pattern"]} pattern'
    if file_kind is None:
        return None
    if signal.get("new_file") is True and edit.new_file:
        return f"a new {file_kind} file"
    least, added = signal.get("min_added_lines", 1), len(edit.added_code)
    if added < least:
        return None
    return f"an edit of a {file_kind} file adding {added} lines, {least} or more"


def _word_at(code: str, match: re.Match) -> str:
    """The whole word a pattern matched part of, such as `MagicMock` for `cMock`."""

    start, end = match.start(), match.end()
    while start > 0 and (code[start - 1].isalnum() or code[start - 1] == "_"):
        start -= 1
    while end < len(code) and (code[end].isalnum() or code[end] == "_"):
        end += 1
    return code[start:end]


def _declared(data) -> list[Reference]:
    """The references with a signal in parsed registry `data`; ValueError
    when its skills or references are not the registry's shape."""

    skills = data.get("skills") if isinstance(data, dict) else None
    if not isinstance(skills, list):
        raise ValueError("the registry lists no skills")
    found = []
    for skill in skills:
        if not isinstance(skill, dict) or not isinstance(skill.get("name"), str):
            raise ValueError("a skill entry has no name")
        entries = skill.get("references", [])
        if not isinstance(entries, list):
            raise ValueError("a skill's references are not a list")
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("file"), str):
                raise ValueError("a reference entry has no file")
            signal = entry.get("signal")
            if signal is None:
                continue  # An advisory reference: no read is required.
            if not isinstance(signal, dict) or not isinstance(signal.get("kind"), str):
                raise ValueError("a reference signal has no kind")
            for key, kind in (("pattern", str), ("file_kind", str), ("min_added_lines", int),
                              ("new_file", bool), ("path", str), ("gate", str),
                              ("min_categories", int)):
                # A bool is an int to Python, but `true` is no line count.
                if key in signal and (not isinstance(signal[key], kind)
                                      or kind is int and isinstance(signal[key], bool)):
                    raise ValueError(f"a reference signal's {key} is not {kind.__name__}")
            found.append(Reference(skill["name"], entry["file"], signal))
    return found


# ---------- the registry's YAML subset ----------------------------------------
#
# Block mappings and sequences, each item indented under its key, `- ` items
# whose first key sits on the dash line, one-line plain scalars (an integer
# when all digits, a boolean when `true` or `false`, any other a string,
# `True`, `yes`, `null`, `~` and `-1` included), one-line quoted scalars
# without escapes, flow sequences of plain
# scalars (`[a, b]`), and `#` comments. A block scalar (`|`), an anchor, a
# flow mapping, a plain scalar wrapped onto more lines, a sequence not
# indented under its key, or a key with no value raises ValueError rather
# than being read wrongly. `validation/adapters.py` checks that the source
# registry reads the same here as with a full YAML parser.

_KEY_RE = re.compile(r"^([A-Za-z_][\w-]*):(?: (.*))?$")
_UNSUPPORTED_START = ("|", ">", "&", "*", "!", "{", "@", "`")


def _parse_yaml(text: str):
    lines = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or stripped == "---":
            continue
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise ValueError("a tab indents a line")
        lines.append([len(raw) - len(raw.lstrip(" ")), _uncommented(raw.strip())])
    value, end = _block(lines, 0, lines[0][0] if lines else 0)
    if end != len(lines):
        raise ValueError("a line is indented where nothing can start")
    return value


def _block(lines: list[list], start: int, indent: int):
    """The block starting at `lines[start]`, at `indent`, and the index after it."""

    if start >= len(lines) or lines[start][0] != indent:
        raise ValueError("an empty or misplaced block")
    if lines[start][1] == "-" or lines[start][1].startswith("- "):
        return _sequence(lines, start, indent)
    return _mapping(lines, start, indent)


def _sequence(lines: list[list], start: int, indent: int):
    items, i = [], start
    while i < len(lines) and lines[i][0] == indent and (lines[i][1] == "-" or lines[i][1].startswith("- ")):
        rest = lines[i][1][2:].strip()
        if not rest:
            item, i = _block(lines, i + 1, _child_indent(lines, i + 1, indent))
        elif _KEY_RE.match(rest):
            # `- key: value`: a mapping whose first line follows the dash.
            lines[i] = [indent + 2, rest]
            item, i = _mapping(lines, i, indent + 2)
        else:
            item, i = _scalar(rest), i + 1
        items.append(item)
    return items, i


def _mapping(lines: list[list], start: int, indent: int):
    mapping, i = {}, start
    while i < len(lines) and lines[i][0] == indent:
        match = _KEY_RE.match(lines[i][1])
        if match is None:
            raise ValueError("a mapping line is not `key: value`")
        key, value = match.group(1), (match.group(2) or "").strip()
        if key in mapping:
            raise ValueError("a mapping repeats a key")
        if value:
            mapping[key], i = _scalar(value), i + 1
        else:
            mapping[key], i = _block(lines, i + 1, _child_indent(lines, i + 1, indent))
    if i < len(lines) and lines[i][0] > indent:
        raise ValueError("a line is indented under a scalar")
    return mapping, i


def _child_indent(lines: list[list], at: int, parent: int) -> int:
    if at >= len(lines) or lines[at][0] <= parent:
        raise ValueError("a key has no value")
    return lines[at][0]


def _scalar(text: str):
    if text.startswith(_UNSUPPORTED_START):
        raise ValueError("an unsupported YAML value")
    if text.startswith("["):
        if not text.endswith("]"):
            raise ValueError("an unclosed flow sequence")
        inner = text[1:-1].strip()
        return [_scalar(part.strip()) for part in inner.split(",")] if inner else []
    if text[0] in "\"'":
        if len(text) < 2 or text[-1] != text[0]:
            raise ValueError("an unclosed quoted value")
        return text[1:-1]
    if text in ("true", "false"):
        return text == "true"
    return int(text) if text.isdigit() else text


def _uncommented(text: str) -> str:
    """`text` without a trailing ` # comment` outside quotes."""

    quote = None
    for index, char in enumerate(text):
        if quote:
            quote = None if char == quote else quote
        elif char in "\"'" and (index == 0 or text[index - 1] in " [,:"):
            quote = char
        elif char == "#" and index > 0 and text[index - 1] == " ":
            return text[:index].rstrip()
    return text
