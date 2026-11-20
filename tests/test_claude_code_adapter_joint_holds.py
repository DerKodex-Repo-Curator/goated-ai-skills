"""Ticket 095: every hold a call would meet arrives in one message.

Each test drives the hook entry point with a transcript in Claude Code's
recorded shape (see `claude_code_adapter_support.py`). A joint message keeps
each hold's own `goated-hold: <gate> | <kind>` line, in the order the gates
fire, and gives each shared paragraph once.
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from claude_code_adapter_support import (
    BRIEF,
    REPO_ROOT,
    ROUTER,
    Session,
    context,
    decision,
    owed_references,
    parse,
    reason,
)

REGISTRY = REPO_ROOT / "stack" / "goated-stack.yaml"
SKILLS = "/opt/goated/skills"
CODING = f"{SKILLS}/software-design-principles/references/coding.md"
TEST_FILE = "tests/test_export.py"
HOLD_LINE = re.compile(r"^goated-hold: ([a-z-]+) \| ([a-z-]+)$", re.MULTILINE)
FULL_ADVICE = "may not be seen"
CHANGE_READ = "print its diff with a git diff or git show command"
SKIP_DIAGNOSE = "goated-skip: diagnose: the failing check's cause is already known"


def hold_lines(output: dict) -> list[tuple[str, str]]:
    return HOLD_LINE.findall(reason(output))


def gates_of(output: dict) -> list[str]:
    return [gate for gate, _ in hold_lines(output)]


def three_gate_edit() -> dict:
    """An edit meeting three holds a line can clear: it removes a conflict
    marker from a security-sensitive file after a check failed twice. Since
    Ticket 118 the read gates no longer hold a file edit, so these three
    stand in for design-reads, reference-reads and repeated-failure."""

    return {"file_path": "src/auth.py",
            "old_string": "<<<<<<< HEAD\nkey = 1\n=======\nkey = 2\n>>>>>>> x\n",
            "new_string": "key = 2\n"}


class SessionCase(unittest.TestCase):
    """Sessions routed `direct` in a temporary folder, with this repo's registry."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def session(self, name: str = "s", route: str = "goated-route: direct") -> Session:
        folder = self.root / name
        folder.mkdir()
        s = Session(folder)
        s.config.registry_path = REGISTRY
        s.prompt("Add CSV export.")
        s.load(ROUTER)
        s.say(route)
        return s

    def three_gate_session(self) -> Session:
        """A turn where an edit meets conflict-resolution, security and repeated-failure."""

        s = self.session("three")
        s.run("pytest -q", success=False)
        s.run("pytest -q", success=False)
        return s


class JointHoldTests(SessionCase):
    """R1: one message carries every hold a call meets, in today's order."""

    def test_an_edit_meeting_three_gates_is_held_once_with_all_three(self) -> None:
        s = self.three_gate_session()
        held = s.call("Edit", three_gate_edit())
        self.assertEqual(decision(held), "deny")
        self.assertEqual(gates_of(held), ["conflict-resolution", "security", "repeated-failure"])
        self.assertTrue(reason(held).startswith("goated-hold: conflict-resolution | justified-skip\n"))

    def test_clearing_all_three_lets_the_retry_pass(self) -> None:
        s = self.three_gate_session()
        s.call("Edit", three_gate_edit())
        s.load("resolving-merge-conflicts")
        s.load("code-security-review")
        s.say(SKIP_DIAGNOSE)
        self.assertEqual(decision(s.call("Edit", three_gate_edit())), "pass")

    def test_a_gate_already_met_is_left_out_of_the_joint_message(self) -> None:
        # Near miss: diagnose skipped, so repeated-failure passes and two holds remain.
        s = self.three_gate_session()
        s.say(SKIP_DIAGNOSE)
        held = s.call("Edit", three_gate_edit())
        self.assertEqual(gates_of(held), ["conflict-resolution", "security"])

    def test_a_read_gate_lands_beside_a_hold_and_owes_nothing_until_retried(self) -> None:
        # Since Ticket 118 a file edit the read gates would hold lands, so on a
        # call another gate holds they add no hold, and the held call owes nothing.
        s = self.session("reads-beside")
        s.load("software-design-principles")
        s.load("tdd")
        s.run("pytest -q", success=False)
        s.run("pytest -q", success=False)
        mocked = {"file_path": TEST_FILE, "old_string": "pass", "new_string": "\n".join(
            ["client = MagicMock()", *(f"assert total_{n} == {n}" for n in range(25))])}
        held = s.call("Edit", mocked)
        self.assertEqual(gates_of(held), ["repeated-failure"])
        self.assertEqual(context(held), "")
        s.say(SKIP_DIAGNOSE)
        landed = s.call("Edit", mocked)
        self.assertEqual(decision(landed), "pass")
        self.assertEqual(owed_references(landed), {
            "software-design-principles/references/coding.md",
            "tdd/references/mocking-and-seams.md", "tdd/references/test-design.md"})

    def test_a_spawn_meeting_pipeline_and_spawn_is_held_once_with_both(self) -> None:
        s = self.session("spawn", "goated-route: standard | requires: tdd")
        held = s.call("Agent", {"prompt": BRIEF})
        self.assertEqual(hold_lines(held), [("pipeline", "strict"), ("spawn", "strict")])
        # Near miss: with the route's skill loaded, only the spawn hold is left.
        s.load("tdd")
        self.assertEqual(hold_lines(s.call("Agent", {"prompt": BRIEF})), [("spawn", "strict")])

    def test_router_first_and_route_line_come_in_one_message(self) -> None:
        folder = self.root / "unrouted"
        folder.mkdir()
        s = Session(folder)
        s.prompt("Add CSV export.")
        edit = {"file_path": "notes.md", "old_string": "a", "new_string": "b"}
        self.assertEqual(gates_of(s.call("Edit", edit)), ["router-first", "route-line"])
        # Near miss: a command that writes nothing meets router-first alone.
        self.assertEqual(gates_of(s.call("Bash", {"command": "make-it"})), ["router-first"])
        # Loading the router and writing a route line, in one retry, clears both.
        s.load(ROUTER)
        s.say("goated-route: direct")
        self.assertEqual(decision(s.call("Edit", edit)), "pass")

    def test_pipeline_waits_for_the_route(self) -> None:
        # With the router unloaded and a requires route already written, pipeline is not judged.
        folder = self.root / "routed-early"
        folder.mkdir()
        s = Session(folder)
        s.prompt("Add CSV export.")
        s.say("goated-route: standard | requires: tdd")
        self.assertEqual(gates_of(s.call("Edit", {"file_path": "notes.md", "old_string": "a",
                                                  "new_string": "b"})), ["router-first"])

    def test_a_script_writing_a_test_and_a_code_file_names_both_in_one_hold(self) -> None:
        s = self.session("two-files")
        script = ("python - <<'EOF'\nopen(\"tests/test_export.py\", \"w\").write(a)\n"
                  "open(\"src/auth.py\", \"w\").write(b)\nEOF")
        held = s.call("Bash", {"command": script})
        self.assertEqual(gates_of(held), ["security", "scripted-edit"])
        scripted = reason(held).split("goated-hold: scripted-edit")[1]
        self.assertIn('"test_export.py"', scripted)
        self.assertIn('"auth.py"', scripted)
        # One retry clears everything: the design skip and the security skip.
        s.say("goated-skip: software-design-principles: one mechanical rename across files")
        s.say("goated-skip: code-security-review: renames a constant with no trust boundary")
        self.assertEqual(decision(s.call("Bash", {"command": script})), "pass")

    def test_a_command_writing_two_targets_asks_for_every_reference_at_once(self) -> None:
        s = self.session("two-refs")
        s.load("write-a-spec")
        s.load("spec-to-tickets")
        command = "cp a.md docs/specs/export.md && cp b.md tickets/001-export.md"
        text = reason(s.call("Bash", {"command": command}))
        self.assertEqual(text.count("goated-hold: reference-reads"), 1, text)
        self.assertIn("write-a-spec/references/spec-template.md", text)
        self.assertIn("spec-to-tickets/references/ticket-slicing-templates.md", text)
        s.read(f"{SKILLS}/write-a-spec/references/spec-template.md")
        s.read(f"{SKILLS}/spec-to-tickets/references/ticket-slicing-templates.md")
        self.assertEqual(decision(s.call("Bash", {"command": command})), "pass")


class SharedTextTests(SessionCase):
    """R3: a paragraph several holds or closeout items share appears once in a message."""

    def test_holds_sharing_the_unseen_line_advice_carry_it_once(self) -> None:
        text = reason(self.three_gate_session().call("Edit", three_gate_edit()))
        self.assertEqual(text.count(FULL_ADVICE), 1, text)
        # Each hold keeps its own typed way out.
        for way_out in ("skip code-security-review", "skip diagnose"):
            self.assertIn(f"`{way_out}`", text)

    def changed_and_loaded(self, name: str) -> Session:
        s = self.session(name)
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.call("Write", {"file_path": "src/export.py", "content": "rate = 1\n"})
        s.load("commit-message")
        s.load("pr-description")
        return s

    def test_a_commit_and_pull_request_sharing_the_change_read_carry_it_once(self) -> None:
        s = self.changed_and_loaded("commit-pr")
        held = s.call("Bash", {"command": 'git commit -m "Add export" && gh pr create '
                                          '--title "Add export" --body "Adds it."'})
        # The closeout comes beside the commit gate (Ticket 120, R4).
        self.assertEqual(gates_of(held), ["commit", "closeout", "pull-request"])
        text = reason(held)
        self.assertEqual(text.count(CHANGE_READ), 1, text)
        self.assertEqual(text.count("rerun any steps chained before it"), 1, text)
        # Near miss: the commit alone still carries both in full.
        alone = reason(self.changed_and_loaded("alone").call(
            "Bash", {"command": 'git commit -m "Add export"'}))
        self.assertIn(CHANGE_READ, alone)
        self.assertIn("rerun any steps chained before it", alone)

    def test_closeout_items_sharing_the_change_read_carry_it_once(self) -> None:
        s = self.session("closeout")
        s.load("software-design-principles")
        s.load("doc-sync")
        s.read(CODING)
        s.call("Edit", {"file_path": "src/export.py", "old_string": "pass",
                        "new_string": "\n".join(f"total_{n} = {n}" for n in range(6))})
        s.run("pytest -q")
        text = stop_reason(s)
        self.assertIn("- Docs:", text)
        self.assertIn("- Design:", text)
        self.assertEqual(text.count(CHANGE_READ), 1, text)


SKIPPED = ("resolving-merge-conflicts", "code-security-review", "diagnose")
SHORT_PLACEMENT = "as this turn's first such hold explained"
CARRIER = "This call has no field for a line"


def bodies(text: str) -> dict[str, str]:
    """Each hold's text in a message, by gate."""

    parts = HOLD_LINE.split(text)
    return {parts[i]: parts[i + 2].strip("\n") for i in range(1, len(parts), 3)}


class ClearingSectionTests(SessionCase):
    """Ticket 111: several holds a line can clear share one closing clearing section."""

    def test_three_line_clearable_holds_end_in_one_clearing_section(self) -> None:
        text = reason(self.three_gate_session().call("Edit", three_gate_edit()))
        held = bodies(text)
        self.assertEqual(list(held), ["conflict-resolution", "security", "repeated-failure"])
        for skill in SKIPPED:
            # Each hold keeps the line it asks for; the section names each override once.
            self.assertEqual(text.count(f"`goated-skip: {skill}: <reason>`"), 1, text)
            self.assertEqual(text.count(f"`skip {skill}`"), 1, text)
            self.assertIn(f"`skip {skill}`", held["repeated-failure"])
        for gate in ("conflict-resolution", "security"):
            self.assertNotIn("Put the skip line", held[gate])
            self.assertNotIn("`skip ", held[gate])
        last = held["repeated-failure"]
        self.assertEqual(last.count(FULL_ADVICE), 1, last)
        self.assertNotIn(SHORT_PLACEMENT, text)
        # The section comes after the hold's own text, and the carrier stays last.
        self.assertLess(last.index("not applied"), last.index(FULL_ADVICE))
        self.assertTrue(last.splitlines()[-1].startswith(CARRIER), last)

    def test_a_later_joint_message_gives_the_placement_in_one_sentence(self) -> None:
        s = self.three_gate_session()
        s.call("Edit", three_gate_edit())
        text = reason(s.call("Edit", three_gate_edit()))
        self.assertNotIn(FULL_ADVICE, text)
        self.assertEqual(text.count(SHORT_PLACEMENT), 1, text)
        for skill in SKIPPED:
            self.assertEqual(text.count(f"`skip {skill}`"), 1, text)
            self.assertEqual(text.count(f"`goated-skip: {skill}: <reason>`"), 1, text)

    def test_a_joint_message_after_a_single_hold_gives_the_placement_in_one_sentence(self) -> None:
        # The turn had the full advice on a hold alone, so the section is one sentence.
        s = self.three_gate_session()
        s.call("Write", {"file_path": "src/auth.py", "content": "key = 1\nsecret = 2\n"})
        text = reason(s.call("Edit", three_gate_edit()))
        self.assertNotIn(FULL_ADVICE, text)
        self.assertEqual(text.count(SHORT_PLACEMENT), 1, text)

    def test_a_single_line_clearable_hold_keeps_its_own_advice(self) -> None:
        # Near miss: one such hold alone is unchanged.
        held = self.session("single").call("Write", {"file_path": "src/auth.py",
                                                       "content": "key = 1\nsecret = 2\n"})
        self.assertEqual(gates_of(held), ["security"])
        text = reason(held)
        self.assertIn("Put the skip line on its own line there", text)
        self.assertEqual(text.count("`skip code-security-review`"), 1, text)
        self.assertNotIn("Put each", text)

    def test_a_strict_hold_beside_one_line_clearable_hold_is_unchanged(self) -> None:
        folder = self.root / "strict"
        folder.mkdir()
        s = Session(folder)
        s.prompt("Add CSV export.")
        held = s.call("Edit", {"file_path": "notes.md", "old_string": "a", "new_string": "b"})
        text = bodies(reason(held))
        self.assertEqual(list(text), ["router-first", "route-line"])
        self.assertIn("Put the route line on its own line there", text["route-line"])
        self.assertNotIn("Put each", reason(held))

    def test_a_route_line_hold_and_a_skip_line_hold_share_one_section(self) -> None:
        s = self.session("both-lines", "goated-route: standard | requires: tdd")
        held = s.call("Write", {"file_path": "src/auth.py", "content": "key = 1\nsecret = 2\n"})
        text = reason(held)
        self.assertEqual(gates_of(held), ["pipeline", "security"])
        self.assertEqual(text.count(FULL_ADVICE), 1, text)
        self.assertIn("route or skip line", bodies(text)["security"])
        for way_out in ("skip routing", "skip code-security-review"):
            self.assertEqual(text.count(f"`{way_out}`"), 1, text)


def stop_reason(s: Session) -> str:
    return parse(s.hook("Stop", stop_hook_active=False, last_assistant_message="")).get("reason", "")


class ShortRepeatTests(SessionCase):
    """R3: a gate's second or later hold in a turn is short; the next turn is full again."""

    def closeout_turn(self, name: str) -> Session:
        s = self.session(name)
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.call("Write", {"file_path": "src/export.py", "content": "rate = 1\n"})
        return s

    def test_a_second_stop_hold_lists_only_the_unmet_items_short(self) -> None:
        s = self.closeout_turn("stop")
        first = stop_reason(s)
        self.assertIn("- Proof:", first)
        self.assertIn("- Docs:", first)
        s.run("pytest -q")  # Meets the Proof item.
        second = stop_reason(s)
        self.assertTrue(second.startswith("goated-hold: closeout | justified-skip\n"), second)
        self.assertIn("Still unmet", second)
        self.assertNotIn("- Proof:", second)
        self.assertIn("- Docs:", second)
        self.assertIn("`goated-skip: doc-sync: <reason>`", second)
        self.assertLess(len(second), len(first))
        # The next turn's first hold is full again.
        s.prompt("Also add JSON export.")
        s.say("goated-route: direct")
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.call("Write", {"file_path": "src/export.py", "content": "rate = 2\n"})
        third = stop_reason(s)
        self.assertNotIn("Still unmet", third)
        self.assertIn("- Proof:", third)

    def test_with_the_marker_unwritable_each_hold_is_full(self) -> None:
        s = self.closeout_turn("unwritable")
        (s.config.state_dir / "turn-markers").write_text("", encoding="utf-8")
        first, second = stop_reason(s), stop_reason(s)
        self.assertEqual(first, second)
        self.assertNotIn("Still unmet", second)
        self.assertIn(FULL_ADVICE, reason(s.call("Write", {"file_path": "src/auth.py",
                                                           "content": "key = 1\n"})))

    def test_advice_and_two_gates_claim_apart_in_one_turn(self) -> None:
        s = self.session("purposes")
        auth = {"file_path": "src/auth.py", "content": "key = 1\n"}
        conflict = {"file_path": "notes.md", "old_string": "<<<<<<< HEAD\na\n=======\nb\n>>>>>>> x\n",
                    "new_string": "b\n"}
        security_1 = reason(s.call("Write", auth))
        self.assertIn(FULL_ADVICE, security_1)
        security_2 = reason(s.call("Write", auth))
        conflict_1 = reason(s.call("Edit", conflict))
        conflict_2 = reason(s.call("Edit", conflict))
        self.assertNotIn("Still unmet", security_1)
        self.assertIn("Still unmet", security_2)
        self.assertNotIn("Still unmet", conflict_1)
        self.assertIn("Still unmet", conflict_2)
        for later in (security_2, conflict_1, conflict_2):
            self.assertNotIn(FULL_ADVICE, later)
        self.assertIn("`skip code-security-review`", security_2)
        self.assertIn("`skip resolving-merge-conflicts`", conflict_2)
        # Neither claim erased the other: the security gate is still short.
        self.assertIn("Still unmet", reason(s.call("Write", auth)))
        # The next turn starts with every form full again.
        s.prompt("Next change.")
        s.say("goated-route: direct")
        again = reason(s.call("Write", auth))
        self.assertIn(FULL_ADVICE, again)
        self.assertNotIn("Still unmet", again)
        self.assertNotIn("Still unmet", reason(s.call("Edit", conflict)))


class ShortFormKeepsTheAskTests(SessionCase):
    """Review of Ticket 095: a short form comes only after the turn showed that ask
    in full, and keeps every constraint needed to clear the hold."""

    COMMIT = {"command": 'git commit -am "Add export"'}
    PR = {"command": 'gh pr create --title "Add export" --body "Adds it."'}

    def changed(self, name: str) -> Session:
        s = self.session(name)
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.call("Write", {"file_path": "src/export.py", "content": "rate = 1\n"})
        return s

    def test_the_first_change_read_hold_after_a_load_hold_is_full(self) -> None:
        # Probe p2: the commit gate held first for the load, then for the read.
        s = self.changed("commit-ask")
        s.call("Bash", self.COMMIT)
        s.load("commit-message")
        # The commit gate's own hold, ahead of the closeout beside it (Ticket 120, R4).
        commit_part = lambda output: reason(output).split("\n\ngoated-hold: closeout")[0]
        second = commit_part(s.call("Bash", self.COMMIT))
        self.assertNotIn("Still unmet", second)
        self.assertIn("--stat", second)
        self.assertIn("chained in the same command", second)
        # Near miss: the same ask again in the turn is short, and still says what does not count.
        third = commit_part(s.call("Bash", self.COMMIT))
        self.assertIn("Still unmet", third)
        self.assertIn("--stat", third)
        self.assertIn("chained", third)

    def test_the_first_pull_request_change_read_hold_is_full(self) -> None:
        # Probe p4.
        s = self.changed("pr-ask")
        s.call("Bash", self.PR)
        s.load("pr-description")
        second = reason(s.call("Bash", self.PR))
        self.assertNotIn("Still unmet", second)
        self.assertIn("--stat", second)

    def test_a_diff_only_short_form_does_not_offer_a_read(self) -> None:
        # Probe p1: a turn that changed no file it names; a Read cannot count.
        s = self.session("diff-only")
        s.say("goated-skip: software-design-principles: one mechanical patch apply")
        s.run("git apply fix.patch")
        s.load("commit-message")
        first = reason(s.call("Bash", self.COMMIT))
        self.assertIn("changed no file it can name", first)
        second = reason(s.call("Bash", self.COMMIT))
        self.assertIn("Still unmet", second)
        self.assertNotIn("Read a file", second)
        self.assertIn("git diff", second)

    def test_a_route_line_short_form_keeps_the_lines_that_break_the_grammar(self) -> None:
        # Probe p3.
        folder = self.root / "malformed"
        folder.mkdir()
        s = Session(folder)
        s.prompt("Add CSV export.")
        s.load(ROUTER)
        edit = {"file_path": "notes.md", "old_string": "a", "new_string": "b"}
        s.call("Edit", edit)
        s.call("Bash", {"command": "true", "description": "goated-route: standard requires tdd"})
        second = reason(s.call("Edit", edit))
        self.assertIn("Still unmet", second)
        self.assertIn("do not match the grammar", second)
        self.assertIn("`goated-route: standard requires tdd` (the pipe separator is required)",
                      second)

    def test_a_route_line_with_trailing_text_is_quoted_with_its_reason(self) -> None:
        folder = self.root / "trailing"
        folder.mkdir()
        s = Session(folder)
        s.prompt("Add CSV export.")
        s.load(ROUTER)
        s.call("Bash", {"command": "true", "description": "goated-route: direct, then the tests"})
        held = reason(s.call("Edit", {"file_path": "notes.md", "old_string": "a", "new_string": "b"}))
        self.assertIn("`goated-route: direct, then the tests` (nothing may follow the line)", held)

    def test_a_closeout_item_first_shown_at_stop_is_full(self) -> None:
        # Items met at a commit's closeout are short later; an item new at Stop is full.
        s = self.changed("closeout-items")
        s.load("commit-message")
        s.run("git diff")
        at_commit = reason(s.call("Bash", self.COMMIT))
        self.assertIn("- Proof:", at_commit)
        self.assertNotIn("- Unfinished:", at_commit)
        s.run("pytest -q", success=False)
        text = stop_reason(s)
        unfinished = next(line for line in text.splitlines() if line.startswith("- Unfinished:"))
        self.assertIn("leave a handoff for what remains", unfinished)

    def test_the_short_closeout_at_a_commit_keeps_the_chained_check_rule(self) -> None:
        s = self.changed("closeout-commit")
        s.load("commit-message")
        s.run("git diff")
        reason(s.call("Bash", self.COMMIT))
        again = reason(s.call("Bash", {"command": 'pytest -q && git commit -am "Add export"'}))
        self.assertIn("Still unmet before committing", again)
        self.assertIn("A check chained before the commit in the same command has not run yet", again)

    def test_short_forms_keep_what_clears_them(self) -> None:
        commit = self.changed("commit-load")
        commit.call("Bash", self.COMMIT)
        self.assertIn("typed", reason(commit.call("Bash", self.COMMIT)))
        # Since Ticket 118 a file edit lands owing its reads, so the design-reads
        # hold is a shell write's: one that shows no text still meets it.
        designed = self.session("design-reads")
        designed.load("software-design-principles")
        reads = {"command": "generate-settings > config/export.json"}
        first = reason(designed.call("Bash", reads))
        self.assertTrue(first.startswith("goated-hold: design-reads | justified-skip\n"), first)
        second = reason(designed.call("Bash", reads))
        self.assertIn("Still unmet", second)
        self.assertIn('"export.json"', second)

    def test_the_briefed_pipeline_short_form_keeps_the_orientation_rule(self) -> None:
        folder = self.root / "briefed"
        folder.mkdir()
        s = Session(folder)
        orientation = s.config.home / ".claude" / "skills" / "session-start-progressive-disclosure"
        orientation.mkdir(parents=True)
        (orientation / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
        s.prompt("Background (from the session that started this one):\nAdd CSV export.\n\n"
                 "goated-route: standard | requires: tdd", origin=None, turnOrigin="host_synthetic")
        s.load("tdd")
        s.call("Edit")
        second = reason(s.call("Edit"))
        self.assertIn("Still unmet", second)
        self.assertIn("`goated-route: direct`", second)
        self.assertIn("lightweight", second)


class CarrierTests(SessionCase):
    """R4: a hold a line can clear, on a call with no line field, names a carrier."""

    AUTH = {"file_path": "src/auth.py", "content": "key = 1\n"}
    AUTH_EDIT = {"file_path": "src/auth.py", "old_string": "a", "new_string": "b"}
    BASH_CARRIER = "a Bash call with the command true"
    POWERSHELL_CARRIER = "a PowerShell call with the command $null"

    def test_an_edit_hold_names_the_bash_carrier_in_a_bash_session(self) -> None:
        s = self.session("bash")
        s.run("ls")
        for tool, tool_input in (("Edit", self.AUTH_EDIT), ("Write", self.AUTH)):
            with self.subTest(tool=tool):
                text = reason(s.call(tool, tool_input))
                self.assertIn(self.BASH_CARRIER, text)
                self.assertNotIn(self.POWERSHELL_CARRIER, text)

    def test_an_edit_hold_names_the_powershell_carrier_in_a_powershell_session(self) -> None:
        s = self.session("powershell")
        s.run("Get-ChildItem", tool="PowerShell")
        text = reason(s.call("Edit", self.AUTH_EDIT))
        self.assertIn(self.POWERSHELL_CARRIER, text)
        self.assertNotIn(self.BASH_CARRIER, text)

    def test_before_the_first_shell_call_the_carrier_is_bash(self) -> None:
        text = reason(self.session("no-shell").call("Edit", self.AUTH_EDIT))
        self.assertIn(self.BASH_CARRIER, text)
        self.assertNotIn(self.POWERSHELL_CARRIER, text)

    def test_a_call_with_a_line_field_or_a_strict_hold_names_no_carrier(self) -> None:
        s = self.session("fields")
        s.run("ls")
        # Near misses: a shell call has a description, and a strict hold takes no line.
        self.assertNotIn("command true", reason(s.call("Bash", {
            "command": "python - <<'EOF'\nopen(\"src/export.py\", \"w\").write(text)\nEOF"})))
        self.assertNotIn("command true", reason(s.call("Agent", {"prompt": BRIEF})))

    def test_each_carrier_passes_before_and_after_the_router_loads_and_carries_the_line(self) -> None:
        for tool, command in (("Bash", "true"), ("PowerShell", "$null")):
            with self.subTest(tool=tool):
                folder = self.root / tool
                folder.mkdir()
                s = Session(folder)
                s.prompt("Harden the login check.")
                carrier = {"command": command, "description": "goated-route: direct"}
                self.assertEqual(decision(s.call(tool, carrier)), "pass")
                s.load(ROUTER)
                skip = {"command": command, "description":
                        "goated-skip: code-security-review: constant with no trust boundary"}
                self.assertEqual(decision(s.call(tool, skip)), "pass")
                self.assertEqual(decision(s.call("Write", self.AUTH)), "pass")


if __name__ == "__main__":
    unittest.main()
