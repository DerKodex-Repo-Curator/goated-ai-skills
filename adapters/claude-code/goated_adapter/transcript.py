"""Read the recent turns of a Claude Code transcript, newest part only.

A Claude Code transcript is JSONL. A *turn* starts at a typed user prompt, or
at a compaction boundary, and runs to the end of the file or to the next such
entry. This module is the only place that knows the transcript's entry shapes;
the rest of the adapter sees `Turn` objects.

The file can be large, so it is read backward from the end in blocks and only
as far back as needed. Claude Code writes it asynchronously, so a reader asked
to judge a tool call first waits briefly for that call's own `tool_use` entry.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from .markers import parse_reply

BLOCK_SIZE = 256 * 1024
MAX_BYTES = 64 * 1024 * 1024
MAX_TURNS = 50
POLL_SECONDS = 0.03

# Typed-looking user entries that Claude Code writes itself; they never open a
# turn. Interrupt markers end a turn, local-command entries wrap slash commands
# such as /model whose output is not a prompt, and task notifications carry a
# background task's result, which Claude Code submits as a prompt.
NOT_PROMPT_PREFIXES = (
    "[Request interrupted by user",
    "<local-command-stdout>",
    "<local-command-stderr>",
    "<local-command-caveat>",
    "<task-notification>",
)


def is_harness_prompt(text: str) -> bool:
    """True when prompt text was submitted by Claude Code itself, not typed."""

    return text.lstrip().startswith(NOT_PROMPT_PREFIXES)


class TranscriptUnreadable(Exception):
    """The transcript cannot be read well enough to judge the current call."""


class Turn:
    """What one turn contains that the adapter's gates care about.

    `loads` lists skills loaded successfully, in order; `route` is the winning
    route line; `skips` and `malformed` come from the turn's marker lines.
    """

    __slots__ = ("key", "is_compaction", "loads", "route", "skips", "malformed", "tool_use_ids")

    def __init__(self, key: str, is_compaction: bool = False) -> None:
        self.key = key
        self.is_compaction = is_compaction
        self.loads: list[str] = []
        self.route: dict | None = None
        self.skips: list[dict] = []
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
    Reading never crosses a compaction boundary.

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
        lines = _lines_backward(path)
        turns: list[Turn] = []
        pending: list[dict] = []
        for line in lines:
            try:
                entry = json.loads(line)
            except ValueError:
                # The last line may still be half-written; older bad lines are
                # skipped rather than trusted.
                continue
            if not isinstance(entry, dict):
                continue
            pending.append(entry)
            if not _opens_turn(entry):
                continue
            turn = _build_turn(list(reversed(pending)))
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
                turns.append(_build_turn(list(reversed(pending)), key="transcript-start"))
    except OSError as exc:
        raise TranscriptUnreadable(f"the transcript could not be read ({exc.strerror})")
    return list(reversed(turns))


def _lines_backward(path: Path):
    """Yield complete lines from the end of the file toward the start."""

    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        position = handle.tell()
        scanned = 0
        tail = b""
        while position > 0:
            size = min(BLOCK_SIZE, position)
            position -= size
            handle.seek(position)
            block = handle.read(size) + tail
            scanned += size
            if scanned > MAX_BYTES:
                raise TranscriptUnreadable(
                    "the current turn is too far back in the transcript to read quickly"
                )
            parts = block.split(b"\n")
            tail = parts[0]
            for part in reversed(parts[1:]):
                if part.strip():
                    yield part.decode("utf-8", errors="replace")
        if tail.strip():
            yield tail.decode("utf-8", errors="replace")


def _opens_turn(entry: dict) -> bool:
    if entry.get("type") == "system" and entry.get("subtype") == "compact_boundary":
        return True
    if entry.get("type") != "user":
        return False
    if entry.get("isSidechain") or entry.get("isMeta") or entry.get("isCompactSummary"):
        return False
    if (entry.get("origin") or {}).get("kind") == "task-notification":
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return False
        text = " ".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    else:
        return False
    return not is_harness_prompt(text)


def _build_turn(entries: list[dict], key: str | None = None) -> Turn:
    """Summarize one turn's entries, given oldest first, opener included."""

    opener = entries[0] if entries and _opens_turn(entries[0]) else None
    turn = Turn(
        key=key or str((opener or {}).get("uuid") or "transcript-start"),
        is_compaction=bool(opener and opener.get("type") == "system"),
    )
    skill_calls: dict[str, str] = {}
    for entry in entries:
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
                    turn.skips.extend(markers.skips)
                    turn.malformed.extend(markers.malformed)
                elif block.get("type") == "tool_use":
                    tool_id = str(block.get("id", ""))
                    turn.tool_use_ids.add(tool_id)
                    if block.get("name") == "Skill":
                        skill = _skill_name((block.get("input") or {}).get("skill"))
                        if skill:
                            skill_calls[tool_id] = skill
        elif entry.get("type") == "user":
            for block in content:
                if (
                    isinstance(block, dict)
                    and block.get("type") == "tool_result"
                    and block.get("tool_use_id") in skill_calls
                    and not block.get("is_error")
                ):
                    turn.loads.append(skill_calls.pop(block["tool_use_id"]))
    return turn


def _skill_name(value: object) -> str:
    """Normalize a Skill-tool argument such as `/tdd` or `plugin:tdd` to `tdd`."""

    if not isinstance(value, str):
        return ""
    words = value.strip().lstrip("/").split()
    return words[0].rsplit(":", 1)[-1] if words else ""
