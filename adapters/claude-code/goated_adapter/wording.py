"""Slots in the rules' hold texts for words only a harness can say.

A hold sometimes names how the agent does something in its harness: the
tool that loads a skill or reads a file, where a route or skip line can go
so the harness keeps it, and which call carries a line for a call with none.
The rules hold no harness wording (ADR 0004): they write a slot here, and the
adapter fills each slot from its own table before the text is shown
(`translation.render` for Claude Code).

A slot is its name, then any arguments each after `|`, between `OPEN` and
`CLOSE`: two private-use characters no keyboard types, so text a hold
quotes, such as a malformed route line or a file name, is never read as a
slot. `SLOT_RE` finds slots; `NAMES` are every slot's name.
"""

from __future__ import annotations

import re

OPEN = ""
CLOSE = ""
SLOT_RE = re.compile(f"{OPEN}([a-z-]+)((?:\\|[^|{OPEN}{CLOSE}]+)*){CLOSE}")


def _slot(name: str, *arguments: str) -> str:
    return OPEN + "|".join((name, *arguments)) + CLOSE


# How the agent loads a skill, as the object of "with": "the Skill tool".
SKILL_TOOL = _slot("skill-tool")
# How the agent reads a file, as the object of "with": "the Read tool".
READ_TOOL = _slot("read-tool")
# A file read call, as a noun or a verb: "Read".
READ = _slot("read")
# What makes a file read whole: "with no limit, offset, or pages".
NO_RANGE = _slot("no-range")
# The file edit tools, after "a file edit tool": "(Edit, MultiEdit, or Write)".
FILE_EDIT_TOOLS = _slot("file-edit-tools")
# Ends a call's hold that a line can clear, on a line of its own: the harness
# names a call that can carry the line when the held call has no field for
# one, or says nothing and drops the line.
CARRIER = _slot("carrier")

FULL_ADVICE = "line-advice"
SHORT_ADVICE = "line-advice-short"
NAMES = frozenset({"skill-tool", "read-tool", "read", "no-range", "file-edit-tools", "carrier",
                   FULL_ADVICE, SHORT_ADVICE})
# A line-advice slot; its groups are the slot's name, the line, and the way out.
ADVICE_RE = re.compile(
    f"{OPEN}({FULL_ADVICE}|{SHORT_ADVICE})\\|([^|{CLOSE}]+)\\|([^|{CLOSE}]+){CLOSE}")


def unseen_line_advice(line: str, way_out: str) -> str:
    """The slot for recovery advice in a hold that a route or skip line can
    clear. `line` names the line ("route line", "skip line"); `way_out` is
    the typed override that stands the hold down. A line in reply text may
    never be seen, so the harness says where else it can go, then gives the
    user's way out. `gates.message` shortens it on every hold of a turn but
    one (`short_advice`)."""

    return _slot(FULL_ADVICE, line, way_out)


def short_advice(line: str, way_out: str) -> str:
    """The slot for the one sentence that stands for `unseen_line_advice`
    once a turn has had it."""

    return _slot(SHORT_ADVICE, line, way_out)
