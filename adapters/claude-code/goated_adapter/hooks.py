"""The adapter's single entry point: one hook input in, one hook output out.

`run_hook` dispatches on `hook_event_name` and owns the adapter's failure rule
(ADR 0003, "fail open, visibly"): when it cannot read what it needs, it lets
the action through and returns a `systemMessage` warning the user sees. It
never blocks because of its own failure.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import gates
from .overrides import parse_overrides
from .policy import router_skill_installed, shared_policy_loaded
from .state import StateStore, StateUnsafe
from .transcript import (
    CONTINUATION,
    NOT_PROMPT,
    TYPED,
    TranscriptUnreadable,
    prompt_text_kind,
    read_recent_turns,
)

STATE_DIR_ENV = "GOATED_ADAPTER_STATE_DIR"
NAMESPACES_ENV = "GOATED_ADAPTER_SKILL_NAMESPACES"
STATE_DIR_NAME = "goated-claude-code-adapter"
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
    distribution installed as a plugin. `from_environment` gives the installed
    defaults; tests pass their own.
    """

    __slots__ = ("state_dir", "home", "lag_wait_seconds", "skill_namespaces")

    def __init__(
        self,
        state_dir: Path,
        home: Path | None = None,
        lag_wait_seconds: float = 1.5,
        skill_namespaces: tuple[str, ...] = (),
    ) -> None:
        self.state_dir = Path(state_dir)
        self.home = Path(home) if home is not None else Path.home()
        self.lag_wait_seconds = lag_wait_seconds
        self.skill_namespaces = tuple(skill_namespaces)

    @classmethod
    def from_environment(cls) -> "Config":
        override = os.environ.get(STATE_DIR_ENV)
        namespaces = os.environ.get(NAMESPACES_ENV, "")
        return cls(
            state_dir=Path(override) if override else _default_state_root() / STATE_DIR_NAME,
            skill_namespaces=tuple(n.strip() for n in namespaces.split(",") if n.strip()),
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
    if payload.get("agent_id"):
        # Routing gates do not apply in subagents: the parent's brief carries
        # the route (spec R9).
        return ""
    tool_name = str(payload.get("tool_name") or "")
    if tool_name not in gates.GATED_TOOLS:
        return ""
    session_id, transcript_path = _session_fields(payload)

    store = StateStore(config.state_dir)
    state, state_warning = store.load(session_id)
    try:
        turns = read_recent_turns(
            transcript_path,
            since_key=state.last_turn,
            tool_use_id=payload.get("tool_use_id"),
            wait_seconds=config.lag_wait_seconds,
        )
    except TranscriptUnreadable as exc:
        raise _FailOpen(str(exc)) from exc
    gates.fold_turns(state, turns, config.skill_namespaces)
    current = turns[-1]
    hold = gates.check_routing(
        state, tool_name, current, _overrides_for(state, current, payload.get("prompt_id"))
    )
    warnings = [state_warning, _save(store, session_id, state)]

    output: dict = {}
    if hold is not None:
        output["hookSpecificOutput"] = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": hold.message(),
        }
    return _with_warnings(output, warnings)


def _session_start(payload: dict, config: Config) -> str:
    """Reset skill proof after compaction; note a missing policy or router once.

    After compaction the router and the task's required skills must load
    again, because their text was summarized away; the route itself carries
    over (spec R5). Turns from before the boundary are never folded back in.
    """

    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise _FailOpen("the hook input has no session_id")
    store = StateStore(config.state_dir)
    state, state_warning = store.load(session_id)
    if payload.get("source") in {"compact", "clear"}:
        state.router_loaded = False
        state.last_turn = None
        if state.task is not None:
            state.task.loads = []

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

    The hook sees only the prompt text. Text that continues the turn, such as a
    task notification, leaves the typed prompt's overrides in place; text
    another session or the app wrote starts a turn with none. The gates check
    again against the transcript, which shows who wrote the prompt.
    """

    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise _FailOpen("the hook input has no session_id")
    prompt = str(payload.get("prompt") or "")
    kind = prompt_text_kind(prompt)
    if kind in (CONTINUATION, NOT_PROMPT):
        return ""
    store = StateStore(config.state_dir)
    state, state_warning = store.load(session_id)
    found = parse_overrides(prompt) if kind == TYPED else parse_overrides("")
    state.overrides = {"prompt_id": payload.get("prompt_id"), **found}

    notes = [state_warning, _save(store, session_id, state)]
    if found["phrases"]:
        typed = ", ".join(f'"{phrase}"' for phrase in found["phrases"])
        notes.insert(0, f"recorded your override for this prompt: {typed}")
    return _with_warnings({}, notes)


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


def _with_warnings(output: dict, warnings) -> str:
    text = "; ".join(w.rstrip(".") for w in warnings if w)
    if text:
        output["systemMessage"] = f"{NAME}: {text}."
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
    "UserPromptSubmit": _user_prompt_submit,
    "SessionStart": _session_start,
}
