"""The adapter's single entry point: one hook input in, one hook output out.

`run_hook` dispatches on `hook_event_name` and owns the adapter's failure rule
(ADR 0003, "fail open, visibly"): when it cannot read what it needs, it lets
the action through and returns a `systemMessage` warning the user sees. It
never blocks because of its own failure.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from . import actions, design_reads, gates, reference_reads
from .overrides import GOATED_SKILLS, parse_overrides
from .policy import (
    installed_skill_names, router_skill_installed, shared_policy_loaded, skill_folder,
)
from .state import StateStore, StateUnsafe
from .transcript import (
    CONTINUATION,
    NOT_PROMPT,
    TYPED,
    TranscriptUnreadable,
    is_host_retry,
    prompt_text_kind,
    read_recent_turns,
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
ROUTER_NOTICE = (
    f"could not find the `{gates.ROUTER_SKILL}` skill among your user, project, "
    "or plugin skills, so writes, spawns, and commands will stay held. Install it, "
    "or type `skip routing` in a prompt to proceed without it."
)


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
        return _fail_open(str(exc))
    except Exception as exc:  # noqa: BLE001 - any adapter bug must fail open, visibly
        return _fail_open(f"it hit an internal error ({type(exc).__name__})")


def _pre_tool_use(payload: dict, config: Config) -> str:
    tool_name = str(payload.get("tool_name") or "")
    if tool_name not in gates.GATED_TOOLS and not actions.is_action_tool(tool_name):
        return ""
    tool_input = payload.get("tool_input")
    tool_input = tool_input if isinstance(tool_input, dict) else {}
    session_id, transcript_path = _session_fields(payload)
    if payload.get("agent_id"):
        return _subagent_pre_tool_use(payload, config, tool_name, tool_input, transcript_path)

    store = StateStore(config.state_dir)
    state, state_warning = store.load(session_id)
    try:
        turns = read_recent_turns(
            transcript_path,
            since_key=state.last_turn,
            prompt_id=_prompt_id(payload),
            wait_seconds=config.lag_wait_seconds,
            current_call=_current_call(payload, tool_name, tool_input),
        )
    except TranscriptUnreadable as exc:
        raise _FailOpen(str(exc)) from exc
    gates.fold_turns(state, turns, config.skill_namespaces)
    current = turns[-1]
    overrides = _overrides_for(state, current, payload.get("prompt_id"))
    unread: list[str] = []

    def spawned() -> dict:
        # Unreadable subagent transcripts count as no changes, with a warning, as at closeout.
        found, missed = _spawned_subagents(current, transcript_path)
        unread.extend(missed)
        return found

    earlier = _since_compaction(state)
    registry_warnings: list[str] = []
    cwd = Path(str(payload.get("cwd") or "."))
    hold = gates.check_routing(
        state, tool_name, tool_input, current, overrides,
        orientation_installed=lambda: gates.ORIENTATION_SKILL in installed_skill_names(cwd, config.home),
    )
    if hold is None:
        hold = actions.check_action(
            tool_name, tool_input, current, overrides, config.skill_namespaces,
            _project(payload, config), spawned, earlier,
            closeout=actions.Closeout(state.design_edits_of(current.key),
                                      _design_ids(payload, config)),
            references=lambda: _registry_references(config, registry_warnings),
        )
    tool_use_id = str(payload.get("tool_use_id") or "")
    if hold is None and tool_use_id:
        # What the design gates required of an edit they let through, for the closeout.
        references = actions.design_references(
            tool_name, tool_input, current, overrides, config.skill_namespaces,
            _project(payload, config), earlier)
        if references:
            state.record_design_edit(current.key, tool_use_id, references)
    hold = gates.advice_once(hold, lambda: _claim_turn(store, session_id, current.key))
    warnings = [state_warning, _save(store, session_id, state), _unread_warning(unread),
                *registry_warnings]
    return _with_warnings(_deny(hold), warnings)


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


def _since_compaction(state) -> actions.SinceCompaction:
    """What the main agent's saved state says counts until the next compaction."""

    return actions.SinceCompaction(
        frozenset(state.loads), frozenset(state.reference_reads), frozenset(state.template_reads),
        spans_turns=True, skill_references_read=frozenset(state.skill_reference_reads))


def _claim_turn(
    store: StateStore, session_id: str, turn_key: str, agent_id: str | None = None
) -> bool:
    """`StateStore.claim_turn`, or True when the marker cannot be claimed or
    read: the hold then gives the advice in full, and no hook fails."""

    try:
        return store.claim_turn(session_id, turn_key, agent_id)
    except (OSError, StateUnsafe):
        return True


def _subagent_pre_tool_use(
    payload: dict, config: Config, tool_name: str, tool_input: dict, transcript_path: str
) -> str:
    """Apply only the action gates, from the subagent's own transcript (spec R9).

    Routing gates do not apply: the parent's brief carries the route. Claude
    Code passes the parent's `transcript_path`; the subagent's entries live
    beside it in `<session>/subagents/agent-<agent_id>.jsonl`. Nobody types a
    subagent's prompts, so no override applies.
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
            current_call=_current_call(payload, tool_name, tool_input),
        )
    except TranscriptUnreadable as exc:
        raise _FailOpen(f"in a subagent, {exc}") from exc
    hold = actions.check_action(
        tool_name, tool_input, turns[-1], {}, config.skill_namespaces,
        _project(payload, config),
    )
    session_id = str(payload.get("session_id"))
    hold = gates.advice_once(hold, lambda: _claim_turn(
        StateStore(config.state_dir), session_id, turns[-1].key, agent_id))
    return _with_warnings(_deny(hold), [])


def _current_call(payload: dict, tool_name: str, tool_input: dict) -> tuple[str, str, dict]:
    """The call being judged, whose own route and skip lines count for it."""

    return str(payload.get("tool_use_id") or ""), tool_name, tool_input


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
            )
        except TranscriptUnreadable:
            unread.append(agent_id)
    return found, unread


def _stop(payload: dict, config: Config) -> str:
    """Hold the end of a turn that changed code until its closeout items are met."""

    session_id, transcript_path = _session_fields(payload)
    store = StateStore(config.state_dir)
    state, state_warning = store.load(session_id)
    try:
        turns = read_recent_turns(
            transcript_path,
            since_key=state.last_turn,
            prompt_id=_prompt_id(payload),
            wait_seconds=config.lag_wait_seconds,
        )
    except TranscriptUnreadable as exc:
        raise _FailOpen(str(exc)) from exc
    gates.fold_turns(state, turns, config.skill_namespaces)
    current = turns[-1]
    subagents, unread = _spawned_subagents(current, transcript_path)
    hold = actions.check_closeout(
        current,
        _overrides_for(state, current, payload.get("prompt_id")),
        config.skill_namespaces,
        str(payload.get("last_assistant_message") or ""),
        subagents,
        _project(payload, config),
        state.design_edits_of(current.key),
        _design_ids(payload, config),
        earlier=_since_compaction(state),
    )
    warnings = [state_warning, _save(store, session_id, state), _unread_warning(unread)]
    output = {"decision": "block", "reason": hold.message()} if hold else {}
    return _with_warnings(output, warnings)


def _unread_warning(unread: list[str]) -> str | None:
    """The warning for subagents whose transcripts could not be read, whose
    changes the action and closeout gates therefore left out; None for none."""

    if not unread:
        return None
    return ("could not read the transcript of subagent " + ", ".join(unread)
            + ", so its changes were not checked")


def _design_ids(payload: dict, config: Config):
    """Reads each design reference's section ids from the installed skill, for
    the closeout's citation item, when called."""

    return lambda: design_reads.section_ids(skill_folder(
        Path(str(payload.get("cwd") or ".")), config.home, actions.DESIGN_SKILL))


def _prompt_id(payload: dict) -> str | None:
    value = payload.get("prompt_id")
    return value if isinstance(value, str) and value else None


def _deny(hold) -> dict:
    if hold is None:
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": hold.message(),
        }
    }


def _session_start(payload: dict, config: Config) -> str:
    """Reset skill proof after compaction; note a missing policy or router once.

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
    state, state_warning = store.load(session_id)
    if payload.get("source") == "startup" and state.task is None:
        state.task_unknown = False
    if payload.get("source") in {"compact", "clear"}:
        state.forget_context()
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
    if notices:
        output["hookSpecificOutput"] = {
            "hookEventName": "SessionStart",
            "additionalContext": " ".join(notices),
        }
    warnings = [*notices, state_warning, _save(store, session_id, state)]
    return _with_warnings(output, warnings)


def _user_prompt_submit(payload: dict, config: Config) -> str:
    """Record the overrides the user typed; they apply to this prompt's turn only.

    The hook sees only the prompt text: its input names no source, and the
    prompt's transcript entry is not yet written. Text that continues the turn,
    such as a task notification, leaves the typed prompt's overrides in place;
    text a subagent, another session, or the app wrote starts a turn with none.
    The gates check again against the transcript, which shows who wrote the
    prompt, so a message this text check misses still applies no override.
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
    store = StateStore(config.state_dir)
    state, state_warning = store.load(session_id)
    if kind == TYPED:
        cwd = Path(str(payload.get("cwd") or "."))
        known = installed_skill_names(cwd, config.home) or GOATED_SKILLS
        found = parse_overrides(prompt, known)
    else:
        found = parse_overrides("")
    state.overrides = {"prompt_id": payload.get("prompt_id"), **found}

    notes = [state_warning, _save(store, session_id, state)]
    output: dict = {}
    if found["phrases"]:
        typed = ", ".join(f'"{phrase}"' for phrase in found["phrases"])
        recorded = f"recorded your override for this prompt: {typed}"
        notes.insert(0, recorded)
        # The notice above reaches a mod with no text; hook context arrives with
        # it, so the skill-usage mod reads the same sentence from here.
        output["hookSpecificOutput"] = {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": _sentence([recorded]),
        }
    return _with_warnings(output, notes)


def _overrides_for(state, turn, payload_prompt_id: object) -> dict:
    """Return stored overrides only for the typed prompt that opened `turn`."""

    stored = state.overrides or {}
    if not turn.typed:
        return {}
    turn_prompt = turn.prompt_id or payload_prompt_id
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


_HANDLERS = {
    "PreToolUse": _pre_tool_use,
    "Stop": _stop,
    "UserPromptSubmit": _user_prompt_submit,
    "SessionStart": _session_start,
}
