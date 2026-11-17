"""Read the recent turns of a Claude Code transcript, newest part only.

A Claude Code transcript is JSONL. A *turn* starts at a user prompt, or at a
compaction boundary, and runs to the end of the file or to the next such
entry. This module is the only place that knows the transcript's entry shapes
and which prompts a person typed; the rest of the adapter sees `Turn` objects.

The file can be large, so it is read backward from the end in blocks and only
as far back as needed. Claude Code writes it asynchronously, so a reader asked
to judge a tool call first waits briefly for that call's own `tool_use` entry.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import NamedTuple

from .markers import ReplyMarkers, parse_reply

BLOCK_SIZE = 256 * 1024
MAX_BYTES = 64 * 1024 * 1024
MAX_TURNS = 50
POLL_SECONDS = 0.03

# How Claude Code marks prompts it submits itself, by text prefix after any
# leading <system-reminder> blocks. Seen in desktop-app and `claude -p`
# transcripts (2.1.3xx).
#
# Never prompts: interrupt markers, wrappers around local slash-command and
# `!` shell input and output.
NOT_PROMPT_PREFIXES = (
    "[Request interrupted by user",
    "<local-command-stdout>",
    "<local-command-stderr>",
    "<local-command-caveat>",
    "<bash-input>",
    "<bash-stdout>",
    "<bash-stderr>",
)
# Results of background work: they continue the current turn.
CONTINUATION_PREFIXES = ("<task-notification>", "<side-sessions-event>")
# Requests written by another agent, another session, or the app: they start a
# turn, but nobody typed them here, so they never carry overrides. Claude Code
# 2.1.3xx opens a subagent's hand-back and another session's message alike with
# the first line below, then an `<agent-message>` or `<cross-session-message>`
# tag; the hook input carries no field saying where a prompt came from, so the
# first line is the prompt hook's only sign. The bare tags count too, in case
# a prompt arrives without that line.
MACHINE_PREFIXES = (
    "Another Claude session sent a message:",
    "<agent-message",
    "<cross-session-message",
    "Background (from the session that started this one)",
    "Task (from the session that started this one)",
)

TYPED = "typed"
MACHINE = "machine"
CONTINUATION = "continuation"
NOT_PROMPT = "not-prompt"

REMINDER_RE = re.compile(r"\A\s*(?:<system-reminder>.*?</system-reminder>\s*)+", re.DOTALL)
COMMAND_NAME_RE = re.compile(r"<command-name>/([^<\s]+)</command-name>")
SKILL_BODY_PREFIX = "Base directory for this skill:"
# A call this adapter held: Claude Code 2.1.3xx records the deny reason as
# `PreToolUse:<tool> hook error: <reason>`, and the reason opens with the hold line.
HOLD_RESULT_RE = re.compile(r"(?:PreToolUse:\S+ hook error: )?goated-hold: ")
# The one input field of each built-in tool that may carry route and skip
# lines: a field that describes the call rather than holds its payload. Other
# tools, MCP tools included, carry none, since their `description` is often
# the payload, such as an issue or merge-request body. The skill-usage mod
# keeps the same table (`LINE_FIELDS` in its `hooks/classify.ts`).
LINE_FIELDS = {
    "Bash": "description",
    "PowerShell": "description",
    "Agent": "description",
    "Task": "description",
    "Skill": "args",
}


def call_line_text(tool_name: str, tool_input: dict) -> str:
    """The text of a tool call that may carry route and skip lines, or "".

    Claude Code can save a message's reply text as a summary that drops the
    lines, but it keeps a call's input as written. Only the field
    `LINE_FIELDS` names for the tool counts, so file text, edit text,
    commands, and tool payloads never carry a line.
    """

    value = tool_input.get(LINE_FIELDS.get(tool_name, ""))
    return value if isinstance(value, str) else ""


def prompt_text_kind(text: str) -> str:
    """Classify prompt text alone: typed, machine, continuation, or not-prompt.

    Hooks that see only the prompt text use this; the transcript reader also
    uses the entry's structured fields, which are more reliable.
    """

    body = REMINDER_RE.sub("", text, count=1).lstrip()
    if body.startswith(NOT_PROMPT_PREFIXES):
        return NOT_PROMPT
    if body.startswith(CONTINUATION_PREFIXES):
        return CONTINUATION
    if body.startswith(MACHINE_PREFIXES):
        return MACHINE
    return TYPED


class TranscriptUnreadable(Exception):
    """The transcript cannot be read well enough to judge the current call."""


class Call:
    """A tool call that has finished in the turn: its name, input, and outcome.

    `ok` is False when the tool result was an error, which includes a call a
    hook held; `held` is True only when this adapter held it, so it never ran.
    `agent_id` is the subagent a spawn started, from the result's
    `toolUseResult.agentId`, else None. `output` is the result's text, and
    `tool_id` the call's `tool_use_id`, "" when the transcript gives none.
    """

    __slots__ = ("name", "input", "ok", "held", "agent_id", "output", "tool_id")

    def __init__(
        self,
        name: str,
        tool_input: dict,
        ok: bool,
        agent_id: str | None = None,
        held: bool = False,
        output: str = "",
        tool_id: str = "",
    ) -> None:
        self.name = name
        self.input = tool_input
        self.ok = ok
        self.held = held
        self.agent_id = agent_id
        self.output = output
        self.tool_id = tool_id


class RouteMark(NamedTuple):
    """A valid route line and where it fell in its turn: how many loads and
    finished calls the turn held when it was written."""

    route: dict
    loads_before: int
    calls_before: int


class Turn:
    """What one turn contains that the adapter's gates care about.

    `typed` says a person typed the prompt that opened the turn, so it may
    carry overrides; `prompt_id` is that prompt's id. `loads` lists raw names
    of skills loaded successfully, in order, and `invoked_load` is the skill
    the prompt itself invoked as `/<skill>`, once its body loaded. `route` is
    the winning route line, `route_marks` every valid route line in order, and
    `malformed` the route-like lines that failed the grammar. `skips` are the
    valid `goated-skip` lines, `design_reads` the valid `goated-design-reads`
    lines and `malformed_design_reads` those that failed the grammar, and
    `texts` the turn's reply texts, in order. Lines count from reply text and
    from the field `call_line_text` reads, once per call id in `call_ids`. `calls` are the tool calls that finished in this
    turn, oldest first, and `unfinished` the `(name, input)` of recorded calls
    with no result yet, oldest first. `opens_transcript` is set on the oldest
    turn read when reading reached the start of the transcript, so no earlier
    turn exists.
    """

    __slots__ = (
        "key", "is_compaction", "typed", "prompt_id", "loads", "invoked_load",
        "route", "route_marks", "malformed", "skips", "calls", "prompt_ids",
        "opens_transcript", "design_reads", "malformed_design_reads", "call_ids",
        "unfinished", "texts",
    )

    def __init__(self, key: str) -> None:
        self.key = key
        self.is_compaction = False
        self.typed = False
        self.prompt_id: str | None = None
        self.loads: list[str] = []
        self.invoked_load: str | None = None
        self.route: dict | None = None
        self.route_marks: list[RouteMark] = []
        self.opens_transcript = False
        self.malformed: list[str] = []
        self.skips: list[dict] = []
        self.design_reads: list[dict] = []
        self.malformed_design_reads: list[str] = []
        self.calls: list[Call] = []
        self.prompt_ids: set[str] = set()
        self.call_ids: set[str] = set()
        self.unfinished: list[tuple[str, dict]] = []
        self.texts: list[str] = []

    def add_markers(self, markers: ReplyMarkers) -> None:
        """Count the marker lines of one reply text or one tool call, in order."""

        if markers.route is not None:
            self.route = markers.route
            self.route_marks.append(RouteMark(markers.route, len(self.loads), len(self.calls)))
        self.malformed.extend(markers.malformed)
        self.skips.extend(markers.skips)
        self.design_reads.extend(markers.design_reads)
        self.malformed_design_reads.extend(markers.malformed_design_reads)

    def add_call(self, tool_id: str, tool_name: str, tool_input: dict) -> None:
        """Count the marker lines a tool call carries, once per call id.

        A line in a call counts from that call on, so it covers the call itself.
        A call with no id is taken to be the newest unfinished recorded call
        when its name and input match that call's, so it is not counted twice.
        """

        if tool_id:
            if tool_id in self.call_ids:
                return
            self.call_ids.add(tool_id)
        elif self.unfinished[-1:] == [(tool_name, tool_input)]:
            return
        self.add_markers(parse_reply(call_line_text(tool_name, tool_input)))


def read_recent_turns(
    path: str | os.PathLike,
    *,
    since_key: str | None,
    prompt_id: str | None = None,
    wait_seconds: float = 0.0,
    sidechain: bool = False,
    current_call: tuple[str, str, dict] | None = None,
) -> list[Turn]:
    """Return recent turns, oldest first, ending with the current turn.

    Turns are collected back to and including the turn keyed `since_key`, the
    last turn the caller has already seen, so that anything written after the
    caller last looked is included. Without `since_key`, or when it is not
    found within the read limits, only the turns read so far are returned.
    Without `since_key`, reading goes on past the current turn only far enough
    to tell whether an earlier turn exists (see `Turn.opens_transcript`).
    Reading never crosses a compaction boundary. It raises
    `TranscriptUnreadable` only when the current turn itself cannot be read.

    When `prompt_id` is given, the current turn must hold an entry of that
    prompt: the reader re-reads for up to `wait_seconds` while the transcript
    catches up, then raises `TranscriptUnreadable`. It never waits for the
    call being judged. In an interactive session Claude Code records the
    assistant message holding that call, with any text and sibling calls in
    it, only after PreToolUse returns, so callers take the call from the hook
    input instead. `current_call` is that call, as `(tool_use_id, tool_name,
    tool_input)`: the route and skip lines it carries count in the current
    turn, once even if the transcript already shows it.

    `sidechain` reads a subagent's own transcript, where every entry is a
    sidechain entry and every prompt was written by the parent agent, so none
    is typed.
    """

    deadline = time.monotonic() + max(wait_seconds, 0.0)
    while True:
        turns = _read_turns_once(Path(path), since_key, sidechain)
        current = turns[-1]
        if prompt_id is None or current.is_compaction or prompt_id in current.prompt_ids:
            if current_call is not None:
                current.add_call(*current_call)
            return turns
        if time.monotonic() >= deadline:
            raise TranscriptUnreadable(
                "the transcript does not yet show the prompt this call belongs to"
            )
        time.sleep(POLL_SECONDS)


def _read_turns_once(path: Path, since_key: str | None, sidechain: bool) -> list[Turn]:
    try:
        turns: list[Turn] = []
        pending: list[dict] = []
        # Set once the current turn is read without `since_key`: the reader
        # then only looks for an earlier turn's opener, collecting nothing.
        probing = False
        for line in _lines_backward(path):
            if line is None:
                # Read limit reached. Older unseen turns are given up, as if
                # `since_key` were not found; the current turn must be whole.
                if not turns:
                    raise TranscriptUnreadable(
                        "the current turn is too large to read quickly"
                    )
                break
            try:
                entry = json.loads(line)
            except ValueError:
                # The last line may still be half-written; older bad lines are
                # skipped rather than trusted.
                continue
            if not isinstance(entry, dict):
                continue
            kind = _opener_kind(entry, sidechain)
            is_opener = kind in (TYPED, MACHINE, "compaction")
            if probing:
                if is_opener:
                    break  # An earlier turn exists.
                continue
            pending.append(entry)
            if not is_opener:
                continue
            turn = _build_turn(list(reversed(pending)), kind, sidechain)
            turns.append(turn)
            pending = []
            if turn.is_compaction or turn.key == since_key or len(turns) >= MAX_TURNS:
                break
            if since_key is None:
                probing = True
        else:
            # Reached the start of the file. Without `since_key`, entries before
            # the first prompt are session-start attachments and are dropped;
            # otherwise they (or a transcript with no prompt yet) form a turn of
            # their own.
            if not probing and (pending or not turns):
                turns.append(_build_turn(list(reversed(pending)), None, sidechain))
            turns[-1].opens_transcript = True
    except OSError as exc:
        raise TranscriptUnreadable(f"the transcript could not be read ({exc.strerror})")
    return list(reversed(turns))


def _lines_backward(path: Path):
    """Yield complete lines from the end of the file toward the start.

    Yields None once `MAX_BYTES` have been read, then stops.
    """

    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        position = handle.tell()
        scanned = 0
        tail = b""
        while position > 0:
            if scanned >= MAX_BYTES:
                yield None
                return
            size = min(BLOCK_SIZE, position)
            position -= size
            handle.seek(position)
            block = handle.read(size) + tail
            scanned += size
            parts = block.split(b"\n")
            tail = parts[0]
            for part in reversed(parts[1:]):
                if part.strip():
                    yield part.decode("utf-8", errors="replace")
        if tail.strip():
            yield tail.decode("utf-8", errors="replace")


def _opener_kind(entry: dict, sidechain: bool = False) -> str | None:
    """Return how an entry relates to turns: an opener kind, or None."""

    if entry.get("type") == "system" and entry.get("subtype") == "compact_boundary":
        return "compaction"
    if entry.get("type") != "user":
        return None
    if entry.get("isCompactSummary"):
        return None
    if bool(entry.get("isSidechain")) != sidechain:
        return None
    if (entry.get("origin") or {}).get("kind") == "peer" or entry.get("turnOrigin") == "peer":
        # A subagent's hand-back or another session's message. Claude Code
        # records it `isMeta` but starts a new turn with it, as the adapter
        # does: whatever its text says, nobody typed it here.
        return MACHINE
    if entry.get("isMeta"):
        return None
    text = _prompt_text(entry)
    if text is None:
        return None
    by_text = prompt_text_kind(text)
    if sidechain:
        # The parent agent wrote every prompt a subagent receives.
        return MACHINE if by_text in (TYPED, MACHINE) else by_text
    if by_text in (NOT_PROMPT, CONTINUATION):
        return by_text
    origin = (entry.get("origin") or {}).get("kind")
    turn_origin = entry.get("turnOrigin")
    if origin == "task-notification" or turn_origin == "task_notification":
        return CONTINUATION
    if origin is not None:
        # The desktop app marks typed prompts `human`; any other origin is the
        # app or a scheduler acting, so it opens a turn but is not typed.
        return TYPED if origin == "human" and by_text == TYPED else MACHINE
    if turn_origin not in (None, "human", "sdk"):
        # Seen: `host_synthetic` (desktop-app prompts). Any origin other than a
        # person or the SDK caller is not typed.
        return MACHINE
    return by_text


def _prompt_text(entry: dict) -> str | None:
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        return " ".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    return None


def _build_turn(entries: list[dict], kind: str | None, sidechain: bool = False) -> Turn:
    """Summarize one turn's entries, given oldest first, opener included."""

    opener = entries[0] if kind else None
    turn = Turn(key=str((opener or {}).get("uuid") or "transcript-start"))
    turn.is_compaction = kind == "compaction"
    turn.typed = kind == TYPED
    if opener is not None and opener.get("promptId"):
        turn.prompt_id = str(opener["promptId"])
    # Every prompt the turn holds, including background results that continue
    # it; Claude Code marks user entries only.
    turn.prompt_ids = {
        str(e["promptId"]) for e in entries if e.get("type") == "user" and e.get("promptId")
    }
    invoked = None
    if opener is not None and kind in (TYPED, MACHINE):
        match = COMMAND_NAME_RE.search(_prompt_text(opener) or "")
        invoked = match.group(1) if match else None

    skill_calls: dict[str, str] = {}
    pending: dict[str, tuple[str, dict]] = {}
    for entry in entries[1:] if opener is not None else entries:
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list) or bool(entry.get("isSidechain")) != sidechain:
            continue
        if entry.get("type") == "assistant":
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    text = str(block.get("text", ""))
                    turn.texts.append(text)
                    turn.add_markers(parse_reply(text))
                elif block.get("type") == "tool_use":
                    tool_id = str(block.get("id", ""))
                    tool_input = block.get("input")
                    pending[tool_id] = (
                        str(block.get("name", "")),
                        tool_input if isinstance(tool_input, dict) else {},
                    )
                    turn.add_call(tool_id, *pending[tool_id])
                    if block.get("name") == "Skill":
                        skill = skill_name((block.get("input") or {}).get("skill"))
                        if skill:
                            skill_calls[tool_id] = skill
        elif entry.get("type") == "user":
            if invoked and entry.get("isMeta") and _starts_skill_body(content):
                # The prompt invoked a skill as `/<skill>`; Claude Code adds
                # its body as a meta entry, which proves the load.
                turn.loads.append(invoked)
                turn.invoked_load = invoked
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                finished_id = str(block.get("tool_use_id", ""))
                finished = pending.pop(finished_id, None)
                if finished is not None:
                    result = entry.get("toolUseResult")
                    agent = result.get("agentId") if isinstance(result, dict) else None
                    text = _result_text(block)
                    turn.calls.append(Call(
                        *finished,
                        ok=not block.get("is_error"),
                        agent_id=agent if isinstance(agent, str) else None,
                        held=bool(block.get("is_error")) and bool(HOLD_RESULT_RE.match(text)),
                        output=text,
                        tool_id=finished_id,
                    ))
                if (
                    block.get("tool_use_id") in skill_calls
                    and not block.get("is_error")
                ):
                    skill = skill_calls.pop(block["tool_use_id"])
                    turn.loads.append(skill)
    turn.unfinished = list(pending.values())
    return turn


def _starts_skill_body(content: list) -> bool:
    first = content[0] if content else None
    return isinstance(first, dict) and str(first.get("text", "")).startswith(SKILL_BODY_PREFIX)


def _result_text(block: dict) -> str:
    """A tool result's text, whether recorded as a string or as text blocks."""

    content = block.get("content")
    if isinstance(content, list):
        return "".join(
            str(part.get("text", "")) for part in content if isinstance(part, dict)
        )
    return str(content or "")


def skill_name(value: object) -> str:
    """Normalize a Skill-tool argument such as `/tdd args` to `tdd`, keeping any
    `namespace:` prefix for the gates to judge."""

    if not isinstance(value, str):
        return ""
    words = value.strip().lstrip("/").split()
    return words[0] if words else ""
