"""Reference checker for the `goated-route`, `goated-skip`, and
`goated-design-reads` marker lines.

The grammar is owned by `stack/fixtures/markers/README.md`; this module is the
repo's executable reading of it, checked against `lines.yaml` and
`design-reads.yaml` in that folder.
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
REFERENCE_FILE = rf"{SKILL}\.md"
DESIGN_READS_RE = re.compile(
    r"^goated-design-reads:[ \t]+(?:none:[ \t]+(\S.*)|"
    rf"({REFERENCE_FILE}(?:[ \t]*,[ \t]*{REFERENCE_FILE})*))$"
)
MIN_REASON_WORDS = 3
FENCE_PREFIXES = ("```", "~~~")

FIXTURE_PATH = Path("stack") / "fixtures" / "markers" / "lines.yaml"
# Kept apart from lines.yaml, which adapters and the skill-usage mod embed whole.
DESIGN_READS_FIXTURE_PATH = FIXTURE_PATH.with_name("design-reads.yaml")


@dataclass
class ReplyMarkers:
    """Markers found in one reply: the winning route, skips, design-reads
    lines, and malformed lines."""

    route: dict[str, object] | None = None
    skips: list[dict[str, str]] = field(default_factory=list)
    design_reads: list[dict[str, object]] = field(default_factory=list)
    malformed: list[str] = field(default_factory=list)

    @property
    def design_read_files(self) -> list[str]:
        """Every file the design-reads lines name, first seen first.

        Lines only add; a `none` line contributes nothing.
        """

        files: list[str] = []
        for line in self.design_reads:
            for name in line.get("files", []):
                if name not in files:
                    files.append(name)
        return files


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


def parse_design_reads_line(line: str) -> dict[str, object] | None:
    """Return the references a candidate line declares, or None if invalid."""

    match = DESIGN_READS_RE.match(line)
    if not match:
        return None
    reason, files = match.groups()
    if reason is not None:
        reason = reason.strip()
        if len(reason.split()) < MIN_REASON_WORDS:
            return None
        return {"form": "none", "reason": reason}
    names = [name.strip() for name in files.split(",")]
    if len(set(names)) != len(names):
        return None
    return {"form": "files", "files": names}


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
            reads = parse_design_reads_line(line)
            if reads is None:
                result.malformed.append(line)
            else:
                result.design_reads.append(reads)
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


def _check_design_reads_replies(replies: object, label: str) -> list[Finding]:
    """Check how whole replies accumulate design-reads lines.

    They live in their own fixture file, so an adapter that does not read
    design-reads lines yet still agrees with every fixture in `lines.yaml`.
    """

    if not isinstance(replies, list) or not replies:
        return [Finding(label, "design_reads_replies must be a non-empty list")]
    findings: list[Finding] = []
    for reply in replies:
        if not isinstance(reply, dict) or not isinstance(reply.get("text"), str):
            findings.append(Finding(label, "each reply needs an identifier and text"))
            continue
        parsed = parse_reply(reply["text"])
        actual = {
            "files": parsed.design_read_files,
            "lines": parsed.design_reads,
            "malformed": parsed.malformed,
        }
        if actual != reply.get("expect"):
            findings.append(
                Finding(
                    label,
                    f"design-reads reply {reply.get('identifier')!r} "
                    f"parsed as {actual!r}",
                )
            )
    return findings


def _load_fixture(repo: Path, fixture: Path) -> tuple[dict | None, str, list[Finding]]:
    path = repo / fixture
    label = fixture.as_posix() if not path.exists() else relative(path, repo)
    data, findings = load_mapping(path, label)
    return data, label, findings


def _validate_design_reads_fixtures(repo: Path) -> list[Finding]:
    data, label, findings = _load_fixture(repo, DESIGN_READS_FIXTURE_PATH)
    if data is None:
        return findings
    findings.extend(
        _check_lines(
            data.get("design_reads_lines"),
            parse_design_reads_line,
            "design_reads_lines",
            label,
        )
    )
    findings.extend(
        _check_design_reads_replies(data.get("design_reads_replies"), label)
    )
    return findings


def validate_marker_fixtures(repo: Path) -> list[Finding]:
    """Check that every marker fixture agrees with the reference grammar."""

    return _validate_route_and_skip_fixtures(repo) + _validate_design_reads_fixtures(
        repo
    )


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
