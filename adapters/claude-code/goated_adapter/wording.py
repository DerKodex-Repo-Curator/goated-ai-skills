"""Slots in the rules' hold texts for words only a harness can say.

A hold sometimes names how the agent does something in its harness: the
tool that loads a skill or reads a file, where a route or skip line can go
so the harness keeps it, and which call carries a line for a call with none.
The rules hold no harness wording (ADR 0004): they write a slot here, and the
adapter fills each slot from its own table before the text is shown
(`translation.render` for Claude Code). A slot is `{{name}}`, or
`{{name|argument|argument}}`.
"""

from __future__ import annotations

import re

# How the agent loads a skill, as the object of "with": "the Skill tool".
SKILL_TOOL = "{{skill-tool}}"
# How the agent reads a file, as the object of "with": "the Read tool".
READ_TOOL = "{{read-tool}}"
# A file read call, as a noun or a verb: "Read".
READ = "{{read}}"
# What makes a file read whole: "with no limit, offset, or pages".
NO_RANGE = "{{no-range}}"
# The file edit tools, after "a file edit tool": "(Edit, MultiEdit, or Write)".
FILE_EDIT_TOOLS = "{{file-edit-tools}}"
# Ends a call's hold that a line can clear: the harness names a call that can
# carry the line when the held call has no field for one, or says nothing.
CARRIER = "{{carrier}}"

FULL_ADVICE = "line-advice"
SHORT_ADVICE = "line-advice-short"
ADVICE_RE = re.compile(r"\{\{(line-advice(?:-short)?)\|([^|}]+)\|([^|}]+)\}\}")


def unseen_line_advice(line: str, way_out: str) -> str:
    """The slot for recovery advice in a hold that a route or skip line can
    clear. `line` names the line ("route line", "skip line"); `way_out` is
    the typed override that stands the hold down. A line in reply text may
    never be seen, so the harness says where else it can go, then gives the
    user's way out. `gates.message` shortens it on every hold of a turn but
    one (`short_advice`)."""

    return f"{{{{{FULL_ADVICE}|{line}|{way_out}}}}}"


def short_advice(line: str, way_out: str) -> str:
    """The slot for the one sentence that stands for `unseen_line_advice`
    once a turn has had it."""

    return f"{{{{{SHORT_ADVICE}|{line}|{way_out}}}}}"
