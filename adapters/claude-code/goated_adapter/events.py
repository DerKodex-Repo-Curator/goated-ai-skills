"""The event model of ADR 0004, as the rules read it.

The rules judge a call by its kind, never by a harness's tool name, and read
a turn as the model's ordered entries: an opener (a prompt, or a
compaction), then prompts that continue the turn, reply texts, calls with
their results, skills a person invoked, and background agents that finished.
An adapter's translation layer builds these from its harness's records; the
rules know nothing else. `stack/schemas/enforcement-event-model.schema.json`
is the model's JSON shape and its authority.

`Turn` also sums up what the rules read of a turn's entries: its loads, its
route and skip lines, and its finished calls in the order they finished.
"""

from __future__ import annotations

import re
from typing import NamedTuple

from .markers import ReplyMarkers, parse_reply

# Call kinds.
FILE_WRITE = "file_write"
SHELL_COMMAND = "shell_command"
SKILL_LOAD = "skill_load"
FILE_READ = "file_read"
SPAWN = "spawn"
COMMIT = "commit"
PULL_REQUEST = "pull_request"
OTHER = "other"

# The shells a shell command runs in.
POSIX = "posix"
POWERSHELL = "powershell"

# Who wrote a prompt. Only a person's prompt may carry overrides.
PERSON = "person"
SESSION = "session"
HOST = "host"
UNKNOWN = "unknown"

# A pull request's repository, `owner/name`; the owner may be a path of
# groups (`group/subgroup/name`). The schema's pattern is the same.
REPOSITORY_RE = re.compile(r"^[^/]+(?:/[^/]+)+$")


class Edit(NamedTuple):
    """One change a file write makes: the text it `removed` and the text it
    `added`. `removed` is None when the call does not say what it replaces,
    and `added` is None when it adds nothing it can show, such as a delete."""

    removed: str | None
    added: str | None


class Result(NamedTuple):
    """How a call finished. `ok` is False when it failed or was refused; `held`
    is True when a GOATED hold refused it, so it never ran; `ran` is False
    when it never ran for any other reason: refused by the harness or another
    hook, or interrupted. Either one means `ok` is False. For a
    spawn, `agent_id` is the agent it started and `background` says it
    started in the background, so its work is done only once an
    `AgentFinished` entry names it."""

    ok: bool
    held: bool = False
    output: str = ""
    agent_id: str | None = None
    background: bool = False
    ran: bool = True


class Call:
    """A call by its kind, with the fields of that kind, and its `result` once
    it has finished (None while it runs, or while it is being judged).

    Every kind has `id` ("" when the harness gives none), `line_text`, the
    one text a route or skip line may be read from, and `action`, an opaque
    key the harness may give so that calls the model shows alike, such as
    spawns by two different tools, count as different actions ("" when it
    gives none). The other fields belong to one kind each:

    - file_write: `path`, `whole_file` (the call writes the whole file, its
      one edit's added text being the content and its replaced text None),
      `creates` (an edit, not a whole-file write, that makes the file when
      it is missing, as a harness may let it), `edits` (empty when the call
      changes nothing);
    - shell_command: `command`, `shell` (`POSIX` or `POWERSHELL`), `background`;
    - skill_load: `skill`, the name as the harness gave it;
    - file_read: `path`, `whole` (False when it asked for part of the file);
    - spawn: `brief`, `starts_now` (False when it only proposes the work),
      `read_only` (the agent has no write, edit, or shell tool), `separate`
      (the agent runs apart from the acting session, as another session
      does, so its report never comes back as this call's result);
    - commit: `message`, None when unknown;
    - pull_request: `base`, `head`, `repository` (`owner/name`, the owner
      perhaps a path of groups, as `REPOSITORY_RE` reads it), each None when
      the call does not name it.
    """

    __slots__ = ("kind", "id", "line_text", "action", "path", "whole_file", "creates", "edits",
                 "command", "shell", "background", "skill", "whole", "brief", "starts_now",
                 "read_only", "separate", "message", "base", "head", "repository", "result")

    def __init__(self, kind: str, *, id: str = "", line_text: str = "", action: str = "",
                 path: str = "", whole_file: bool = False, creates: bool = False,
                 edits: tuple[Edit, ...] = (), command: str = "", shell: str = POSIX,
                 background: bool = False, skill: str = "", whole: bool = True, brief: str = "",
                 starts_now: bool = True, read_only: bool = False, separate: bool = False,
                 message: str | None = None, base: str | None = None, head: str | None = None,
                 repository: str | None = None, result: Result | None = None) -> None:
        self.kind = kind
        self.id = id
        self.line_text = line_text
        self.action = action
        self.path = path
        self.whole_file = whole_file
        self.creates = creates
        self.edits = tuple(edits)
        self.command = command
        self.shell = shell
        self.background = background
        self.skill = skill
        self.whole = whole
        self.brief = brief
        self.starts_now = starts_now
        self.read_only = read_only
        self.separate = separate
        self.message = message
        self.base = base
        self.head = head
        self.repository = repository
        self.result = result

    def finished(self, result: Result) -> "Call":
        """This call with `result`."""

        call = Call.__new__(Call)
        for name in Call.__slots__:
            setattr(call, name, getattr(self, name))
        call.result = result
        return call

    def same_as(self, other: "Call") -> bool:
        """Whether `other` is this call, its id and result aside."""

        return all(getattr(self, name) == getattr(other, name)
                   for name in Call.__slots__ if name not in ("id", "result"))

    @property
    def ok(self) -> bool:
        return self.result is not None and self.result.ok

    @property
    def held(self) -> bool:
        return self.result is not None and self.result.held

    @property
    def ran(self) -> bool:
        """The call has finished and did run, whatever its outcome."""

        return self.result is not None and self.result.ran and not self.result.held

    @property
    def output(self) -> str:
        return self.result.output if self.result is not None else ""

    @property
    def agent_id(self) -> str | None:
        return self.result.agent_id if self.result is not None else None

    @property
    def launched_async(self) -> bool:
        """A spawn that started its agent in the background."""

        return self.result is not None and self.result.background

    def whole_read_path(self) -> str | None:
        """The path a finished file read read whole, else None.

        A read of part of a file is partial (Ticket 092): a required
        reference, template, or the red flags count only when read whole.
        """

        if self.kind != FILE_READ or not self.ok or not self.whole:
            return None
        return self.path or None


class Prompt(NamedTuple):
    """A prompt, as a turn's opener or as an entry that continues the turn.
    `text` is its author's own text; `pasted` the text a person pasted, never
    read for overrides; `starts_session` marks the brief that opened a
    session another session started, whose route line counts as the first
    turn's."""

    author: str
    text: str
    pasted: tuple[str, ...] = ()
    starts_session: bool = False


class Compaction(NamedTuple):
    """A compaction, which opens a turn of its own."""


class ReplyText(NamedTuple):
    text: str


class SkillInvoked(NamedTuple):
    """A person loaded a skill by name, such as a typed command."""

    skill: str


class AgentFinished(NamedTuple):
    """A background agent this session spawned has finished."""

    agent_id: str


class CallFinished(NamedTuple):
    """Where the call with id `call_id`, made earlier in the turn, finished.

    The call's entry stays where it was made and carries the result; this
    entry gives only the place, so a call's lines count where it was made
    while finished calls come in the order they finished. A finished call
    with no such entry finished where it was made.
    """

    call_id: str


class Turn:
    """One turn: its `key`, its `opener` (a `Prompt`, a `Compaction`, or None
    when no opener was read), and its `entries` in order, with what the rules
    read of them.

    `typed`: a person wrote the opener, so it may carry overrides. `loads`
    are the names of skills loaded, in order: each skill load that finished
    ok, and each skill a person invoked. `route` is the winning route line,
    `routes` every valid one in order, `malformed` the route-like lines that
    failed the grammar, and `skips` the valid skip lines; they come from
    reply texts and from each call's `line_text` where the call was made, a
    call's counting once per call id, at its first entry. `texts` are the
    reply texts and `call_texts` the calls' line texts, in order. `calls`
    are the finished calls in the order they finished (see `CallFinished`),
    `unfinished` the calls with no result yet. `brief_route` is the
    route line of the brief that started the session, which is also the
    turn's first route line. `finished_agents` are the background agents
    whose completion arrived in the turn. `opens_session` says no earlier
    turn exists.

    `pending` is the call being judged, not yet an entry: its lines count in
    the turn, once even if an entry already shows it.
    """

    __slots__ = (
        "key", "opener", "entries", "is_compaction", "typed", "loads", "route", "routes",
        "malformed", "skips", "calls", "unfinished", "texts", "call_texts", "call_ids",
        "brief_route", "finished_agents", "opens_session",
    )

    def __init__(self, key: str, opener: Prompt | Compaction | None, entries: list,
                 *, opens_session: bool = False, pending: Call | None = None) -> None:
        self.key = key
        self.opener = opener
        self.entries = entries
        self.opens_session = opens_session
        self.is_compaction = isinstance(opener, Compaction)
        self.typed = isinstance(opener, Prompt) and opener.author == PERSON
        self.loads: list[str] = []
        self.route: dict | None = None
        self.routes: list[dict] = []
        self.malformed: list[str] = []
        self.skips: list[dict] = []
        self.calls: list[Call] = []
        self.unfinished: list[Call] = []
        self.texts: list[str] = []
        self.call_texts: list[str] = []
        self.call_ids: set[str] = set()
        self.finished_agents: set[str] = set()
        self.brief_route: dict | None = None
        if isinstance(opener, Prompt) and opener.starts_session:
            self.brief_route = parse_reply(opener.text).route
            if self.brief_route is not None:
                self.route = self.brief_route
                self.routes.append(self.brief_route)
        marked = {entry.call_id for entry in entries if isinstance(entry, CallFinished)}
        # The newest entry of each call id: an id recorded twice is one call,
        # whose lines count at its first entry.
        newest = {entry.id: index for index, entry in enumerate(entries)
                  if isinstance(entry, Call) and entry.id}
        awaiting: dict[str, Call] = {}  # Finished calls whose place is marked later.
        for index, entry in enumerate(entries):
            if isinstance(entry, Call):
                self._count_lines(entry)
                if entry.result is None:
                    if not entry.id or newest[entry.id] == index:
                        self.unfinished.append(entry)
                elif entry.id in marked:
                    awaiting[entry.id] = entry
                else:
                    self._finish(entry)
            elif isinstance(entry, CallFinished):
                if entry.call_id in awaiting:
                    self._finish(awaiting.pop(entry.call_id))
            elif isinstance(entry, ReplyText):
                self.texts.append(entry.text)
                self.add_markers(parse_reply(entry.text))
            elif isinstance(entry, SkillInvoked):
                self.loads.append(entry.skill)
            elif isinstance(entry, AgentFinished):
                self.finished_agents.add(entry.agent_id)
        if pending is not None:
            self._count_lines(pending)

    def _finish(self, call: Call) -> None:
        """Take `call` as the next call to finish."""

        self.calls.append(call)
        if call.kind == SKILL_LOAD and call.ok and call.skill:
            self.loads.append(call.skill)

    def add_markers(self, markers: ReplyMarkers) -> None:
        """Count the marker lines of one reply text or one call, in order."""

        if markers.route is not None:
            self.route = markers.route
            self.routes.append(markers.route)
        self.malformed.extend(markers.malformed)
        self.skips.extend(markers.skips)

    def _count_lines(self, call: Call) -> None:
        """Count the lines a call carries, once per call id. A call with no id
        is taken to be the newest unfinished call when it is the same call,
        so it is not counted twice."""

        if call.id:
            if call.id in self.call_ids:
                return
            self.call_ids.add(call.id)
        elif self.unfinished and self.unfinished[-1].same_as(call):
            return
        if call.line_text:
            self.call_texts.append(call.line_text)
            self.add_markers(parse_reply(call.line_text))
