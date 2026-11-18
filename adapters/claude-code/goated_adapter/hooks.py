"""The adapter's single entry point: one hook input in, one hook output out.

`run_hook` dispatches on `hook_event_name` and owns the adapter's failure rule
(ADR 0003, "fail open, visibly"): when it cannot read what it needs, it lets
the action through and returns a `systemMessage` warning the user sees. It
never blocks because of its own failure. A hook that runs after the action
(`PostToolUse`) has no action to let through, so its failure adds nothing.

Each handler turns its hook input into the event model (`translation`,
`transcript`), asks the rules, and puts their hold text into Claude Code's
words (`translation.render`).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from . import actions, friction, gates, onboarding, reference_reads, translation
from .events import Result
from .overrides import GOATED_SKILLS, parse_overrides
from .policy import (
    installed_skill_names, router_skill_installed, shared_policy_loaded,
)
from .state import StateStore, StateUnsafe
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
RETROSPECTIVE_NOTICE = (
    "{count} GOATED holds this session were declined or left unanswered. The "
    "`retrospective` skill can turn that friction into improvements to the "
    "project's checks, standards, or instructions, such as after a wave of "
    "delegated tickets is merged. This is a notice; nothing is held."
)
ROUTER_NOTICE = (
    f"could not find the `{gates.ROUTER_SKILL}` skill among your user, project, "
    "or plugin skills, so writes, spawns, and commands will stay held. Install it, "
    "or type `skip routing` in a prompt to proceed without it."
)
# The turn marker's purpose for the early closeout note (Ticket 096), apart
# from the unseen-line advice's and each hold's.
CLOSEOUT_NOTE = "closeout-note"


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
    `from_environment` gives the installed defaults; tests pass their own.
    """

    __slots__ = ("state_dir", "home", "lag_wait_seconds", "skill_namespaces", "project_dir",
                 "registry_path", "registry_named")

    def __init__(
        self,
        state_dir: Path,
        home: Path | None = None,
        lag_wait_seconds: float = 1.5,
        skill_namespaces: tuple[str, ...] = (),
        project_dir: str | None = None,
        registry_path: Path | None = None,
        registry_named: bool = False,
    ) -> None:
        self.state_dir = Path(state_dir)
        self.home = Path(home) if home is not None else Path.home()
        self.lag_wait_seconds = lag_wait_seconds
        self.skill_namespaces = tuple(skill_namespaces)
        self.project_dir = project_dir
        self.registry_path = Path(registry_path) if registry_path is not None else None
        self.registry_named = registry_named

    @classmethod
    def from_environment(cls) -> "Config":
        override = os.environ.get(STATE_DIR_ENV)
        namespaces = os.environ.get(NAMESPACES_ENV, "")
        registry = os.environ.get(REGISTRY_ENV)
        return cls(
            state_dir=Path(override) if override else _default_state_root() / STATE_DIR_NAME,
            skill_namespaces=tuple(n.strip() for n in namespaces.split(",") if n.strip()),
            project_dir=os.environ.get(PROJECT_DIR_ENV) or None,
            registry_path=Path(registry) if registry else DEFAULT_REGISTRY,
            registry_named=bool(registry),
        )


def _default_state_root() -> Path:
    """A per-user folder no other local user can pre-create.

    POSIX uses `$XDG_STATE_HOME` or `~/.local/state`, not the shared `/tmp`.
    Windows uses the per-user temp folder, found as `tempfile` would, without
    the import cost.
    """

    if os.name != "nt":
        xdg = os.environ.get("XDG_STATE_HOME")
        return Path(xdg) if xdg else Path.home() / ".local" / "state"
    for name in ("TEMP", "TMP"):
        value = os.environ.get(name)
        if value:
            return Path(value)
    return Path.home() / "AppData" / "Local" / "Temp"


def _project(payload: dict, config: Config) -> actions.Project | None:
    """The project whose files the action and closeout gates count."""

    return actions.find_project(str(payload.get("cwd") or "") or None, config.project_dir)


def _agent_folders(config: Config) -> list[str]:
    """Claude Code's own configuration folders, where no write is scratch:
    `~/.claude`, and the one in the configured home."""

    return ["~/.claude", os.path.join(str(config.home), ".claude")]


def _load_state(store: StateStore, session_id: str):
    """`store.load`, with a shell saved by an older adapter as its tool name
    ("Bash", "PowerShell") read as that tool's shell."""

    state, warning = store.load(session_id)
    state.shell = translation.COMMAND_TOOLS.get(state.shell, state.shell)
    return state, warning


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


def _pre_tool_use(payload: dict, config: Config) -> str:
    tool_name = str(payload.get("tool_name") or "")
    if not translation.is_judged(tool_name):
        return ""
    call = translation.call_of(tool_name, payload.get("tool_input"),
                               str(payload.get("tool_use_id") or ""))
    session_id, transcript_path = _session_fields(payload)
    if payload.get("agent_id"):
        return _subagent_pre_tool_use(payload, config, tool_name, call, transcript_path)

    store = StateStore(config.state_dir)
    state, state_warning = _load_state(store, session_id)
    try:
        reading = read_recent_turns(
            transcript_path,
            since_key=state.last_turn,
            prompt_id=_prompt_id(payload),
            wait_seconds=config.lag_wait_seconds,
            current_call=call,
        )
    except TranscriptUnreadable as exc:
        raise _FailOpen(str(exc)) from exc
    turns = reading.turns
    gates.fold_turns(state, turns, config.skill_namespaces)
    _settle_holds(state, turns, config)
    current = turns[-1]
    overrides = _overrides_for(state, current, reading.prompt_id, payload.get("prompt_id"))
    unread: list[str] = []

    def spawned() -> dict:
        # Unreadable subagent transcripts count as no changes, with a warning, as at closeout.
        found, missed = _spawned_subagents(current, transcript_path)
        unread.extend(missed)
        return found

    earlier = _since_compaction(state)
    registry_warnings: list[str] = []
    cwd = Path(str(payload.get("cwd") or "."))
    routing = gates.check_routing(
        state, call, current, overrides,
        orientation_installed=lambda: gates.ORIENTATION_SKILL in installed_skill_names(cwd, config.home),
        writes_scratch=lambda: actions.writes_only_scratch(
            call, _project(payload, config), _agent_folders(config)
        ),
    )
    # Every gate judges the call, so one message carries every hold (Ticket 095).
    holds = routing + actions.check_action(
        call, current, overrides, config.skill_namespaces,
        _project(payload, config), spawned, earlier,
        closeout=actions.Closeout(state.spawn_templates_of(current.key),
                                  _route_intensity(state), state.briefed),
        references=lambda: _registry_references(config, registry_warnings),
    )
    if not holds and call.id:
        # Which templates a spawn's brief followed, for the closeout.
        templates = actions.brief_templates(
            call, current, overrides, config.skill_namespaces, earlier)
        if templates:
            state.record_spawn_templates(current.key, call.id, templates)
    friction.observe(state, current, friction.action_of(call), holds)
    text = gates.message(holds, lambda purpose: _claim_turn(
        store, session_id, current.key, purpose), call=True)
    warnings = [state_warning, _save(store, session_id, state), _unread_warning(unread),
                *registry_warnings]
    return _with_warnings(_deny(translation.render(text, tool_name, state.shell)), warnings)


def _registry_references(config: Config, warnings: list[str]) -> tuple:
    """The installed registry's declared references, or () when it cannot be
    used, failing open: a registry that does not parse, or a missing one the
    user named, adds a warning to `warnings`; a missing default is silent."""

    try:
        return reference_reads.load(config.registry_path)
    except reference_reads.RegistryUnreadable as exc:
        if not exc.missing or config.registry_named:
            warnings.append(f"could not use the GOATED registry at {config.registry_path} ({exc}), "
                            "so the reference-reads gate asked for nothing")
        return ()


def _route_intensity(state) -> str | None:
    """The current task's route intensity (`full`), or None without a `requires:` route."""

    return state.task.route.get("intensity") if state.task else None


def _since_compaction(state) -> actions.SinceCompaction:
    """What the main agent's saved state says counts until the next compaction."""

    return actions.SinceCompaction(
        frozenset(state.loads), frozenset(state.reference_reads), frozenset(state.template_reads),
        spans_turns=True, skill_references_read=frozenset(state.skill_reference_reads))


def _claim_turn(
    store: StateStore, session_id: str, turn_key: str, purpose: str,
    agent_id: str | None = None,
) -> bool:
    """`StateStore.claim_turn`, or True when the marker cannot be claimed or
    read: the hold then gives its full text, and no hook fails."""

    try:
        return store.claim_turn(session_id, turn_key, purpose, agent_id)
    except (OSError, StateUnsafe):
        return True


def _subagent_pre_tool_use(
    payload: dict, config: Config, tool_name: str, call, transcript_path: str
) -> str:
    """Apply only the action gates, from the subagent's own transcript (spec R9).

    Routing gates do not apply: the parent's brief carries the route. Claude
    Code passes the parent's `transcript_path`; the subagent's entries live
    beside it in `<session>/subagents/agent-<agent_id>.jsonl`. Nobody types a
    subagent's prompts, so no override applies. A commit meets the closeout
    of the subagent's own turn (Ticket 098); it was started from its
    parent's brief, so, as a briefed session, it meets no Review item, and it
    records no spawn templates, so the `review-intake` gate holds nothing.
    """

    agent_id = str(payload.get("agent_id"))
    if not AGENT_ID_RE.match(agent_id):
        raise _FailOpen("the hook input has an unexpected agent_id")
    path = _subagent_transcript(transcript_path, agent_id)
    try:
        turns = read_recent_turns(
            path,
            since_key=None,
            wait_seconds=0.0,
            sidechain=True,
            current_call=call,
        ).turns
    except TranscriptUnreadable as exc:
        raise _FailOpen(f"in a subagent, {exc}") from exc
    holds = actions.check_action(
        call, turns[-1], {}, config.skill_namespaces,
        _project(payload, config), closeout=actions.Closeout(briefed=True),
    )
    session_id = str(payload.get("session_id"))
    text = gates.message(holds, lambda purpose: _claim_turn(
        StateStore(config.state_dir), session_id, turns[-1].key, purpose, agent_id), call=True)
    return _with_warnings(_deny(translation.render(text, tool_name, gates.last_shell(turns))), [])


def _subagent_transcript(transcript_path: str, agent_id: str) -> Path:
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


def _stop(payload: dict, config: Config) -> str:
    """Hold the end of a turn that changed code until its closeout items are met."""

    session_id, transcript_path = _session_fields(payload)
    store = StateStore(config.state_dir)
    state, state_warning = _load_state(store, session_id)
    try:
        reading = read_recent_turns(
            transcript_path,
            since_key=state.last_turn,
            prompt_id=_prompt_id(payload),
            wait_seconds=config.lag_wait_seconds,
        )
    except TranscriptUnreadable as exc:
        raise _FailOpen(str(exc)) from exc
    turns = reading.turns
    gates.fold_turns(state, turns, config.skill_namespaces)
    _settle_holds(state, turns, config)
    current = turns[-1]
    subagents, unread = _spawned_subagents(current, transcript_path)
    hold = actions.check_closeout(
        current,
        _overrides_for(state, current, reading.prompt_id, payload.get("prompt_id")),
        config.skill_namespaces,
        str(payload.get("last_assistant_message") or ""),
        subagents,
        _project(payload, config),
        earlier=_since_compaction(state),
        spawn_templates=state.spawn_templates_of(current.key),
        intensity=_route_intensity(state),
        briefed=state.briefed,
    )
    holds = [hold] if hold else []
    friction.observe(state, current, friction.STOP, holds)
    if hold is None:
        # The turn ends here, and so do its typed overrides: a subagent's
        # report arriving later continues the turn (see `is_own_report`)
        # without them. Another hook may still block this Stop, so the turn
        # then goes on without its overrides, which only holds more.
        state.overrides = {}
    warnings = [state_warning, _save(store, session_id, state), _unread_warning(unread)]
    text = translation.render(gates.message(holds, lambda purpose: _claim_turn(
        store, session_id, current.key, purpose)))
    output = {"decision": "block", "reason": text} if text else {}
    return _with_warnings(output, warnings)


def _post_tool_use(payload: dict, config: Config) -> str:
    """After the main agent's first finished code change of a turn by a file
    edit tool, add one note naming the closeout items the turn will meet
    (Ticket 096), as context for the agent. It never holds anything.

    The call is taken from the hook's own payload, since the transcript may
    not show it yet; the transcript and state say only what the payload
    cannot, such as which skills count as loaded. A subagent has no
    closeout, so gets no note; nor does a turn the closeout already held,
    which has seen its items. The note's claim on the turn marker has its
    own purpose, and a claim that fails or cannot be made adds no note.
    """

    tool_name = str(payload.get("tool_name") or "")
    if (tool_name not in translation.FILE_WRITE_TOOLS or payload.get("agent_id")
            or not _finished(payload.get("tool_response"))):
        return ""
    call = translation.call_of(tool_name, payload.get("tool_input"),
                               str(payload.get("tool_use_id") or ""))
    session_id, transcript_path = _session_fields(payload)
    store = StateStore(config.state_dir)
    state, _ = _load_state(store, session_id)
    # The call's PreToolUse saved its turn as the last seen, so a turn that
    # already has its note is known here without reading the transcript.
    if state.last_turn and store.turn_claimed(session_id, state.last_turn, CLOSEOUT_NOTE):
        return ""
    try:
        reading = read_recent_turns(
            transcript_path,
            since_key=state.last_turn,
            prompt_id=_prompt_id(payload),
            wait_seconds=config.lag_wait_seconds,
            current_call=call,
        )
    except TranscriptUnreadable as exc:
        raise _FailOpen(str(exc)) from exc
    # Read only: the hooks that judge calls own the saved state.
    turns = reading.turns
    gates.fold_turns(state, turns, config.skill_namespaces)
    current = turns[-1]
    if (state.held_gates.get("turn") == current.key
            and actions.CLOSEOUT_GATE in state.held_gates["gates"]):
        return ""
    text = translation.render(actions.closeout_note(
        current, call.finished(Result(ok=True)),
        _overrides_for(state, current, reading.prompt_id, payload.get("prompt_id")),
        config.skill_namespaces, _project(payload, config), _since_compaction(state),
        _route_intensity(state)))
    if not text:
        return ""
    try:
        claimed = store.claim_turn(session_id, current.key, CLOSEOUT_NOTE)
    except (OSError, StateUnsafe):
        claimed = False  # The note is advice: without a marker it could repeat, so none.
    if not claimed:
        return ""
    return json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse", "additionalContext": _sentence([text])}})


def _finished(tool_response: object) -> bool:
    """Whether a PostToolUse `tool_response` shows the call did its work: an
    object that reports no error and no failure. Anything else, such as an
    error's text, may be a call that changed nothing."""

    return (isinstance(tool_response, dict) and not tool_response.get("error")
            and not tool_response.get("is_error") and tool_response.get("success") is not False)


def _settle_holds(state, turns, config: Config) -> None:
    """Settle the friction count's open holds against the turns just read."""

    friction.settle(state, turns, lambda raw: gates.goated_skill_name(raw, config.skill_namespaces))


def _settle_unseen(state, payload: dict, config: Config) -> None:
    """Settle open holds against the turns since the last one seen, before a
    typed prompt closes them: a read or skip line after the last hook call,
    such as in a turn the user interrupted, answers a hold too. Reading never
    crosses a compaction, so what came before one stays unseen. Best effort:
    an unreadable transcript leaves the holds to count as unanswered."""

    path = payload.get("transcript_path")
    if not state.open_holds or not isinstance(path, str) or not path:
        return
    try:
        turns = read_recent_turns(path, since_key=state.last_turn, wait_seconds=0.0).turns
    except TranscriptUnreadable:
        return
    _settle_holds(state, turns, config)


def _unread_warning(unread: list[str]) -> str | None:
    """The warning for subagents whose transcripts could not be read, whose
    changes the action and closeout gates therefore left out; None for none."""

    if not unread:
        return None
    return ("could not read the transcript of subagent " + ", ".join(unread)
            + ", so its changes were not checked")


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


def _session_start(payload: dict, config: Config) -> str:
    """Reset skill proof after compaction; note a missing policy or router once
    per session, and missing agent files once per project.

    After compaction or `/clear` every skill must load again, and the design
    references and spawn-brief templates be read again, because their text
    was summarized away; the route itself carries over (spec R5). Turns from
    before the boundary are never folded back in.
    A new session (`startup`) has no task yet, so `continue` may start one.
    """

    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise _FailOpen("the hook input has no session_id")
    store = StateStore(config.state_dir)
    state, state_warning = _load_state(store, session_id)
    if payload.get("source") == "startup" and state.task is None:
        state.task_unknown = False
    if payload.get("source") in {"compact", "clear"}:
        state.forget_context()
        friction.forget_open(state)
        state.last_turn = None
        store.clear_turn_markers(session_id)

    output: dict = {}
    notices = []
    if not state.policy_notice_shown:
        state.policy_notice_shown = True
        cwd = Path(str(payload.get("cwd") or "."))
        if not shared_policy_loaded(cwd, config.home):
            notices.append(POLICY_NOTICE)
        if not router_skill_installed(cwd, config.home, gates.ROUTER_SKILL):
            notices.append(ROUTER_NOTICE)
    record_warnings: list[str] = []
    try:
        onboarding_notice = _onboarding_notice(store, payload, config, record_warnings)
    except (OSError, StateUnsafe) as exc:
        # The notice is advice: losing it must not lose this start's reset.
        onboarding_notice = None
        record_warnings.append(f"could not check its onboarding notice ({exc})")
    if onboarding_notice:
        notices.append(onboarding_notice)
    if notices:
        output["hookSpecificOutput"] = {
            "hookEventName": "SessionStart",
            "additionalContext": " ".join(notices),
        }
    warnings = [*notices, state_warning, _save(store, session_id, state), *record_warnings]
    return _with_warnings(output, warnings)


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
    store = StateStore(config.state_dir)
    state, state_warning = _load_state(store, session_id)
    if kind == TYPED:
        cwd = Path(str(payload.get("cwd") or "."))
        known = installed_skill_names(cwd, config.home) or GOATED_SKILLS
        found = parse_overrides(typed_prompt(prompt).text, known)
        # Holds the last turn left open are unanswered, unless what followed
        # them, which no hook may have seen, or this prompt's overrides settle them.
        _settle_unseen(state, payload, config)
        friction.close_turn(state, found)
    else:
        found = parse_overrides("")
    state.overrides = {"prompt_id": payload.get("prompt_id"), **found}
    notices = []
    if found["phrases"]:
        typed = ", ".join(f'"{phrase}"' for phrase in found["phrases"])
        notices.append(f"recorded your override for this prompt: {typed}")
    if kind == TYPED and friction.claim_retrospective_notice(state):
        notices.append(RETROSPECTIVE_NOTICE.format(count=state.friction))

    notes = [*notices, state_warning, _save(store, session_id, state)]
    output: dict = {}
    if notices:
        # The notices above reach a mod with no text; hook context arrives with
        # them, so the skill-usage mod reads the same sentence from here.
        output["hookSpecificOutput"] = {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": _sentence(notices),
        }
    return _with_warnings(output, notes)


def _overrides_for(state, turn, turn_prompt_id: str | None, payload_prompt_id: object) -> dict:
    """Return stored overrides only for the typed prompt that opened `turn`,
    whose id the transcript gives as `turn_prompt_id` (None when it gives
    none) and the hook input as `payload_prompt_id`."""

    stored = state.overrides or {}
    if not turn.typed:
        return {}
    turn_prompt = turn_prompt_id or payload_prompt_id
    if stored.get("prompt_id") and turn_prompt and stored["prompt_id"] != turn_prompt:
        return {}
    return stored


def _save(store: StateStore, session_id: str, state) -> str | None:
    """Save best effort: a hold already decided stands even if saving fails."""

    try:
        store.save(session_id, state)
    except OSError as exc:
        return f"could not save its session state ({exc.strerror or type(exc).__name__})"
    return None


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
