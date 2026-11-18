"""The adapter's single entry point: one hook input in, one hook output out.

`run_hook` dispatches on `hook_event_name` and owns the adapter's failure rule
(ADR 0003, "fail open, visibly"): when it cannot read what it needs, it lets
the action through and returns a `systemMessage` warning the user sees. It
never blocks because of its own failure. A hook that runs after the action
(`PostToolUse`) has no action to let through, so its failure adds nothing.

Each handler turns its hook input into the event model (`translation`,
`transcript`), asks the shared core (`goated_core.judge`), and puts its
decision into Claude Code's hook output, hold text in Claude Code's words
(`translation.render`).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from goated_core import actions, gates, judge
from goated_core.events import Result
from goated_core.state import StateStore, StateUnsafe, default_root
from goated_core.usage_log import UsageLog, path_from_environment

from . import onboarding, translation
from .policy import installed_skill_names, router_skill_installed, shared_policy_loaded
from .transcript import (
    CONTINUATION,
    NOT_PROMPT,
    TYPED,
    TranscriptUnreadable,
    is_host_retry,
    is_own_report,
    prompt_text_kind,
    read_recent_turns,
    typed_prompt,
)

STATE_DIR_ENV = "GOATED_ADAPTER_STATE_DIR"
NAMESPACES_ENV = "GOATED_ADAPTER_SKILL_NAMESPACES"
REGISTRY_ENV = "GOATED_ADAPTER_REGISTRY"
# The installed registry when the adapter sits in its distribution, as the
# README's install steps place it: `<goated-root>/adapters/claude-code/`.
DEFAULT_REGISTRY = Path(__file__).resolve().parents[3] / "stack" / "goated-stack.yaml"
# Claude Code sets this to the project's root folder in a hook's environment.
PROJECT_DIR_ENV = "CLAUDE_PROJECT_DIR"
STATE_DIR_NAME = "goated-claude-code-adapter"
# The adapter's name in the core's usage log.
ADAPTER_NAME = "claude-code"
AGENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
# A turn key no turn has, so the reader returns every turn back to the start
# (or to its turn limit).
ALL_TURNS = "<all turns>"
NAME = "GOATED Claude Code adapter"
POLICY_NOTICE = (
    "the GOATED shared policy is not loaded in this session, so the "
    "`using-goated-ai-skills` router runs from its standalone fallback. To load "
    "it, follow the Claude Code steps in the GOATED install guide."
)
ROUTER_NOTICE = (
    f"could not find the `{gates.ROUTER_SKILL}` skill among your user, project, "
    "or plugin skills, so writes, spawns, and commands will stay held. Install it, "
    "or type `skip routing` in a prompt to proceed without it."
)
# Claude Code's session start sources, in the event model's words.
SESSION_SOURCES = {"startup": judge.NEW, "resume": judge.RESUMED,
                   "compact": judge.AFTER_COMPACTION, "clear": judge.CLEARED}


class Config:
    """Where the adapter keeps state and finds instruction files.

    `lag_wait_seconds` bounds how long a PreToolUse call waits for the
    transcript to show the call being judged. `skill_namespaces` lists plugin
    namespaces whose `ns:skill` loads count as GOATED skills, for a GOATED
    distribution installed as a plugin. `project_dir` is the project's root
    folder, when Claude Code names one. `registry_path` is the installed
    registry the `reference-reads` gate reads; None reads none.
    `registry_named`: the user named that path (`GOATED_ADAPTER_REGISTRY`),
    so a missing file there is worth a warning; a missing default is not.
    `usage_log` is the core's usage log the adapter writes to, as
    `claude-code`; None keeps none.
    `from_environment` gives the installed defaults; tests pass their own.
    """

    __slots__ = ("state_dir", "home", "lag_wait_seconds", "skill_namespaces", "project_dir",
                 "registry_path", "registry_named", "usage_log")

    def __init__(
        self,
        state_dir: Path,
        home: Path | None = None,
        lag_wait_seconds: float = 1.5,
        skill_namespaces: tuple[str, ...] = (),
        project_dir: str | None = None,
        registry_path: Path | None = None,
        registry_named: bool = False,
        usage_log: UsageLog | None = None,
    ) -> None:
        self.state_dir = Path(state_dir)
        self.home = Path(home) if home is not None else Path.home()
        self.lag_wait_seconds = lag_wait_seconds
        self.skill_namespaces = tuple(skill_namespaces)
        self.project_dir = project_dir
        self.registry_path = Path(registry_path) if registry_path is not None else None
        self.registry_named = registry_named
        self.usage_log = usage_log

    @classmethod
    def from_environment(cls) -> "Config":
        """The installed defaults; the usage log is at `GOATED_USAGE_LOG`, else
        the core's per-user default (`usage_log.default_path`), and none when
        `GOATED_USAGE_LOG` is `off`."""

        override = os.environ.get(STATE_DIR_ENV)
        namespaces = os.environ.get(NAMESPACES_ENV, "")
        registry = os.environ.get(REGISTRY_ENV)
        log = path_from_environment()
        return cls(
            state_dir=Path(override) if override else default_root() / STATE_DIR_NAME,
            skill_namespaces=tuple(n.strip() for n in namespaces.split(",") if n.strip()),
            project_dir=os.environ.get(PROJECT_DIR_ENV) or None,
            registry_path=Path(registry) if registry else DEFAULT_REGISTRY,
            registry_named=bool(registry),
            usage_log=UsageLog(log, ADAPTER_NAME) if log else None,
        )

    def settings(self) -> judge.Settings:
        """The core's settings for this configuration. Sessions saved by the
        adapter before the core existed are upgraded as they load."""

        return judge.Settings(self.state_dir, self.skill_namespaces, self.registry_path,
                              self.registry_named, upgrade_state=translation.upgrade_state,
                              usage_log=self.usage_log)


class _FailOpen(Exception):
    """Raised inside a handler when the adapter must let the action through."""


def run_hook(raw_input: str, config: Config) -> str:
    """Handle one hook call and return the JSON text to print, or "" for no output."""

    try:
        payload = json.loads(raw_input)
        if not isinstance(payload, dict):
            raise ValueError("hook input is not a JSON object")
    except ValueError:
        return _fail_open("it could not read its hook input")

    event = payload.get("hook_event_name")
    handler = _HANDLERS.get(event)
    if handler is None:
        return ""
    try:
        return handler(payload, config)
    except (_FailOpen, StateUnsafe) as exc:
        return "" if event in _AFTER_THE_ACTION else _fail_open(str(exc))
    except Exception as exc:  # noqa: BLE001 - any adapter bug must fail open, visibly
        if event in _AFTER_THE_ACTION:
            return ""
        return _fail_open(f"it hit an internal error ({type(exc).__name__})")


# The event model from Claude Code's hook input --------------------------------


def _situation(payload: dict, config: Config, session_id: str,
               transcript_path: str | None = None, agent_id: str | None = None,
               with_project: bool = True) -> judge.Situation:
    """Where the hook's event happens: the project Claude Code names (looked
    up only `with_project`, for the events that judge files), its own
    folders as the agent's (never scratch), the skills it can find, and the
    turns of the subagents a turn spawned, read from their transcripts."""

    cwd = Path(str(payload.get("cwd") or "."))
    return judge.Situation(
        session_id,
        agent_id=agent_id,
        project=actions.find_project(str(payload.get("cwd") or "") or None, config.project_dir)
        if with_project else None,
        # Claude Code's own configuration folders: `~/.claude`, and the
        # one in the configured home.
        agent_folders=["~/.claude", os.path.join(str(config.home), ".claude")],
        installed_skills=lambda: installed_skill_names(cwd, config.home),
        subagents=lambda turn: _spawned_subagents(turn, transcript_path or ""),
        project_folder=config.project_dir or str(payload.get("cwd") or "") or None,
    )


def _reader(payload: dict, config: Config, transcript_path: str, call=None):
    """The core's turn reader for the main agent's transcript: it waits for
    the hook's prompt to show, and counts `call`, the call being judged,
    in the current turn. The prompt key is the transcript's id for the
    current turn's prompt, else the hook input's."""

    def read(since_key: str | None):
        try:
            reading = read_recent_turns(
                transcript_path,
                since_key=since_key,
                prompt_id=_prompt_id(payload),
                wait_seconds=config.lag_wait_seconds,
                current_call=call,
            )
        except TranscriptUnreadable as exc:
            raise _FailOpen(str(exc)) from exc
        return reading.turns, reading.prompt_id or payload.get("prompt_id")

    return read


def _subagent_transcript(transcript_path: str, agent_id: str) -> Path:
    """Claude Code passes a subagent's hooks the parent's `transcript_path`;
    the subagent's entries live beside it in `<session>/subagents/agent-<agent_id>.jsonl`."""

    main = Path(transcript_path)
    return main.parent / main.stem / "subagents" / f"agent-{agent_id}.jsonl"


def _spawned_subagents(turn, transcript_path: str) -> tuple[dict, list[str]]:
    """Read every turn of each subagent `turn` spawned; return them and the ids not read."""

    found: dict = {}
    unread: list[str] = []
    for call in turn.calls:
        agent_id = call.agent_id
        if not agent_id or agent_id in found or not AGENT_ID_RE.match(agent_id):
            continue
        try:
            found[agent_id] = read_recent_turns(
                _subagent_transcript(transcript_path, agent_id),
                since_key=ALL_TURNS,
                wait_seconds=0.0,
                sidechain=True,
            ).turns
        except TranscriptUnreadable:
            unread.append(agent_id)
    return found, unread


# Handlers ----------------------------------------------------------------------


def _pre_tool_use(payload: dict, config: Config) -> str:
    tool_name = str(payload.get("tool_name") or "")
    if not translation.is_judged(tool_name):
        return ""
    call = translation.call_of(tool_name, payload.get("tool_input"),
                               str(payload.get("tool_use_id") or ""))
    session_id, transcript_path = _session_fields(payload)
    if payload.get("agent_id"):
        agent_id = str(payload.get("agent_id"))
        if not AGENT_ID_RE.match(agent_id):
            raise _FailOpen("the hook input has an unexpected agent_id")
        path = _subagent_transcript(transcript_path, agent_id)

        def read(since_key):
            # A subagent's own transcript, where every prompt is its parent's.
            try:
                return read_recent_turns(path, since_key=None, wait_seconds=0.0,
                                         sidechain=True, current_call=call).turns, None
            except TranscriptUnreadable as exc:
                raise _FailOpen(f"in a subagent, {exc}") from exc

        decision = judge.judge_call(config.settings(),
                                    _situation(payload, config, session_id, agent_id=agent_id),
                                    call, read)
    else:
        decision = judge.judge_call(config.settings(),
                                    _situation(payload, config, session_id, transcript_path),
                                    call, _reader(payload, config, transcript_path, call))
    text = translation.render(decision.message(), tool_name, decision.shell)
    output = _deny(text)
    # A lasting skip let a read gate pass (spec R4): tell the agent which skip did.
    carried = decision.texts(judge.SKIP_CARRIED)
    if carried:
        specific = output.setdefault("hookSpecificOutput", {"hookEventName": "PreToolUse"})
        specific["additionalContext"] = _sentence(translation.render(t) for t in carried)
    return _with_warnings(output, decision.texts(judge.WARNING))


def _stop(payload: dict, config: Config) -> str:
    """Hold the end of a turn that changed code until its closeout items are met."""

    session_id, transcript_path = _session_fields(payload)
    decision = judge.judge_turn_end(
        config.settings(), _situation(payload, config, session_id, transcript_path),
        _reader(payload, config, transcript_path),
        str(payload.get("last_assistant_message") or ""))
    text = translation.render(decision.message())
    output = {"decision": "block", "reason": text} if text else {}
    return _with_warnings(output, decision.texts(judge.WARNING))


def _post_tool_use(payload: dict, config: Config) -> str:
    """After the main agent's first finished code change of a turn by a file
    edit tool, add the core's early closeout note as context for the agent
    (Ticket 096). It never holds anything.

    The call is taken from the hook's own payload, since the transcript may
    not show it yet; the transcript and state say only what the payload
    cannot, such as which skills count as loaded.
    """

    tool_name = str(payload.get("tool_name") or "")
    if (tool_name not in translation.FILE_WRITE_TOOLS or payload.get("agent_id")
            or not _finished(payload.get("tool_response"))):
        return ""
    call = translation.call_of(tool_name, payload.get("tool_input"),
                               str(payload.get("tool_use_id") or ""))
    session_id, transcript_path = _session_fields(payload)
    decision = judge.note_finished_call(
        config.settings(), _situation(payload, config, session_id, transcript_path),
        call.finished(Result(ok=True)), _reader(payload, config, transcript_path, call))
    notes = decision.texts(judge.CLOSEOUT_NOTE_KIND)
    if not notes:
        return ""
    text = translation.render(notes[0])
    return json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse", "additionalContext": _sentence([text])}})


def _finished(tool_response: object) -> bool:
    """Whether a PostToolUse `tool_response` shows the call did its work: an
    object that reports no error and no failure. Anything else, such as an
    error's text, may be a call that changed nothing."""

    return (isinstance(tool_response, dict) and not tool_response.get("error")
            and not tool_response.get("is_error") and tool_response.get("success") is not False)


def _session_start(payload: dict, config: Config) -> str:
    """Start the session's context in the core; note a missing policy or
    router once per session, and missing agent files once per project."""

    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise _FailOpen("the hook input has no session_id")
    cwd = Path(str(payload.get("cwd") or "."))

    def first_notices() -> list[str]:
        notices = []
        if not shared_policy_loaded(cwd, config.home):
            notices.append(POLICY_NOTICE)
        if not router_skill_installed(cwd, config.home, gates.ROUTER_SKILL):
            notices.append(ROUTER_NOTICE)
        return notices

    decision = judge.start_session(
        config.settings(), _situation(payload, config, session_id, with_project=False),
        SESSION_SOURCES.get(payload.get("source"), judge.RESUMED), first_notices)
    notices = decision.texts(judge.SESSION_NOTICE)
    record_warnings: list[str] = []
    try:
        onboarding_notice = _onboarding_notice(StateStore(config.state_dir), payload, config,
                                               record_warnings)
    except (OSError, StateUnsafe) as exc:
        # The notice is advice: losing it must not lose this start's reset.
        onboarding_notice = None
        record_warnings.append(f"could not check its onboarding notice ({exc})")
    if onboarding_notice:
        notices.append(onboarding_notice)
    output: dict = {}
    if notices:
        output["hookSpecificOutput"] = {
            "hookEventName": "SessionStart",
            "additionalContext": " ".join(notices),
        }
    return _with_warnings(output, [*notices, *decision.texts(judge.WARNING), *record_warnings])


def _onboarding_notice(
    store: StateStore, payload: dict, config: Config, warnings: list[str]
) -> str | None:
    """The onboarding notice when it is due for the session's project, else
    None; records what it names beside the session state, outside the project
    folder. A record that cannot be saved adds a warning to `warnings`: the
    notice may then show again at the next start."""

    root = onboarding.project_root(str(payload.get("cwd") or "") or None, config.project_dir)
    if root is None or not root.is_dir():
        return None
    key = onboarding.project_key(root)
    missing = onboarding.missing_files(root)
    last_shown = store.onboarding_shown(key)
    skills = [f.skill for f in missing]
    if last_shown is None or set(last_shown) != set(skills):
        try:
            store.record_onboarding_shown(key, skills)
        except OSError as exc:
            warnings.append("could not record its onboarding notice "
                            f"({exc.strerror or type(exc).__name__})")
    return onboarding.notice(missing) if onboarding.notice_due(missing, last_shown) else None


def _user_prompt_submit(payload: dict, config: Config) -> str:
    """Record the overrides the user typed; they apply to this prompt's turn only.

    The hook sees only the prompt text: its input names no source, and the
    prompt's transcript entry is not yet written. Text that continues the turn,
    such as a task notification or the report of a subagent this session
    spawned (`is_own_report`), leaves the typed prompt's overrides in place;
    text another subagent, another session, or the app wrote starts a turn
    with none. The gates check again against the transcript, which shows who
    wrote the prompt, so a message this text check misses still applies no
    override.

    The hook input carries no origin, so this check cannot match the
    transcript reader's tie, which also needs the entry's `origin.from` to
    name the agent. Typed text shaped like a report naming a spawned agent is
    taken here for a report: it records nothing and keeps the earlier
    prompt's overrides. The reader sees a typed origin and opens a machine
    turn, to which those overrides never apply, so none leaks.
    """

    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise _FailOpen("the hook input has no session_id")
    prompt = str(payload.get("prompt") or "")
    kind = prompt_text_kind(prompt)
    if kind in (CONTINUATION, NOT_PROMPT) or is_host_retry(prompt):
        # An app retry continues the turn. A typed "Try again" opens a new
        # turn, whose prompt id never matches the overrides kept here.
        return ""
    if kind != TYPED and is_own_report(str(payload.get("transcript_path") or ""), prompt):
        return ""
    path = payload.get("transcript_path")

    def unseen(since_key):
        # Reading never crosses a compaction, so what came before one stays
        # unseen. Best effort: an unreadable transcript leaves the holds to
        # count as unanswered.
        if not isinstance(path, str) or not path:
            return None
        try:
            return read_recent_turns(path, since_key=since_key, wait_seconds=0.0).turns
        except TranscriptUnreadable:
            return None

    decision = judge.record_prompt(
        config.settings(), _situation(payload, config, session_id, with_project=False),
        typed_prompt(prompt).text if kind == TYPED else None,
        payload.get("prompt_id"), unseen)
    notices = decision.texts(judge.OVERRIDE_RECORDED, judge.SESSION_NOTICE)
    output: dict = {}
    if notices:
        # The notices above reach a mod with no text; hook context arrives with
        # them, so the skill-usage mod reads the same sentence from here.
        output["hookSpecificOutput"] = {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": _sentence(notices),
        }
    return _with_warnings(output, [*notices, *decision.texts(judge.WARNING)])


# Hook output ----------------------------------------------------------------------


def _prompt_id(payload: dict) -> str | None:
    value = payload.get("prompt_id")
    return value if isinstance(value, str) and value else None


def _deny(text: str) -> dict:
    """The PreToolUse output that holds a call with the message `text`; {} for none."""

    if not text:
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": text,
        }
    }


def _sentence(parts) -> str:
    """The adapter's one notice sentence for these parts, or "" when there are none."""

    text = "; ".join(p.rstrip(".") for p in parts if p)
    return f"{NAME}: {text}." if text else ""


def _with_warnings(output: dict, warnings) -> str:
    text = _sentence(warnings)
    if text:
        output["systemMessage"] = text
    return json.dumps(output) if output else ""


def _session_fields(payload: dict) -> tuple[str, str]:
    session_id = payload.get("session_id")
    transcript_path = payload.get("transcript_path")
    if not isinstance(session_id, str) or not session_id:
        raise _FailOpen("the hook input has no session_id")
    if not isinstance(transcript_path, str) or not transcript_path:
        raise _FailOpen("the hook input has no transcript_path")
    return session_id, transcript_path


def _fail_open(why: str) -> str:
    return json.dumps(
        {"systemMessage": f"{NAME}: {why}, so this action was allowed without checks."}
    )


# Events that run after the action: their failure has no action to let
# through, and the call's `PreToolUse` has already warned of the same cause,
# so it adds nothing (Ticket 096).
_AFTER_THE_ACTION = frozenset({"PostToolUse"})

_HANDLERS = {
    "PreToolUse": _pre_tool_use,
    "PostToolUse": _post_tool_use,
    "Stop": _stop,
    "UserPromptSubmit": _user_prompt_submit,
    "SessionStart": _session_start,
}
