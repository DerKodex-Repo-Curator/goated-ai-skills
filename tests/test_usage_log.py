"""The neutral usage log and its report (Ticket 082).

The core appends what each event showed to a local log, in the format
`stack/schemas/usage-log.schema.json` documents: holds with what they ask,
their outcomes, skill loads with their cause, route and skip lines,
reference reads. Both ways into the core write the same entries, the
Claude Code adapter's apart from its name. All content is synthetic.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from jsonschema import Draft202012Validator

from claude_code_adapter_support import ROUTER, Session
from core_scenarios import run_scenario
from usage_log_session import recorded_session

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = REPO_ROOT / "adapters" / "core"
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from goated_core import request as core_request  # noqa: E402
from goated_core import usage_log  # noqa: E402

REPORT = CORE_DIR / "goated_usage_report.py"
REGISTRY = REPO_ROOT / "stack" / "goated-stack.yaml"
SCHEMA = REPO_ROOT / "stack" / "schemas" / "usage-log.schema.json"
SESSION = "scenario-session"
EDIT = {"kind": "file_write", "path": "src/export.py",
        "edits": [{"removed": "limit = 1", "added": "limit = 2"}]}
# A hold and its clearing: router-first and route-line hold an edit, the
# router loads and a route line follows, and the edit goes through.
ROUTED_EDIT = {"name": "a routed edit", "steps": [
    {"prompt": {"type": "prompt", "author": "person", "text": "Fix the export bug."}},
    {"call": EDIT, "expect": {"decision": "hold", "holds": [
        {"gate": "router-first", "kind": "strict"}, {"gate": "route-line", "kind": "strict"}]}},
    {"call": {"kind": "skill_load", "skill": ROUTER}},
    {"reply": "goated-route: direct"},
    {"call": EDIT},
]}


def clock() -> float:
    return 1000.0


def core_log(root: Path, scenario: dict, log_path: Path) -> list[dict]:
    """Run `scenario` through the core's request call, logging to `log_path`."""

    log = usage_log.UsageLog(log_path, "worked-example", clock=clock)
    settings = core_request.Settings(root / "core-state", registry_path=REGISTRY, usage_log=log)
    run = run_scenario(root, scenario, lambda request: core_request.decide(request, settings))
    assert not run.failures, run.failures
    return usage_log.read_log(log_path).entries


def report_command(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(REPORT), *args], capture_output=True,
                          text=True, encoding="utf-8")


def without(entries: list[dict], *fields: str) -> list[dict]:
    return [{k: v for k, v in entry.items() if k not in fields} for entry in entries]


class CoreLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.log_path = self.root / "logs" / "usage-log.jsonl"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_a_hold_and_its_clearing_are_logged_in_order(self) -> None:
        entries = core_log(self.root, ROUTED_EDIT, self.log_path)
        common = {"log": usage_log.LOG_VERSION, "t": 1000.0, "adapter": "worked-example",
                  "session": SESSION}
        project = entries[0]["project"]
        self.assertRegex(project, r"^[0-9a-f]{10}$")
        self.assertEqual(without(entries, "project"), [
            {**common, "type": "prompt", "named": []},
            {**common, "type": "hold", "gate": "router-first", "kind": "strict",
             "named": [ROUTER]},
            {**common, "type": "hold", "gate": "route-line", "kind": "strict", "named": []},
            {**common, "type": "load", "skill": ROUTER, "cause": "hold"},
            {**common, "type": "route", "form": "direct"},
            {**common, "type": "outcome", "gate": "router-first", "outcome": "answered"},
            {**common, "type": "outcome", "gate": "route-line", "outcome": "answered"},
        ])
        self.assertTrue(all(entry["project"] == project for entry in entries))

    def test_a_claude_code_session_logs_the_same_entries_but_the_adapter_name(self) -> None:
        core = core_log(self.root, ROUTED_EDIT, self.log_path)
        claude = self.claude_code_log(self.root, self.log_path.with_name("claude-code.jsonl"))
        self.assertEqual({entry["adapter"] for entry in claude}, {"claude-code"})
        self.assertEqual(without(claude, "adapter"), without(core, "adapter"))

    def test_a_route_line_in_a_later_turn_logs_under_its_own_prompt(self) -> None:
        # Near miss: a second turn's facts follow its own prompt, never the first's.
        scenario = {"name": "two turns", "steps": [
            *ROUTED_EDIT["steps"],
            {"prompt": {"type": "prompt", "author": "person", "text": "Use `tdd` now."}},
            {"call": {"kind": "skill_load", "skill": "tdd"}},
            {"reply": "goated-route: direct\n"
                      "goated-skip: doc-sync: no durable docs describe the export limit"},
            {"call": EDIT},
        ]}
        entries = core_log(self.root, scenario, self.log_path)
        second = [e["type"] for e in entries][[e["type"] for e in entries].index("prompt", 1):]
        self.assertEqual(second, ["prompt", "load", "route", "skip"])
        load = next(e for e in entries if e["type"] == "load" and e["skill"] == "tdd")
        self.assertEqual(load["cause"], "named")
        skip = next(e for e in entries if e["type"] == "skip")
        self.assertEqual(skip["reason"], "no durable docs describe the export limit")

    def test_a_log_that_cannot_be_written_never_changes_the_decision(self) -> None:
        self.log_path.mkdir(parents=True)  # A folder where the log file should be.
        log = usage_log.UsageLog(self.log_path, "worked-example", clock=clock)
        settings = core_request.Settings(self.root / "core-state", registry_path=REGISTRY,
                                         usage_log=log)
        run = run_scenario(self.root, {"name": "unwritable", "steps": ROUTED_EDIT["steps"][:2]},
                           lambda request: core_request.decide(request, settings))
        decisions = [decision for _, decision in run.exchanges]
        self.assertEqual([d["decision"] for d in decisions], ["allow", "hold"])
        self.assertEqual([h["gate"] for h in decisions[1]["holds"]], ["router-first", "route-line"])
        # Said once per session, not at every event.
        self.assertEqual([[n["kind"] for n in d["notices"]] for d in decisions], [["warning"], []])
        self.assertIn("could not write the usage log", decisions[0]["notices"][0]["text"])

    def test_no_path_prompt_text_or_file_content_reaches_the_log(self) -> None:
        secret = "D:/work/private-client/plan.md"
        scenario = {"name": "private words", "steps": [
            {"prompt": {"type": "prompt", "author": "person",
                        "text": f"Read {secret} and fix the acme-payroll export."}},
            {"call": {"kind": "file_read", "path": secret, "whole": True},
             "result": {"ok": True, "output": "acme-payroll salaries"}},
            {"call": {"kind": "skill_load", "skill": ROUTER}},
            {"reply": f"goated-skip: tdd: the file {secret} has no tests for acme-payroll"},
            {"call": {"kind": "file_read", "whole": False,
                      "path": "/opt/agent/.claude/skills/tdd/references/test-design.md"}},
            {"turn_end": True},
        ]}
        entries = core_log(self.root, scenario, self.log_path)
        text = self.log_path.read_text(encoding="utf-8")
        for private in ("private-client", "someone", "salaries", "Read C:", "fix the"):
            self.assertNotIn(private, text)
        skip = next(e for e in entries if e["type"] == "skip")
        self.assertEqual(skip["reason"], "the file <path> has no tests for acme-payroll")
        ref = next(e for e in entries if e["type"] == "ref")
        self.assertEqual(ref, {**ref, "skill": "tdd", "file": "references/test-design.md",
                               "read_tool": True, "partial": True})

    def test_a_project_folder_named_skills_is_no_skill_and_file_digests_are_salted(self) -> None:
        own = "src/skills/payroll-export/q3-layoffs.txt"
        scenario = {"name": "own skills folder", "steps": [
            {"prompt": {"type": "prompt", "author": "person", "text": "Look."}},
            {"call": {"kind": "file_read", "path": own, "whole": True}},
            {"call": {"kind": "shell_command", "shell": "posix", "command": f"cat {own}"}},
            {"turn_end": True},
        ]}
        entries = core_log(self.root, scenario, self.log_path)
        self.assertEqual([e["type"] for e in entries], ["prompt", "file_read", "turn_end"])
        self.assertNotIn("payroll", self.log_path.read_text(encoding="utf-8"))
        # The same path in a log with another salt has another digest, so a
        # guessed path cannot be checked without the log's salt.
        (self.root / "again").mkdir()
        again = core_log(self.root / "again", scenario, self.root / "other" / "usage-log.jsonl")
        self.assertRegex(entries[1]["file"], r"^[0-9a-f]{16}$")
        self.assertNotEqual(entries[1]["file"], again[1]["file"])

    def test_skip_reasons_mask_every_path_form_and_keep_words(self) -> None:
        cases = {
            "see `src/export.py` first": "see `<path>` first",
            'the file "docs/a/b.md" is old': 'the file "<path>" is old',
            "nothing (a/b/c) needed": "nothing (<path>) needed",
            "read https://example.com/x today": "read <path> today",
            "edit src/x.ts, then stop": "edit <path>, then stop",
            "and/or ~5 words stay": "and/or ~5 words stay",
            "C:\\work\\x and ~/notes": "<path> and <path>",
        }
        for reason, kept in cases.items():
            with self.subTest(reason=reason):
                self.assertEqual(usage_log.stored_reason(reason), kept)

    def test_a_log_of_an_unknown_version_is_refused_with_a_clear_message(self) -> None:
        core_log(self.root, ROUTED_EDIT, self.log_path)
        self.assertTrue(usage_log.read_log(self.log_path).entries)  # Near miss: version 1 reads.
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"log": 2, "type": "prompt"}) + "\n")
        with self.assertRaisesRegex(usage_log.LogUnreadable,
                                    r"line 8 .* log version 2, which this reader does not know"):
            usage_log.read_log(self.log_path).entries
        done = report_command("--log", str(self.log_path))
        self.assertEqual(done.returncode, 1)
        self.assertIn("log version 2", done.stderr)
        self.assertEqual(done.stdout, "")

    def test_lines_that_are_no_entry_are_skipped_and_counted_not_fatal(self) -> None:
        core_log(self.root, ROUTED_EDIT, self.log_path)
        good = len(usage_log.read_log(self.log_path).entries)
        common = {"log": 1, "t": 1.0, "adapter": "x", "session": "s", "project": None}
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write('{"log": 1, "t": 1.0, "adap\n')  # Cut short by a writer.
            handle.write("[1, 2]\n")
            handle.write(json.dumps({**common, "type": "load", "cause": "agent"}) + "\n")
            handle.write(json.dumps({**common, "type": "hold", "gate": "g", "kind": "strict",
                                     "named": [], "items": [{"skill": "tdd"}]}) + "\n")
            handle.write(json.dumps({**common, "type": "turn_end"}) + "\n")
        reading = usage_log.read_log(self.log_path)
        self.assertEqual((len(reading.entries), reading.skipped), (good + 2, 3))
        done = report_command("--log", str(self.log_path))
        self.assertEqual(done.returncode, 0, done.stderr)
        # The hold whose item has no label is counted as skipped too, not a crash.
        self.assertIn("4 lines were skipped as no entry.", done.stdout)

    def test_the_report_lists_projects_and_keeps_one_by_its_folder(self) -> None:
        core_log(self.root, ROUTED_EDIT, self.log_path)
        project = usage_log.read_log(self.log_path).entries[0]["project"]
        done = report_command("--log", str(self.log_path))
        self.assertIn(f"| {project} | 1 |", done.stdout)
        folder = self.root / "home" / "work" / "project"
        mine = report_command("--log", str(self.log_path), "--project-folder", str(folder))
        self.assertIn("1 sessions", mine.stdout)
        # Near miss: another folder keeps nothing.
        other = report_command("--log", str(self.log_path), "--project-folder", str(self.root))
        self.assertIn("0 sessions, from none.", other.stdout)

    def test_the_report_summarises_both_adapters_and_filters_them_apart(self) -> None:
        core_log(self.root, ROUTED_EDIT, self.log_path)
        self.claude_code_log(self.root, self.log_path)  # The same log, a second adapter.
        project = usage_log.read_log(self.log_path).entries[0]["project"]

        both = report_command("--log", str(self.log_path))
        self.assertEqual(both.returncode, 0, both.stderr)
        self.assertIn("2 sessions, from `claude-code`, `worked-example`.", both.stdout)
        self.assertIn(f"| {ROUTER} | 0 | 0 | 2 | 0 | 0 | 0 | 2 |", both.stdout)
        self.assertIn("| router-first | 2 | 2 | 0 | 0 | 0 |", both.stdout)
        self.assertIn("| direct | 2 |", both.stdout)

        one = report_command("--log", str(self.log_path), "--adapter", "claude-code")
        self.assertIn("1 sessions, from `claude-code`.", one.stdout)
        self.assertIn("| router-first | 1 | 1 | 0 | 0 | 0 |", one.stdout)

        mine = report_command("--log", str(self.log_path), "--project", project)
        self.assertIn("2 sessions", mine.stdout)
        # Near miss: another project's key keeps nothing.
        other = report_command("--log", str(self.log_path), "--project", "0000000000")
        self.assertIn("0 sessions, from none.", other.stdout)
        self.assertNotIn("router-first", other.stdout)

    def test_the_command_logs_where_the_caller_says(self) -> None:
        request = {"event_model": 3, "session": {"id": "s1", "agent": {"role": "main"}},
                   "project": {"folders": [str(self.root)], "working_folder": str(self.root),
                               "home": str(self.root)},
                   "turns": [{"key": "t1", "entries": [], "opener": {
                       "type": "prompt", "author": "person", "text": "Hello."}}],
                   "event": {"type": "prompt_submitted"}}
        done = subprocess.run(
            [sys.executable, str(CORE_DIR / "goated_judge.py"), "--state-dir",
             str(self.root / "state"), "--usage-log", str(self.log_path)],
            input=json.dumps(request), capture_output=True, text=True, check=True,
            env={**os.environ, core_request.ADAPTER_ENV: "worked-example"})
        self.assertEqual(json.loads(done.stdout)["decision"], "allow")
        entries = usage_log.read_log(self.log_path).entries
        self.assertEqual([(e["type"], e["adapter"]) for e in entries],
                         [("prompt", "worked-example")])

    def test_off_keeps_no_log_and_only_the_claude_code_adapter_has_a_default(self) -> None:
        from goated_adapter import Config

        with mock.patch.dict(os.environ, {usage_log.LOG_ENV: "OFF"}):
            self.assertIsNone(usage_log.path_from_environment())
            self.assertIsNone(Config.from_environment().usage_log)
            self.assertIsNone(core_request.settings_from_environment().usage_log)
        with mock.patch.dict(os.environ, {}):
            os.environ.pop(usage_log.LOG_ENV, None)
            self.assertEqual(Config.from_environment().usage_log.path, usage_log.default_path())
            # Near miss: the command and `decide` keep no log unless one is named.
            self.assertIsNone(core_request.settings_from_environment().usage_log)
            named = core_request.settings_from_environment(log_path=str(self.log_path))
            self.assertEqual(named.usage_log.path, self.log_path)
            self.assertIsNone(core_request.settings_from_environment(log_path="off").usage_log)

    def test_the_default_log_is_a_per_user_folder_not_a_project(self) -> None:
        # The process environment is the edge the location is read from.
        with mock.patch.dict(os.environ, {"LOCALAPPDATA": "D:/AppData/Local",
                                          "XDG_STATE_HOME": "/xdg/state"}):
            os.environ.pop(usage_log.LOG_ENV, None)
            expected = (Path("D:/AppData/Local") if os.name == "nt"
                        else Path("/xdg/state")) / "goated" / "usage-log.jsonl"
            self.assertEqual(usage_log.path_from_environment(), expected)
            os.environ[usage_log.LOG_ENV] = str(self.log_path)
            self.assertEqual(usage_log.path_from_environment(), self.log_path)
            self.assertEqual(usage_log.path_from_environment("/named.jsonl"),
                             Path("/named.jsonl"))

    def test_every_entry_written_matches_the_documented_format(self) -> None:
        validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")))
        entries = [*core_log(self.root, ROUTED_EDIT, self.log_path), *recorded_session()["log"]]
        self.assertEqual({e["type"] for e in entries} - {"prompt", "hold", "load", "route",
                                                          "outcome", "override", "skip", "ref",
                                                          "skill_read", "file_read", "change",
                                                          "turn_end"}, set())
        for entry in entries:
            with self.subTest(entry=entry["type"]):
                self.assertEqual([e.message for e in validator.iter_errors(entry)], [])
        # Near miss: a hold that kept its text, or a prompt that kept its words, is no entry.
        hold = next(e for e in entries if e["type"] == "hold")
        self.assertTrue(list(validator.iter_errors({**hold, "text": "Load the skill."})))
        prompt = next(e for e in entries if e["type"] == "prompt")
        self.assertTrue(list(validator.iter_errors({**prompt, "text": "Fix the export bug."})))

    @staticmethod
    def claude_code_log(root: Path, log_path: Path) -> list[dict]:
        """The scenario of `ROUTED_EDIT` as a Claude Code session in the same
        project, logging to `log_path` beside the core's log (one salt)."""

        s = Session(root, SESSION)
        s.config.usage_log = usage_log.UsageLog(log_path, "claude-code", clock=clock)
        edit = {"file_path": str(s.project / "src" / "export.py"),
                "old_string": "limit = 1", "new_string": "limit = 2"}
        s.prompt("Fix the export bug.")
        s.call("Edit", edit)
        s.load(ROUTER)
        s.say("goated-route: direct")
        s.call("Edit", edit)
        return usage_log.read_log(log_path).entries


# Each writer process appends `count` one-entry batches, as hooks of
# parallel sessions do, through the recorder's public flush.
WRITER = """
import sys
sys.path.insert(0, sys.argv[1])
from pathlib import Path
from goated_core import usage_log
log = usage_log.UsageLog(Path(sys.argv[2]), "writer")
for n in range(int(sys.argv[4])):
    r = usage_log.Recorder(log, Path(sys.argv[3]), f"session-{sys.argv[5]}", None, None,
                           frozenset)
    r.turn_end()
    warning = r.flush()
    assert warning is None, warning
"""


class LogFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.log_path = self.root / "logs" / "usage-log.jsonl"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def flush_one(self) -> str | None:
        r = usage_log.Recorder(usage_log.UsageLog(self.log_path, "t"), self.root / "state", "s",
                               None, str(self.root), frozenset)
        r.turn_end()
        return r.flush()

    @unittest.skipIf(os.name == "nt", "POSIX folder modes")
    def test_the_log_folder_is_private_and_a_shared_one_is_refused(self) -> None:
        self.assertIsNone(self.flush_one())
        self.assertEqual(self.log_path.parent.stat().st_mode & 0o077, 0)
        self.assertEqual((self.log_path.parent / usage_log.SALT_NAME).stat().st_mode & 0o077, 0)
        # Near miss: a folder others may write to is not trusted with the log.
        self.log_path.parent.chmod(0o777)
        self.assertIn("not private", self.flush_one() or "")

    def test_writers_in_many_processes_lose_and_mix_no_line(self) -> None:
        processes, count = 8, 150
        writers = [subprocess.Popen([sys.executable, "-c", WRITER, str(CORE_DIR),
                                     str(self.log_path), str(self.root / "state"), str(count),
                                     str(n)], stderr=subprocess.PIPE)
                   for n in range(processes)]
        for writer in writers:
            _, error = writer.communicate(timeout=120)
            self.assertEqual(writer.returncode, 0, error.decode("utf-8", "replace"))
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), processes * count)
        reading = usage_log.read_log(self.log_path)
        self.assertEqual((len(reading.entries), reading.skipped), (processes * count, 0))
        self.assertEqual({e["session"] for e in reading.entries},
                         {f"session-{n}" for n in range(processes)})


if __name__ == "__main__":
    unittest.main()
