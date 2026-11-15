"""The adapter's own reader for `goated-route` and `goated-skip` lines.

The grammar is owned by `stack/fixtures/markers/README.md` in the GOATED source
repo. This copy exists so an installed adapter needs nothing from that repo;
the repo's tests check it against the same `lines.yaml` fixtures as the
reference checker, so the two cannot drift silently.
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
    """Markers found in one reply: the winning route, skips, and malformed lines."""

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
