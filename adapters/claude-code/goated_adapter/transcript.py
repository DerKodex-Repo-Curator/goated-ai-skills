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

from .markers import parse_reply

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
# Requests written by another session or the app: they start a turn, but nobody
# typed them here, so they never carry overrides.
MACHINE_PREFIXES = (
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


def prompt_text_kind(text: str) -> str:
    """Classify prompt text alone: typed, machine, continuation, or not-prompt.

    Hooks that see only the prompt text use this; the transcript reader also
    uses the entry's structured fields, which are more reliable.
    """

    body = REMINDER_RE.sub("", text, count=1)
    if body.startswith(NOT_PROMPT_PREFIXES):
        return NOT_PROMPT
    if body.startswith(CONTINUATION_PREFIXES):
        return CONTINUATION
    if body.startswith(MACHINE_PREFIXES):
        return MACHINE
    return TYPED


class TranscriptUnreadable(Exception):
    """The transcript cannot be read well enough to judge the current call."""


class Turn:
    """What one turn contains that the adapter's gates care about.

    `typed` says a person typed the prompt that opened the turn, so it may
    carry overrides; `prompt_id` is that prompt's id. `loads` lists raw names
    of skills loaded successfully, in order. `task_loads` lists the loads that
    count for a task the turn starts: skills the prompt itself invoked as
    `/<skill>`, plus loads after the winning route line. `route` is the
    winning route line and `malformed` the route-like lines that failed the
    grammar.
    """

    __slots__ = (
        "key", "is_compaction", "typed", "prompt_id", "loads", "task_loads",
        "route", "malformed", "tool_use_ids",
    )

    def __init__(self, key: str) -> None:
        self.key = key
        self.is_compaction = False
        self.typed = False
        self.prompt_id: str | None = None
        self.loads: list[str] = []
        self.task_loads: list[str] = []
        self.route: dict | None = None
        self.malformed: list[str] = []
        self.tool_use_ids: set[str] = set()


def read_recent_turns(
    path: str | os.PathLike,
    *,
    since_key: str | None,
    tool_use_id: str | None,
    wait_seconds: float,
) -> list[Turn]:
    """Return recent turns, oldest first, ending with the current turn.

    Turns are collected back to and including the turn keyed `since_key`, the
    last turn the caller has already seen, so that anything written after the
    caller last looked is included. Without `since_key`, or when it is not
    found within the read limits, only the turns read so far are returned.
    Reading never crosses a compaction boundary. It raises
    `TranscriptUnreadable` only when the current turn itself cannot be read.

    When `tool_use_id` is given, the current turn must contain that tool call;
    the reader re-reads for up to `wait_seconds` while the transcript catches
    up, then raises `TranscriptUnreadable`.
    """

    deadline = time.monotonic() + max(wait_seconds, 0.0)
    while True:
        turns = _read_turns_once(Path(path), since_key)
        if tool_use_id is None or tool_use_id in turns[-1].tool_use_ids:
            return turns
        if time.monotonic() >= deadline:
            raise TranscriptUnreadable(
                "the transcript does not yet show the current tool call"
            )
        time.sleep(POLL_SECONDS)


def _read_turns_once(path: Path, since_key: str | None) -> list[Turn]:
    try:
        turns: list[Turn] = []
        pending: list[dict] = []
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
            pending.append(entry)
            kind = _opener_kind(entry)
            if kind not in (TYPED, MACHINE, "compaction"):
                continue
            turn = _build_turn(list(reversed(pending)), kind)
            turns.append(turn)
            pending = []
            if (
                turn.is_compaction
                or since_key is None
                or turn.key == since_key
                or len(turns) >= MAX_TURNS
            ):
                break
        else:
            # Reached the start of the file: entries before the first prompt
            # (session-start attachments, or a transcript with no prompt yet)
            # form a turn of their own.
            if pending or not turns:
                turns.append(_build_turn(list(reversed(pending)), None))
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


def _opener_kind(entry: dict) -> str | None:
    """Return how an entry relates to turns: an opener kind, or None."""

    if entry.get("type") == "system" and entry.get("subtype") == "compact_boundary":
        return "compaction"
    if entry.get("type") != "user":
        return None
    if entry.get("isSidechain") or entry.get("isMeta") or entry.get("isCompactSummary"):
        return None
    text = _prompt_text(entry)
    if text is None:
        return None
    by_text = prompt_text_kind(text)
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
        # Seen: `host_synthetic` (desktop-app prompts) and `peer` (another
        # session). Any origin other than a person or the SDK caller is not typed.
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


def _build_turn(entries: list[dict], kind: str | None) -> Turn:
    """Summarize one turn's entries, given oldest first, opener included."""

    opener = entries[0] if kind else None
    turn = Turn(key=str((opener or {}).get("uuid") or "transcript-start"))
    turn.is_compaction = kind == "compaction"
    turn.typed = kind == TYPED
    if opener is not None and opener.get("promptId"):
        turn.prompt_id = str(opener["promptId"])
    invoked = None
    if opener is not None and kind in (TYPED, MACHINE):
        match = COMMAND_NAME_RE.search(_prompt_text(opener) or "")
        invoked = match.group(1) if match else None

    skill_calls: dict[str, str] = {}
    for entry in entries[1:] if opener is not None else entries:
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list) or entry.get("isSidechain"):
            continue
        if entry.get("type") == "assistant":
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    markers = parse_reply(str(block.get("text", "")))
                    if markers.route is not None:
                        turn.route = markers.route
                        turn.task_loads = [s for s in turn.loads if s == invoked][:1]
                    turn.malformed.extend(markers.malformed)
                elif block.get("type") == "tool_use":
                    tool_id = str(block.get("id", ""))
                    turn.tool_use_ids.add(tool_id)
                    if block.get("name") == "Skill":
                        skill = _skill_name((block.get("input") or {}).get("skill"))
                        if skill:
                            skill_calls[tool_id] = skill
        elif entry.get("type") == "user":
            if invoked and entry.get("isMeta") and _starts_skill_body(content):
                # The prompt invoked a skill as `/<skill>`; Claude Code adds
                # its body as a meta entry, which proves the load.
                turn.loads.append(invoked)
                turn.task_loads.append(invoked)
                continue
            for block in content:
                if (
                    isinstance(block, dict)
                    and block.get("type") == "tool_result"
                    and block.get("tool_use_id") in skill_calls
                    and not block.get("is_error")
                ):
                    skill = skill_calls.pop(block["tool_use_id"])
                    turn.loads.append(skill)
                    turn.task_loads.append(skill)
    return turn


def _starts_skill_body(content: list) -> bool:
    first = content[0] if content else None
    return isinstance(first, dict) and str(first.get("text", "")).startswith(SKILL_BODY_PREFIX)


def _skill_name(value: object) -> str:
    """Normalize a Skill-tool argument such as `/tdd args` to `tdd`, keeping any
    `namespace:` prefix for the gates to judge."""

    if not isinstance(value, str):
        return ""
    words = value.strip().lstrip("/").split()
    return words[0] if words else ""
