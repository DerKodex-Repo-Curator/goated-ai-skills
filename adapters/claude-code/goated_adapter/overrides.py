"""The phrases a user can type to stand a routing hold down for one turn.

Only the user-prompt hook calls this, on the `prompt` field Claude Code passes
it, and the gates apply the result only to a turn the transcript shows a
person typed, so an agent's or another session's text never produces an
override (spec R8). The phrase set is documented in the adapter README; change
both together.
"""

from __future__ import annotations

import re

SKILL = r"[a-z0-9]+(?:-[a-z0-9]+)*"
ROUTING_RE = re.compile(r"\bskip\s+(?:the\s+)?(?:routing|router)\b", re.IGNORECASE)
SKILL_SKIP_RE = re.compile(rf"\bskip\s+(?:the\s+)?`?({SKILL})`?(?:\s+skill)?\b", re.IGNORECASE)
# A directive negated just before it ("don't skip routing", "never skip tdd",
# "no need to skip doc-sync") asks for the opposite. One adverb may sit between,
# as in "do not ever skip".
NEGATION_RE = re.compile(
    r"(?:\bdon[’']?t|\bdo\s+not|\bnever|\bno\s+need\s+to)\s+(?:\w+\s+)?$", re.IGNORECASE
)
HARNESS_BLOCK_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)
NOT_SKILLS = frozenset({"routing", "router"})


def parse_overrides(prompt: str) -> dict:
    """Return the overrides a typed prompt asks for.

    The result has `routing` (stand down router-first, route-line, and pipeline
    holds), `skills` (pipeline requirements to stand down), and `phrases` (the
    matched text, for the record). Harness-injected `<system-reminder>` blocks
    are not typed by the user and are ignored, as are negated phrases.
    """

    text = HARNESS_BLOCK_RE.sub(" ", prompt or "")
    routing = [m.group(0) for m in ROUTING_RE.finditer(text) if not _negated(text, m.start())]
    phrases = list(routing)
    skills: list[str] = []
    for match in SKILL_SKIP_RE.finditer(text):
        skill = match.group(1).lower()
        if skill in NOT_SKILLS or skill in skills or _negated(text, match.start()):
            continue
        skills.append(skill)
        phrases.append(match.group(0))
    return {"routing": bool(routing), "skills": skills, "phrases": phrases}


def _negated(text: str, start: int) -> bool:
    return bool(NEGATION_RE.search(text[max(0, start - 40) : start]))
