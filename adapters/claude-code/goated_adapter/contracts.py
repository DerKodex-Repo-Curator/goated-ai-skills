"""Mechanical content checks drawn from the skills' own contracts (spec R7).

Only text that is in the tool input is checked, and only for what a skill's
contract states plainly enough to test without judgement:

- a commit message follows `commit-message`'s output contract: a non-empty
  subject of at most 72 characters ("usually 72 characters or fewer"), a
  blank line before any body, and no credential in the text ("Do not include
  secrets, tokens ... in commit text");
- a spawn brief carries the headings its template cannot drop. `handoff`'s
  spawn brief says an agent that inherits everything still gets "the task,
  the scope, and what done looks like", so Goal, Scope, and Done Means stay.
  `subagent-driven-development`'s implementer and reviewer prompts require the
  task or review mode, the write ownership or review inputs, and the report
  format. Every brief also carries the skills line that `handoff`'s spawn
  brief defines (Ticket 071): `goated-skills: <skill>, <skill>` naming the
  skills the new agent reads first, or `goated-skills: none: <reason>`.

Whether a message or brief is *good* stays the skill's judgement, not this
module's, and so does whether the named skills are the right ones.
"""

from __future__ import annotations

import re

from .markers import FENCE_PREFIXES, MIN_REASON_WORDS, SKILL, candidate_line

SUBJECT_LIMIT = 72
# Well-known credential shapes. A match is reported by kind, never echoed.
SECRET_RE = re.compile(
    r"\b(?:gh[opsu]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_-]{20,}"
    r"|sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|xox[abprs]-[A-Za-z0-9-]{10,})"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)
HEADING_RE = re.compile(r"^[ ]{0,3}#{1,6}[ \t]+(.+?)[ \t#]*$", re.MULTILINE)


class BriefTemplate:
    """A spawn-brief template: the skill that owns it, its file, and its kept headings."""

    __slots__ = ("skill", "reference", "headings")

    def __init__(self, skill: str, reference: str, headings: tuple[str, ...]) -> None:
        self.skill = skill
        self.reference = reference
        self.headings = headings

    def missing_headings(self, brief: str) -> list[str]:
        found = [h.strip().lower() for h in HEADING_RE.findall(brief)]
        return [h for h in self.headings if not any(f.startswith(h.lower()) for f in found)]


BRIEF_TEMPLATES = (
    BriefTemplate("handoff", "handoff/references/spawn-brief.md", ("Goal", "Scope", "Done Means")),
    BriefTemplate(
        "subagent-driven-development",
        "subagent-driven-development/references/implementer-prompt.md",
        ("Task", "Ownership", "Required Report Format"),
    ),
    BriefTemplate(
        "subagent-driven-development",
        "subagent-driven-development/references/reviewer-prompt.md",
        ("Review Mode", "Review Inputs", "Required Report Format"),
    ),
)


SKILLS_LINE_PREFIX = "goated-skills:"
SKILLS_LINE_RE = re.compile(
    rf"^goated-skills:[ \t]+(?:none:[ \t]+(\S.*)|((?!none$){SKILL}(?:[ \t]*,[ \t]*{SKILL})*))$"
)


def skills_line_problem(brief: str) -> str | None:
    """Say what is wrong with the brief's skills line, as a predicate for "The
    brief ..."; None when it has a valid one. Like a route line, the line counts
    only on its own line outside code blocks, bare or in one pair of backticks;
    one valid line is enough."""

    malformed = False
    in_fence = False
    for raw in brief.splitlines():
        if raw.strip().startswith(FENCE_PREFIXES):
            in_fence = not in_fence
            continue
        line = candidate_line(raw)
        if in_fence or not line.lower().startswith(SKILLS_LINE_PREFIX):
            continue
        match = SKILLS_LINE_RE.match(line)
        reason = match and match.group(1)
        if match and (reason is None or len(reason.split()) >= MIN_REASON_WORDS):
            return None
        malformed = True
    if malformed:
        return (
            "has a skills line that names no skill in lowercase, or says none without "
            f"a reason of {MIN_REASON_WORDS} words or more"
        )
    return "lacks a skills line"


def commit_message_problems(message: str) -> list[str]:
    """Return what breaks the commit-message contract, in plain words; [] when none."""

    problems = []
    lines = message.strip("\n").split("\n")
    subject = lines[0].strip()
    if not subject:
        problems.append("the subject line is empty")
    elif len(subject) > SUBJECT_LIMIT:
        problems.append(
            f"the subject is {len(subject)} characters; keep it to {SUBJECT_LIMIT} or fewer"
        )
    if len(lines) > 1 and lines[1].strip():
        problems.append("put a blank line between the subject and the body")
    if SECRET_RE.search(message):
        problems.append(
            "the message contains what looks like a credential; describe the exposure "
            "without the value"
        )
    return problems
