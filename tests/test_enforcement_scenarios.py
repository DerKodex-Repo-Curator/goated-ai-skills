"""The conformance scenarios under `stack/fixtures/enforcement/` (Ticket 079).

Each scenario is valid against the event model, names no harness, and gets
the decision it expects at every judged step from today's Claude Code
adapter. Together they cover each gate of the contract holding, each way it
clears, and a near miss.
"""

from __future__ import annotations

import copy
import re
import tempfile
import unittest
from pathlib import Path

from claude_code_scenarios import run_scenario
from enforcement_support import contract_gates, scenario_files, validator

# Names only a harness, or a harness's hook or tool, would use.
HARNESS_NAMES = re.compile(
    r"\b(?:Claude|PreToolUse|PostToolUse|UserPromptSubmit|SessionStart|MultiEdit|NotebookEdit"
    r"|OpenCode|Codex|Orca)\b|mcp__|\bPi Agent\b"
)


class ScenarioFileTests(unittest.TestCase):
    def test_there_are_scenario_files(self) -> None:
        self.assertTrue(scenario_files())

    def test_every_scenario_file_is_valid_against_the_event_model(self) -> None:
        check = validator("scenario_file")
        for path, document in scenario_files().items():
            with self.subTest(path.name):
                self.assertEqual([e.message for e in check.iter_errors(document)], [])

    def test_no_scenario_names_a_harness_or_its_tools(self) -> None:
        for path in scenario_files():
            with self.subTest(path.name):
                self.assertIsNone(HARNESS_NAMES.search(path.read_text(encoding="utf-8")))


class ScenarioCoverageTests(unittest.TestCase):
    def covered(self) -> set[tuple[str, str, str]]:
        return {(c["gate"], c["case"], c.get("way", ""))
                for document in scenario_files().values()
                for scenario in document["scenarios"] for c in scenario["covers"]}

    def test_every_contract_gate_holds_clears_each_way_and_has_a_near_miss(self) -> None:
        covered = self.covered()
        for gate, ways in contract_gates().items():
            with self.subTest(gate):
                missing = [case for case in ("holds", "near-miss")
                           if (gate, case, "") not in covered]
                missing += [f"clears by {way}" for way in sorted(ways)
                            if (gate, "clears", way) not in covered]
                self.assertEqual(missing, [])

    def test_scenarios_cover_only_gates_and_ways_the_contract_names(self) -> None:
        gates = contract_gates()
        for gate, case, way in self.covered():
            with self.subTest(gate=gate, case=case, way=way):
                self.assertIn(gate, gates)
                if case == "clears":
                    self.assertIn(way, gates[gate])

    def test_a_scenario_covers_a_joint_hold(self) -> None:
        joint = [step for document in scenario_files().values()
                 for scenario in document["scenarios"] for step in scenario["steps"]
                 if len(step.get("expect", {}).get("holds", [])) > 1]
        self.assertTrue(joint)


class EventModelVersionTests(unittest.TestCase):
    REQUEST = {
        "event_model": 1,
        "session": {"id": "s1", "agent": {"role": "main"}},
        "project": {"folders": ["/work/app"], "working_folder": "/work/app", "home": "/home/u"},
        "turns": [{"key": "t1", "opener": {"type": "prompt", "author": "person", "text": "Go."},
                   "entries": []}],
        "event": {"type": "turn_end"},
    }

    def test_a_request_of_the_known_version_is_valid(self) -> None:
        self.assertEqual(list(validator().iter_errors(self.REQUEST)), [])

    def test_a_request_of_an_unknown_version_is_rejected(self) -> None:
        for version in (2, 0, "1"):
            with self.subTest(version=version):
                request = copy.deepcopy(self.REQUEST)
                request["event_model"] = version
                self.assertTrue(list(validator().iter_errors(request)))

    def test_a_decision_carries_several_holds_in_order_only_when_it_holds(self) -> None:
        check = validator("decision")
        holds = [{"gate": "router-first", "kind": "strict", "text": "Load the router."},
                 {"gate": "route-line", "kind": "strict", "text": "Write a route line."}]
        self.assertEqual(list(check.iter_errors(
            {"event_model": 1, "decision": "hold", "holds": holds, "notices": []})), [])
        self.assertTrue(list(check.iter_errors(
            {"event_model": 1, "decision": "allow", "holds": holds, "notices": []})))
        self.assertTrue(list(check.iter_errors(
            {"event_model": 1, "decision": "hold", "holds": [], "notices": []})))


class ClaudeCodeConformanceTests(unittest.TestCase):
    """Every scenario, translated into the Claude Code adapter's hook input,
    gets the decision it expects at every judged step."""

    def test_every_scenario_passes_against_the_claude_code_adapter(self) -> None:
        request = validator()
        for path, document in scenario_files().items():
            for scenario in document["scenarios"]:
                with self.subTest(f"{path.stem}: {scenario['name']}"):
                    with tempfile.TemporaryDirectory() as folder:
                        result = run_scenario(Path(folder), scenario)
                    self.assertEqual(result.failures, [])
                    for built in result.requests:
                        self.assertEqual([e.message for e in request.iter_errors(built)], [])


if __name__ == "__main__":
    unittest.main()
