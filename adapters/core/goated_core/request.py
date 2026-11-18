"""The core's request call: one event-model request in, one decision out.

`decide` takes a request as `stack/schemas/enforcement-event-model.schema.json`
shapes it, already parsed from JSON, and returns the decision as a plain
value ready for `json.dumps`. `goated_judge.py`, beside this package, is
the same call as a command. Both answer the same request the same way.

The request carries every turn since the last compaction. The core keeps
the session facts that outlast them under `Settings.state_dir`, keyed by
the request's session id, and reads only the turns since the last one it
saw, as `judge` asks. A prompt's overrides are recorded when the request
for its `prompt_submitted` event arrives, keyed by its turn, so a harness
that sends no such event gets no override. Hold texts come in neutral
words (`wording.neutral`).

Fail open, visibly: a request the core cannot read, or of an event model
version it does not know, and any failure while judging, is answered with
`allow` and a `fail_open` notice that says why.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import actions, events, gates, judge, usage_log, wording
from .events import (
    AgentFinished, Call, CallFinished, Compaction, Edit, Prompt, ReplyText, Result,
    SkillInvoked, Turn,
)
from .judge import Settings
from .state import default_root

EVENT_MODEL = 2
STATE_DIR_ENV = "GOATED_CORE_STATE_DIR"
NAMESPACES_ENV = "GOATED_CORE_SKILL_NAMESPACES"
REGISTRY_ENV = "GOATED_CORE_REGISTRY"
# The name the usage log records for the adapter calling the core.
ADAPTER_ENV = "GOATED_CORE_ADAPTER"
DEFAULT_ADAPTER = "core"
STATE_DIR_NAME = "goated-core"
# The registry when the core sits in its distribution: `<goated-root>/adapters/core/`.
DEFAULT_REGISTRY = Path(__file__).resolve().parents[3] / "stack" / "goated-stack.yaml"
NAME = "GOATED enforcement core"
ROUTER_NOTICE = (
    f"could not find the `{gates.ROUTER_SKILL}` skill among the installed skills, so "
    "writes, spawns, and commands will stay held. Install it, or type `skip routing` in "
    "a prompt to proceed without it."
)

__all__ = ["EVENT_MODEL", "Settings", "decide", "settings_from_environment"]


class Unreadable(ValueError):
    """The request does not have the event model's shape."""


def settings_from_environment(state_dir: str | None = None,
                              registry: str | None = None,
                              log_path: str | None = None) -> Settings:
    """The core's settings from its environment variables, each argument
    given winning: the state folder (`GOATED_CORE_STATE_DIR`, by default a
    per-user folder), GOATED skill namespaces (`GOATED_CORE_SKILL_NAMESPACES`,
    comma-separated), the registry (`GOATED_CORE_REGISTRY`, by default the
    distribution's), and the usage log (`GOATED_USAGE_LOG`, by default
    `usage_log.default_path()`), written as the adapter `GOATED_CORE_ADAPTER`
    names itself, `core` when it names none."""

    state_dir = state_dir or os.environ.get(STATE_DIR_ENV)
    named = registry or os.environ.get(REGISTRY_ENV)
    namespaces = os.environ.get(NAMESPACES_ENV, "")
    return Settings(
        Path(state_dir) if state_dir else default_root() / STATE_DIR_NAME,
        tuple(n.strip() for n in namespaces.split(",") if n.strip()),
        Path(named) if named else DEFAULT_REGISTRY,
        registry_named=bool(named),
        usage_log=usage_log.UsageLog(usage_log.path_from_environment(log_path),
                                     os.environ.get(ADAPTER_ENV) or DEFAULT_ADAPTER),
    )


def decide(request: object, settings: Settings | None = None) -> dict:
    """The decision for `request`, as the event model's `decision` shapes it.
    Never raises: whatever stops the core from judging allows the event,
    with a `fail_open` notice."""

    settings = settings or settings_from_environment()
    if isinstance(request, dict) and "event_model" not in request:
        return fail_open("it could not read the request (it has no event_model, the event "
                         f"model version; this core knows version {EVENT_MODEL})")
    if isinstance(request, dict) and request["event_model"] != EVENT_MODEL:
        version = request["event_model"]
        return fail_open(f"the request is of event model version {version!r}, which it does "
                         f"not know (it knows version {EVENT_MODEL})")
    try:
        reading = _Reading(request)
    except Exception as exc:  # noqa: BLE001 - a request of any shape, even nested too deep, fails open
        return fail_open(f"it could not read the request ({_reason(exc)})")
    try:
        decision = reading.judge(settings)
        holds = [{"gate": hold.gate, "kind": hold.kind, "text": wording.neutral(hold.text)}
                 for hold in decision.holds]
        notices = [{"kind": notice.kind, "text": _sentence(notice.text)}
                   for notice in decision.notices]
    except Exception as exc:  # noqa: BLE001 - any core failure must fail open, visibly
        return fail_open(f"it could not judge the request ({type(exc).__name__}: {exc})")
    return {"event_model": EVENT_MODEL, "decision": "hold" if holds else "allow",
            "holds": holds, "notices": notices}


def _sentence(text: str) -> str:
    """A notice's text as one sentence that names the core."""

    return f"{NAME}: {wording.neutral(text).rstrip('.')}."


def fail_open(why: str) -> dict:
    """The decision that allows an event the core could not judge, saying why."""

    return {"event_model": EVENT_MODEL, "decision": "allow", "holds": [], "notices": [
        {"kind": judge.FAIL_OPEN, "text": f"{NAME}: {why}, so this event was allowed "
                                          "without checks."}]}


def _reason(exc: Exception) -> str:
    return str(exc) if isinstance(exc, Unreadable) else f"{type(exc).__name__}: {exc}"


class _Reading:
    """A request read into the event model's Python objects."""

    def __init__(self, request: object) -> None:
        request = _object(request, "the request")
        session = _object(request["session"], "session")
        self.session_id = _text(session["id"], "session.id")
        agent = _object(session["agent"], "session.agent")
        self.agent_id = (_text(agent["id"], "session.agent.id")
                         if agent.get("role") == "subagent" else None)
        project = _object(request["project"], "project")
        self.folders = [_text(f, "project.folders") for f in _list(project["folders"], "folders")]
        self.working_folder = _text(project["working_folder"], "project.working_folder")
        # The folder a leading `~` names, the agent's home rather than this process's.
        self.home = _text(project["home"], "project.home")
        self.agent_folders = [_text(f, "project.agent_folders")
                              for f in _list(project.get("agent_folders", []), "agent_folders")]
        skills = project.get("installed_skills")
        self.installed = (None if skills is None else frozenset(
            _text(s, "project.installed_skills") for s in _list(skills, "installed_skills")))
        self.event = _object(request["event"], "event")
        self.call = (_call(_object(self.event["call"], "event.call"))
                     if self.event.get("type") in ("pending_call", "finished_call") else None)
        if self.event.get("type") == "finished_call":
            self.call = self.call.finished(_result(_object(self.event["result"], "event.result")))
        # The entries of each spawned agent's own turn, by agent id.
        self.agent_entries: dict[str, list] = {}
        raw_turns = _list(request["turns"], "turns")
        # The call being judged counts in the current turn only.
        self.turns = [self._turn(_object(t, "a turn"), n == 0,
                                 self.call if n == len(raw_turns) - 1 else None)
                      for n, t in enumerate(raw_turns)]
        if not self.turns and self.event.get("type") != "session_start":
            raise Unreadable("it has no turns")

    def judge(self, settings: Settings) -> judge.Decision:
        situation = judge.Situation(
            self.session_id, agent_id=self.agent_id,
            project=actions.find_project(self.working_folder, *self.folders,
                                         homes=(self.home,)),
            agent_folders=self.agent_folders,
            installed_skills=lambda: self.installed,
            subagents=self._subagents,
            project_folder=self.folders[0] if self.folders else self.working_folder,
        )
        kind = self.event.get("type")
        if kind == "pending_call":
            return judge.judge_call(settings, situation, self.call, self._read)
        if kind == "finished_call":
            return judge.note_finished_call(settings, situation, self.call, self._read)
        if kind == "turn_end":
            return judge.judge_turn_end(settings, situation, self._read)
        if kind == "prompt_submitted":
            return self._prompt(settings, situation)
        if kind == "session_start":
            source = self.event.get("source")
            if source not in (judge.NEW, judge.RESUMED, judge.AFTER_COMPACTION, judge.CLEARED):
                raise Unreadable(f"a session start from {source!r}")
            return judge.start_session(settings, situation, source, self._first_notices)
        raise Unreadable(f"an event of type {kind!r}")

    def _prompt(self, settings: Settings, situation: judge.Situation) -> judge.Decision:
        """Record the current turn's prompt, unless the prompt submitted
        continues the turn: the turn's last entry is then that prompt."""

        current = self.turns[-1]
        if current.entries and isinstance(current.entries[-1], Prompt):
            return judge.Decision()
        opener = current.opener
        typed = opener.text if isinstance(opener, Prompt) and opener.author == events.PERSON \
            else None
        return judge.record_prompt(settings, situation, typed, current.key,
                                   lambda since: self._read(since)[0])

    def _read(self, since_key: str | None):
        """The turns back to and including `since_key`'s, or all the request
        carries when it carries no such turn; a subagent's current turn only.
        The prompt key is the current turn's key, as `_prompt` records it."""

        if self.agent_id is not None:
            return self.turns[-1:], None
        keys = [turn.key for turn in self.turns]
        start = keys.index(since_key) if since_key in keys else 0
        return self.turns[start:], self.turns[-1].key

    def _subagents(self, turn: Turn) -> tuple[dict, list[str]]:
        """Each agent `turn`'s spawns started, with its own turn; an agent
        whose entries the request does not carry did nothing it can count."""

        found = {}
        for call in turn.calls:
            if call.agent_id and call.agent_id not in found:
                found[call.agent_id] = [Turn(call.agent_id, None,
                                             self.agent_entries.get(call.agent_id, []))]
        return found, []

    def _first_notices(self) -> list[str]:
        if self.installed is not None and gates.ROUTER_SKILL not in self.installed:
            return [ROUTER_NOTICE]
        return []

    def _turn(self, data: dict, first: bool, pending: Call | None) -> Turn:
        opener = _opener(_object(data["opener"], "a turn's opener"))
        entries = [entry for entry in (self._entry(_object(e, "an entry"))
                                       for e in _list(data["entries"], "entries"))
                   if entry is not None]
        return Turn(_text(data["key"], "a turn's key"), opener, entries,
                    opens_session=first and not isinstance(opener, Compaction), pending=pending)

    def _entry(self, data: dict):
        kind = data.get("type")
        if kind == "prompt":
            return _prompt(data)
        if kind == "reply_text":
            return ReplyText(_text(data["text"], "reply_text.text", empty=True))
        if kind == "call":
            call = _call(_object(data["call"], "a call entry's call"))
            if "result" in data:
                result = _object(data["result"], "a call's result")
                call = call.finished(_result(result))
                agent = result.get("agent")
                if isinstance(agent, dict) and "entries" in agent:
                    self.agent_entries[call.agent_id] = [
                        entry for entry in (self._entry(_object(e, "an entry"))
                                            for e in _list(agent["entries"], "agent.entries"))
                        if entry is not None]
            return call
        if kind == "call_finished":
            return CallFinished(_text(data["id"], "call_finished.id"))
        if kind == "skill_invoked":
            return SkillInvoked(_text(data["skill"], "skill_invoked.skill"))
        if kind == "agent_finished":
            return AgentFinished(_text(data["agent_id"], "agent_finished.agent_id"))
        if kind == "turn_ended":
            # The core keeps that a turn's end was allowed (`judge.judge_turn_end`).
            return None
        raise Unreadable(f"an entry of type {kind!r}")


def _opener(data: dict):
    if data.get("type") == "compaction":
        return Compaction()
    return _prompt(data)


def _prompt(data: dict) -> Prompt:
    author = data.get("author")
    if author not in (events.PERSON, events.SESSION, events.HOST, events.UNKNOWN):
        raise Unreadable(f"a prompt by {author!r}")
    return Prompt(author, _text(data["text"], "prompt.text", empty=True),
                  tuple(_text(p, "prompt.pasted", empty=True)
                        for p in _list(data.get("pasted", []), "pasted")),
                  data.get("starts_session") is True)


_KINDS = frozenset({events.FILE_WRITE, events.SHELL_COMMAND, events.SKILL_LOAD, events.FILE_READ,
                    events.SPAWN, events.COMMIT, events.PULL_REQUEST, events.OTHER})


def _call(data: dict) -> Call:
    """A call of the model's `call` shape as `events.Call`."""

    kind = data.get("kind")
    if kind not in _KINDS:
        raise Unreadable(f"a call of kind {kind!r}")
    common = {"id": _text(data.get("id", ""), "call.id", empty=True),
              "line_text": _text(data.get("line_text", ""), "call.line_text", empty=True),
              "action": _text(data.get("action", ""), "call.action", empty=True)}
    if kind == events.FILE_WRITE:
        edits = [_object(e, "an edit") for e in _list(data["edits"], "edits")]
        return Call(kind, path=_text(data["path"], "call.path"),
                    whole_file=data.get("whole_file") is True, creates=data.get("creates") is True,
                    edits=tuple(Edit(_maybe(e["removed"]), _maybe(e["added"])) for e in edits),
                    **common)
    if kind == events.SHELL_COMMAND:
        shell = data["shell"]
        if shell not in (events.POSIX, events.POWERSHELL):
            raise Unreadable(f"a command in the shell {shell!r}")
        return Call(kind, command=_text(data["command"], "call.command", empty=True),
                    shell=shell, background=data.get("background") is True, **common)
    if kind == events.SKILL_LOAD:
        return Call(kind, skill=_text(data["skill"], "call.skill"), **common)
    if kind == events.FILE_READ:
        return Call(kind, path=_text(data["path"], "call.path"), whole=data["whole"] is True,
                    **common)
    if kind == events.SPAWN:
        return Call(kind, brief=_text(data["brief"], "call.brief", empty=True),
                    starts_now=data["starts_now"] is True, read_only=data.get("read_only") is True,
                    separate=data.get("separate") is True, **common)
    if kind == events.COMMIT:
        return Call(kind, message=_maybe(data.get("message")), **common)
    if kind == events.PULL_REQUEST:
        repository = _maybe(data.get("repository"))
        return Call(kind, base=_maybe(data.get("base")), head=_maybe(data.get("head")),
                    repository=repository if repository and events.REPOSITORY_RE.match(repository)
                    else None, **common)
    return Call(kind, **common)


def _result(data: dict) -> Result:
    agent = data.get("agent")
    agent = _object(agent, "result.agent") if agent is not None else {}
    held = data.get("held") is True
    return Result(ok=data["ok"] is True, held=held,
                  output=_text(data.get("output", ""), "result.output", empty=True),
                  agent_id=_text(agent["id"], "result.agent.id") if agent else None,
                  background=agent.get("background") is True,
                  ran=data.get("ran") is not False)


def _object(value, what: str) -> dict:
    if not isinstance(value, dict):
        raise Unreadable(f"{what} is not an object")
    return value


def _list(value, what: str) -> list:
    if not isinstance(value, list):
        raise Unreadable(f"{what} is not a list")
    return value


def _text(value, what: str, empty: bool = False) -> str:
    if not isinstance(value, str) or (not value and not empty):
        raise Unreadable(f"{what} is not a {'' if empty else 'non-empty '}string")
    return value


def _maybe(value) -> str | None:
    """A string field the model allows to be null; anything else is unknown (None)."""

    return value if isinstance(value, str) else None
