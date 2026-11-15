"""The phrases a user can type to stand a routing hold down for one turn.

Only the user-prompt hook calls this, on the `prompt` field Claude Code passes
it, so an agent's own text can never produce an override (spec R8). The phrase
set is documented in the adapter README; change both together.
"""

from __future__ import annotations

import re

SKILL = r"[a-z0-9]+(?:-[a-z0-9]+)*"
ROUTING_RE = re.compile(r"\b(?:skip|no)\s+(?:the\s+)?(?:routing|router)\b", re.IGNORECASE)
SKILL_SKIP_RE = re.compile(rf"\bskip\s+(?:the\s+)?`?({SKILL})`?(?:\s+skill)?\b", re.IGNORECASE)
HARNESS_BLOCK_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)
NOT_SKILLS = frozenset({"routing", "router"})


def parse_overrides(prompt: str) -> dict:
    """Return the overrides a typed prompt asks for.

    The result has `routing` (stand down router-first, route-line, and pipeline
    holds), `skills` (pipeline requirements to stand down), and `phrases` (the
    matched text, for the record). Harness-injected `<system-reminder>` blocks
    are not typed by the user and are ignored.
    """

    text = HARNESS_BLOCK_RE.sub(" ", prompt or "")
    phrases = [m.group(0) for m in ROUTING_RE.finditer(text)]
    skills: list[str] = []
    for match in SKILL_SKIP_RE.finditer(text):
        skill = match.group(1).lower()
        if skill not in NOT_SKILLS and skill not in skills:
            skills.append(skill)
            phrases.append(match.group(0))
    return {"routing": bool(ROUTING_RE.search(text)), "skills": skills, "phrases": phrases}
