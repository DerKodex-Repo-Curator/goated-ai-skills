"""The neutral usage log (Ticket 082): what each judged event showed, appended
to a local file that every harness's adapter writes alike.

The format is `stack/schemas/usage-log.schema.json`: JSON Lines, one entry
per line, each carrying the log's version (`LOG_VERSION`), the time, the
adapter's name, the session id, the project key and, for a subagent, its
id. The entries are what the skill-usage mod stores and nothing more: a
person's prompt only as the skills it names, a hold only as its gate, kind
and what it asks for, skip reasons masked and cut as the mod keeps them,
installed skills' files as paths within the skill, and other files read
only as digests salted with the log's salt. No prompt text, hold text, file
content or project path is written.

`Recorder` is the one way in: `judge` makes one per event and says, in
order, what the event read (`turns`: the route and skip lines, loads with
their cause, reference reads and code changes no earlier event logged) and
what it showed (outcomes, holds, a prompt, a turn end). `flush` writes it
all, one batch of lines per event under a lock on the whole log, so writers
in many processes never lose or mix a line. How far each turn was read
lives in a small cursor file per session and agent under the core's state
folder. Writing is best effort: `flush` never raises, and a log that cannot
be written leaves the decision as it was, with one warning per session.

`read_log` reads a log back: it refuses a log with an entry of a version it
does not know, and passes over, counting them, lines that are no entry.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from . import actions, events, markers, wording
from .events import Call, CallFinished, Prompt, ReplyText, SkillInvoked, Turn
from .gates import ROUTER_SKILL
from .state import (
    StateUnsafe, _safe_name, _write_json, default_root, ensure_private_directory,
)

LOG_VERSION = 1
LOG_ENV = "GOATED_USAGE_LOG"
# The value of `GOATED_USAGE_LOG` (or `--usage-log`) that keeps no log.
OFF = "off"
LOG_NAME = "usage-log.jsonl"
SALT_NAME = "usage-log-salt"
CURSOR_DIR = "usage-log"
KEY_DIGITS = 10
# The fields each entry type needs besides the common ones, as the schema says.
_COMMON = {"t": (int, float), "adapter": str, "session": str, "type": str}
_NEEDS = {"prompt": ("named",), "override": ("phrases",), "load": ("skill", "cause"),
          "hold": ("gate", "kind", "named"), "outcome": ("gate", "outcome"),
          "skip": ("skill", "reason"), "route": ("form",), "ref": ("skill", "file"),
          "skill_read": ("skills",), "file_read": ("file",), "change": (), "turn_end": (),
          "compaction": ()}

# Why a skill loaded, in the order the mod judges it (`hooks/classify.ts`):
# a person's typed command, a subagent's own choice, the person's prompt
# naming it, a hold asking for it, the route the router chose, or the agent.
SLASH, SUBAGENT, NAMED, HOLD, ROUTE, AGENT = "slash", "subagent", "named", "hold", "route", "agent"
CAUSES = (SLASH, NAMED, HOLD, ROUTE, AGENT, SUBAGENT)

# What a hold asks for, read from its text as the skill-usage mod reads it
# (`adapterHoldNamed` in `hooks/classify.ts`).
_BACKTICKED_SKILL = re.compile(r"`([a-z0-9]+(?:-[a-z0-9]+)*)`")
_DESIGN_REFERENCE = re.compile(
    r"`software-design-principles/references/([a-z0-9]+(?:-[a-z0-9]+)*\.md)`")
_SKILL_REFERENCE = re.compile(
    r"`([a-z0-9]+(?:-[a-z0-9]+)*/references/[a-z0-9]+(?:-[a-z0-9]+)*\.md)`")
_OFFERED_SKIP = re.compile(r"`goated-skip: ([a-z0-9]+(?:-[a-z0-9]+)*): ")
_CLOSEOUT_ITEM = re.compile(r"^- ([A-Z][A-Za-z ]*): (.*)$")
_BRIEF_ADDED = re.compile(r"A session started from a brief loads `([a-z0-9]+(?:-[a-z0-9]+)*)`")
_MARKER_WORDS = frozenset({"goated-hold", "goated-route", "goated-skip"})

# A skip reason as the mod keeps it (`storedReason` in `hooks/holds.ts`): each
# word, its wrapping quotes, backticks, brackets and trailing punctuation set
# aside, that is a path is masked. A path starts with a drive (`C:/`), a
# slash, or `~/`, holds a backslash or `://`, or holds a slash and either a
# second one or a file extension at its end (`src/x.ts`, `a/b/c`); `and/or`
# and `~5` are words.
REASON_LIMIT = 160
_WRAP_START = "`\"'([{<"
_WRAP_END = "`\"')]}>.,;:!?"
_PATH_START = re.compile(r"^(?:[A-Za-z]:[\\/]|[\\/]|~[\\/])")
_EXTENSION = re.compile(r"\.[A-Za-z0-9]+$")

# A path into a skill folder, as the mod finds one (`skillPaths` in `hooks/classify.ts`).
_SKILL_PATH = re.compile(r"(?<![\w.-])skills[\\/]([^\s\"'`|;&<>()]+)", re.ASCII)
_SUPPORT_DIRS = frozenset({"references", "reference", "scripts", "templates", "assets",
                           "examples", "docs"})

# How long to wait for another event's lock on a cursor or on the log, and
# when such a lock is stale, left by a process that stopped.
_CURSOR_WAIT_SECONDS = 1.0
_LOG_WAIT_SECONDS = 5.0
_LOCK_STALE_SECONDS = 10.0
# How many recent reply texts a cursor remembers, to count a turn end's last text once.
_TEXTS_KEPT = 8


class LogUnreadable(ValueError):
    """The log cannot be read, or holds an entry of a version this reader does not know."""


class LogReading(NamedTuple):
    """A log as read: its `entries`, oldest first, and how many lines were
    `skipped` as no entry (not JSON, not an object, or missing a field its
    type needs), such as a line a crashed writer cut short."""

    entries: list[dict]
    skipped: int


class UsageLog:
    """Where the log lives (`path`), which adapter writes to it (`adapter`,
    a short name such as `claude-code`), and the clock its times come from."""

    __slots__ = ("path", "adapter", "clock")

    def __init__(self, path: Path, adapter: str,
                 clock: Callable[[], float] = time.time) -> None:
        self.path = Path(path)
        self.adapter = adapter
        self.clock = clock


def default_path() -> Path:
    """The log's place when the caller names none: a per-user data folder,
    never a project's. Windows uses `%LOCALAPPDATA%\\goated`, else the
    per-user temp folder's `goated`; elsewhere `$XDG_STATE_HOME/goated`,
    else `~/.local/state/goated`."""

    local = os.environ.get("LOCALAPPDATA") if os.name == "nt" else None
    return (Path(local) if local else default_root()) / "goated" / LOG_NAME


def path_from_environment(named: str | None = None, default: bool = True) -> Path | None:
    """The log's path: `named`, else `GOATED_USAGE_LOG`, else `default_path()`
    when `default`, else None. `off` in any case, named or set, keeps none
    (None)."""

    named = named or os.environ.get(LOG_ENV)
    if named and named.strip().lower() == OFF:
        return None
    if named:
        return Path(named)
    return default_path() if default else None


def read_log(path: Path) -> LogReading:
    """The log at `path`, oldest first; no entries when there is no log.

    An entry of a version other than `LOG_VERSION` is refused, not guessed
    at: it raises `LogUnreadable`, which names its line. A line that is no
    entry of this version (not JSON, not an object, or missing a field its
    type needs) is passed over and counted, so one bad line never hides the
    rest. A log that cannot be read raises `LogUnreadable` too."""

    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return LogReading([], 0)
    except OSError as exc:
        raise LogUnreadable(f"could not read the usage log at {path} "
                            f"({exc.strerror or exc})") from exc
    entries = []
    skipped = 0
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except (ValueError, RecursionError):
            entry = None
        version = entry.get("log") if isinstance(entry, dict) else None
        if isinstance(version, int) and not isinstance(version, bool) and version != LOG_VERSION:
            raise LogUnreadable(
                f"line {number} of the usage log at {path} is of log version {version}, "
                f"which this reader does not know (it knows version {LOG_VERSION})")
        if version == LOG_VERSION and _complete(entry):
            entries.append(entry)
        else:
            skipped += 1
    return LogReading(entries, skipped)


def _complete(entry: dict) -> bool:
    """Whether `entry` has every field its type needs, the common ones typed."""

    needs = _NEEDS.get(entry.get("type"))
    return (needs is not None
            and all(isinstance(entry.get(k), kind) for k, kind in _COMMON.items())
            and all(k in entry for k in needs))


class Recorder:
    """The entries one judged event adds to the log, for `session_id` and,
    in a subagent, `agent_id`. `project_folder` is the folder whose key the
    entries carry, or None for none; `skills()` gives the installed skill
    names, the ones a prompt may name and whose folders' files count as a
    skill's, called only when needed. Say what the event read and showed, in
    that order, then `flush`."""

    def __init__(self, log: UsageLog, state_dir: Path, session_id: str,
                 agent_id: str | None, project_folder: str | None,
                 skills: Callable[[], frozenset[str]]) -> None:
        self.log = log
        self.session_id = session_id
        self.agent_id = agent_id
        self.project_folder = project_folder
        self.skills = skills
        self.cursor_path = (Path(state_dir) / CURSOR_DIR
                            / (_safe_name(session_id)
                               + (f".{_safe_name(agent_id)}" if agent_id else "") + ".json"))
        # What to log, run in order under the cursor's lock by `flush`.
        self._steps: list[Callable[[_Writing], None]] = []

    def turns(self, turns: list[Turn], final_text: str = "",
              pending: Call | None = None) -> None:
        """The facts of `turns`, oldest first, that no earlier event logged.
        `final_text` is the turn's last reply text when the turns may not
        hold it yet; it counts once, here or where it later shows. `pending`
        is the call being judged, whose lines count before its holds."""

        self._steps.append(lambda w: w.turns(turns, final_text, pending))

    def outcomes(self, settled: list[tuple[str, str]]) -> None:
        """Each settled hold, as (gate, outcome)."""

        self._steps.append(lambda w: [w.add("outcome", gate=g, outcome=o) for g, o in settled])

    def holds(self, shown: list, stop: bool = False) -> None:
        """Each hold of `shown` (`gates.Shown`, as the core gives it), as what
        it asks for; `stop`: they held a turn's end, not a call."""

        self._steps.append(lambda w: w.holds(shown, stop))

    def prompt(self, typed_text: str | None, phrases: list[str]) -> None:
        """A prompt that opens a turn, as the skills its typed text names
        (none for a prompt no person typed), and the overrides recorded for it."""

        self._steps.append(lambda w: w.prompt(typed_text, phrases))

    def turn_end(self) -> None:
        """The turn ended as an answer: its end was let through."""

        self._steps.append(lambda w: (w.add("turn_end"), w.cursor.update(ended=True)))

    def turn_ended(self) -> bool:
        """Whether the last turn this session's log read ended as an answer,
        so every fact of it is logged, and the next prompt need not read it
        again. False when the cursor cannot be read."""

        return _load_cursor(self.cursor_path)["ended"]

    def compaction(self) -> None:
        """The context was compacted: what loaded before no longer counts."""

        self._steps.append(lambda w: w.compaction())

    def flush(self) -> str | None:
        """Write what was said: take the cursor's lock, read the cursor, work
        out the entries, append them, save the cursor, and let the lock go.
        Returns a warning when the log could not be written, the first time
        in the session only, else None; never raises, so the log never blocks
        a call."""

        if not self._steps:
            return None
        cursor_lock = None
        try:
            ensure_private_directory(self.cursor_path.parent, "usage log's cursor folder")
            cursor_lock = _lock(self.cursor_path.with_suffix(".lock"), _CURSOR_WAIT_SECONDS)
            writing = _Writing(self, _load_cursor(self.cursor_path))
            for step in self._steps:
                step(writing)
            if writing.entries:
                _append(self.log.path, writing.entries)
            _write_json(self.cursor_path, writing.cursor)
        except Exception as exc:  # noqa: BLE001 - the log is best effort and never blocks a call
            return self._warn_once(
                f"could not write the usage log ({getattr(exc, 'strerror', None) or exc})")
        finally:
            self._steps = []
            _unlock(cursor_lock)
        return None

    def _warn_once(self, text: str) -> str | None:
        """`text` the first time the session's log fails, None after; `text`
        whenever even the mark that it was said cannot be made."""

        try:
            with open(self.cursor_path.with_suffix(".warned"), "x", encoding="utf-8"):
                return text
        except FileExistsError:
            return None
        except OSError:
            return text


class _Writing:
    """One flush's work: the cursor as read, and the entries it adds."""

    def __init__(self, recorder: Recorder, cursor: dict) -> None:
        self.recorder = recorder
        self.cursor = cursor
        self.entries: list[dict] = []
        self._key: str | None | bool = False
        self._salt: str | None | bool = False
        # Whether this flush began reading a turn the cursor had not seen.
        self._adopted = False

    def add(self, entry_type: str, /, **fields) -> None:
        r = self.recorder
        entry = {"log": LOG_VERSION, "t": r.log.clock(), "adapter": r.log.adapter,
                 "session": r.session_id, "project": self._project_key()}
        if r.agent_id:
            entry["agent"] = r.agent_id
        entry["type"] = entry_type
        entry.update(fields)
        self.entries.append(entry)

    def _project_key(self) -> str | None:
        if self._key is False:
            folder, salt = self.recorder.project_folder, self._log_salt()
            self._key = project_key(folder, salt) if folder and salt else None
        return self._key

    def _log_salt(self) -> str | None:
        """The log's salt, or None when it cannot be read or made: then no
        project key or file digest is written, rather than an unsalted one."""

        if self._salt is False:
            try:
                self._salt = _salt(self.recorder.log.path)
            except (OSError, ValueError, StateUnsafe):
                self._salt = None
        return self._salt

    # What the event showed ----------------------------------------------

    def holds(self, shown: list, stop: bool) -> None:
        for hold in shown:
            text = wording.neutral(hold.text)
            entry = {"gate": hold.gate, "kind": hold.kind, **asks_of(hold.gate, text)}
            if stop:
                entry["stop"] = True
            self.add("hold", **entry)
            self.cursor["asked"] = sorted({*self.cursor["asked"], *entry["named"]})

    def prompt(self, typed_text: str | None, phrases: list[str]) -> None:
        named = skills_named(typed_text, self.recorder.skills()) if typed_text else []
        self.add("prompt", named=named)
        if phrases:
            self.add("override", phrases=[phrase.lower() for phrase in phrases])
        # The turn this prompt opens was read just now, or will be later.
        self.cursor["named" if self._adopted else "next_named"] = named

    def compaction(self) -> None:
        self.add("compaction")
        self.cursor = _fresh_cursor()

    # What the event read ------------------------------------------------

    def turns(self, turns: list[Turn], final_text: str, pending: Call | None) -> None:
        keys = [turn.key for turn in turns]
        # Turns before the cursor's were logged by earlier events.
        start = keys.index(self.cursor["turn"]) if self.cursor["turn"] in keys else 0
        for turn in turns[start:]:
            self._turn(turn)
        if pending is not None and turns:
            self._call_lines(pending)
        if final_text and turns:
            digest = _digest(final_text)
            if digest not in self.cursor["texts_seen"]:
                self._markers(final_text)
                self.cursor["final"] = digest

    def _turn(self, turn: Turn) -> None:
        """The facts of `turn` past the cursor, in the order of its entries;
        a call counts where it finished."""

        cursor = self.cursor
        if cursor["turn"] != turn.key:
            named = cursor["next_named"]
            if named is None:
                opener = turn.opener
                named = (skills_named(opener.text, self.recorder.skills())
                         if turn.typed and isinstance(opener, Prompt) else [])
            cursor.update(_fresh_cursor(), turn=turn.key, named=named)
            self._adopted = True
        finished = {call.id: call for call in turn.calls if call.id}
        for call_id in [i for i in cursor["waiting"] if i in finished]:
            cursor["waiting"].remove(call_id)
            self._call(finished[call_id])
        marked = {entry.call_id for entry in turn.entries if isinstance(entry, CallFinished)}
        for entry in turn.entries[cursor["entries"]:]:
            if isinstance(entry, ReplyText):
                digest = _digest(entry.text)
                if digest == cursor["final"]:
                    cursor["final"] = None
                else:
                    self._markers(entry.text)
                cursor["texts_seen"] = [*cursor["texts_seen"], digest][-_TEXTS_KEPT:]
            elif isinstance(entry, Call):
                self._call_lines(entry)
                if entry.result is None or entry.id in marked:
                    if entry.id and entry.id not in cursor["waiting"]:
                        cursor["waiting"].append(entry.id)
                else:
                    self._call(entry)
            elif isinstance(entry, CallFinished):
                if entry.call_id in cursor["waiting"] and entry.call_id in finished:
                    cursor["waiting"].remove(entry.call_id)
                    self._call(finished[entry.call_id])
            elif isinstance(entry, SkillInvoked):
                self._load(_short(entry.skill), SLASH)
        cursor["entries"] = len(turn.entries)

    def _call_lines(self, call: Call) -> None:
        """The route and skip lines of a call's line text, once per call."""

        key = call.id or _digest(call.kind + call.line_text)
        if key in self.cursor["lined"]:
            return
        self.cursor["lined"].append(key)
        if call.line_text:
            self._markers(call.line_text)

    def _markers(self, text: str) -> None:
        found = markers.parse_reply(text)
        if found.route is not None:
            self.add("route", **found.route)
        for skip in found.skips:
            self.add("skip", skill=skip["skill"], reason=stored_reason(skip["reason"]))

    def _call(self, call: Call) -> None:
        """The facts of one finished call: a load, a code change, or the
        files a read or command reached."""

        if call.kind == events.SKILL_LOAD:
            if call.ok and call.skill:
                skill = _short(call.skill)
                self._load(skill, self._cause(skill))
            return
        if call.kind == events.FILE_WRITE:
            if call.ok and actions.is_code(call.path.replace("\\", "/")):
                self.add("change")
            return
        if call.kind == events.FILE_READ:
            target, read_tool = call.path, True
        elif call.kind == events.SHELL_COMMAND:
            target, read_tool = call.command, False
        else:
            return
        # Only an installed skill's folder is a skill's: a project's own
        # `skills/` folder, and the files in it, are never named.
        installed = self.recorder.skills()
        if self.recorder.agent_id is None:
            # Only the main agent's reads answer holds by files read.
            salt = self._log_salt() if read_tool and call.ok else None
            if salt:
                self.add("file_read", file=_digest(f"{salt}\n{_comparable(target)}"))
            reached = [skill for skill in skills_in_path(target) if skill in installed]
            if reached:
                self.add("skill_read", skills=reached)
        for skill, file in skill_files(target):
            if skill not in installed:
                continue
            entry: dict = {"skill": skill, "file": file}
            if read_tool:
                entry["read_tool"] = True
                if not call.whole:
                    entry["partial"] = True
            self.add("ref", **entry)

    def _cause(self, skill: str) -> str:
        asked = skill in self.cursor["asked"]
        if self.recorder.agent_id is not None:
            return HOLD if asked else SUBAGENT
        if skill in self.cursor["named"]:
            return NAMED
        if asked:
            return HOLD
        if self.cursor["router"] and skill != ROUTER_SKILL:
            return ROUTE
        return AGENT

    def _load(self, skill: str, cause: str) -> None:
        self.add("load", skill=skill, cause=cause)
        if skill == ROUTER_SKILL:
            self.cursor["router"] = True


def _fresh_cursor() -> dict:
    """A cursor that has read nothing: the turn read last and how far
    (`entries`), its calls not yet finished, the calls whose lines counted,
    its recent reply texts and a turn end's last one, the skills its prompt
    named, those its holds asked for, whether the router loaded in it,
    whether its end was logged, and the skills a prompt not yet read as a
    turn named."""

    return {"turn": None, "entries": 0, "waiting": [], "lined": [], "texts_seen": [],
            "final": None, "named": [], "asked": [], "router": False, "ended": False,
            "next_named": None}


def _load_cursor(path: Path) -> dict:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _fresh_cursor()
    fresh = _fresh_cursor()
    if not isinstance(loaded, dict) or set(loaded) != set(fresh):
        return fresh
    return loaded


# Reading what a text or path names -----------------------------------------


def asks_of(gate: str, text: str) -> dict:
    """What a hold of `gate` with `text` asks for, as the skill-usage mod
    reads it: `named`, the skills it backticks alone or offers as a skip
    line, in order; `skip_only`, those it offers only as a skip line;
    `refs`, the references a design or reference-reads hold asks to read;
    `items`, a closeout's items with the skill each names; and
    `brief_added`, the skill a pipeline hold asks for because the session
    started from a brief. A key with nothing in it is left out, but `named`.
    The route-line hold asks for a route line, which is no skill."""

    if gate == "router-first":
        return {"named": [ROUTER_SKILL]}
    if gate == "route-line":
        return {"named": []}
    found = _named_in(gate, text)
    brief = _BRIEF_ADDED.search(text) if gate == "pipeline" else None
    if brief:
        found["brief_added"] = [brief[1]]
    items = _items_listed(text) if gate == "closeout" else []
    if items:
        found["items"] = items
    return found


def _named_in(gate: str, text: str) -> dict:
    asked = (_SKILL_REFERENCE if gate == "reference-reads"
             else _DESIGN_REFERENCE if gate in ("design", "design-reads") else None)
    refs = [m[1] for m in asked.finditer(text)] if asked else []

    def names(pattern: re.Pattern) -> list[tuple[int, str]]:
        return [(m.start(), m[1]) for m in pattern.finditer(text) if m[1] not in _MARKER_WORDS]

    loads = names(_BACKTICKED_SKILL)
    ordered = sorted(loads + names(_OFFERED_SKIP), key=lambda found: found[0])
    named = list(dict.fromkeys(skill for _, skill in ordered))
    loaded = {skill for _, skill in loads}
    found: dict = {"named": named}
    skip_only = [skill for skill in named if skill not in loaded]
    if skip_only:
        found["skip_only"] = skip_only
    if refs:
        found["refs"] = refs
    return found


def _items_listed(text: str) -> list[dict]:
    items: list[dict] = []
    for line in re.split(r"\r?\n", text):
        item = _CLOSEOUT_ITEM.match(line)
        if not item:
            continue
        named = _named_in("closeout", item[2])["named"]
        if named and not any(i["label"] == item[1] and i["skill"] == named[0] for i in items):
            items.append({"label": item[1], "skill": named[0]})
    return items


def skills_named(text: str, skills) -> list[str]:
    """The skills of `skills` that `text` names, backticked, slashed or as a
    whole word, in sorted order."""

    return [skill for skill in sorted(skills)
            if re.search(rf"(?<![\w-])/?{re.escape(skill)}(?![\w-])", text, re.ASCII)]


def stored_reason(reason: str) -> str:
    """A skip reason as the log keeps it: each path-like word masked as
    `<path>`, then cut to `REASON_LIMIT` characters, its last an ellipsis."""

    masked = re.sub(r"\S+", lambda word: _masked_word(word[0]), reason)
    return masked if len(masked) <= REASON_LIMIT else masked[:REASON_LIMIT - 1] + "…"


def _masked_word(word: str) -> str:
    """`word` with the path inside its wrapping masked as `<path>`; the word
    itself when it holds no path."""

    inner = word.lstrip(_WRAP_START)
    start = word[:len(word) - len(inner)]
    core = inner.rstrip(_WRAP_END)
    end = inner[len(core):]
    is_path = bool(core) and (
        _PATH_START.match(core) is not None or "\\" in core or "://" in core
        or ("/" in core and (core.count("/") >= 2 or _EXTENSION.search(core) is not None)))
    return f"{start}<path>{end}" if is_path else word


def _skill_paths(text: str) -> list[tuple[str, list[str]]]:
    """Each path into a skill folder that `text` names, as its skill and the
    parts below it: the folder holding a SKILL.md or a supporting folder,
    else the first folder under `skills`."""

    found = []
    for match in _SKILL_PATH.finditer(text):
        parts = [p for p in re.split(r"[\\/]", match[1]) if p]
        support = next((i for i, p in enumerate(parts) if i > 0 and p in _SUPPORT_DIRS), -1)
        if len(parts) > 1 and parts[-1].upper() == "SKILL.MD":
            at = len(parts) - 2
        else:
            at = support - 1 if support > 0 else 0
        skill = parts[at] if at < len(parts) else ""
        if re.fullmatch(r"[\w-]+", skill, re.ASCII):
            found.append((skill, parts[at + 1:]))
    return found


def skills_in_path(text: str) -> list[str]:
    """The skill folders a path or command reaches into, in order."""

    return list(dict.fromkeys(skill for skill, _ in _skill_paths(text)))


def skill_files(text: str) -> list[tuple[str, str]]:
    """The supporting files of skills a path or command reads, each as its
    skill and its path within the skill (`references/x.md`); a skill's
    SKILL.md, a folder and a glob are none."""

    found: dict = {}
    for skill, below in _skill_paths(text):
        file = "/".join(below)
        name = below[-1] if below else ""
        if (not file or re.search(r"[*?]", file) or not re.search(r"\.\w+$", name, re.ASCII)
                or name.upper() == "SKILL.MD"):
            continue
        found[f"{skill}/{file}"] = (skill, file)
    return list(found.values())


def _comparable(path: str) -> str:
    """A path as the mod compares files read (`comparablePath` in `hooks/holds.ts`)."""

    if re.match(r"[a-z]:", path, re.I) or "\\" in path:
        path = path.replace("\\", "/").lower()
    parts: list[str] = []
    for part in path.split("/"):
        if part == ".":
            continue
        if part == ".." and parts and parts[-1] not in ("..", ""):
            parts.pop()
        else:
            parts.append(part)
    return "/".join(parts)


def _short(skill: str) -> str:
    """A skill's bare name: `plugin:skill` and `skill` are the same skill."""

    return skill.split(":")[-1]


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# The project key ------------------------------------------------------------


def project_key(folder: str, salt: str) -> str:
    """The key of a project folder under the log's salt, made as the
    skill-usage mod makes its own: the first hex digits of the SHA-256
    digest of the salt and the folder's path, the folder being its
    repository's root (the main working tree's, for a worktree) when it lies
    in one. One path spelled with either slash, with or without a trailing
    one, and with a drive letter in any case, is one key."""

    path = _repository_root(folder).replace("\\", "/").rstrip("/")
    if re.match(r"[A-Za-z]:", path):
        path = path.lower()
    return hashlib.sha256(f"{salt}\n{path}".encode("utf-8")).hexdigest()[:KEY_DIGITS]


def _repository_root(folder: str) -> str:
    """The repository root at or above `folder`, the main working tree's for
    a worktree, else `folder` itself."""

    here = Path(folder)
    for candidate in (here, *here.parents):
        git = candidate / ".git"
        try:
            if git.is_dir():
                return str(candidate)
            if git.is_file():
                gitdir = git.read_text(encoding="utf-8").partition("gitdir:")[2].strip()
                main, found, _ = gitdir.replace("\\", "/").partition("/.git/worktrees/")
                return main if found and main else str(candidate)
        except OSError:
            return folder
    return folder


def _salt(log_path: Path) -> str:
    """The salt beside the log, made once: 16 random bytes as hex."""

    path = Path(log_path).parent / SALT_NAME
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        pass
    ensure_private_directory(path.parent, "usage log folder")
    salt = os.urandom(16).hex()
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return path.read_text(encoding="utf-8").strip()
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(salt)
    return salt


# Files ----------------------------------------------------------------------


class LogBusy(OSError):
    """Another writer held the log's lock past the wait, and it is not stale."""


def project_key_of_log(log_path: Path, folder: str) -> str | None:
    """The key the log at `log_path` gives the project `folder`, or None when
    the log has no salt yet (so no entry has that key)."""

    try:
        salt = (Path(log_path).parent / SALT_NAME).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return project_key(folder, salt)


def _append(path: Path, entries: list[dict]) -> None:
    """Append `entries` as lines, under the log's lock, in one write to a
    descriptor opened for appending: Windows emulates appending with a seek
    before each write, so without the lock writers in other processes could
    write over each other's lines. The folder is the user's alone, as skip
    reasons are kept as written but for their paths. Raises `OSError`
    (`LogBusy` when the lock could not be had)."""

    path = Path(path)
    ensure_private_directory(path.parent, "usage log folder")
    data = "".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in entries)
    lock = _lock(path.with_name(path.name + ".lock"), _LOG_WAIT_SECONDS)
    if lock is None:
        raise LogBusy("another writer held the usage log too long")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0),
                     0o600)
        try:
            view = memoryview(data.encode("utf-8"))
            while view:
                view = view[os.write(fd, view):]
        finally:
            os.close(fd)
    finally:
        _unlock(lock)


def _lock(lock: Path, wait: float) -> Path | None:
    """Take the lock file `lock`, waiting up to `wait` seconds for its holder
    and breaking a lock older than `_LOCK_STALE_SECONDS`, left by a process
    that stopped; None when it cannot be had. The caller lets it go with
    `_unlock`."""

    deadline = time.monotonic() + wait
    while True:
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
            return lock
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > _LOCK_STALE_SECONDS:
                    lock.unlink()
                    continue
            except OSError:
                pass
            if time.monotonic() > deadline:
                return None
            time.sleep(0.01)
        except PermissionError:
            # Windows refuses to create a file another process is deleting.
            if time.monotonic() > deadline:
                return None
            time.sleep(0.01)


def _unlock(lock: Path | None) -> None:
    if lock is not None:
        try:
            lock.unlink()
        except OSError:
            pass
