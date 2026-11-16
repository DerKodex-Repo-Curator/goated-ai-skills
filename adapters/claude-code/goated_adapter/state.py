"""Per-session adapter state, one small JSON file per Claude Code session.

State holds only what the transcript's current turn cannot answer on its own:
the current task and its proof, whether the router loaded since the last
compaction, the last turn seen, and the latest user overrides. Apart from the
short override phrases a user typed, it holds no prompt or reply text.
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

    __slots__ = ("router_loaded", "last_turn", "task", "overrides", "policy_notice_shown")

    def __init__(self) -> None:
        self.router_loaded = False
        self.last_turn: str | None = None
        self.task: Task | None = None
        self.overrides: dict = {}
        self.policy_notice_shown = False

    def to_json(self) -> dict:
        return {
            "router_loaded": self.router_loaded,
            "last_turn": self.last_turn,
            "task": self.task.to_json() if self.task else None,
            "overrides": self.overrides,
            "policy_notice_shown": self.policy_notice_shown,
        }

    @classmethod
    def from_json(cls, data: object) -> "SessionState":
        """Rebuild state from `to_json` output; raise ValueError on any other shape."""

        if not isinstance(data, dict):
            raise ValueError("state is not an object")
        state = cls()
        state.router_loaded = _expect(data.get("router_loaded", False), bool)
        state.policy_notice_shown = _expect(data.get("policy_notice_shown", False), bool)
        state.last_turn = _expect(data.get("last_turn"), (str, type(None)))
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
    """A task's route is `direct` or a `requires:` route; `continue` never starts one."""

    route = _expect(route, dict)
    if route.get("form") == "direct":
        return {"form": "direct"}
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

        A missing file is a new session. An unreadable or corrupt file starts
        fresh, which can only re-hold, never pass, and says so.
        """

        self._ensure_private_directory()
        path = self._path(session_id)
        if not path.exists():
            return SessionState(), None
        try:
            return SessionState.from_json(json.loads(path.read_text(encoding="utf-8"))), None
        except (OSError, ValueError):
            return SessionState(), "its saved session state was unreadable and was reset"

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

    def _ensure_private_directory(self) -> None:
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if os.name == "nt":
            return  # The Windows default, the per-user temp folder, is private.
        info = self.directory.lstat()
        if self.directory.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise StateUnsafe(
                f"its state folder {self.directory} is not private to this user"
            )

    def _path(self, session_id: str) -> Path:
        safe = UNSAFE_NAME_CHARS.sub("_", session_id)[:128] or "unknown"
        return self.directory / f"{safe}.json"


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
