"""The adapter's own reader for `goated-route` and `goated-skip` lines.

The grammar is owned by `stack/fixtures/markers/README.md` in the GOATED source
repo. This copy exists so an installed adapter needs nothing from that repo;
the repo's tests check it against the same `lines.yaml` fixtures as the
reference checker, so the two cannot drift silently. A `goated-design-reads:`
line, which no gate reads any more (Ticket 089), is ignored like other prose.
"""

from __future__ import annotations

import re

SKILL = r"[a-z0-9]+(?:-[a-z0-9]+)*"
ROUTE_RE = re.compile(
    r"^goated-route:[ \t]+(?:(direct|continue)|(lightweight|standard|full)"
    rf"[ \t]+\|[ \t]+requires:[ \t]+({SKILL}(?:[ \t]*,[ \t]*{SKILL})*))$"
)
SKIP_RE = re.compile(rf"^goated-skip:[ \t]+({SKILL}):[ \t]+(\S.*)$")
MIN_REASON_WORDS = 3
FENCE_PREFIXES = ("```", "~~~")


class ReplyMarkers:
    """Markers found in one reply: the winning route, skips, and malformed route
    and skip lines."""

    __slots__ = ("route", "skips", "malformed")

    def __init__(self) -> None:
        self.route: dict | None = None
        self.skips: list[dict] = []
        self.malformed: list[str] = []


def candidate_line(raw: str) -> str:
    """Strip whitespace and unwrap one pair of enclosing single backticks."""

    line = raw.strip()
    if len(line) > 2 and line[0] == "`" and line[-1] == "`" and line[1] != "`":
        line = line[1:-1].strip()
    return line


def parse_route_line(line: str) -> dict | None:
    """Return the route a candidate line declares, or None if it is not valid."""

    match = ROUTE_RE.match(line)
    if not match:
        return None
    keyword, intensity, skills = match.groups()
    if keyword:
        return {"form": keyword}
    requires = [skill.strip() for skill in skills.split(",")]
    if len(set(requires)) != len(requires):
        return None
    return {"form": "route", "intensity": intensity, "requires": requires}


def parse_skip_line(line: str) -> dict | None:
    """Return the skill and reason a candidate line skips, or None if invalid."""

    match = SKIP_RE.match(line)
    if not match:
        return None
    skill, reason = match.group(1), match.group(2).strip()
    if len(reason.split()) < MIN_REASON_WORDS:
        return None
    return {"skill": skill, "reason": reason}


ROUTE_KEYWORDS = ("direct", "continue")
INTENSITIES = ("lightweight", "standard", "full")
PUNCTUATION_ONLY = re.compile(r"^[.,;:!?]+$")
REQUIRES_LIST = re.compile(r"\|[ \t]+requires:(.*)$")


def malformed_reason(line: str) -> str:
    """Why `line`, a candidate route or skip line that does not parse, breaks
    the grammar, in the words of the marker fixtures' `why`; for a whole
    route line with text after it, "nothing may follow the line". A hold
    quotes it beside the line (round 6, R11)."""

    if line.lower().startswith("goated-skip:"):
        return _skip_line_reason(line)
    if not line.startswith("goated-route:"):
        return "the prefix is lowercase"
    body = line[len("goated-route:"):]
    if not body[:1].isspace():
        return "whitespace is required after the colon"
    words = body.split()
    first = words[0] if words else ""
    if first.lower() in ROUTE_KEYWORDS + INTENSITIES and first != first.lower():
        return "keywords are lowercase"
    if first in ROUTE_KEYWORDS and body.lstrip()[len(first):].lstrip().startswith("|"):
        return f"{first} takes no skill list"
    if first in INTENSITIES:
        requires = REQUIRES_LIST.search(body)
        if requires is None:
            return ("the pipe separator is required" if "requires" in body
                    else "an intensity needs a requires list")
        skills = requires.group(1).strip()
        if not skills:
            return "the requires list is non-empty"
        if skills.endswith(","):
            return "no trailing comma"
        listed = [skill.strip() for skill in skills.split(",")]
        if any(skill != skill.lower() for skill in listed):
            return "skill names are lowercase kebab-case"
        if len(set(listed)) != len(listed):
            return "the requires list has no duplicates"
        if any(re.fullmatch(f"{SKILL}(?:[ \t]+{SKILL})+", skill) for skill in listed):
            return "skills are comma-separated"
    elif first not in ROUTE_KEYWORDS and re.fullmatch(r"[a-z]+", first) and "|" in body:
        return "intensity is lightweight, standard, or full"
    return _trailing_reason(line)


def _trailing_reason(line: str) -> str:
    """The reason for a route line that holds a whole route line followed by
    more text, or else the plain one."""

    for end in range(len(line) - 1, len("goated-route:"), -1):
        if parse_route_line(line[:end].rstrip()) is not None:
            rest = line[end:].strip()
            return ("no trailing punctuation" if PUNCTUATION_ONLY.match(rest)
                    else "nothing may follow the line")
    return "it does not match the grammar"


def _skip_line_reason(line: str) -> str:
    """Why the skip line `line` does not parse."""

    if not line.startswith("goated-skip:"):
        return "the prefix is lowercase"
    body = line[len("goated-skip:"):]
    if not body[:1].isspace():
        return "whitespace is required after the prefix colon"
    skill, colon, reason = body.strip().partition(":")
    if not colon:
        return "a reason is required"
    if "," in skill:
        return "one skill per skip line"
    if not re.fullmatch(SKILL, skill):
        return "skill names are lowercase kebab-case"
    if not reason.strip():
        return "the reason is non-empty"
    if not reason[:1].isspace():
        return "whitespace is required after the skill colon"
    if len(reason.split()) < MIN_REASON_WORDS:
        return "the reason has at least three words"  # MIN_REASON_WORDS
    return "it does not match the grammar"


def parse_reply(text: str) -> ReplyMarkers:
    """Collect the markers in a whole reply, ignoring fenced code blocks."""

    result = ReplyMarkers()
    in_fence = False
    for raw in text.splitlines():
        if raw.strip().startswith(FENCE_PREFIXES):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        line = candidate_line(raw)
        lowered = line.lower()
        if lowered.startswith("goated-route:"):
            route = parse_route_line(line)
            if route is None:
                result.malformed.append(line)
            else:
                result.route = route
        elif lowered.startswith("goated-skip:"):
            skip = parse_skip_line(line)
            if skip is None:
                result.malformed.append(line)
            else:
                result.skips.append(skip)
    return result
