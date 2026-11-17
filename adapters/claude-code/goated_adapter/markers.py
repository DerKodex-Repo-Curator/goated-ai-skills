"""The adapter's own reader for `goated-route`, `goated-skip`, and
`goated-design-reads` lines.

The grammar is owned by `stack/fixtures/markers/README.md` in the GOATED source
repo. This copy exists so an installed adapter needs nothing from that repo;
the repo's tests check it against the same `lines.yaml` and
`design-reads.yaml` fixtures as the reference checker, so the two cannot drift silently.
"""

from __future__ import annotations

import re

SKILL = r"[a-z0-9]+(?:-[a-z0-9]+)*"
ROUTE_RE = re.compile(
    r"^goated-route:[ \t]+(?:(direct|continue)|(lightweight|standard|full)"
    rf"[ \t]+\|[ \t]+requires:[ \t]+({SKILL}(?:[ \t]*,[ \t]*{SKILL})*))$"
)
SKIP_RE = re.compile(rf"^goated-skip:[ \t]+({SKILL}):[ \t]+(\S.*)$")
FILE = rf"{SKILL}\.md"
DESIGN_READS_RE = re.compile(
    rf"^goated-design-reads:[ \t]+(?:none:[ \t]+(\S.*)|({FILE}(?:[ \t]*,[ \t]*{FILE})*))$"
)
MIN_REASON_WORDS = 3
FENCE_PREFIXES = ("```", "~~~")


class ReplyMarkers:
    """Markers found in one reply: the winning route, skips, and malformed route
    and skip lines; and the design-reads lines, valid and malformed, kept apart
    so route holds never quote them."""

    __slots__ = ("route", "skips", "malformed", "design_reads", "malformed_design_reads")

    def __init__(self) -> None:
        self.route: dict | None = None
        self.skips: list[dict] = []
        self.malformed: list[str] = []
        self.design_reads: list[dict] = []
        self.malformed_design_reads: list[str] = []


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


def parse_design_reads_line(line: str) -> dict | None:
    """Return what a candidate design-reads line declares, or None if invalid:
    `{"form": "files", "files": [...]}` or `{"form": "none", "reason": ...}`."""

    match = DESIGN_READS_RE.match(line)
    if not match:
        return None
    reason, files = match.groups()
    if reason is not None:
        reason = reason.strip()
        return {"form": "none", "reason": reason} if len(reason.split()) >= MIN_REASON_WORDS else None
    names = [name.strip() for name in files.split(",")]
    if len(set(names)) != len(names):
        return None
    return {"form": "files", "files": names}


def declared_files(lines: list[dict]) -> list[str]:
    """The union of the files design-reads lines name, in first-seen order."""

    return list(dict.fromkeys(f for line in lines for f in line.get("files", ())))


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
        elif lowered.startswith("goated-design-reads:"):
            declared = parse_design_reads_line(line)
            if declared is None:
                result.malformed_design_reads.append(line)
            else:
                result.design_reads.append(declared)
    return result
