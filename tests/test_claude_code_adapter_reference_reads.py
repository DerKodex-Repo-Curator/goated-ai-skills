"""Ticket 067: the `reference-reads` gate holds an edit until the skill
references the registry declares for its signals have been read.

Each test drives the hook entry point with a transcript in Claude Code's
recorded shape (see `claude_code_adapter_support.py`), reading the
registry at `Config.registry_path`: this repo's own `stack/goated-stack.yaml`
for the first enforced set, or a fixture registry written by the test.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from claude_code_adapter_support import (
    BRIEF,
    REPO_ROOT,
    ROUTER,
    Session,
    decision,
    parse,
    reason,
)
from goated_adapter import Config, reference_reads

REGISTRY = REPO_ROOT / "stack" / "goated-stack.yaml"
SKILLS = "/opt/goated/skills"
MOCKING = f"{SKILLS}/tdd/references/mocking-and-seams.md"
TEST_DESIGN = f"{SKILLS}/tdd/references/test-design.md"
WAITING = f"{SKILLS}/diagnose/references/condition-based-waiting.md"
TEST_FILE = "tests/test_export.py"
CODE_FILE = "src/export.py"
SKIP_TDD = "goated-skip: tdd: the mock is an existing shared fixture"
GATE_LINE = "goated-hold: reference-reads | justified-skip"


def edit(path: str, *lines: str) -> dict:
    return {"file_path": path, "old_string": "pass", "new_string": "\n".join(lines)}


def plain_lines(count: int) -> list[str]:
    """Test lines that match no registry pattern."""

    return [f"assert total_{n} == {n}" for n in range(count)]


def hold_line(output: dict) -> str:
    return reason(output).split("\n", 1)[0]


def stop(s: Session) -> dict:
    return parse(s.hook("Stop", stop_hook_active=False, last_assistant_message=""))


class ReferenceReadsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._sessions = 0

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def session(self, registry: Path | None = REGISTRY) -> Session:
        self._sessions += 1
        folder = self.root / f"s{self._sessions}"
        folder.mkdir()
        s = Session(folder, session_id=f"session-{self._sessions}")
        s.project.mkdir(parents=True)
        s.config.registry_path = registry
        return s

    def first_turn(self, *skills: str, registry: Path | None = REGISTRY,
                   prompt: str = "Work on the exporter.") -> Session:
        s = self.session(registry)
        s.prompt(prompt)
        s.load(ROUTER)
        s.say("goated-route: direct")
        for skill in skills:
            s.load(skill)
        return s

    @staticmethod
    def later_turn(s: Session) -> Session:
        stop(s)
        s.prompt("Carry on.")
        s.say("goated-route: continue")
        return s

    def assertHeldFor(self, output: dict, path: str) -> None:
        self.assertEqual(hold_line(output), GATE_LINE, reason(output))
        self.assertIn(f"`{path}`", reason(output))

    def assertPasses(self, output: dict) -> None:
        self.assertEqual(decision(output), "pass", reason(output))


class MockingAndSeams(ReferenceReadsTestCase):
    """AC: with `tdd` loaded, a test edit adding a mock is held until
    `mocking-and-seams.md` is read; one with no mock is not held for it."""

    def test_a_mock_in_a_test_edit_is_held_until_the_reference_is_read(self) -> None:
        s = self.first_turn("tdd")
        held = s.call("Edit", edit(TEST_FILE, "client = MagicMock()"))
        self.assertHeldFor(held, "tdd/references/mocking-and-seams.md")
        self.assertIn("`goated-skip: tdd: <reason>`", reason(held))
        self.assertIn("mock-or-patch", reason(held))
        self.assertIn('"MagicMock"', reason(held))
        s.read(MOCKING)
        self.assertPasses(s.call("Edit", edit(TEST_FILE, "client = MagicMock()")))

    def test_each_form_of_a_mock_or_patch_is_held(self) -> None:
        for added in ('@patch("export.client")', "monkeypatch.setattr(export, 'x', 1)",
                      "store = FakeStore()", "fetch = jest.fn()", "spy = vi.spyOn(api, 'get')",
                      "from unittest import mock", "client = mocker.Mock()"):
            with self.subTest(added=added):
                s = self.first_turn("tdd")
                self.assertHeldFor(s.call("Edit", edit(TEST_FILE, added)),
                                   "tdd/references/mocking-and-seams.md")

    def test_a_test_edit_with_no_mock_is_not_held_for_it(self) -> None:
        s = self.first_turn("tdd")
        for added in ("assert dispatch(order) == 3", "# a mock would hide the bug here",
                      "assert hotpatching_level == 2"):
            with self.subTest(added=added):
                self.assertPasses(s.call("Edit", edit(TEST_FILE, added)))

    def test_a_mock_outside_a_test_file_is_not_held_for_it(self) -> None:
        s = self.first_turn("tdd")
        self.assertPasses(s.call("Edit", edit(CODE_FILE, "client = MagicMock()")))

    def test_a_write_of_a_new_test_file_with_a_mock_is_held(self) -> None:
        s = self.first_turn("tdd")
        held = s.call("Write", {"file_path": TEST_FILE, "content": "from unittest import mock\n"})
        self.assertHeldFor(held, "tdd/references/mocking-and-seams.md")

    def test_an_edit_keeping_a_mock_its_old_text_held_is_not_held(self) -> None:
        s = self.first_turn("tdd")
        self.assertPasses(s.call("Edit", {
            "file_path": TEST_FILE, "old_string": "client = MagicMock()\nassert run(client)",
            "new_string": "client = MagicMock()\nassert run(client) == 1",
        }))

    def test_a_multiedit_carrying_a_mock_is_held(self) -> None:
        s = self.first_turn("tdd")
        held = s.call("MultiEdit", {"file_path": TEST_FILE, "edits": [
            {"old_string": "a = 1", "new_string": "a = 2"},
            {"old_string": "pass", "new_string": "client = MagicMock()"},
        ]})
        self.assertHeldFor(held, "tdd/references/mocking-and-seams.md")


class NotLoaded(ReferenceReadsTestCase):
    """AC: with `tdd` not loaded, neither edit is held by the gate."""

    def test_neither_edit_is_held_while_tdd_does_not_count_as_loaded(self) -> None:
        s = self.first_turn()
        self.assertPasses(s.call("Edit", edit(TEST_FILE, "client = MagicMock()")))
        self.assertPasses(s.call("Edit", edit(TEST_FILE, *plain_lines(6))))

    def test_another_skills_load_does_not_count(self) -> None:
        s = self.first_turn("diagnose")
        self.assertPasses(s.call("Edit", edit(TEST_FILE, "client = MagicMock()")))


class TestDesign(ReferenceReadsTestCase):
    """AC: a four-line test edit is not held for `test-design.md`; a five-line one is."""

    def test_four_lines_pass_and_five_lines_are_held(self) -> None:
        s = self.first_turn("tdd")
        self.assertPasses(s.call("Edit", edit(TEST_FILE, *plain_lines(4))))
        held = s.call("Edit", edit(TEST_FILE, *plain_lines(5)))
        self.assertHeldFor(held, "tdd/references/test-design.md")
        self.assertNotIn("mocking-and-seams.md", reason(held))
        s.read(TEST_DESIGN)
        self.assertPasses(s.call("Edit", edit(TEST_FILE, *plain_lines(5))))

    def test_five_lines_of_non_test_code_are_not_held_for_it(self) -> None:
        s = self.first_turn("tdd")
        held = s.call("Edit", edit(CODE_FILE, *[f"total_{n} = {n}" for n in range(5)]))
        # The design gate holds a substantial code edit; this gate does not.
        self.assertNotEqual(hold_line(held), GATE_LINE)
        self.assertPasses(s.call("Edit", edit(CODE_FILE, *[f"total_{n} = {n}" for n in range(4)])))

    def test_lines_kept_from_the_old_text_do_not_count(self) -> None:
        context = ["def test_a():", "    x = 1", "    y = 2", "    z = 3", "    assert x"]
        s = self.first_turn("tdd")
        self.assertPasses(s.call("Edit", {
            "file_path": TEST_FILE, "old_string": "\n".join(context),
            "new_string": "\n".join(context[:-1] + ["    assert x == 1"]),
        }))

    def test_a_new_four_line_file_with_a_trailing_newline_is_not_held(self) -> None:
        s = self.first_turn("tdd")
        self.assertPasses(s.call("Write", {"file_path": "tests/test_new.py",
                                           "content": "\n".join(plain_lines(4)) + "\n"}))
        held = s.call("Write", {"file_path": "tests/test_new.py",
                                "content": "\n".join(plain_lines(5)) + "\n"})
        self.assertHeldFor(held, "tdd/references/test-design.md")

    def test_a_write_over_a_test_file_counts_only_the_lines_it_adds(self) -> None:
        s = self.first_turn("tdd")
        existing = s.project / TEST_FILE
        existing.parent.mkdir(parents=True)
        old = "\n".join(plain_lines(8)) + "\n"
        existing.write_text(old, encoding="utf-8")
        self.assertPasses(s.call("Write", {"file_path": TEST_FILE,
                                           "content": old + "assert extra == 9\n"}))

    def test_a_long_test_edit_with_a_mock_asks_for_both(self) -> None:
        s = self.first_turn("tdd")
        held = s.call("Edit", edit(TEST_FILE, "client = MagicMock()", *plain_lines(4)))
        self.assertHeldFor(held, "tdd/references/test-design.md")
        self.assertIn("`tdd/references/mocking-and-seams.md`", reason(held))


class ConditionBasedWaiting(ReferenceReadsTestCase):
    """AC: with `diagnose` loaded, an edit adding a sleep is held until
    `condition-based-waiting.md` is read; the word in a comment does not count."""

    def test_a_sleep_is_held_until_the_reference_is_read(self) -> None:
        s = self.first_turn("diagnose")
        held = s.call("Edit", edit(CODE_FILE, "time.sleep(0.5)"))
        self.assertHeldFor(held, "diagnose/references/condition-based-waiting.md")
        self.assertIn("`goated-skip: diagnose: <reason>`", reason(held))
        s.read(WAITING)
        self.assertPasses(s.call("Edit", edit(CODE_FILE, "time.sleep(0.5)")))

    def test_each_form_of_a_sleep_retry_or_timeout_is_held(self) -> None:
        for path, added in ((CODE_FILE, "for attempt in retry(3):"),
                            (CODE_FILE, "response = get(url, timeout=5)"),
                            ("src/poll.ts", "setTimeout(check, 100)"),
                            (CODE_FILE, "await asyncio.sleep(1)"),
                            (CODE_FILE, "while not ready: poll()"),
                            (CODE_FILE, "MAX_RETRIES = 3"),
                            (CODE_FILE, "poll_interval = 5"),
                            ("src/poll.ts", "const pollInterval = 5"),
                            ("src/e2e.ts", "await page.waitForSelector('#ok')"),
                            (TEST_FILE, "wait_for_element(page)"),
                            (TEST_FILE, "wait_for(lambda: done)")):
            with self.subTest(added=added):
                s = self.first_turn("diagnose")
                self.assertHeldFor(s.call("Edit", edit(path, added)),
                                   "diagnose/references/condition-based-waiting.md")

    def test_the_word_in_a_comment_or_another_word_does_not_count(self) -> None:
        s = self.first_turn("diagnose")
        for added in ("# no sleep or retry: the event fires once", "value = retrieve(key)",
                      "count = pollen + 1", "label = waitformat(1)", "x = pollenCount",
                      '"""Waits for nothing; no timeout."""',
                      "total = 1  # retry once if this fails"):
            with self.subTest(added=added):
                self.assertPasses(s.call("Edit", edit(CODE_FILE, added)))

    def test_a_sleep_in_a_document_is_not_held(self) -> None:
        s = self.first_turn("diagnose")
        self.assertPasses(s.call("Edit", edit("docs/guide.md", "Sleep a second, then retry.")))

    def test_a_sleep_outside_the_project_is_not_held(self) -> None:
        s = self.first_turn("diagnose")
        outside = str(s.root / "scratch" / "probe.py")
        self.assertPasses(s.call("Edit", edit(outside, "time.sleep(1)")))


class ReadsCount(ReferenceReadsTestCase):
    """AC: after the read, a later matching edit passes until a compaction."""

    def test_a_read_counts_in_later_turns_until_a_compaction(self) -> None:
        s = self.first_turn("tdd")
        s.read(MOCKING)
        self.assertPasses(s.call("Edit", edit(TEST_FILE, "client = MagicMock()")))
        self.later_turn(s)
        self.assertPasses(s.call("Edit", edit(TEST_FILE, "client = MagicMock()")))
        stop(s)
        s.compact()
        s.prompt("Carry on.")
        s.load(ROUTER)
        s.say("goated-route: continue")
        s.load("tdd")
        self.assertHeldFor(s.call("Edit", edit(TEST_FILE, "client = MagicMock()")),
                           "tdd/references/mocking-and-seams.md")

    def test_a_failed_read_or_a_shell_print_does_not_count(self) -> None:
        s = self.first_turn("tdd")
        s.read(MOCKING, success=False)
        s.run(f"cat {MOCKING}")
        self.assertHeldFor(s.call("Edit", edit(TEST_FILE, "client = MagicMock()")),
                           "tdd/references/mocking-and-seams.md")

    def test_a_read_of_another_skills_file_of_that_name_does_not_count(self) -> None:
        s = self.first_turn("tdd")
        s.read(f"{SKILLS}/diagnose/references/mocking-and-seams.md")
        self.assertHeldFor(s.call("Edit", edit(TEST_FILE, "client = MagicMock()")),
                           "tdd/references/mocking-and-seams.md")

    def test_a_windows_path_counts(self) -> None:
        s = self.first_turn("tdd")
        s.read("D:\\goated\\skills\\tdd\\references\\mocking-and-seams.md")
        self.assertPasses(s.call("Edit", edit(TEST_FILE, "client = MagicMock()")))


class SkipLine(ReferenceReadsTestCase):
    """AC: a skip line naming the skill clears the hold for the turn only."""

    def test_a_skip_line_clears_the_skills_references_for_the_turn(self) -> None:
        s = self.first_turn("tdd")
        s.say(SKIP_TDD)
        self.assertPasses(s.call("Edit", edit(TEST_FILE, "client = MagicMock()")))
        self.assertPasses(s.call("Edit", edit(TEST_FILE, *plain_lines(5))))
        self.later_turn(s)
        self.assertHeldFor(s.call("Edit", edit(TEST_FILE, "client = MagicMock()")),
                           "tdd/references/mocking-and-seams.md")

    def test_a_skip_line_naming_another_skill_does_not_clear_it(self) -> None:
        s = self.first_turn("tdd", "diagnose")
        s.say("goated-skip: diagnose: the wait is the system under test")
        held = s.call("Edit", edit(TEST_FILE, "client = MagicMock()", "time.sleep(1)"))
        self.assertHeldFor(held, "tdd/references/mocking-and-seams.md")
        self.assertNotIn("condition-based-waiting.md", reason(held))

    def test_a_hold_naming_two_skills_names_no_single_way_out(self) -> None:
        s = self.first_turn("tdd", "diagnose")
        held = s.call("Edit", edit(TEST_FILE, "client = MagicMock()", "time.sleep(1)"))
        self.assertIn("`goated-skip: diagnose: <reason>`", reason(held))
        self.assertIn("`goated-skip: tdd: <reason>`", reason(held))
        self.assertIn("`skip <skill>`", reason(held))
        self.assertNotIn("`skip diagnose`", reason(held))

    def test_a_typed_skip_clears_it(self) -> None:
        s = self.first_turn("tdd", prompt="Work on the exporter. skip tdd")
        self.assertPasses(s.call("Edit", edit(TEST_FILE, "client = MagicMock()")))


class RegistryEntries(ReferenceReadsTestCase):
    """AC: a registry entry of an existing kind is enforced with no adapter change."""

    def fixture_registry(self) -> Path:
        path = self.root / "fixture-stack.yaml"
        path.write_text(
            "schema_version: 1.0.0\n"
            "reference_patterns:\n"
            "  - name: sleep-retry-or-timeout\n"
            "    description: Added text introduces a sleep.\n"
            "skills:\n"
            "  - name: prototype\n"
            "    path: skills/engineering/prototype/SKILL.md\n"
            "    domains: [software]\n"
            "    references:\n"
            "      - file: spike-waits.md\n"
            "        signal:\n"
            "          kind: edit-adds-pattern\n"
            "          pattern: sleep-retry-or-timeout\n"
            "      - file: spike-notes.md\n"
            "        advisory: Whether a spike is done is a judgment no tool call shows.\n"
            "  - name: tdd\n"
            "    path: skills/engineering/tdd/SKILL.md\n"
            "    references:\n"
            "      - file: long-tests.md\n"
            "        signal:\n"
            "          kind: edit-of-file-kind\n"
            "          file_kind: test\n"
            "          min_added_lines: 2\n"
            "      - file: spawn-brief.md\n"
            "        signal:\n"
            "          kind: existing-rule\n"
            "          gate: spawn\n"
            "      - file: later.md\n"
            "        signal:\n"
            "          kind: write-under-path\n"
            "          path: docs/specs/\n",
            encoding="utf-8",
        )
        return path

    def test_fixture_entries_of_the_edit_kinds_are_enforced(self) -> None:
        registry = self.fixture_registry()
        s = self.first_turn("prototype", registry=registry)
        self.assertHeldFor(s.call("Edit", edit(CODE_FILE, "time.sleep(1)")),
                           "prototype/references/spike-waits.md")
        s = self.first_turn("tdd", registry=registry)
        self.assertPasses(s.call("Edit", edit(TEST_FILE, *plain_lines(1))))
        held = s.call("Edit", edit(TEST_FILE, *plain_lines(2)))
        self.assertHeldFor(held, "tdd/references/long-tests.md")
        # The fixture replaced the real registry, so its references are all there is.
        self.assertNotIn("test-design.md", reason(held))

    def test_other_kinds_and_advisory_entries_ask_for_nothing_here(self) -> None:
        s = self.first_turn("tdd", "prototype", registry=self.fixture_registry())
        self.assertPasses(s.call("Write", {"file_path": "docs/specs/x.md", "content": "# X\n"}))
        self.assertPasses(s.call("Edit", edit("docs/notes.md", "Some notes.")))

    def test_the_reader_gives_what_the_registry_declares(self) -> None:
        data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
        expected = sorted(
            (skill["name"], entry["file"], entry["signal"])
            for skill in data["skills"] for entry in skill.get("references", [])
            if "signal" in entry
        )
        found = sorted((r.skill, r.file, r.signal) for r in reference_reads.load(REGISTRY))
        self.assertEqual(found, expected)


class NoRegistry(ReferenceReadsTestCase):
    """AC: with no readable registry, the gate holds nothing."""

    def test_a_missing_or_unreadable_registry_holds_nothing(self) -> None:
        broken = self.root / "broken.yaml"
        broken.write_text("skills:\n  - name: tdd\n    references: |\n      text\n", encoding="utf-8")
        not_a_file = self.root / "folder.yaml"
        not_a_file.mkdir()
        indentless = self.root / "indentless.yaml"
        indentless.write_text("skills:\n- name: tdd\n  references: []\n", encoding="utf-8")
        for registry in (None, self.root / "missing.yaml", broken, not_a_file, indentless):
            with self.subTest(registry=registry):
                s = self.first_turn("tdd", "diagnose", registry=registry)
                self.assertPasses(s.call("Edit", edit(TEST_FILE, "client = MagicMock()")))
                self.assertPasses(s.call("Edit", edit(CODE_FILE, "time.sleep(1)")))

    def test_the_default_registry_is_the_distributions_beside_the_adapter(self) -> None:
        with mock.patch.dict(os.environ):
            os.environ.pop("GOATED_ADAPTER_REGISTRY", None)
            self.assertEqual(Config.from_environment().registry_path, REGISTRY)
        with mock.patch.dict(os.environ, {"GOATED_ADAPTER_REGISTRY": str(self.root / "r.yaml")}):
            self.assertEqual(Config.from_environment().registry_path, self.root / "r.yaml")

    def warning(self, s: Session) -> str:
        return parse(s.hook("PreToolUse", tool_name="Edit", tool_use_id="toolu_w",
                            tool_input=edit(TEST_FILE, "client = MagicMock()"))).get("systemMessage", "")

    def test_a_registry_that_does_not_parse_warns_and_holds_nothing(self) -> None:
        broken = self.root / "broken.yaml"
        broken.write_text("skills:\n- name: tdd\n", encoding="utf-8")
        s = self.first_turn("tdd", registry=broken)
        output = parse(s.hook("PreToolUse", tool_name="Edit", tool_use_id="toolu_w",
                              tool_input=edit(TEST_FILE, "client = MagicMock()")))
        self.assertPasses(output)
        self.assertIn("registry", output.get("systemMessage", ""))
        self.assertIn("broken.yaml", output.get("systemMessage", ""))

    def test_a_missing_registry_warns_only_when_the_environment_names_it(self) -> None:
        missing = self.root / "missing.yaml"
        s = self.first_turn("tdd", registry=missing)
        self.assertEqual(self.warning(s), "")
        s = self.first_turn("tdd", registry=missing)
        s.config.registry_named = True
        self.assertIn("missing.yaml", self.warning(s))

    def test_a_registry_with_a_malformed_signal_value_declares_nothing(self) -> None:
        for field in ("pattern: [mock-or-patch]", "file_kind: 3", "min_added_lines: five"):
            with self.subTest(field=field):
                registry = self.root / "malformed.yaml"
                kind = "edit-of-file-kind" if field.startswith("min") else "edit-adds-pattern"
                extra = "\n          file_kind: test" if field.startswith("min") else ""
                registry.write_text(
                    "skills:\n  - name: tdd\n    references:\n      - file: x.md\n"
                    f"        signal:\n          kind: {kind}\n          {field}{extra}\n",
                    encoding="utf-8",
                )
                with self.assertRaises(reference_reads.RegistryUnreadable):
                    reference_reads.load(registry)
                s = self.first_turn("tdd", registry=registry)
                self.assertPasses(s.call("Edit", edit(TEST_FILE, "client = MagicMock()", *plain_lines(5))))


class OtherGatesUnchanged(ReferenceReadsTestCase):
    """AC: the `design`, `design-reads` and `spawn` holds are unchanged."""

    def outputs(self, registry: Path | None) -> list[dict]:
        s = self.first_turn("software-design-principles", "tdd", registry=registry)
        s.read(MOCKING)
        s.read(TEST_DESIGN)
        return [
            s.call("Write", {"file_path": "src/new_module.py",
                             "content": "".join(f"VALUE_{n} = {n}\n" for n in range(6))}),
            s.call("Edit", edit(TEST_FILE, *plain_lines(6))),
            s.call("Edit", edit(CODE_FILE, "try:", "    run()", "except OSError:", "    raise")),
            s.spawn("a1", BRIEF),
        ]

    def test_the_other_holds_read_the_same_with_and_without_the_registry(self) -> None:
        with_registry, without = self.outputs(REGISTRY), self.outputs(None)
        self.assertEqual([hold_line(o) for o in with_registry], [
            "goated-hold: design | justified-skip",
            "goated-hold: design-reads | justified-skip",
            "goated-hold: design-reads | justified-skip",
            "goated-hold: spawn | strict",
        ])
        self.assertEqual([reason(o) for o in with_registry], [reason(o) for o in without])

    def test_existing_rule_references_are_not_asked_for_by_this_gate(self) -> None:
        s = self.first_turn("software-design-principles", "handoff")
        s.say("goated-skip: software-design-principles: only adds a test fixture value")
        self.assertPasses(s.call("Edit", edit(TEST_FILE, *plain_lines(6))))


if __name__ == "__main__":
    unittest.main()
