"""Per-session adapter state, one small JSON file per Claude Code session.

State holds only what the transcript's current turn cannot answer on its own:
the current task and its proof, whether missing or reset state lost the task,
whether the router loaded since the last compaction, which design references
were read since it, the last turn seen, and the latest user overrides. Beside
it, a marker names the turn whose hold gave the unseen-line advice in full. Apart from the short override phrases a user typed,
it holds no prompt or reply text.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9_-]")
REPLACE_ATTEMPTS = 5
REPLACE_RETRY_SECONDS = 0.02
# Beside the state files: one empty file per session, named for the turn that
# claimed it.
TURN_MARKERS_DIR = "turn-markers"


class Task:
    """The current task: its route and the GOATED skills loaded for it so far."""

    __slots__ = ("route", "started_turn", "loads")

    def __init__(self, route: dict, started_turn: str, loads=None) -> None:
        self.route = route
        self.started_turn = started_turn
        self.loads: list[str] = list(loads or [])

    def to_json(self) -> dict:
        return {"route": self.route, "started_turn": self.started_turn, "loads": self.loads}


class SessionState:
    """Everything the adapter remembers about one session between hook calls."""

    __slots__ = (
        "router_loaded", "last_turn", "task", "task_unknown", "overrides", "policy_notice_shown",
        "reference_reads", "design_edits", "brief_routed",
    )

    def __init__(self) -> None:
        self.router_loaded = False
        # True while the route came from the brief that opened the session and
        # no prompt a person typed has opened a turn since: router-first is met.
        self.brief_routed = False
        self.last_turn: str | None = None
        self.task: Task | None = None
        # True when saved state was missing or unreadable: the session may have
        # had a task, so `continue` cannot start one until a full route line
        # does, or the session is shown to have none.
        self.task_unknown = False
        self.overrides: dict = {}
        self.policy_notice_shown = False
        # The design references (`errors.md`) read since the last compaction.
        self.reference_reads: list[str] = []
        # The design references each edit of one turn required when the
        # design gates judged it: {"turn": <turn key>, "edits": {<tool_use_id>: [<file>]}}.
        self.design_edits: dict = {}

    def record_design_edit(self, turn: str, tool_use_id: str, references: list[str]) -> None:
        """Keep what an edit the design gates let through required, for the
        turn's closeout; an earlier turn's edits are dropped."""

        if self.design_edits.get("turn") != turn:
            self.design_edits = {"turn": turn, "edits": {}}
        self.design_edits["edits"][tool_use_id] = list(references)

    def design_edits_of(self, turn: str) -> dict[str, list[str]]:
        """What `record_design_edit` kept for `turn`'s edits, by tool_use_id."""

        return dict(self.design_edits["edits"]) if self.design_edits.get("turn") == turn else {}

    def to_json(self) -> dict:
        return {
            "router_loaded": self.router_loaded,
            "brief_routed": self.brief_routed,
            "last_turn": self.last_turn,
            "task": self.task.to_json() if self.task else None,
            "task_unknown": self.task_unknown,
            "overrides": self.overrides,
            "policy_notice_shown": self.policy_notice_shown,
            "reference_reads": self.reference_reads,
            "design_edits": self.design_edits,
        }

    @classmethod
    def from_json(cls, data: object) -> "SessionState":
        """Rebuild state from `to_json` output; raise ValueError on any other shape."""

        if not isinstance(data, dict):
            raise ValueError("state is not an object")
        state = cls()
        state.router_loaded = _expect(data.get("router_loaded", False), bool)
        state.brief_routed = _expect(data.get("brief_routed", False), bool)
        state.policy_notice_shown = _expect(data.get("policy_notice_shown", False), bool)
        state.last_turn = _expect(data.get("last_turn"), (str, type(None)))
        state.task_unknown = _expect(data.get("task_unknown", False), bool)
        state.reference_reads = _string_list(data.get("reference_reads", []))
        design_edits = _expect(data.get("design_edits", {}), dict)
        if design_edits:
            edits = _expect(design_edits.get("edits"), dict)
            state.design_edits = {
                "turn": _expect(design_edits.get("turn"), str),
                "edits": {_expect(k, str): _string_list(v) for k, v in edits.items()},
            }
        task = _expect(data.get("task"), (dict, type(None)))
        if task is not None:
            state.task = Task(
                route=_valid_route(task.get("route")),
                started_turn=_expect(task.get("started_turn"), str),
                loads=_string_list(task.get("loads", [])),
            )
        overrides = _expect(data.get("overrides", {}), dict)
        if overrides:
            state.overrides = {
                "prompt_id": _expect(overrides.get("prompt_id"), (str, type(None))),
                "routing": _expect(overrides.get("routing", False), bool),
                "skills": _string_list(overrides.get("skills", [])),
                "commit_message": _expect(overrides.get("commit_message"), (str, type(None))),
                "phrases": _string_list(overrides.get("phrases", [])),
            }
        return state


def _expect(value, kinds):
    if not isinstance(value, kinds):
        raise ValueError(f"unexpected state value {type(value).__name__}")
    return value


def _string_list(value) -> list:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("expected a list of strings")
    return list(value)


def _valid_route(route) -> dict:
    """A task's route is `direct`, a `requires:` route, or `continue` when that
    started the session's first task, with no required skills."""

    route = _expect(route, dict)
    if route.get("form") in ("direct", "continue"):
        return {"form": route["form"]}
    if route.get("form") == "route":
        requires = _string_list(route.get("requires"))
        if requires:
            return {
                "form": "route",
                "intensity": _expect(route.get("intensity"), str),
                "requires": requires,
            }
    raise ValueError("unexpected task route")


class StateUnsafe(Exception):
    """The state folder could be written by another user, so it cannot be trusted."""


class StateStore:
    """Loads and saves `SessionState` under one directory, keyed by session.

    The store only uses a directory it owns and that nobody else can write;
    otherwise it raises `StateUnsafe`, because planted state could make holds
    pass.
    """

    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)

    def load(self, session_id: str) -> tuple[SessionState, str | None]:
        """Return the session's state and a warning when stored state was unusable.

        A missing file starts fresh quietly; an unreadable or corrupt one
        starts fresh and says so. Either way the fresh state marks the task
        unknown, because the session may already have had one, so `continue`
        cannot start a task until a session start or a read of the whole
        transcript shows there is none. A fresh start can only re-hold, never
        pass.
        """

        self._ensure_private_directory()
        path = self._path(session_id)
        fresh = SessionState()
        fresh.task_unknown = True
        if not path.exists():
            return fresh, None
        try:
            return SessionState.from_json(json.loads(path.read_text(encoding="utf-8"))), None
        except (OSError, ValueError):
            return fresh, "its saved session state was unreadable and was reset"

    def save(self, session_id: str, state: SessionState) -> None:
        """Write state atomically so a concurrent hook never reads half a file."""

        self._ensure_private_directory()
        path = self._path(session_id)
        # Unique per process, created exclusively and never through a link.
        # `tempfile` is avoided because importing it costs every hook call
        # several milliseconds.
        temp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        temp.unlink(missing_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            with os.fdopen(os.open(temp, flags, 0o600), "w", encoding="utf-8") as stream:
                json.dump(state.to_json(), stream)
            _replace(temp, path)
        except BaseException:
            temp.unlink(missing_ok=True)
            raise

    def claim_turn(self, session_id: str, turn_key: str) -> bool:
        """Claim the session's marker for `turn_key`; True for the first claim.

        The claim is one exclusive file create, so of several hooks claiming
        at once exactly one gets True. A successful claim drops the session's
        markers of earlier turns. Raises OSError, or StateUnsafe, when the
        marker cannot be made or read.
        """

        folder = self.directory / TURN_MARKERS_DIR
        self._ensure_private_directory(folder)
        prefix = f"{_safe_name(session_id)}."
        marker = folder / f"{prefix}{_safe_name(turn_key)}"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            os.close(os.open(marker, flags, 0o600))
        except FileExistsError:
            return False
        self._drop_markers(folder, prefix, keep=marker.name)
        return True

    def clear_turn_markers(self, session_id: str) -> None:
        """Drop the session's turn marker, best effort, as its state is reset."""

        folder = self.directory / TURN_MARKERS_DIR
        if folder.is_dir():
            self._drop_markers(folder, f"{_safe_name(session_id)}.")

    @staticmethod
    def _drop_markers(folder: Path, prefix: str, keep: str | None = None) -> None:
        # Safe names hold no "." or glob character, so the prefix matches only
        # this session's markers.
        for old in folder.glob(f"{prefix}*"):
            if old.name != keep:
                try:
                    old.unlink(missing_ok=True)
                except OSError:
                    pass  # A stale marker only names an old turn; the next claim retries.

    def _ensure_private_directory(self, directory: Path | None = None) -> None:
        directory = directory or self.directory
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name == "nt":
            return  # The Windows default, the per-user temp folder, is private.
        info = directory.lstat()
        if directory.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise StateUnsafe(
                f"its state folder {directory} is not private to this user"
            )

    def _path(self, session_id: str) -> Path:
        return self.directory / f"{_safe_name(session_id)}.json"


def _safe_name(raw: str) -> str:
    return UNSAFE_NAME_CHARS.sub("_", raw)[:128] or "unknown"


def _replace(source: Path, target: Path) -> None:
    """`os.replace`, retried briefly: on Windows it fails while another hook
    process has the target open for reading."""

    for attempt in range(REPLACE_ATTEMPTS):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(REPLACE_RETRY_SECONDS)
