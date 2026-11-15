"""Detect whether the GOATED shared policy is among Claude Code's instructions.

The shared policy (`stack/AGENTS.md` in a GOATED distribution) only applies
when an instruction file Claude Code loads contains it or imports it (spec R2).
This module knows where Claude Code looks; it checks for the policy's title.
File contents are only searched, never returned or logged.
"""

from __future__ import annotations

import re
from pathlib import Path

POLICY_TITLE = "GOATED Integrated Stack Policy"
IMPORT_RE = re.compile(r"^@(\S+)\s*$", re.MULTILINE)
PROJECT_FILES = ("AGENTS.md", "CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md")
MAX_FILE_BYTES = 512 * 1024


def shared_policy_loaded(cwd: Path, home: Path) -> bool:
    """Return True when an instruction file Claude Code loads carries the policy.

    Checks the user's `~/.claude/CLAUDE.md` and `~/.claude/rules/`, then the
    project files and `.claude/rules/` in `cwd` and each parent directory,
    following `@path` imports one level deep. For a project inside `home`, the
    parent walk stops at `home`. It does not model Claude Code's rule that a
    `CLAUDE.md` can stop `AGENTS.md` from loading, so it can report a policy as
    loaded when that setting hides it.
    """

    for path in _instruction_files(cwd, home):
        text = _read(path)
        if POLICY_TITLE in text:
            return True
        for target in IMPORT_RE.findall(text):
            imported = Path(target).expanduser()
            if not imported.is_absolute():
                imported = path.parent / imported
            if POLICY_TITLE in _read(imported):
                return True
    return False


def _instruction_files(cwd: Path, home: Path):
    user_dir = home / ".claude"
    yield user_dir / "CLAUDE.md"
    yield from _rules(user_dir / "rules")
    for directory in (cwd, *cwd.parents):
        for name in PROJECT_FILES:
            yield directory / name
        yield from _rules(directory / ".claude" / "rules")
        if directory == home:
            break


def _rules(directory: Path) -> list[Path]:
    try:
        return sorted(directory.rglob("*.md")) if directory.is_dir() else []
    except OSError:
        return []


def _read(path: Path) -> str:
    try:
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
