"""Behavior tests for the route-line and skip-line reference checker."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.validate_skills import validate_marker_fixtures
from scripts.validation.markers import parse_reply


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "stack" / "fixtures" / "markers" / "lines.yaml"


class ReplyParsingTests(unittest.TestCase):
    def test_reads_route_and_skips_from_a_reply(self) -> None:
        result = parse_reply(
            "Plan settled.\n"
            "goated-route: standard | requires: tdd, doc-sync\n"
            "goated-skip: handoff: work finishes in this turn\n"
        )

        self.assertEqual(
            result.route,
            {"form": "route", "intensity": "standard", "requires": ["tdd", "doc-sync"]},
        )
        self.assertEqual(
            result.skips,
            [{"skill": "handoff", "reason": "work finishes in this turn"}],
        )
        self.assertEqual(result.malformed, [])

    def test_fenced_examples_do_not_emit_markers(self) -> None:
        result = parse_reply("```text\ngoated-route: direct\n```\n")

        self.assertIsNone(result.route)

    def test_malformed_marker_is_reported_not_accepted(self) -> None:
        result = parse_reply("goated-route: standard | requires: tdd, tdd\n")

        self.assertIsNone(result.route)
        self.assertEqual(result.malformed, ["goated-route: standard | requires: tdd, tdd"])

    def test_short_skip_reason_is_malformed(self) -> None:
        result = parse_reply("goated-skip: doc-sync: not needed\n")

        self.assertEqual(result.skips, [])
        self.assertEqual(result.malformed, ["goated-skip: doc-sync: not needed"])

    def test_a_design_reads_line_is_not_a_marker(self) -> None:
        # Ticket 089: the line left the grammar, so one an agent still writes is prose.
        result = parse_reply(
            "goated-design-reads: process.md, errors.md\n"
            "goated-design-reads: references/process.md\n"
        )

        self.assertIsNone(result.route)
        self.assertEqual(result.skips, [])
        self.assertEqual(result.malformed, [])
        # The near miss: a malformed skip line beside it is still reported.
        result = parse_reply("goated-design-reads: errors.md\ngoated-skip: tdd: no\n")
        self.assertEqual(result.malformed, ["goated-skip: tdd: no"])

class MarkerFixtureValidationTests(unittest.TestCase):
    def test_current_marker_fixtures_are_valid(self) -> None:
        self.assertEqual(validate_marker_fixtures(REPO_ROOT), [])

    def test_fixture_whose_expectation_disagrees_with_grammar_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            target = repo / "stack" / "fixtures" / "markers"
            shutil.copytree(FIXTURE.parent, target)
            data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
            data["route_lines"]["invalid"].append(
                {"line": "goated-route: direct", "why": "wrongly listed"}
            )
            (target / "lines.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")

            findings = validate_marker_fixtures(repo)

        self.assertTrue(
            any("goated-route: direct" in finding.message for finding in findings)
        )

    def test_the_missing_fixture_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            findings = validate_marker_fixtures(Path(temp_dir))

        # One finding for lines.yaml; design-reads.yaml is gone (Ticket 089).
        self.assertEqual(len(findings), 1)
        self.assertIn("lines.yaml", findings[0].path)

    def test_the_design_reads_fixture_is_gone(self) -> None:
        self.assertFalse(FIXTURE.with_name("design-reads.yaml").exists())


if __name__ == "__main__":
    unittest.main()
