"""The conformance runner and the worked example adapter (Ticket 083).

`scripts/run_conformance.py` runs the conformance scenarios through an
adapter by way of a translator its author writes. The worked example in
`adapters/example/` is a toy tool loop with its adapter and translator:
it passes every scenario, by the Python call and by the command, and sends
only requests the event model allows. An adapter that never blocks, and a
translator that maps a tool wrongly, fail the scenarios they should, by
name, with the expected and actual decision.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from enforcement_support import validator

from scripts import run_conformance

EXAMPLE = run_conformance.REPO_ROOT / "adapters" / "example"
EXAMPLE_TRANSLATOR = EXAMPLE / "conformance_translator.py"
BROKEN_TRANSLATOR = Path(__file__).resolve().parent / "broken_conformance_translator.py"
RUNNER = run_conformance.REPO_ROOT / "scripts" / "run_conformance.py"
DESIGN_HOLDS = "writes: a substantial code change waits for design principles"

sys.path.insert(0, str(EXAMPLE))

import conformance_translator as example  # noqa: E402
import goated_example_adapter as adapter  # noqa: E402
import toy_loop  # noqa: E402


def _run_all(make) -> dict[str, list[str]]:
    scenarios = run_conformance.load_scenarios()
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = pool.map(lambda pair: run_conformance.run_scenario(*pair, make), scenarios)
    return {result.name: result.failures for result in results}


def _example_with(setup: dict, adapter_class=None, judge=None):
    """The example translator over an adapter of `adapter_class`, asking
    the core through `judge` (by default the Python call)."""

    hooks = (adapter_class or adapter.GoatedAdapter)(
        setup["project"], setup["home"], "conformance-session",
        installed_skills=setup["installed_skills"], agent=setup["agent"],
        judge=judge or adapter.python_judge(setup["state_dir"]))
    return example.Translator(setup, hooks)


class WorkedExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sent: list[tuple[dict, dict]] = []

        def recording(setup: dict):
            judge = adapter.python_judge(setup["state_dir"])

            def recorded(request: dict) -> dict:
                decision = judge(request)
                cls.sent.append((request, decision))
                return decision

            return _example_with(setup, judge=recorded)

        cls.failures = _run_all(recording)

    def test_the_worked_example_passes_every_scenario_through_the_runner(self) -> None:
        self.assertEqual(len(self.failures), len(run_conformance.load_scenarios()))
        for name, failures in self.failures.items():
            with self.subTest(name):
                self.assertEqual(failures, [])

    def test_every_request_the_example_sends_is_valid_against_the_event_model(self) -> None:
        request, decision = validator(), validator("decision")
        self.assertTrue(self.sent)
        for sent, got in self.sent:
            self.assertEqual([e.message for e in request.iter_errors(sent)], [])
            self.assertEqual([e.message for e in decision.iter_errors(got)], [])

    def test_the_example_passes_by_the_core_command_too(self) -> None:
        def by_command(setup: dict):
            return _example_with(setup, judge=adapter.command_judge(setup["state_dir"]))

        results = run_conformance.run_scenarios(by_command, only="design principles")
        self.assertTrue(results)
        for result in results:
            with self.subTest(result.name):
                self.assertEqual(result.failures, [])

    def test_an_agent_in_the_loop_answers_a_hold_and_its_call_then_runs(self) -> None:
        ran: list[str] = []

        def write(args: dict):
            ran.append(args["path"])
            return toy_loop.ToolOutput(text="written")

        def agent(loop) -> bool:
            output = loop.use_tool("edit_file", {"path": "notes.md",
                                                 "edits": [{"old": "a", "new": "b"}]})
            if output.blocked:
                # The hold names its gate and the skill to load; the agent
                # loads it and writes the route line the hold asks for.
                self.assertIn("goated-hold: router-first | strict", output.text)
                loop.use_tool("use_skill", {"name": "using-goated-ai-skills"})
                loop.say("goated-route: direct")
                return False
            return True

        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            hooks = adapter.GoatedAdapter(home / "work" / "app", home, "demo",
                                          installed_skills=["using-goated-ai-skills"],
                                          judge=adapter.python_judge(home / "state"))
            loop = toy_loop.ToolLoop({"edit_file": write, "use_skill": lambda args:
                                      toy_loop.ToolOutput(text="loaded")}, hooks)
            loop.run_turn("Tidy the notes.", agent)
        self.assertEqual(ran, ["notes.md"])
        self.assertEqual(loop.transcript[-1], {"role": "end"})
        self.assertEqual([kind for kind, _ in hooks.decisions][:2],
                         ["prompt_submitted", "pending_call"])

    def test_a_decision_the_core_could_not_make_lets_the_call_run_and_says_so(self) -> None:
        from goated_core.request import fail_open

        hooks = adapter.GoatedAdapter(Path("/work/app"), Path("/home/u"), "s",
                                      judge=lambda request: fail_open("it was not reachable"))
        loop = toy_loop.ToolLoop({"edit_file": lambda args: toy_loop.ToolOutput()}, hooks)
        loop.submit("Change it.")
        output = loop.use_tool("edit_file", {"path": "a.py", "edits": [{"old": "a", "new": "b"}]})
        self.assertFalse(output.blocked)
        shown = [item["text"] for item in loop.transcript if item["role"] == "harness"]
        self.assertTrue(shown)
        self.assertTrue(all("allowed without checks" in text for text in shown))


class RunnerBitesTests(unittest.TestCase):
    def test_an_adapter_that_never_blocks_fails_a_scenario_that_holds(self) -> None:
        class NeverBlocks(adapter.GoatedAdapter):
            def before_tool(self, loop, use):
                answer = super().before_tool(loop, use)
                return toy_loop.HookAnswer(
                    messages=answer.messages[1:] if answer.block else answer.messages)

        [result] = run_conformance.run_scenarios(
            lambda setup: _example_with(setup, NeverBlocks), only=DESIGN_HOLDS)
        self.assertFalse(result.passed)
        self.assertIn("step 4 (call file_write): expected {'decision': 'hold', 'holds': "
                      "[('design', 'justified-skip')]", result.failures[0])
        self.assertIn("got {'decision': 'allow', 'holds': []", result.failures[0])

    def test_a_translator_that_maps_writes_wrongly_fails_the_write_scenarios(self) -> None:
        failures = _run_all(run_conformance.load_translator(str(BROKEN_TRANSLATOR)))
        self.assertIn("got {'decision': 'allow'", failures[DESIGN_HOLDS][0])
        # The near miss: every scenario with no file write still passes.
        no_writes = {name for name, scenario in run_conformance.load_scenarios()
                     if all(step.get("call", {}).get("kind") != "file_write"
                            for step in scenario["steps"])}
        self.assertTrue(no_writes)
        self.assertEqual({name: failures[name] for name in no_writes if failures[name]}, {})


class RunnerCommandTests(unittest.TestCase):
    def run_command(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(RUNNER), *args], capture_output=True,
                              text=True, cwd=run_conformance.REPO_ROOT)

    def test_the_command_reports_each_scenario_and_exits_zero_when_all_pass(self) -> None:
        done = self.run_command(str(EXAMPLE_TRANSLATOR), "--only", "design principles")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn(f"PASS {DESIGN_HOLDS}\n", done.stdout)
        self.assertRegex(done.stdout, r"\n(\d+) of \1 scenarios passed\n$")

    def test_the_command_names_a_failing_scenario_with_both_decisions(self) -> None:
        done = self.run_command(str(BROKEN_TRANSLATOR), "--file", "writes", "--only",
                                "a substantial code change")
        self.assertEqual(done.returncode, 1)
        self.assertIn(f"FAIL {DESIGN_HOLDS}\n    step 4 (call file_write): expected "
                      "{'decision': 'hold'", done.stdout)
        self.assertIn("got {'decision': 'allow'", done.stdout)
        self.assertIn("0 of 1 scenarios passed", done.stdout)

    def test_the_command_refuses_a_translator_it_cannot_find(self) -> None:
        done = self.run_command(str(EXAMPLE / "missing.py"))
        self.assertEqual(done.returncode, 2)
        self.assertIn("no translator file", done.stderr)

    def test_the_command_fails_when_no_scenario_matches(self) -> None:
        done = self.run_command(str(EXAMPLE_TRANSLATOR), "--only", "no such scenario")
        self.assertEqual(done.returncode, 1)
        self.assertIn("0 of 0 scenarios passed", done.stdout)


if __name__ == "__main__":
    unittest.main()
