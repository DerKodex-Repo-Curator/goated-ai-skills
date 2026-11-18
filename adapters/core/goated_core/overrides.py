"""The phrases a user can type to stand a hold down for one turn.

It reads a prompt a person typed, as the event model holds it: the adapter
has removed the blocks its harness inserts and moved pasted text out, so
neither is read. The gates apply the result only to a turn whose opener a
person wrote, so an agent's or another session's text never produces an
override (spec R8). The phrase set is documented in the adapter README; change
both together.
"""

from __future__ import annotations

import re

SKILL = r"[a-z0-9]+(?:-[a-z0-9]+)*"
ROUTING_RE = re.compile(r"\bskip\s+(?:the\s+)?(?:routing|router)\b", re.IGNORECASE)
# A closing backtick ends the name itself: requiring a word boundary after it
# failed at the end of "skip `doc-sync`" and dropped the backtick from the match.
SKILL_SKIP_RE = re.compile(
    rf"\bskip\s+(?:the\s+)?`?({SKILL})(?:`|\b)(?:\s+skill\b)?", re.IGNORECASE
)
# A directive negated just before it ("don't skip routing", "never skip tdd",
# "no need to skip doc-sync") asks for the opposite. One adverb may sit between,
# as in "do not ever skip".
NEGATION_RE = re.compile(
    r"(?:\bdon[’']?t|\bdo\s+not|\bnever|\bno\s+need\s+to)\s+(?:\w+\s+)?$", re.IGNORECASE
)
# "commit message: <text>", "commit it with the message "<text>"", or a fenced
# block right after such a phrase. The words between "commit" and "message"
# stay on one line and short, so prose that merely mentions both is not read,
# and neither is the skill name `commit-message`.
COMMIT_MESSAGE_RE = re.compile(
    r"\bcommit\b(?!-)[^\n]{0,40}?\bmessage\b(?:[ \t]+(?:is|of))?[ \t]*[:=]?[ \t]*", re.IGNORECASE
)
FENCED_RE = re.compile(r"\n?[ \t]*```[^\n]*\n(.*?)\n[ \t]*```", re.DOTALL)
QUOTED_RES = (
    re.compile(r'"([^"\n]+)"'),
    re.compile(r"\u201c([^\u201d\n]+)\u201d"),
    re.compile(r"`([^`\n]+)`"),
    re.compile(r"'([^'\n]+)'"),
)
NOT_SKILLS = frozenset({"routing", "router"})
# The GOATED registry's skill names (`stack/goated-stack.yaml`), used when no
# installed skill can be found. A test keeps this list equal to the registry.
GOATED_SKILLS = frozenset(
    {
        "agent-instructions-integrator", "architecture-design-map", "caveman",
        "code-refinement", "code-security-review", "commit-message", "context-matrix-map",
        "design-codebase-architecture", "diagnose", "doc-sync", "documentation-cleanup",
        "documentation-writer", "framework-agnostic-skill-creator", "goated-prompt",
        "grill-me", "grill-with-docs", "handoff", "knowledge-retrieval", "learning-capture",
        "pr-description", "project-context-calibration", "project-standards-calibration",
        "prototype", "receiving-code-review", "resolving-merge-conflicts", "retrospective",
        "review-codebase-architecture", "session-start-progressive-disclosure",
        "setup-scribe", "software-design-principles", "source-grounded-research",
        "spec-to-tickets", "standards-and-spec-review", "subagent-driven-development",
        "tdd", "using-goated-ai-skills", "verification-before-completion", "wayfinder",
        "write-a-spec", "writing-plans",
    }
)


def parse_overrides(prompt: str, known_skills: frozenset[str] = GOATED_SKILLS) -> dict:
    """Return the overrides a typed prompt's own text (`Prompt.text`) asks for.

    The result has `routing` (stand down router-first, route-line, and pipeline
    holds), `skills` (skills whose holds stand down), `commit_message` (the
    commit message the user supplied, or None), and `phrases` (the matched
    text, for the record). `skip <name>` counts only when `<name>` is in
    `known_skills`, so "skip line" or "skip the first two lines" is not an
    override. Negated phrases are ignored.
    """

    text = prompt or ""
    routing = [m.group(0) for m in ROUTING_RE.finditer(text) if not _negated(text, m.start())]
    phrases = list(routing)
    skills: list[str] = []
    for match in SKILL_SKIP_RE.finditer(text):
        skill = match.group(1).lower()
        if (
            skill in NOT_SKILLS or skill not in known_skills or skill in skills
            or _negated(text, match.start())
        ):
            continue
        skills.append(skill)
        # Recorded without backticks, so "skip `tdd`" counts as "skip tdd".
        phrases.append(match.group(0).replace("`", ""))
    message = _commit_message(text)
    if message is not None:
        # The phrase names the override; the message text stays out of the record.
        phrases.append("commit message")
    return {
        "routing": bool(routing),
        "skills": skills,
        "commit_message": message,
        "phrases": phrases,
    }


def _commit_message(text: str) -> str | None:
    """Return the commit message the user typed, if a phrase supplies one."""

    for match in COMMIT_MESSAGE_RE.finditer(text):
        if _negated(text, match.start()):
            continue
        rest = text[match.end() :]
        fenced = FENCED_RE.match(rest)
        if fenced:
            return fenced.group(1).strip() or None
        for quoted in QUOTED_RES:
            found = quoted.match(rest)
            if found:
                return found.group(1).strip() or None
        line = rest.split("\n", 1)[0].strip()
        if match.group(0).rstrip().endswith((":", "=")) and line:
            return line
    return None


def _negated(text: str, start: int) -> bool:
    return bool(NEGATION_RE.search(text[max(0, start - 40) : start]))
