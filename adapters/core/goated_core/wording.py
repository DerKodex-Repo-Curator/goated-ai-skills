"""Slots in the rules' hold texts for words only a harness can say.

A hold sometimes names how the agent does something in its harness: the
tool that loads a skill or reads a file, where a route or skip line can go
so the harness keeps it, and which call carries a line for a call with none.
The rules hold no harness wording (ADR 0004): they write a slot here. An
adapter that calls the core in Python (`judge`) may fill each slot from its
own table before the text is shown (`translation.render` for Claude Code);
the core's request call (`request.decide`), and so its command, fills them
with the neutral words of `neutral`, so no decision it returns carries a
slot.

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
    user's way out. `gates.shown_holds` shortens it on every hold of a turn but
    one (`short_advice`)."""

    return _slot(FULL_ADVICE, line, way_out)


def short_advice(line: str, way_out: str) -> str:
    """The slot for the one sentence that stands for `unseen_line_advice`
    once a turn has had it."""

    return _slot(SHORT_ADVICE, line, way_out)


# Neutral words -----------------------------------------------------------------

# Each phrase slot in words any harness can show.
NEUTRAL_PHRASES = {
    SKILL_TOOL: "the harness's skill loader",
    READ_TOOL: "a file read",
    READ: "read",
    NO_RANGE: "with no range",
    FILE_EDIT_TOOLS: "(a file write call)",
}


def neutral(text: str) -> str:
    """`text` with every slot filled in neutral words.

    Every call of the event model may carry a line in its `line_text`, so
    the carrier slot says nothing and goes with the line break before it.
    The line advice says where a line counts, without a harness's reasons
    for why reply text may not be seen. Raises ValueError for a slot with no
    neutral words, a rule's mistake.
    """

    text = text.replace("\n" + CARRIER, "")

    def fill(slot: re.Match) -> str:
        if slot[0] == CARRIER:
            return ""
        if slot[0] in NEUTRAL_PHRASES:
            return NEUTRAL_PHRASES[slot[0]]
        advice = ADVICE_RE.fullmatch(slot[0])
        if advice is None:
            raise ValueError(f"no neutral wording for the slot {slot[1]!r}")
        name, line, way_out = advice.groups()
        if name == SHORT_ADVICE:
            return (f"Put the {line} on its own line, as this turn's first such hold "
                    f"explained, or tell the user they can type `{way_out}` in their prompt.")
        return (f"Put the {line} on its own line in reply text or in a call's line text; it "
                f"counts from there on. Then make the call again. If that is held again, "
                f"tell the user they can type `{way_out}` in their prompt.")

    return SLOT_RE.sub(fill, text)
