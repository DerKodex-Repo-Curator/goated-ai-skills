"""Ticket 067: the `reference-reads` gate holds an edit until the skill
references the registry declares for its signals have been read.

Each test drives the hook entry point with a transcript in Claude Code's
recorded shape (see `claude_code_adapter_support.py`), reading the
registry at `Config.registry_path`: this repo's own `stack/goated-stack.yaml`
for the first enforced set, or a fixture registry written by the test.
"""

from __future__ import annotations

import os
import re
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
from goated_adapter import Config
from goated_core import reference_reads

REGISTRY = REPO_ROOT / "stack" / "goated-stack.yaml"
SKILLS = "/opt/goated/skills"
MOCKING = f"{SKILLS}/tdd/references/mocking-and-seams.md"
TEST_DESIGN = f"{SKILLS}/tdd/references/test-design.md"
WAITING = f"{SKILLS}/diagnose/references/condition-based-waiting.md"
SPEC_TEMPLATE = f"{SKILLS}/write-a-spec/references/spec-template.md"
TICKET_TEMPLATES = f"{SKILLS}/spec-to-tickets/references/ticket-slicing-templates.md"
ROOT_CAUSE = f"{SKILLS}/diagnose/references/root-cause-tracing.md"
CHECKLIST = f"{SKILLS}/code-security-review/references/security-review-checklist.md"
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

    def test_patch_is_held_only_as_a_call_or_decorator(self) -> None:
        """Round 4, R2: `patch` selects as `patch(`, `@patch`, `mock.patch` or
        `patch.<name>(`; the bare word is a diff or a fix as often as a mock."""

        for added in ('@patch("x")', '@patch.object(export, "client")',
                      'with mock.patch("export.client"):', 'patch.object(export, "client")',
                      'client = patch("export.client")', "m = MagicMock()"):
            with self.subTest(added=added):
                s = self.first_turn("tdd")
                self.assertHeldFor(s.call("Edit", edit(TEST_FILE, added)),
                                   "tdd/references/mocking-and-seams.md")
        s = self.first_turn("tdd")
        for added in ("patch = load_diff()", "assert apply(patch) == 3",
                      "assert patch.applies", "assert apply_patch(diff)"):
            with self.subTest(added=added):
                self.assertPasses(s.call("Edit", edit(TEST_FILE, added)))

    def test_a_mock_word_inside_a_quoted_string_is_not_held_for_it(self) -> None:
        s = self.first_turn("tdd")
        for added in ('assert kind == "patch"', "assert name == 'MagicMock'",
                      'assert run(["mock", "stub"]) == "fake: \\"spy\\""',
                      "label = `a mock`"):
            with self.subTest(added=added):
                self.assertPasses(s.call("Edit", edit(TEST_FILE, added)))

    def test_a_line_whose_strings_cannot_be_read_still_selects(self) -> None:
        """Where a line's strings cannot be read for certain, its words select, as before."""

        for added in ('doc = """uses MagicMock"""', "name = 'MagicMock",
                      'label = f"{MagicMock()}"', "label = `${mock()}`"):
            with self.subTest(added=added):
                s = self.first_turn("tdd")
                self.assertHeldFor(s.call("Edit", edit(TEST_FILE, added)),
                                   "tdd/references/mocking-and-seams.md")

    def test_a_quote_that_opens_no_string_in_its_language_leaves_the_line_unread(self) -> None:
        """Lead review of 100: a Rust lifetime is no string, so its words select."""

        s = self.first_turn("tdd")
        self.assertHeldFor(s.call("Edit", edit("tests/x_test.rs",
                                               "fn f(m: &'a MockDb, n: &'a X) {}")),
                           "tdd/references/mocking-and-seams.md")
        # The near miss: a char literal and a string hold no mock.
        s = self.first_turn("tdd")
        self.assertPasses(s.call("Edit", edit("tests/x_test.rs",
                                              "let c = 'm'; assert_eq!(kind, \"mock\");")))

    def test_a_string_that_interpolates_code_leaves_the_line_unread(self) -> None:
        for path, added in (("tests/a_test.kt", 'val s = "$fakeRepo"'),
                            ("tests/a_test.cs", 'var s = $@"{mock}";'),
                            (TEST_FILE, 'label = t"{mock}"')):
            with self.subTest(added=added):
                s = self.first_turn("tdd")
                self.assertHeldFor(s.call("Edit", edit(path, added)),
                                   "tdd/references/mocking-and-seams.md")
        # The near misses: no interpolation, or `$` in a Python string, which is text.
        for path, added in (("tests/a_test.kt", 'val s = "fake"'),
                            ("tests/a_test.cs", 'var s = @"{mock}";'),
                            (TEST_FILE, 'label = "$mock"')):
            with self.subTest(added=added):
                s = self.first_turn("tdd")
                self.assertPasses(s.call("Edit", edit(path, added)))


class MocksOfCode(ReferenceReadsTestCase):
    """Ticket 115 (spec R6, AC8): the mocking reference is asked for a mock or
    patch of code, not for a patched environment or test data in a string."""

    def test_monkeypatch_selects_only_as_a_patch_of_code(self) -> None:
        for added in ('monkeypatch.setattr(mod, "f", g)', 'monkeypatch.delattr(mod, "f")',
                      "with monkeypatch.context() as m:"):
            with self.subTest(added=added):
                s = self.first_turn("tdd")
                self.assertHeldFor(s.call("Edit", edit(TEST_FILE, added)),
                                   "tdd/references/mocking-and-seams.md")
        s = self.first_turn("tdd")
        for added in ('monkeypatch.setenv("X", "1")', "def test_x(monkeypatch):",
                      'monkeypatch.delenv("X")', 'monkeypatch.setitem(settings, "k", 1)',
                      'monkeypatch.delitem(settings, "k")', "monkeypatch.chdir(tmp_path)",
                      "monkeypatch.syspath_prepend(str(tmp_path))"):
            with self.subTest(added=added):
                self.assertPasses(s.call("Edit", edit(TEST_FILE, added)))

    def test_lines_inside_a_triple_quoted_string_select_nothing(self) -> None:
        s = self.first_turn("tdd")
        for lines in (('CONFIG = """', "[providers.fake]", "fake = true", '"""'),
                      ("write(tmp_path, '''", "[providers.fake]", "''')"),
                      ('config = textwrap.dedent("""', "    [providers.fake]",
                       '""").strip()')):
            with self.subTest(lines=lines):
                self.assertPasses(s.call("Edit", edit(TEST_FILE, *lines)))

    def test_the_same_words_as_code_still_select(self) -> None:
        for lines in (("[providers.fake]",), ("store = Fake()",), ("fake = Fake()",),
                      # A string that opens and closes on one line ends there.
                      ('label = """a"""', "fake = Fake()"),
                      # A docstring is no string these lines are inside.
                      ('"""Docs."""', "fake = Fake()"),
                      # Code after the string has closed.
                      ('CONFIG = """', "[x]", '"""', "store = FakeStore()")):
            with self.subTest(lines=lines):
                s = self.first_turn("tdd")
                self.assertHeldFor(s.call("Edit", edit(TEST_FILE, *lines)),
                                   "tdd/references/mocking-and-seams.md")

    def test_a_line_whose_string_opener_the_edit_does_not_show_is_read_as_today(self) -> None:
        for lines in (("[providers.fake]", '"""'),
                      ("fake = true", '"""', "x = 1")):
            with self.subTest(lines=lines):
                s = self.first_turn("tdd")
                self.assertHeldFor(s.call("Edit", edit(TEST_FILE, *lines)),
                                   "tdd/references/mocking-and-seams.md")

    def test_a_line_that_may_interpolate_code_is_read_as_today(self) -> None:
        for path, lines in ((TEST_FILE, ('text = f"""', "{fake_client()}", '"""')),
                            ("tests/a.test.js", ("const s = `", "${mockApi()}", "`;"))):
            with self.subTest(lines=lines):
                s = self.first_turn("tdd")
                self.assertHeldFor(s.call("Edit", edit(path, *lines)),
                                   "tdd/references/mocking-and-seams.md")
        # The near miss: an f-string line holding no braces is text.
        s = self.first_turn("tdd")
        self.assertPasses(s.call("Edit", edit(TEST_FILE, 'text = f"""', "fake = true", '"""')))

    def test_lines_inside_a_javascript_template_literal_select_nothing(self) -> None:
        s = self.first_turn("tdd")
        self.assertPasses(s.call("Edit", edit("tests/a.test.ts", "const toml = `",
                                              "[providers.fake]", "fake = true", "`;")))
        # The near miss: the same words as code, once the literal has closed.
        s = self.first_turn("tdd")
        self.assertHeldFor(s.call("Edit", edit("tests/a.test.ts", "const toml = `", "[x]", "`;",
                                               "const api = fakeApi();")),
                           "tdd/references/mocking-and-seams.md")

    def test_a_patch_token_ends_at_the_call(self) -> None:
        for added, token in (('patch.object(A, "b")', '("patch.object")'),
                             ('patch ("x")', '("patch")'),
                             ('patch.dict(os.environ, {})', '("patch.dict")')):
            with self.subTest(added=added):
                s = self.first_turn("tdd")
                held = s.call("Edit", edit(TEST_FILE, added))
                self.assertIn(f"adds a mock or patch {token}", reason(held))

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


CODING = "software-design-principles/references/coding.md"
TEST_DESIGN_PATH = "tdd/references/test-design.md"
HELD_PATH_RE = re.compile(r"`([a-z0-9-]+/references/[a-z0-9-]+\.md)`")


class TestEditThresholds(ReferenceReadsTestCase):
    """Ticket 090 (spec R9): with `software-design-principles` and `tdd`
    loaded, a test-file edit requires `coding.md` and `test-design.md` only
    when it creates the file or adds twenty or more lines, an added line being
    one of the new text not in the old text."""

    def required(self, tool: str, tool_input: dict, *, mock_read: bool = True,
                 on_disk: str | None = None) -> set[str]:
        """Every reference the holds of one call ask for, in a turn where both
        skills load: each named is read and the call retried until it passes.
        `on_disk` is the test file's text before the call, if it exists."""

        s = self.first_turn("software-design-principles", "tdd")
        if mock_read:
            s.read(MOCKING)
        if on_disk is not None:
            target = s.project / tool_input["file_path"]
            target.parent.mkdir(parents=True)
            target.write_text(on_disk, encoding="utf-8")
        asked: set[str] = set()
        for _ in range(5):
            output = s.call(tool, tool_input)
            if decision(output) == "pass":
                return asked
            named = set(HELD_PATH_RE.findall(reason(output))) - asked
            self.assertTrue(named, reason(output))
            asked |= named
            for path in named:
                s.read(f"{SKILLS}/{path}")
        self.fail("the call was still held after reading every reference named")

    def test_a_ten_line_edit_of_an_existing_test_file_requires_nothing(self) -> None:
        self.assertEqual(self.required("Edit", edit(TEST_FILE, *plain_lines(10))), set())

    def test_a_write_creating_a_three_line_test_file_requires_both(self) -> None:
        content = "\n".join(plain_lines(3)) + "\n"
        self.assertEqual(self.required("Write", {"file_path": TEST_FILE, "content": content}),
                         {CODING, TEST_DESIGN_PATH})

    def test_a_write_over_a_test_file_on_disk_is_not_a_creation(self) -> None:
        old = "\n".join(plain_lines(8)) + "\n"
        content = "\n".join(plain_lines(11)) + "\n"
        self.assertEqual(self.required("Write", {"file_path": TEST_FILE, "content": content},
                                       on_disk=old), set())

    def test_an_edit_with_no_old_text_creating_the_file_requires_both(self) -> None:
        created = {"file_path": TEST_FILE, "old_string": "",
                   "new_string": "\n".join(plain_lines(3)) + "\n"}
        self.assertEqual(self.required("Edit", created), {CODING, TEST_DESIGN_PATH})
        # The near miss: the same Edit of a file already on disk creates nothing.
        self.assertEqual(self.required("Edit", created, on_disk="\n".join(plain_lines(8)) + "\n"),
                         set())

    def test_a_file_already_on_disk_is_not_created_even_when_empty(self) -> None:
        # A known limit: a file a shell command made (`touch`) is on disk, so a
        # later Write over it is no creation, whatever made it.
        content = "\n".join(plain_lines(3)) + "\n"
        self.assertEqual(self.required("Write", {"file_path": TEST_FILE, "content": content},
                                       on_disk=""), set())

    def test_twenty_added_lines_require_both_and_nineteen_neither(self) -> None:
        self.assertEqual(self.required("Edit", edit(TEST_FILE, *plain_lines(20))),
                         {CODING, TEST_DESIGN_PATH})
        self.assertEqual(self.required("Edit", edit(TEST_FILE, *plain_lines(19))), set())

    def test_unchanged_context_does_not_count_and_a_changed_line_does(self) -> None:
        context = [f"assert kept_{n} == {n}" for n in range(30)]
        four_more = {"file_path": TEST_FILE, "old_string": "\n".join(context),
                     "new_string": "\n".join(context + plain_lines(4))}
        self.assertEqual(self.required("Edit", four_more), set())
        changed = {"file_path": TEST_FILE, "old_string": "\n".join(context[:20]),
                   "new_string": "\n".join(f"assert kept_{n} == {n + 1}" for n in range(20))}
        self.assertEqual(self.required("Edit", changed), {CODING, TEST_DESIGN_PATH})
        nineteen = dict(changed, new_string="\n".join(
            f"assert kept_{n} == {n + 1}" for n in range(19)) + f"\n{context[19]}")
        self.assertEqual(self.required("Edit", nineteen), set())

    def test_a_mock_still_requires_mocking_and_seams_at_any_size(self) -> None:
        self.assertEqual(self.required("Edit", edit(TEST_FILE, "client = MagicMock()"),
                                       mock_read=False),
                         {"tdd/references/mocking-and-seams.md"})
        self.assertEqual(self.required("Edit", edit(TEST_FILE, "client = Client()"),
                                       mock_read=False), set())
        self.assertEqual(self.required("Edit", edit(TEST_FILE, "client = MagicMock()",
                                                    *plain_lines(19)), mock_read=False),
                         {CODING, TEST_DESIGN_PATH, "tdd/references/mocking-and-seams.md"})

    def test_twenty_lines_of_non_test_code_are_not_held_for_test_design(self) -> None:
        s = self.first_turn("tdd")
        held = s.call("Edit", edit(CODE_FILE, *[f"total_{n} = {n}" for n in range(20)]))
        # The design gate holds a substantial code edit; this gate does not.
        self.assertNotEqual(hold_line(held), GATE_LINE)

    def test_each_hold_says_why_in_the_registrys_terms(self) -> None:
        s = self.first_turn("software-design-principles", "tdd")
        held = s.call("Edit", edit(TEST_FILE, *plain_lines(20)))
        self.assertIn(f"`{CODING}` (an edit of a test file adding 20 lines, 20 or more)",
                      reason(held))
        s = self.first_turn("tdd")
        held = s.call("Write", {"file_path": TEST_FILE, "content": "assert True\n"})
        self.assertIn(f"`{TEST_DESIGN_PATH}` (a new test file)", reason(held))


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
    """AC: a skip line naming the skill clears the hold, and lasts the task
    for the references it cleared on that kind of file (Ticket 101)."""

    def test_a_skip_line_lasts_the_task_with_a_notice_naming_it(self) -> None:
        s = self.first_turn("tdd")
        s.say(SKIP_TDD)
        self.assertPasses(s.call("Edit", edit(TEST_FILE, "client = MagicMock()")))
        self.assertPasses(s.call("Edit", edit(TEST_FILE, *plain_lines(5))))
        self.later_turn(s)
        carried = s.call("Edit", edit(TEST_FILE, "client = MagicMock()"))
        self.assertPasses(carried)
        context = carried["hookSpecificOutput"]["additionalContext"]
        self.assertIn("`goated-skip: tdd`", context)
        self.assertIn("`tdd/references/mocking-and-seams.md`", context)

    def test_a_new_task_ends_the_lasting_skip(self) -> None:
        s = self.first_turn("tdd")
        s.say(SKIP_TDD)
        self.assertPasses(s.call("Edit", edit(TEST_FILE, "client = MagicMock()")))
        stop(s)
        s.prompt("Now the importer.")
        s.say("goated-route: direct")
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
            "      - file: decisions.md\n"
            "        signal:\n"
            "          kind: write-under-path\n"
            "          path: docs/decisions/\n"
            "      - file: failing-tests.md\n"
            "        signal:\n"
            "          kind: gate-fires\n"
            "          gate: repeated-failure\n"
            "      - file: wide-change.md\n"
            "        signal:\n"
            "          kind: sensitive-category-count\n"
            "          min_categories: 3\n",
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

    def test_fixture_entries_of_the_turn_kinds_are_enforced(self) -> None:
        registry = self.fixture_registry()
        s = self.first_turn("tdd", registry=registry)
        self.assertPasses(s.call("Write", {"file_path": "docs/specs/x.md", "content": "# X\n"}))
        self.assertHeldFor(s.call("Write", {"file_path": "docs/decisions/x.md", "content": "# X\n"}),
                           "tdd/references/decisions.md")

        s = self.first_turn("tdd", registry=registry)
        s.run(CHECK, success=False)
        s.run(CHECK, success=False)
        self.assertHeldFor(s.call("Edit", edit("docs/notes.md", "Some notes.")),
                           "tdd/references/failing-tests.md")

        # The fixture declares nothing for `code-security-review`; it loads for the security gate.
        s = self.first_turn("tdd", "code-security-review", registry=registry)
        self.assertPasses(s.call("Edit", edit("src/auth/login.py", "check()")))
        self.assertPasses(s.call("Edit", edit("package.json", '"a": "1"')))
        self.assertHeldFor(s.call("Edit", edit(".env", "KEY=1")), "tdd/references/wide-change.md")

    def test_advisory_entries_ask_for_nothing(self) -> None:
        s = self.first_turn("tdd", "prototype", registry=self.fixture_registry())
        self.assertPasses(s.call("Edit", edit("docs/notes.md", "Some notes.")))
        held = s.call("Write", {"file_path": "docs/decisions/x.md", "content": "# X\n"})
        self.assertNotIn("spike-notes.md", reason(held))

    def test_a_gate_the_adapter_does_not_observe_fails_open(self) -> None:
        # Not a way to declare a reference: validate_skills rejects such an entry
        # (tests/test_validate_adapters.py). This guards an installed registry the
        # validator never saw, which must not hold every write.
        self.assertEqual(reference_reads.OBSERVED_GATES, frozenset({"repeated-failure"}))
        reference = reference_reads.Reference(
            "tdd", "x.md", {"kind": "gate-fires", "gate": "pr-review"})
        edit_ = reference_reads.Edit(True, False, [], gates=frozenset({"repeated-failure"}))
        self.assertEqual(reference_reads.selected([reference], edit_), [])

    def test_a_path_signal_naming_no_path_selects_nothing(self) -> None:
        reference = reference_reads.Reference("tdd", "x.md", {"kind": "write-under-path"})
        edit = reference_reads.Edit(False, False, [], project_paths=("none/x.md", "docs/x.md"))
        self.assertEqual(reference_reads.selected([reference], edit), [])

    def test_the_reader_gives_what_the_registry_declares(self) -> None:
        data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
        expected = sorted(
            (skill["name"], entry["file"], entry["signal"])
            for skill in data["skills"] for entry in skill.get("references", [])
            if "signal" in entry
        )
        found = sorted((r.skill, r.file, r.signal) for r in reference_reads.load(REGISTRY))
        self.assertEqual(found, expected)


class SpecTemplate(ReferenceReadsTestCase):
    """AC (Ticket 068): with `write-a-spec` loaded, a write under `docs/specs/`
    is held until `spec-template.md` is read; one under `docs/` elsewhere is not."""

    def test_a_write_under_docs_specs_is_held_until_the_template_is_read(self) -> None:
        s = self.first_turn("write-a-spec")
        held = s.call("Write", {"file_path": "docs/specs/2026-11-17-export.md", "content": "# X\n"})
        self.assertHeldFor(held, "write-a-spec/references/spec-template.md")
        self.assertIn('"docs/specs/"', reason(held))
        self.assertIn("`goated-skip: write-a-spec: <reason>`", reason(held))
        s.read(SPEC_TEMPLATE)
        self.assertPasses(s.call("Write", {"file_path": "docs/specs/2026-11-17-export.md",
                                           "content": "# X\n"}))

    def test_a_write_under_docs_elsewhere_is_not_held(self) -> None:
        s = self.first_turn("write-a-spec")
        for path in ("docs/plans/2026-11-17-export.md", "docs/specs.md",
                     "src/docs/specs/notes.md"):
            with self.subTest(path=path):
                self.assertPasses(s.call("Write", {"file_path": path, "content": "# X\n"}))

    def test_an_absolute_path_inside_the_project_is_held(self) -> None:
        s = self.first_turn("write-a-spec")
        path = str(s.project / "docs" / "specs" / "x.md")
        self.assertHeldFor(s.call("Edit", edit(path, "More.")),
                           "write-a-spec/references/spec-template.md")

    def test_a_shell_write_under_the_path_is_held(self) -> None:
        s = self.first_turn("write-a-spec")
        self.assertHeldFor(s.call("Bash", {"command": "echo '# X' > docs/specs/x.md"}),
                           "write-a-spec/references/spec-template.md")
        self.assertPasses(s.call("Bash", {"command": "echo '# X' > docs/plans/x.md"}))

    def test_without_the_skill_loaded_it_is_not_held(self) -> None:
        s = self.first_turn("tdd")
        self.assertPasses(s.call("Write", {"file_path": "docs/specs/x.md", "content": "# X\n"}))


class TicketTemplates(ReferenceReadsTestCase):
    """AC (Ticket 068): with `spec-to-tickets` loaded, a write under `tickets/`
    is held until the templates are read; a file outside the project named
    `tickets/x` is not."""

    def test_a_write_under_tickets_is_held_until_the_templates_are_read(self) -> None:
        s = self.first_turn("spec-to-tickets")
        held = s.call("Write", {"file_path": "tickets/080-export.md", "content": "# T\n"})
        self.assertHeldFor(held, "spec-to-tickets/references/ticket-slicing-templates.md")
        s.read(TICKET_TEMPLATES)
        self.assertPasses(s.call("Write", {"file_path": "tickets/080-export.md", "content": "# T\n"}))

    def test_the_hold_names_the_write(self) -> None:
        s = self.first_turn("spec-to-tickets")
        held = s.call("Write", {"file_path": "tickets/080-export.md", "content": "# T\n"})
        self.assertIn('This write to "080-export.md" needs', reason(held))
        self.assertIn("This write was not applied.", reason(held))

    def test_a_shell_write_from_an_unknown_folder_is_not_judged(self) -> None:
        s = self.first_turn("spec-to-tickets")
        self.assertPasses(s.call("Bash", {"command": "cd $DIR && echo x > tickets/a.md"}))

    def test_a_session_below_the_checkout_judges_from_each_project_root(self) -> None:
        (self.root / "s1").mkdir()
        s = Session(self.root / "s1", session_id="session-below")
        s.project.mkdir(parents=True)
        (s.project / ".git").mkdir()
        s.cwd = s.project / "web"
        s.cwd.mkdir()
        s.config.registry_path = REGISTRY
        s.prompt("Slice the spec.")
        s.load(ROUTER)
        s.say("goated-route: direct")
        s.load("spec-to-tickets")
        # The checkout's own tickets folder, reached from the session's folder.
        self.assertHeldFor(s.call("Write", {"file_path": str(s.project / "tickets" / "x.md"),
                                            "content": "# T\n"}),
                           "spec-to-tickets/references/ticket-slicing-templates.md")
        # The session's folder is a project root too, so its own `tickets/` counts.
        self.assertHeldFor(s.call("Write", {"file_path": "tickets/y.md", "content": "# T\n"}),
                           "spec-to-tickets/references/ticket-slicing-templates.md")
        self.assertPasses(s.call("Write", {"file_path": "docs/tickets/z.md", "content": "# T\n"}))

    def test_a_tickets_folder_outside_the_project_is_not_held(self) -> None:
        s = self.first_turn("spec-to-tickets")
        outside = self.root / "elsewhere" / "tickets" / "x.md"
        self.assertPasses(s.call("Write", {"file_path": str(outside), "content": "# T\n"}))
        self.assertPasses(s.call("Bash", {"command": f"echo T > '{outside.as_posix()}'"}))


CHECK = "uv run python -m unittest discover -s tests"


class RootCauseTracing(ReferenceReadsTestCase):
    """AC (Ticket 068): with `diagnose` loaded, the first write after one check
    failed twice is held until `root-cause-tracing.md` is read; after one
    failure it is not."""

    def test_a_write_after_two_failures_is_held_until_the_reference_is_read(self) -> None:
        s = self.first_turn("diagnose")
        s.run(CHECK, success=False)
        self.assertPasses(s.call("Edit", edit(CODE_FILE, "total = 1")))
        s.run(CHECK, success=False)
        held = s.call("Edit", edit(CODE_FILE, "total = 2"))
        self.assertHeldFor(held, "diagnose/references/root-cause-tracing.md")
        self.assertIn("repeated-failure", reason(held))
        s.read(ROOT_CAUSE)
        self.assertPasses(s.call("Edit", edit(CODE_FILE, "total = 2")))

    def test_a_document_or_shell_write_is_held_too(self) -> None:
        s = self.first_turn("diagnose")
        s.run(CHECK, success=False)
        s.run(CHECK, success=False)
        self.assertHeldFor(s.call("Edit", edit("docs/notes.md", "Cause unknown.")),
                           "diagnose/references/root-cause-tracing.md")
        self.assertHeldFor(s.call("Bash", {"command": "echo x > src/notes.txt"}),
                           "diagnose/references/root-cause-tracing.md")

    def test_rerunning_the_check_is_not_held(self) -> None:
        s = self.first_turn("diagnose")
        s.run(CHECK, success=False)
        s.run(CHECK, success=False)
        self.assertPasses(s.run(f"{CHECK} > test-output.txt", success=False))

    def test_a_write_naming_no_file_or_outside_the_project_is_held_too(self) -> None:
        # The same writes the repeated-failure gate holds, wherever they land.
        for call in (("Bash", {"command": "git apply fix.patch"}),
                     ("Bash", {"command": "patch -p1 < fix.patch"}),
                     ("Edit", edit(str(self.root / "scratch" / "export.py"), "total = 2"))):
            with self.subTest(call=call):
                s = self.first_turn("diagnose")
                s.run(CHECK, success=False)
                s.run(CHECK, success=False)
                held = s.call(*call)
                self.assertHeldFor(held, "diagnose/references/root-cause-tracing.md")
                if call[0] == "Bash":
                    self.assertTrue(reason(held).split("\n")[1].startswith("This write needs"),
                                    reason(held))

    def test_one_failure_or_a_pass_between_is_not_held(self) -> None:
        s = self.first_turn("diagnose")
        s.run(CHECK, success=False)
        self.assertPasses(s.call("Edit", edit(CODE_FILE, "total = 1")))
        s.run(CHECK)
        s.run(CHECK, success=False)
        self.assertPasses(s.call("Edit", edit(CODE_FILE, "total = 2")))

    def test_without_diagnose_the_repeated_failure_gate_holds_instead(self) -> None:
        s = self.first_turn("tdd")
        s.run(CHECK, success=False)
        s.run(CHECK, success=False)
        self.assertEqual(hold_line(s.call("Edit", edit(CODE_FILE, "total = 2"))),
                         "goated-hold: repeated-failure | justified-skip")


class SecurityChecklist(ReferenceReadsTestCase):
    """AC (Ticket 068): with `code-security-review` loaded, a sensitive write
    when the turn's changes span two categories is held until the checklist
    is read; with one category it is not."""

    def test_a_second_category_is_held_until_the_checklist_is_read(self) -> None:
        s = self.first_turn("code-security-review")
        self.assertPasses(s.call("Edit", edit("src/auth/login.py", "check()")))
        held = s.call("Edit", edit("package.json", '"left-pad": "1.0.0"'))
        self.assertHeldFor(held, "code-security-review/references/security-review-checklist.md")
        self.assertIn("2 categories (auth, dependencies)", reason(held))
        s.read(CHECKLIST)
        self.assertPasses(s.call("Edit", edit("package.json", '"left-pad": "1.0.0"')))

    def test_writes_in_one_category_are_not_held(self) -> None:
        s = self.first_turn("code-security-review")
        self.assertPasses(s.call("Edit", edit("src/auth/login.py", "check()")))
        self.assertPasses(s.call("Edit", edit("src/auth/session.py", "renew()")))

    def test_a_write_to_a_file_that_is_not_sensitive_is_not_held(self) -> None:
        s = self.first_turn("code-security-review")
        s.call("Edit", edit("src/auth/login.py", "check()"))
        s.call("Bash", {"command": "echo x > .env"})
        self.assertPasses(s.call("Edit", edit(CODE_FILE, "total = 1")))

    def test_a_subagents_sensitive_write_counts_as_a_category(self) -> None:
        s = self.first_turn("code-security-review", "handoff")
        s.read(f"{SKILLS}/handoff/references/spawn-brief.md")
        agent = s.subagent("c1")
        agent.prompt("Update the lockfile.", hook=False)
        agent.load("code-security-review")
        agent.call("Edit", edit("package.json", '"a": "1"'), agent_id="c1",
                   agent_type="general-purpose")
        self.assertPasses(s.spawn("c1", BRIEF))
        held = s.call("Edit", edit("src/auth/login.py", "check()"))
        self.assertHeldFor(held, "code-security-review/references/security-review-checklist.md")
        self.assertIn("(auth, dependencies)", reason(held))

    def test_a_shell_write_counts_as_a_category(self) -> None:
        s = self.first_turn("code-security-review")
        self.assertPasses(s.call("Bash", {"command": "echo KEY=1 > .env"}))
        self.assertHeldFor(s.call("Edit", edit("src/auth/login.py", "check()")),
                           "code-security-review/references/security-review-checklist.md")


class TurnSignalSkipLines(ReferenceReadsTestCase):
    """AC (Ticket 068): each hold clears on a skip line naming its skill."""

    def test_a_skip_line_naming_the_skill_clears_each_hold(self) -> None:
        cases = (
            ("write-a-spec", lambda s: None,
             lambda s: s.call("Write", {"file_path": "docs/specs/x.md", "content": "# X\n"})),
            ("spec-to-tickets", lambda s: None,
             lambda s: s.call("Write", {"file_path": "tickets/x.md", "content": "# T\n"})),
            ("diagnose", lambda s: (s.run(CHECK, success=False), s.run(CHECK, success=False)),
             lambda s: s.call("Edit", edit(CODE_FILE, "total = 2"))),
            ("code-security-review", lambda s: s.call("Edit", edit("src/auth/login.py", "x()")),
             lambda s: s.call("Edit", edit("package.json", '"a": "1"'))),
        )
        for skill, before, write in cases:
            with self.subTest(skill=skill):
                s = self.first_turn(skill)
                before(s)
                held = write(s)
                self.assertEqual(hold_line(held), GATE_LINE, reason(held))
                self.assertIn(f"skip {skill}", reason(held))
                s.say("goated-skip: tdd: not this skill")
                self.assertEqual(hold_line(write(s)), GATE_LINE)
                s.say(f"goated-skip: {skill}: the reference does not apply here")
                self.assertPasses(write(s))


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
        for field in ("pattern: [mock-or-patch]", "file_kind: 3", "min_added_lines: five",
                      "min_added_lines: true", "new_file: sometimes", "new_file: 1"):
            with self.subTest(field=field):
                registry = self.root / "malformed.yaml"
                of_kind = field.startswith(("min", "new"))
                kind = "edit-of-file-kind" if of_kind else "edit-adds-pattern"
                extra = "\n          file_kind: test" if of_kind else ""
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
            s.call("Edit", edit(TEST_FILE, *plain_lines(20))),
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
        # A test edit's `coding.md` follows the registry's test-edit rule (Ticket
        # 090), so only its reason differs: the registry's threshold, or none.
        self.assertIn("20 or more", reason(with_registry[1]))
        self.assertIn("(edits a test file)", reason(without[1]))
        del with_registry[1], without[1]
        self.assertEqual([reason(o) for o in with_registry], [reason(o) for o in without])

    def test_existing_rule_references_are_not_asked_for_by_this_gate(self) -> None:
        s = self.first_turn("software-design-principles", "handoff")
        s.say("goated-skip: software-design-principles: only adds a test fixture value")
        self.assertPasses(s.call("Edit", edit(TEST_FILE, *plain_lines(6))))


if __name__ == "__main__":
    unittest.main()
