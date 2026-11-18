"""The neutral usage log (Ticket 082): what each judged event showed, appended
to a local file that every harness's adapter writes alike.

The format is `stack/schemas/usage-log.schema.json`: JSON Lines, one entry
per line, each carrying the log's version (`LOG_VERSION`), the time, the
adapter's name, the session id, the project key and, for a subagent, its
id. The entries are what the skill-usage mod stores and nothing more: a
person's prompt only as the skills it names, a hold only as its gate, kind
and what it asks for, skip reasons masked and cut as the mod keeps them,
skill files as paths within the skill, and other files read only as
digests. No prompt text, hold text, file content or project path is written.

`Recorder` is the one way in: `judge` makes one per event and says, in
order, what the event read (`turns`: the route and skip lines, loads with
their cause, reference reads and code changes no earlier event logged) and
what it showed (outcomes, holds, a prompt, a turn end). `flush` writes it
all. How far each turn was read lives in a small cursor file per session
and agent under the core's state folder. Writing is best effort: `flush`
never raises, and a log that cannot be written leaves the decision as it
was, with a warning.

`read_entries` reads a log back, refusing one with an entry of a version it
does not know.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Callable
from pathlib import Path

from . import actions, events, markers, wording
from .events import Call, CallFinished, Prompt, ReplyText, SkillInvoked, Turn
from .gates import ROUTER_SKILL
from .state import _safe_name, _write_json, default_root

LOG_VERSION = 1
LOG_ENV = "GOATED_USAGE_LOG"
LOG_NAME = "usage-log.jsonl"
SALT_NAME = "usage-log-salt"
CURSOR_DIR = "usage-log"
KEY_DIGITS = 10

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

# A skip reason as the mod keeps it (`storedReason` in `hooks/holds.ts`).
REASON_LIMIT = 160
_PATH_WORD = re.compile(r"(?<!\S)(?:[A-Za-z]:[\\/]|[\\/]|~[\\/]|\S*\\)\S*")

# A path into a skill folder, as the mod finds one (`skillPaths` in `hooks/classify.ts`).
_SKILL_PATH = re.compile(r"(?<![\w.-])skills[\\/]([^\s\"'`|;&<>()]+)", re.ASCII)
_SUPPORT_DIRS = frozenset({"references", "reference", "scripts", "templates", "assets",
                           "examples", "docs"})

# How long to wait for another event's hold on the cursor, and when such a hold is stale.
_LOCK_WAIT_SECONDS = 1.0
_LOCK_STALE_SECONDS = 10.0
# How many recent reply texts a cursor remembers, to count a turn end's last text once.
_TEXTS_KEPT = 8


class LogUnreadable(ValueError):
    """The log cannot be read, or holds an entry of a version this reader does not know."""


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
    never a project's. Windows uses `%LOCALAPPDATA%\\goated`; elsewhere
    `$XDG_STATE_HOME/goated`, else `~/.local/state/goated`."""

    local = os.environ.get("LOCALAPPDATA") if os.name == "nt" else None
    return (Path(local) if local else default_root()) / "goated" / LOG_NAME


def path_from_environment(named: str | None = None) -> Path:
    """The log's path: `named`, else `GOATED_USAGE_LOG`, else `default_path()`."""

    named = named or os.environ.get(LOG_ENV)
    return Path(named) if named else default_path()


def read_entries(path: Path) -> list[dict]:
    """Every entry of the log at `path`, oldest first; [] when there is no
    log. Raises `LogUnreadable` for a line that is not an entry, or for an
    entry of an unknown version, which is refused rather than guessed at. A
    last line cut short, as by a writer that stopped mid-line, is passed over."""

    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    except (OSError, UnicodeDecodeError) as exc:
        raise LogUnreadable(f"could not read the usage log at {path} "
                            f"({getattr(exc, 'strerror', None) or exc})") from exc
    entries = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            if number == len(lines):
                continue
            raise LogUnreadable(f"line {number} of the usage log at {path} is not JSON") from None
        if not isinstance(entry, dict):
            raise LogUnreadable(f"line {number} of the usage log at {path} is not an entry")
        if entry.get("log") != LOG_VERSION:
            raise LogUnreadable(
                f"line {number} of the usage log at {path} is of log version "
                f"{entry.get('log')!r}, which this reader does not know (it knows version "
                f"{LOG_VERSION})")
        entries.append(entry)
    return entries


class Recorder:
    """The entries one judged event adds to the log, for `session_id` and,
    in a subagent, `agent_id`. `project_folder` is the folder whose key the
    entries carry, or None for none; `skills()` gives the skill names a
    prompt may name, called only when needed. Say what the event read and
    showed, in that order, then `flush`."""

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

        self._steps.append(lambda w: w.add("turn_end"))

    def compaction(self) -> None:
        """The context was compacted: what loaded before no longer counts."""

        self._steps.append(lambda w: w.compaction())

    def flush(self) -> str | None:
        """Write what was said: take the cursor's lock, read the cursor, work
        out the entries, append them, save the cursor, and let the lock go.
        Returns a warning when the log could not be written, else None; never
        raises, so the log never blocks a call."""

        if not self._steps:
            return None
        lock = None
        try:
            lock = _lock(self.cursor_path)
            writing = _Writing(self, _load_cursor(self.cursor_path))
            for step in self._steps:
                step(writing)
            if writing.entries:
                _append(self.log.path, writing.entries)
            _write_json(self.cursor_path, writing.cursor)
        except Exception as exc:  # noqa: BLE001 - the log is best effort and never blocks a call
            return f"could not write the usage log ({getattr(exc, 'strerror', None) or exc})"
        finally:
            self._steps = []
            if lock is not None:
                try:
                    lock.unlink()
                except OSError:
                    pass
        return None


class _Writing:
    """One flush's work: the cursor as read, and the entries it adds."""

    def __init__(self, recorder: Recorder, cursor: dict) -> None:
        self.recorder = recorder
        self.cursor = cursor
        self.entries: list[dict] = []
        self._key: str | None | bool = False
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
            folder = self.recorder.project_folder
            try:
                self._key = project_key(folder, _salt(self.recorder.log.path)) if folder else None
            except OSError:
                self._key = None
        return self._key

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
        if self.recorder.agent_id is None:
            # Only the main agent's reads answer holds by files read.
            if read_tool and call.ok:
                self.add("file_read", file=_digest(_comparable(target)))
            reached = skills_in_path(target)
            if reached:
                self.add("skill_read", skills=reached)
        for skill, file in skill_files(target):
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
    named, those its holds asked for, whether the router loaded in it, and
    the skills a prompt not yet read as a turn named."""

    return {"turn": None, "entries": 0, "waiting": [], "lined": [], "texts_seen": [],
            "final": None, "named": [], "asked": [], "router": False, "next_named": None}


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

    masked = _PATH_WORD.sub("<path>", reason)
    return masked if len(masked) <= REASON_LIMIT else masked[:REASON_LIMIT - 1] + "…"


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
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    salt = os.urandom(16).hex()
    try:
        with open(path, "x", encoding="utf-8") as handle:
            handle.write(salt)
    except FileExistsError:
        return path.read_text(encoding="utf-8").strip()
    return salt


# Files ----------------------------------------------------------------------


def _append(path: Path, entries: list[dict]) -> None:
    """Append `entries` as lines in one write, so concurrent writers' lines never mix."""

    path = Path(path)
    # The folder is the user's alone where the system has modes: skip reasons
    # are kept as written, but for paths.
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    text = "".join(json.dumps(entry, ensure_ascii=False) + "\n" for entry in entries)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(text)


def _lock(cursor_path: Path) -> Path | None:
    """Take the cursor's lock, waiting briefly for another event of the same
    session and agent; None when it cannot, and the cursor is then used
    unlocked, at worst logging a fact twice."""

    lock = cursor_path.with_suffix(".lock")
    lock.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    deadline = time.monotonic() + _LOCK_WAIT_SECONDS
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
            time.sleep(0.02)
