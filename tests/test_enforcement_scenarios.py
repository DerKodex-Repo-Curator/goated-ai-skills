"""The conformance scenarios under `stack/fixtures/enforcement/` (Ticket 079).

Each scenario is valid against the event model, names no harness, and gets
the decision it expects at every judged step from today's Claude Code
adapter. Together they cover each gate of the contract holding, each way it
clears, and a near miss.
"""

from __future__ import annotations

import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from claude_code_scenarios import run_scenario
from enforcement_support import (
    contract_closeout_labels, contract_gates, scenario_files, validator,
)

# Names only a harness, or a harness's hook or tool, would use: whole words,
# case-sensitive, so "read" or "pipeline" in prose is fine.
HARNESS_NAMES = re.compile(
    r"\b(?:Claude|PreToolUse|PostToolUse|UserPromptSubmit|SessionStart|Stop|SubagentStop"
    r"|Bash|PowerShell|Edit|MultiEdit|NotebookEdit|Write|Read|Skill|Task|Agent"
    r"|OpenCode|Codex|Orca|Pi)\b|mcp__"
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


def _scenarios() -> list[dict]:
    return [scenario for document in scenario_files().values()
            for scenario in document["scenarios"]]


def _judged(scenario: dict) -> list[tuple[str, dict]]:
    """Each call or turn end the scenario judges, as a key that is the same
    for the same call, with the decision it expects."""

    judged = []
    for step in scenario["steps"]:
        if "call" in step:
            key = json.dumps(step["call"], sort_keys=True)
        elif "turn_end" in step:
            key = "turn_end"
        else:
            continue
        judged.append((key, step.get("expect", {"decision": "allow"})))
    return judged


def _held_by(expect: dict, gate: str) -> bool:
    return any(hold["gate"] == gate for hold in expect.get("holds", []))


class ScenarioCoverageTests(unittest.TestCase):
    def test_every_contract_gate_holds_and_has_a_near_miss(self) -> None:
        covered = {(c["gate"], c["case"]) for s in _scenarios() for c in s["covers"]}
        for gate in contract_gates():
            with self.subTest(gate):
                self.assertEqual([case for case in ("holds", "near-miss")
                                  if (gate, case) not in covered], [])

    def test_scenarios_cover_only_gates_the_contract_names(self) -> None:
        gates = contract_gates()
        for scenario in _scenarios():
            for cover in scenario["covers"]:
                with self.subTest(scenario["name"], gate=cover["gate"]):
                    self.assertIn(cover["gate"], gates)

    def test_each_case_is_shown_by_the_scenario_itself(self) -> None:
        """A scenario that says a gate holds shows it holding; one that says
        it clears shows the same call held without the clearing step and
        allowed with it; a near miss never holds by that gate."""

        for scenario in _scenarios():
            judged = _judged(scenario)
            for cover in scenario["covers"]:
                gate, case = cover["gate"], cover["case"]
                with self.subTest(scenario["name"], gate=gate, case=case):
                    held = {key for key, expect in judged if _held_by(expect, gate)}
                    allowed = {key for key, expect in judged if expect["decision"] == "allow"}
                    if case == "holds":
                        self.assertTrue(held)
                    elif case == "clears":
                        self.assertTrue(held & allowed)
                    elif case == "near-miss":
                        self.assertFalse(held)

    def test_a_scenario_covers_a_joint_hold(self) -> None:
        joint = [step for scenario in _scenarios() for step in scenario["steps"]
                 if len(step.get("expect", {}).get("holds", [])) > 1]
        self.assertTrue(joint)

    def test_every_closeout_label_is_pinned_by_a_scenario(self) -> None:
        pinned = {label for scenario in _scenarios() for step in scenario["steps"]
                  for hold in step.get("expect", {}).get("holds", [])
                  for label in hold.get("items", [])}
        self.assertEqual(sorted(contract_closeout_labels() - pinned), [])
        self.assertEqual(sorted(pinned - contract_closeout_labels()), [])

    def test_every_closeout_hold_names_its_items(self) -> None:
        for scenario in _scenarios():
            for step in scenario["steps"]:
                for hold in step.get("expect", {}).get("holds", []):
                    if hold["gate"] == "closeout":
                        with self.subTest(scenario["name"]):
                            self.assertIn("items", hold)


class EventModelVersionTests(unittest.TestCase):
    REQUEST = {
        "event_model": 3,
        "session": {"id": "s1", "agent": {"role": "main"}},
        "project": {"folders": ["/work/app"], "working_folder": "/work/app", "home": "/home/u"},
        "turns": [{"key": "t1", "opener": {"type": "prompt", "author": "person", "text": "Go."},
                   "entries": []}],
        "event": {"type": "turn_end"},
    }

    def test_a_request_of_the_known_version_is_valid(self) -> None:
        self.assertEqual(list(validator().iter_errors(self.REQUEST)), [])

    def test_a_request_of_an_unknown_version_is_rejected(self) -> None:
        for version in (1, 2, 4, 0, "3"):
            with self.subTest(version=version):
                request = copy.deepcopy(self.REQUEST)
                request["event_model"] = version
                self.assertTrue(list(validator().iter_errors(request)))

    def test_a_decision_carries_several_holds_in_order_only_when_it_holds(self) -> None:
        check = validator("decision")
        holds = [{"gate": "router-first", "kind": "strict", "text": "Load the router."},
                 {"gate": "route-line", "kind": "strict", "text": "Write a route line."}]
        self.assertEqual(list(check.iter_errors(
            {"event_model": 3, "decision": "hold", "holds": holds, "notices": []})), [])
        self.assertTrue(list(check.iter_errors(
            {"event_model": 3, "decision": "allow", "holds": holds, "notices": []})))
        self.assertTrue(list(check.iter_errors(
            {"event_model": 3, "decision": "hold", "holds": [], "notices": []})))


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
