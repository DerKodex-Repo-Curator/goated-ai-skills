"""The onboarding notice: which agent files a project lacks, and the skill for each.

The three onboarding skills state the rule this module enforces (Ticket 073):
a project missing one of these files at its root is set up with that file's
skill. The notice is shown once per project, and again only when a file goes
missing that was present when it was last shown. It never blocks. Whether it
was shown is recorded beside the session state, outside the project folder.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import NamedTuple

from goated_core.gates import CONTEXT_DOCS


class AgentFile(NamedTuple):
    """One agent file a project should have: what it is, the root-relative
    paths that count as it (any one does), and the skill that writes it."""

    what: str
    paths: tuple[str, ...]
    skill: str


# The paths each skill writes by default. Claude Code also loads a project's
# `.claude/CLAUDE.md`, so it counts as an instruction file too.
AGENT_FILES = (
    AgentFile("an agent instruction file", ("AGENTS.md", "CLAUDE.md", ".claude/CLAUDE.md"),
              "agent-instructions-integrator"),
    AgentFile("a context map", ("docs/agents/context-matrix.md",), "context-matrix-map"),
    AgentFile("a standards document", ("docs/agents/project-standards.md",),
              "project-standards-calibration"),
)


def project_root(cwd: str | None, project_dir: str | None) -> Path | None:
    """The project's root folder: Claude Code's project folder when it names
    one, else the nearest folder at or above `cwd` holding a `.git` entry,
    else `cwd`. None without either."""

    if project_dir:
        return Path(project_dir)
    if not cwd:
        return None
    start = Path(cwd)
    return next((folder for folder in (start, *start.parents) if (folder / ".git").exists()), start)


def missing_files(root: Path) -> list[AgentFile]:
    """The agent files `root` has none of the paths for, in `AGENT_FILES` order."""

    return [f for f in AGENT_FILES if not any((root / path).is_file() for path in f.paths)]


def context_docs(root: Path | None) -> list[str]:
    """The project's own context documents at `root` (`gates.CONTEXT_DOCS`)
    that exist as files, in that order, for the core to name; none without a
    root."""

    if root is None:
        return []
    return [doc for doc in CONTEXT_DOCS if (root / doc).is_file()]


def project_key(root: Path) -> str:
    """A stable name for `root` across sessions, as the record of the notice keys it."""

    return os.path.normcase(os.path.abspath(root))


def notice_due(missing: list[AgentFile], last_shown: list[str] | None) -> bool:
    """Whether the notice shows: a file is missing that the notice last shown
    for this project (`last_shown`, the skills it named; None for never) did
    not name. A file added back since brings no notice."""

    return any(f.skill not in (last_shown or ()) for f in missing)


def notice(missing: list[AgentFile]) -> str:
    """The notice naming each missing file's paths and onboarding skill."""

    parts = [
        f"{f.what} ({' or '.join(f'`{path}`' for path in f.paths[:2])}), which "
        f"`{f.skill}` writes"
        for f in missing
    ]
    return (
        "this project lacks " + "; ".join(parts) + ". Load the named onboarding skill "
        "when the work allows, such as before serious work in the project. This notice "
        "shows once per project; nothing is held."
    )
