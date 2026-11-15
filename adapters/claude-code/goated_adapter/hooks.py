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
from .policy import shared_policy_loaded
from .state import StateStore, StateUnsafe
from .transcript import TranscriptUnreadable, is_harness_prompt, read_recent_turns

STATE_DIR_ENV = "GOATED_ADAPTER_STATE_DIR"
NAME = "GOATED Claude Code adapter"
POLICY_NOTICE = (
    "the GOATED shared policy is not loaded in this session, so the "
    "`using-goated-ai-skills` router runs from its standalone fallback. To load "
    "it, follow the Claude Code steps in the GOATED install guide."
)


class Config:
    """Where the adapter keeps state and finds instruction files.

    `lag_wait_seconds` bounds how long a PreToolUse call waits for the
    transcript to show the call being judged. `from_environment` gives the
    installed defaults; tests pass their own.
    """

    __slots__ = ("state_dir", "home", "lag_wait_seconds")

    def __init__(
        self, state_dir: Path, home: Path | None = None, lag_wait_seconds: float = 1.5
    ) -> None:
        self.state_dir = Path(state_dir)
        self.home = Path(home) if home is not None else Path.home()
        self.lag_wait_seconds = lag_wait_seconds

    @classmethod
    def from_environment(cls) -> "Config":
        override = os.environ.get(STATE_DIR_ENV)
        return cls(state_dir=Path(override) if override else _temp_root() / STATE_DIR_NAME)


STATE_DIR_NAME = "goated-claude-code-adapter"


def _temp_root() -> Path:
    """The OS temporary folder, found as `tempfile` would, without importing it."""

    for name in ("TMPDIR", "TEMP", "TMP"):
        value = os.environ.get(name)
        if value:
            return Path(value)
    return Path("/tmp") if os.name != "nt" else Path.home() / "AppData" / "Local" / "Temp"


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
    gates.fold_turns(state, turns)
    hold = gates.check_routing(
        state, tool_name, turns[-1], _overrides_for(state, payload.get("prompt_id"))
    )
    store.save(session_id, state)

    output: dict = {}
    if hold is not None:
        output["hookSpecificOutput"] = {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": hold.message(),
        }
    if state_warning:
        output["systemMessage"] = f"{NAME}: {state_warning}."
    return json.dumps(output) if output else ""


def _session_start(payload: dict, config: Config) -> str:
    """Reset router proof after compaction and note a missing shared policy once."""

    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise _FailOpen("the hook input has no session_id")
    store = StateStore(config.state_dir)
    state, state_warning = store.load(session_id)
    if payload.get("source") in {"compact", "clear"}:
        # The router must load again for the next task (spec R5), and turns
        # from before the boundary must not be folded back in.
        state.router_loaded = False
        state.last_turn = None

    output: dict = {}
    if not state.policy_notice_shown:
        state.policy_notice_shown = True
        cwd = Path(str(payload.get("cwd") or "."))
        if not shared_policy_loaded(cwd, config.home):
            output = {
                "systemMessage": f"{NAME}: {POLICY_NOTICE}",
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": POLICY_NOTICE,
                },
            }
    store.save(session_id, state)
    if state_warning:
        output["systemMessage"] = " ".join(
            filter(None, [output.get("systemMessage"), f"{NAME}: {state_warning}."])
        )
    return json.dumps(output) if output else ""


def _user_prompt_submit(payload: dict, config: Config) -> str:
    """Record the overrides the user typed; they apply to this prompt's turn only.

    Prompts Claude Code submits itself, such as task notifications, are not
    typed and never yield overrides. They continue the current turn, so the
    typed prompt's overrides also cover them.
    """

    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        raise _FailOpen("the hook input has no session_id")
    prompt = str(payload.get("prompt") or "")
    store = StateStore(config.state_dir)
    state, state_warning = store.load(session_id)
    if is_harness_prompt(prompt):
        found = {"phrases": []}
        if state.overrides and payload.get("prompt_id"):
            continued = state.overrides.setdefault("continued_prompt_ids", [])
            continued.append(payload["prompt_id"])
    else:
        found = parse_overrides(prompt)
        state.overrides = {"prompt_id": payload.get("prompt_id"), **found}
    store.save(session_id, state)

    notes = []
    if found["phrases"]:
        typed = ", ".join(f'"{phrase}"' for phrase in found["phrases"])
        notes.append(f"recorded your override for this prompt: {typed}")
    if state_warning:
        notes.append(state_warning)
    return json.dumps({"systemMessage": f"{NAME}: " + "; ".join(notes) + "."}) if notes else ""


def _overrides_for(state, prompt_id: object) -> dict:
    """Return stored overrides only when they belong to the prompt being handled."""

    stored = state.overrides or {}
    owned = {stored.get("prompt_id"), *stored.get("continued_prompt_ids", [])} - {None}
    if owned and prompt_id and prompt_id not in owned:
        return {}
    return stored


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
