"""Reference checker for the `goated-route` and `goated-skip` marker lines.

The grammar is owned by `stack/fixtures/markers/README.md`; this module is the
repo's executable reading of it, checked against `lines.yaml` in that folder.
Framework adapters may carry their own parser but must agree with the same
fixtures.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .shared import Finding, load_mapping, relative

SKILL = r"[a-z0-9]+(?:-[a-z0-9]+)*"
ROUTE_RE = re.compile(
    r"^goated-route:[ \t]+(?:(direct|continue)|(lightweight|standard|full)"
    rf"[ \t]+\|[ \t]+requires:[ \t]+({SKILL}(?:[ \t]*,[ \t]*{SKILL})*))$"
)
SKIP_RE = re.compile(rf"^goated-skip:[ \t]+({SKILL}):[ \t]+(\S.*)$")
MIN_REASON_WORDS = 3
FENCE_PREFIXES = ("```", "~~~")

FIXTURE_PATH = Path("stack") / "fixtures" / "markers" / "lines.yaml"


@dataclass
class ReplyMarkers:
    """Markers found in one reply: the winning route, skips, and malformed lines."""

    route: dict[str, object] | None = None
    skips: list[dict[str, str]] = field(default_factory=list)
    malformed: list[str] = field(default_factory=list)


def candidate_line(raw: str) -> str:
    """Strip whitespace and unwrap one pair of enclosing single backticks."""

    line = raw.strip()
    if len(line) > 2 and line[0] == "`" and line[-1] == "`" and line[1] != "`":
        line = line[1:-1].strip()
    return line


def parse_route_line(line: str) -> dict[str, object] | None:
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


def parse_skip_line(line: str) -> dict[str, str] | None:
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


def _check_lines(
    cases: object,
    parser,
    section: str,
    label: str,
) -> list[Finding]:
    """Check one valid/invalid section of the line fixtures against a parser."""

    if not isinstance(cases, dict):
        return [Finding(label, f"{section} must be a mapping with valid and invalid")]
    findings: list[Finding] = []
    for kind in ("valid", "invalid"):
        entries = cases.get(kind)
        if not isinstance(entries, list) or not entries:
            findings.append(Finding(label, f"{section}.{kind} must be a non-empty list"))
            continue
        for entry in entries:
            line = entry.get("line") if isinstance(entry, dict) else None
            if not isinstance(line, str):
                findings.append(Finding(label, f"{section}.{kind} entry needs a line"))
                continue
            parsed = parser(line)
            if kind == "valid" and parsed != entry.get("expect"):
                findings.append(
                    Finding(label, f"{section} {line!r} parsed as {parsed!r}")
                )
            if kind == "invalid":
                if parsed is not None:
                    findings.append(
                        Finding(label, f"{section} {line!r} is listed invalid but parses")
                    )
                if not entry.get("why"):
                    findings.append(Finding(label, f"{section} {line!r} needs a why"))
    return findings


def _load_fixture(repo: Path, fixture: Path) -> tuple[dict | None, str, list[Finding]]:
    path = repo / fixture
    label = fixture.as_posix() if not path.exists() else relative(path, repo)
    data, findings = load_mapping(path, label)
    return data, label, findings


def validate_marker_fixtures(repo: Path) -> list[Finding]:
    """Check that every marker fixture agrees with the reference grammar."""

    return _validate_route_and_skip_fixtures(repo)


def _validate_route_and_skip_fixtures(repo: Path) -> list[Finding]:
    data, label, findings = _load_fixture(repo, FIXTURE_PATH)
    if data is None:
        return findings

    findings.extend(
        _check_lines(data.get("route_lines"), parse_route_line, "route_lines", label)
    )
    findings.extend(
        _check_lines(data.get("skip_lines"), parse_skip_line, "skip_lines", label)
    )

    replies = data.get("replies")
    if not isinstance(replies, list) or not replies:
        findings.append(Finding(label, "replies must be a non-empty list"))
        return findings
    for reply in replies:
        if not isinstance(reply, dict) or not isinstance(reply.get("text"), str):
            findings.append(Finding(label, "each reply needs an identifier and text"))
            continue
        parsed = parse_reply(reply["text"])
        actual = {
            "route": parsed.route,
            "skips": parsed.skips,
            "malformed": parsed.malformed,
        }
        if actual != reply.get("expect"):
            findings.append(
                Finding(
                    label,
                    f"reply {reply.get('identifier')!r} parsed as {actual!r}",
                )
            )
    return findings
