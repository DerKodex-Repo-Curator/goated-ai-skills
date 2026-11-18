"""The shared core's two ways in (Ticket 081, ADR 0004).

The Python call (`goated_core.request.decide`) and the command
(`adapters/core/goated_judge.py`) take one event-model request and answer
one decision. Every conformance scenario gets the decision it expects at
each step through both, and the two give the same decision at every step.
A request the core cannot read, or of a version it does not know, is
allowed with a reason; sessions with different ids keep their own state.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from core_scenarios import (
    COMMAND, command_judge, python_judge, run_scenario,
)
from enforcement_support import scenario_files, validator

from goated_core import request as core_request

WRITE = {"type": "pending_call", "call": {
    "kind": "file_write", "id": "w1", "path": "/work/app/src/app.py",
    "edits": [{"removed": "a = 1\n", "added": "a = 2\n"}]}}


def _request(session_id: str = "s1", **changes) -> dict:
    request = {
        "event_model": 2,
        "session": {"id": session_id, "agent": {"role": "main"}},
        "project": {"folders": ["/work/app"], "working_folder": "/work/app",
                    "home": "/home/u", "installed_skills": []},
        "turns": [{"key": "t1", "opener": {"type": "prompt", "author": "person",
                                           "text": "Change the app."}, "entries": []}],
        "event": WRITE,
    }
    request.update(changes)
    return request


def _command(text: str, state_dir: Path) -> dict:
    done = subprocess.run([sys.executable, str(COMMAND), "--state-dir", str(state_dir)],
                          input=text.encode("utf-8"), capture_output=True, check=True)
    return json.loads(done.stdout.decode("utf-8"))


class CoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = Path(self._tmp.name) / "state"
        self.settings = core_request.Settings(self.state_dir)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def decide(self, request) -> dict:
        decision = core_request.decide(request, self.settings)
        self.assertEqual([e.message for e in validator("decision").iter_errors(decision)], [])
        return decision


class FailOpenTests(CoreTestCase):
    def assert_allowed_with_reason(self, decision: dict, reason: str) -> None:
        self.assertEqual(decision["decision"], "allow")
        self.assertEqual(decision["holds"], [])
        self.assertEqual([n["kind"] for n in decision["notices"]], ["fail_open"])
        self.assertIn(reason, decision["notices"][0]["text"])
        self.assertIn("allowed without checks", decision["notices"][0]["text"])

    def test_a_request_that_is_not_json_is_allowed_with_a_reason(self) -> None:
        decision = _command("{not json", self.state_dir)
        self.assert_allowed_with_reason(decision, "could not read the request")

    def test_a_request_the_core_cannot_read_is_allowed_with_a_reason(self) -> None:
        for broken in (["a list"], {"event_model": 2}, _request(turns="none"),
                       _request(event={"type": "pending_call", "call": {"kind": "file_write"}})):
            with self.subTest(request=broken):
                self.assert_allowed_with_reason(self.decide(broken), "could not read the request")

    def test_a_request_of_an_unknown_version_is_allowed_with_a_reason(self) -> None:
        for version in (1, 3, "2", None):
            with self.subTest(version=version):
                decision = self.decide(_request(event_model=version))
                self.assert_allowed_with_reason(decision, "event model version")

    def test_a_request_with_no_version_names_the_missing_key(self) -> None:
        decision = self.decide({"version": "9.9"})
        self.assert_allowed_with_reason(decision, "has no event_model")

    def test_the_command_answers_json_python_cannot_parse_with_a_reason(self) -> None:
        # An integer longer than Python's digit limit, and nesting deeper
        # than its recursion limit, both stop the parser itself.
        for text in ('{"event_model": 2, "n": ' + "1" * 5000 + "}",
                     "[" * 100_000 + "]" * 100_000):
            with self.subTest(text=text[:20]):
                self.assert_allowed_with_reason(_command(text, self.state_dir),
                                                "could not read the request")

    def test_a_request_nested_too_deep_to_read_is_allowed_with_a_reason(self) -> None:
        entries: list = []
        for n in range(3000):
            entries = [{"type": "call", "call": {"kind": "spawn", "brief": "", "starts_now": True},
                        "result": {"ok": True, "agent": {"id": f"a{n}", "entries": entries}}}]
        request = _request()
        request["turns"][0]["entries"] = entries
        self.assert_allowed_with_reason(self.decide(request), "could not read the request")

    def test_the_command_answers_an_unknown_version_the_same_way(self) -> None:
        decision = _command(json.dumps(_request(event_model=3)), self.state_dir)
        self.assert_allowed_with_reason(decision, "event model version 3")

    def test_a_readable_request_of_the_known_version_is_judged(self) -> None:
        # The near miss: the same write, well formed, meets router-first.
        decision = self.decide(_request())
        self.assertEqual(decision["decision"], "hold")
        self.assertEqual(decision["holds"][0]["gate"], "router-first")
        self.assertEqual(decision["notices"], [])


class SessionStateTests(CoreTestCase):
    def test_two_sessions_with_different_ids_keep_separate_state(self) -> None:
        # The turn markers are session state: a session's second hold of the
        # same ask in a turn is short, while another session's first is full.
        first = self.decide(_request("session-a"))["holds"][0]["text"]
        again = self.decide(_request("session-a"))["holds"][0]["text"]
        other = self.decide(_request("session-b"))["holds"][0]["text"]
        self.assertNotEqual(again, first)
        self.assertEqual(other, first)

    def test_ids_that_differ_only_in_unsafe_characters_keep_separate_state(self) -> None:
        # The near miss: `a.b` and `a_b`, and ids differing only in case or
        # past their 128th character, are different sessions.
        long = "s" * 128
        for one, other in (("a.b", "a_b"), ("Sess", "sess"), (long + "1", long + "2")):
            with self.subTest(one=one, other=other):
                first = self.decide(_request(one))["holds"][0]["text"]
                self.assertEqual(self.decide(_request(other))["holds"][0]["text"], first)

    def test_turn_keys_that_differ_only_in_unsafe_characters_are_different_turns(self) -> None:
        turn = _request()["turns"][0]
        first = self.decide(_request(turns=[{**turn, "key": "t.1"}]))["holds"][0]["text"]
        other = self.decide(_request(turns=[{**turn, "key": "t_1"}]))["holds"][0]["text"]
        self.assertEqual(other, first)

    def test_state_is_kept_under_the_folder_the_caller_names(self) -> None:
        self.decide(_request("session-a"))
        self.assertTrue((self.state_dir / "session-a.json").is_file())


class WordingTests(CoreTestCase):
    def test_no_decision_carries_an_unfilled_wording_slot(self) -> None:
        from goated_core import wording
        shell = {"type": "pending_call", "call": {
            "kind": "shell_command", "id": "c1", "command": "git commit -m x",
            "shell": "posix"}}
        for event in (WRITE, shell):
            with self.subTest(event=event["call"]["kind"]):
                text = json.dumps(self.decide(_request(event=event)))
                self.assertNotIn(wording.OPEN, text)
                self.assertNotIn(wording.CLOSE, text)


def _scenarios() -> list[tuple[str, dict]]:
    return [(f"{path.stem}: {scenario['name']}", scenario)
            for path, document in scenario_files().items()
            for scenario in document["scenarios"]]


def _run_both(scenario: dict):
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        by_call = run_scenario(root / "python", scenario, python_judge(root / "python-state"))
        by_command = run_scenario(root / "command", scenario,
                                  command_judge(root / "command-state"))
    return by_call, by_command


class ConformanceTests(unittest.TestCase):
    """Every scenario, through both ways in."""

    @classmethod
    def setUpClass(cls) -> None:
        scenarios = _scenarios()
        with ThreadPoolExecutor(max_workers=8) as pool:
            cls.results = dict(zip((name for name, _ in scenarios),
                                   pool.map(lambda pair: _run_both(pair[1]), scenarios)))

    def test_every_scenario_passes_through_the_python_call(self) -> None:
        for name, (by_call, _) in self.results.items():
            with self.subTest(name):
                self.assertEqual(by_call.failures, [])

    def test_every_scenario_passes_through_the_command(self) -> None:
        for name, (_, by_command) in self.results.items():
            with self.subTest(name):
                self.assertEqual(by_command.failures, [])

    def test_the_two_ways_in_give_the_same_decision_at_every_step(self) -> None:
        for name, (by_call, by_command) in self.results.items():
            with self.subTest(name):
                self.assertEqual(len(by_call.exchanges), len(by_command.exchanges))
                for (_, called), (_, commanded) in zip(by_call.exchanges, by_command.exchanges):
                    self.assertEqual(_neutral_paths(called), _neutral_paths(commanded))

    def test_every_request_and_decision_is_valid_against_the_event_model(self) -> None:
        request, decision = validator(), validator("decision")
        for name, (by_call, _) in self.results.items():
            with self.subTest(name):
                for sent, got in by_call.exchanges:
                    self.assertEqual([e.message for e in request.iter_errors(sent)], [])
                    self.assertEqual([e.message for e in decision.iter_errors(got)], [])


def _neutral_paths(decision: dict) -> dict:
    """`decision` with the run's own folder names, which differ between the
    two runs, made alike."""

    text = json.dumps(decision)
    for folder in ("python", "command"):
        text = text.replace(f"/{folder}/", "/run/")
    return json.loads(text)


if __name__ == "__main__":
    unittest.main()
