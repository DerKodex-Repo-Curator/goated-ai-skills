"""Find what Claude Code will load at session start: the shared policy and the router.

The shared policy (`stack/AGENTS.md` in a GOATED distribution) only applies
when an instruction file Claude Code loads contains it or imports it (spec R2),
and the router-first hold can only clear if the `using-goated-ai-skills` skill
is installed. This module knows where Claude Code looks for both. File contents
are only searched, never returned or logged.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

POLICY_TITLE = "GOATED Integrated Stack Policy"
IMPORT_RE = re.compile(r"^@(\S+)\s*$", re.MULTILINE)
PROJECT_FILES = ("AGENTS.md", "CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md")
MAX_FILE_BYTES = 512 * 1024
PLUGIN_SKILL_DEPTHS = range(1, 5)


def shared_policy_loaded(cwd: Path, home: Path) -> bool:
    """Return True when an instruction file Claude Code loads carries the policy.

    Checks the user's `~/.claude/CLAUDE.md` and `~/.claude/rules/`, then the
    project files and `.claude/rules/` in `cwd` and each parent directory,
    following `@path` imports one level deep. For a project inside `home`, the
    parent walk stops at `home`. Imports are only opened inside `cwd`, `home`,
    or the importing file's folder, and never on a network (UNC) path, so a
    cloned repository cannot make this hook reach out to another host. It does
    not model Claude Code's rule that a `CLAUDE.md` can stop `AGENTS.md` from
    loading, so it can report a policy as loaded when that setting hides it.
    """

    for path in _instruction_files(cwd, home):
        text = _read(path)
        if POLICY_TITLE in text:
            return True
        for target in IMPORT_RE.findall(text):
            imported = _allowed_import(target, path.parent, (cwd, home, path.parent))
            if imported is not None and POLICY_TITLE in _read(imported):
                return True
    return False


def router_skill_installed(cwd: Path, home: Path, skill: str) -> bool:
    """Return True when Claude Code can find `skill` as a user, project, or plugin skill."""

    user_dir = home / ".claude"
    candidates = [user_dir / "skills" / skill / "SKILL.md"]
    candidates += [d / ".claude" / "skills" / skill / "SKILL.md" for d in _project_dirs(cwd, home)]
    if any(path.is_file() for path in candidates):
        return True
    plugins = user_dir / "plugins"
    for depth in PLUGIN_SKILL_DEPTHS:
        pattern = "/".join(["*"] * depth + ["skills", skill, "SKILL.md"])
        if next(plugins.glob(pattern), None) is not None:
            return True
    return False


def _instruction_files(cwd: Path, home: Path):
    user_dir = home / ".claude"
    yield user_dir / "CLAUDE.md"
    yield from _rules(user_dir / "rules")
    for directory in _project_dirs(cwd, home):
        for name in PROJECT_FILES:
            yield directory / name
        yield from _rules(directory / ".claude" / "rules")


def _project_dirs(cwd: Path, home: Path):
    for directory in (cwd, *cwd.parents):
        yield directory
        if directory == home:
            break


def _allowed_import(target: str, base: Path, roots) -> Path | None:
    """Resolve an `@` import without touching the file system; None when refused."""

    if target.startswith(("\\\\", "//")):
        return None
    path = Path(target).expanduser()
    if not path.is_absolute():
        path = base / path
    absolute = os.path.normcase(os.path.abspath(path))
    if absolute.startswith(("\\\\", "//")):
        return None
    for root in roots:
        root_abs = os.path.normcase(os.path.abspath(root))
        try:
            if os.path.commonpath([absolute, root_abs]) == root_abs:
                return Path(absolute)
        except ValueError:  # different drives
            continue
    return None


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
