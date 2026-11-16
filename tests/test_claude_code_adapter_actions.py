"""Behavior tests for the Claude Code adapter's action, shell-write, and closeout gates.

Like `test_claude_code_adapter.py`, each test drives the adapter's single hook
entry point with hook inputs and a transcript in Claude Code's recorded shape
(see `claude_code_adapter_support.py`).
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from claude_code_adapter_support import (
    BRIEF,
    ROUTER,
    SPAWN_BRIEF_PATH,
    Session,
    decision,
    parse,
    reason,
)

SHELL_WRITES = (
    ("Bash", "echo done > notes.txt"),
    ("Bash", "printf 'x' >> log.txt"),
    ("Bash", "make 2>&1 | tee build.log"),
    ("Bash", "sed -i 's/a/b/' src/app.py"),
    ("Bash", "sed -E -i.bak 's/a/b/' src/app.py"),
    ("Bash", "cp a.py b.py"),
    ("Bash", "mv old.py new.py"),
    ("Bash", "rm -rf build"),
    ("Bash", "cd src && rm stale.py"),
    ("Bash", "git apply fix.patch"),
    ("Bash", "git checkout -- src/app.py"),
    ("Bash", "git checkout HEAD~1 -- src/app.py"),
    ("Bash", "cat <<'EOF' > src/new.py\nprint('hi')\nEOF"),
    ("PowerShell", "Set-Content -Path notes.txt -Value 'x'"),
    ("PowerShell", "'x' | Out-File notes.txt"),
    ("PowerShell", "Add-Content log.txt 'line'"),
    ("PowerShell", "Copy-Item a.py b.py"),
    ("PowerShell", "Move-Item a.py b.py"),
    ("PowerShell", "Remove-Item build -Recurse"),
    ("PowerShell", "del stale.txt"),
)

SHELL_FREE = (
    ("Bash", "git status"),
    ("Bash", "cat src/app.py"),
    ("Bash", "grep -n 'def ' src/app.py | head -5"),
    ("Bash", "uv run python -m unittest discover -s tests -v 2>&1 | tail -20"),
    ("Bash", "pytest -q 2>/dev/null"),
    ("Bash", "ls > /dev/null"),
    ("Bash", "echo 'a > b' && git diff --stat"),
    ("Bash", "sed -n '1,20p' src/app.py"),
    ("Bash", "git checkout main"),
    ("Bash", "git log --oneline -5"),
    ("PowerShell", "Get-Content notes.txt"),
    ("PowerShell", "Test-Path build 2>$null"),
)


class AdapterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.session = Session(self.root)
        self._sessions = 0

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def fresh(self) -> Session:
        """A new session in its own folder, for subtests that need a clean start."""

        self._sessions += 1
        folder = self.root / f"s{self._sessions}"
        folder.mkdir()
        return Session(folder, session_id=f"session-{self._sessions}")

    def routed(self, route: str = "goated-route: direct", prompt: str = "Do the task.") -> Session:
        s = self.session
        s.prompt(prompt)
        s.load(ROUTER)
        s.say(route)
        return s


def hold_line(output: dict) -> str:
    return reason(output).split("\n", 1)[0]


class ShellWriteTests(AdapterTestCase):
    def test_shell_writes_meet_the_route_line_hold(self) -> None:
        for tool, command in SHELL_WRITES:
            with self.subTest(command=command):
                s = self.fresh()
                s.prompt("Tidy the build output.")
                s.load(ROUTER)
                held = s.call(tool, {"command": command})
                self.assertEqual(hold_line(held), "goated-hold: route-line | strict")
                s.say("goated-route: direct")
                self.assertEqual(decision(s.call(tool, {"command": command})), "pass")

    def test_shell_writes_meet_the_pipeline_hold(self) -> None:
        for tool, command in SHELL_WRITES:
            with self.subTest(command=command):
                s = self.fresh()
                s.prompt("Tidy the build output.")
                s.load(ROUTER)
                s.say("goated-route: standard | requires: tdd")
                held = s.call(tool, {"command": command})
                self.assertEqual(hold_line(held), "goated-hold: pipeline | strict")
                s.load("tdd")
                self.assertEqual(decision(s.call(tool, {"command": command})), "pass")

    def test_reads_test_runs_and_git_status_stay_free(self) -> None:
        for tool, command in SHELL_FREE:
            with self.subTest(command=command):
                s = self.fresh()
                s.prompt("Tidy the build output.")
                s.load(ROUTER)
                s.say("goated-route: standard | requires: tdd")
                self.assertEqual(decision(s.call(tool, {"command": command})), "pass")


def commit(message: str) -> dict:
    return {"command": f'git add -A && git commit -m "{message}"'}


class CommitHoldTests(AdapterTestCase):
    def test_commit_is_held_until_commit_message_loads_in_this_turn(self) -> None:
        s = self.routed()

        held = s.call("Bash", commit("Add CSV export"))
        self.assertEqual(hold_line(held), "goated-hold: commit | strict")
        self.assertIn("commit-message", reason(held))

        s.load("commit-message")
        self.assertEqual(decision(s.call("Bash", commit("Add CSV export"))), "pass")

    def test_an_unchanged_retry_never_passes(self) -> None:
        s = self.routed()

        for _ in range(3):
            self.assertEqual(decision(s.call("Bash", commit("Add CSV export"))), "deny")

    def test_a_skip_line_never_passes_the_strict_commit_hold(self) -> None:
        s = self.routed()
        s.say("goated-skip: commit-message: the message is already written and fine")

        self.assertEqual(decision(s.call("Bash", commit("Add CSV export"))), "deny")

    def test_a_load_in_an_earlier_turn_does_not_satisfy_a_later_commit(self) -> None:
        s = self.routed()
        s.load("commit-message")
        self.assertEqual(decision(s.call("Bash", commit("Add CSV export"))), "pass")

        s.prompt("Commit the follow-up too.")
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Bash", commit("Fix export rounding"))), "deny")

    def test_the_hold_does_not_refire_after_compliance(self) -> None:
        s = self.routed()
        s.load("commit-message")

        self.assertEqual(decision(s.call("Bash", commit("Add CSV export"))), "pass")
        self.assertEqual(decision(s.call("Bash", commit("Add export docs"))), "pass")

    def test_commit_forms_are_recognized(self) -> None:
        for command in (
            "git commit -m 'Add CSV export'",
            "git -C repo commit --amend --no-edit",
            "cd repo; git commit -F msg.txt",
            "git commit",
        ):
            with self.subTest(command=command):
                s = self.fresh()
                s.prompt("Commit it.")
                s.load(ROUTER)
                s.say("goated-route: direct")
                held = s.call("Bash", {"command": command})
                self.assertEqual(hold_line(held), "goated-hold: commit | strict")

    def test_mentions_of_commit_are_not_commits(self) -> None:
        s = self.routed()
        for command in ("git log -1 --format=%B", "echo 'git commit later'", "git commit-tree x"):
            with self.subTest(command=command):
                self.assertEqual(decision(s.call("Bash", {"command": command})), "pass")


class CommitMessageContentTests(AdapterTestCase):
    def loaded(self) -> Session:
        s = self.routed()
        s.load("commit-message")
        return s

    def test_a_message_breaking_the_contract_is_held(self) -> None:
        cases = {
            "empty subject": {"command": 'git commit -m ""'},
            "long subject": commit("Add " + "very " * 16 + "long subject"),
            "no blank line": {
                "command": "git commit -F - <<'EOF'\nAdd CSV export\nBody right under it.\nEOF"
            },
        }
        for name, command in cases.items():
            with self.subTest(case=name):
                s = self.fresh()
                s.prompt("Commit it.")
                s.load(ROUTER)
                s.say("goated-route: direct")
                s.load("commit-message")
                held = s.call("Bash", command)
                self.assertEqual(hold_line(held), "goated-hold: commit | strict")
                self.assertIn("commit-message", reason(held))

    def test_a_message_with_a_secret_shape_is_held(self) -> None:
        s = self.loaded()
        token = "ghp_" + "A1b2C3d4E5f6G7h8I9j0" * 2
        held = s.call("Bash", commit(f"Rotate token {token}"))
        self.assertEqual(decision(held), "deny")
        self.assertNotIn(token, reason(held))

    def test_well_formed_messages_pass(self) -> None:
        s = self.loaded()
        heredoc = (
            'git commit -m "$(cat <<\'EOF\'\nAdd CSV export\n\nExplain why the export'
            ' exists.\nEOF\n)"'
        )
        here_string = "git commit -m @'\nAdd CSV export\n\nWhy it exists.\n'@"
        for command in (heredoc, here_string, "git commit -m 'Add CSV export' -m 'Body.'"):
            with self.subTest(command=command):
                self.assertEqual(decision(s.call("Bash", {"command": command})), "pass")


class CommitOverrideTests(AdapterTestCase):
    def test_a_user_typed_commit_message_stands_the_hold_down(self) -> None:
        s = self.session
        s.prompt('Commit this with the message "Fix export rounding".')
        s.load(ROUTER)
        s.say("goated-route: direct")

        self.assertEqual(decision(s.call("Bash", commit("Fix export rounding"))), "pass")

    def test_a_different_message_is_still_held(self) -> None:
        s = self.session
        s.prompt('Commit this with the message "Fix export rounding".')
        s.load(ROUTER)
        s.say("goated-route: direct")

        self.assertEqual(decision(s.call("Bash", commit("Rework the exporter"))), "deny")

    def test_the_override_lasts_only_for_that_prompt(self) -> None:
        s = self.session
        s.prompt("Commit message: Fix export rounding")
        s.load(ROUTER)
        s.say("goated-route: direct")
        self.assertEqual(decision(s.call("Bash", commit("Fix export rounding"))), "pass")

        s.prompt("Commit again.")
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Bash", commit("Fix export rounding"))), "deny")

    def test_an_agent_written_commit_message_is_not_an_override(self) -> None:
        s = self.routed()
        s.say('I will commit with the message "Fix export rounding".')

        self.assertEqual(decision(s.call("Bash", commit("Fix export rounding"))), "deny")

    def test_a_user_typed_skill_skip_stands_the_hold_down(self) -> None:
        s = self.session
        s.prompt("Commit it and skip commit-message this time.")
        s.load(ROUTER)
        s.say("goated-route: direct")

        self.assertEqual(decision(s.call("Bash", commit("Add CSV export"))), "pass")


class PullRequestHoldTests(AdapterTestCase):
    def test_pr_creation_is_held_until_pr_description_loads(self) -> None:
        s = self.routed()
        command = {"command": "gh pr create --title 'Add export' --body-file body.md"}

        held = s.call("Bash", command)
        self.assertEqual(hold_line(held), "goated-hold: pull-request | strict")
        s.say("goated-skip: pr-description: the body is already drafted well")
        self.assertEqual(decision(s.call("Bash", command)), "deny")

        s.load("pr-description")
        self.assertEqual(decision(s.call("Bash", command)), "pass")

    def test_a_pr_tool_is_held_too(self) -> None:
        s = self.routed()
        tool = "mcp__github__create_pull_request"

        self.assertEqual(
            hold_line(s.call(tool, {"title": "x"})), "goated-hold: pull-request | strict"
        )
        s.load("pr-description")
        self.assertEqual(decision(s.call(tool, {"title": "x"})), "pass")

    def test_other_gh_commands_stay_free(self) -> None:
        s = self.routed()

        self.assertEqual(decision(s.call("Bash", {"command": "gh pr view 12"})), "pass")


class SpawnBriefTests(AdapterTestCase):
    def test_a_spawn_is_held_until_handoff_loads_and_its_template_is_read(self) -> None:
        s = self.routed()

        held = s.call("Agent", {"prompt": BRIEF})
        self.assertEqual(hold_line(held), "goated-hold: spawn | strict")
        s.load("handoff")
        held = s.call("Agent", {"prompt": BRIEF})
        self.assertEqual(decision(held), "deny")
        self.assertIn("spawn-brief.md", reason(held))

        s.read(SPAWN_BRIEF_PATH, success=False)
        self.assertEqual(decision(s.call("Agent", {"prompt": BRIEF})), "deny")
        s.read(SPAWN_BRIEF_PATH)
        self.assertEqual(decision(s.call("Agent", {"prompt": BRIEF})), "pass")
        self.assertEqual(decision(s.call("Agent", {"prompt": BRIEF})), "pass")

    def test_a_brief_missing_a_required_section_is_held(self) -> None:
        s = self.routed()
        s.brief_with_handoff()
        brief = "## Goal\n\nAudit the exporter.\n\n## Scope\n\n- Work in: src/export/\n"

        held = s.call("Agent", {"prompt": brief})
        self.assertEqual(hold_line(held), "goated-hold: spawn | strict")
        self.assertIn("## Done Means", reason(held))

    def test_a_skip_line_never_passes_the_spawn_hold(self) -> None:
        s = self.routed()
        s.say("goated-skip: handoff: this is only a quick lookup agent")

        self.assertEqual(decision(s.call("Agent", {"prompt": BRIEF})), "deny")

    def test_the_implementer_prompt_counts_with_its_own_sections(self) -> None:
        s = self.routed()
        s.load("subagent-driven-development")
        s.read(
            "/opt/goated/skills/subagent-driven-development/references/implementer-prompt.md"
        )
        brief = (
            "## Task\n\nAdd export.\n\n## Ownership\n\n- src/\n\n"
            "## Required Report Format\n\n- Status\n"
        )

        self.assertEqual(decision(s.call("Agent", {"prompt": brief})), "pass")
        held = s.call("Agent", {"prompt": BRIEF})
        self.assertIn("## Task", reason(held))

    def test_session_spawns_without_a_brief_are_not_held(self) -> None:
        s = self.routed()
        tool = "mcp__ccd_session__start_session"

        offer = {"title": "Fix it", "initiation": "offer"}
        self.assertEqual(decision(s.call(tool, offer)), "pass")
        self.assertEqual(decision(s.call(tool, {"prompt": "do it"})), "deny")


def write(path: str, lines: int = 6) -> dict:
    return {"file_path": path, "content": "\n".join(f"line {n}" for n in range(lines))}


class DesignHoldTests(AdapterTestCase):
    def test_a_substantial_code_edit_is_held_until_design_loads(self) -> None:
        s = self.routed()

        held = s.call("Write", write("src/export.py"))
        self.assertEqual(hold_line(held), "goated-hold: design | justified-skip")
        self.assertEqual(decision(s.call("Write", write("src/export.py"))), "deny")

        s.load("software-design-principles")
        self.assertEqual(decision(s.call("Write", write("src/export.py"))), "pass")
        self.assertEqual(decision(s.call("Write", write("src/other.py"))), "pass")

    def test_a_skip_line_passes_the_design_hold(self) -> None:
        s = self.routed()
        self.assertEqual(decision(s.call("Write", write("src/export.py"))), "deny")

        s.say("goated-skip: software-design-principles: this is a mechanical rename only")
        self.assertEqual(decision(s.call("Write", write("src/export.py"))), "pass")

    def test_a_skip_line_with_too_short_a_reason_does_not_pass(self) -> None:
        s = self.routed()
        s.say("goated-skip: software-design-principles: mechanical")

        self.assertEqual(decision(s.call("Write", write("src/export.py"))), "deny")

    def test_small_edits_and_docs_are_not_held(self) -> None:
        s = self.routed()

        self.assertEqual(decision(s.call("Write", write("src/export.py", lines=2))), "pass")
        self.assertEqual(decision(s.call("Write", write("docs/guide.md", lines=40))), "pass")

    def test_a_load_in_an_earlier_turn_does_not_count(self) -> None:
        s = self.routed()
        s.load("software-design-principles")
        self.assertEqual(decision(s.call("Write", write("src/export.py"))), "pass")

        s.prompt("Now the importer.")
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Write", write("src/import.py"))), "deny")


class SecurityHoldTests(AdapterTestCase):
    def test_a_sensitive_path_is_held_until_security_review_loads(self) -> None:
        s = self.routed()
        edit = {"file_path": "src/auth/login.py", "old_string": "a", "new_string": "b"}

        held = s.call("Edit", edit)
        self.assertEqual(hold_line(held), "goated-hold: security | justified-skip")
        self.assertIn("auth", reason(held))
        self.assertEqual(decision(s.call("Edit", edit)), "deny")
        s.load("code-security-review")
        self.assertEqual(decision(s.call("Edit", edit)), "pass")

    def test_a_skip_line_passes_the_security_hold(self) -> None:
        s = self.routed()
        s.say("goated-skip: code-security-review: only a comment typo in the file")

        edit = {"file_path": "package.json", "old_string": "a", "new_string": "b"}
        self.assertEqual(decision(s.call("Edit", edit)), "pass")

    def test_ordinary_paths_and_docs_are_not_held(self) -> None:
        s = self.routed()
        for path in ("src/export.py", "docs/auth.md"):
            with self.subTest(path=path):
                edit = {"file_path": path, "old_string": "a", "new_string": "b"}
                self.assertEqual(decision(s.call("Edit", edit)), "pass")


class SubagentActionTests(AdapterTestCase):
    """Inside a subagent, action gates apply and routing gates do not (spec R9)."""

    def setUp(self) -> None:
        super().setUp()
        self.session.prompt("Delegate the export work.")
        self.agent = self.session.subagent("a7")

    def sub_call(self, tool: str, tool_input: dict) -> dict:
        return self.agent.call(tool, tool_input, agent_id="a7", agent_type="general-purpose")

    def test_routing_gates_do_not_apply_but_action_gates_do(self) -> None:
        a = self.agent
        a.prompt("Implement the export. Skip routing and skip commit-message.", hook=False)

        self.assertEqual(decision(self.sub_call("Edit", {"file_path": "notes.md"})), "pass")
        self.assertEqual(
            hold_line(self.sub_call("Bash", commit("Add export"))),
            "goated-hold: commit | strict",
        )
        self.assertEqual(
            hold_line(self.sub_call("Write", write("src/export.py"))),
            "goated-hold: design | justified-skip",
        )

    def test_a_subagent_load_clears_its_own_hold(self) -> None:
        a = self.agent
        a.prompt("Implement the export.", hook=False)
        a.load("commit-message")

        self.assertEqual(decision(self.sub_call("Bash", commit("Add export"))), "pass")

    def test_a_parent_load_does_not_clear_a_subagent_hold(self) -> None:
        self.session.load("commit-message")
        self.agent.prompt("Implement the export.", hook=False)

        self.assertEqual(decision(self.sub_call("Bash", commit("Add export"))), "deny")

    def test_a_missing_subagent_transcript_fails_open(self) -> None:
        output = parse(self.session.hook(
            "PreToolUse", tool_name="Bash", tool_input=commit("Add export"),
            tool_use_id="toolu_x", agent_id="unknown9", agent_type="general-purpose",
        ))
        self.assertEqual(decision(output), "pass")
        self.assertIn("allowed without checks", output.get("systemMessage", ""))


def stop(s: Session, final: str = "") -> dict:
    return parse(s.hook("Stop", stop_hook_active=False, last_assistant_message=final))


def closeout_line(output: dict) -> str:
    return str(output.get("reason", "")).split("\n", 1)[0] if output.get("decision") else ""


class CloseoutTests(AdapterTestCase):
    def changed(self, path: str = "src/export.py") -> Session:
        s = self.routed()
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        self.assertEqual(decision(s.call("Write", write(path))), "pass")
        return s

    def test_a_turn_without_code_changes_ends_freely(self) -> None:
        s = self.routed()
        s.call("Write", write("docs/guide.md"))
        s.run("cat src/export.py")

        self.assertEqual(stop(s), {})

    def test_a_code_change_needs_fresh_proof_and_a_retry_never_passes(self) -> None:
        s = self.changed()

        for _ in range(2):
            held = stop(s)
            self.assertEqual(closeout_line(held), "goated-hold: closeout | justified-skip")
            self.assertIn("Proof", held["reason"])

        s.run("uv run python -m unittest discover -s tests")
        held = stop(s)
        self.assertNotIn("Proof", held["reason"])
        self.assertIn("doc-sync", held["reason"])

        s.load("doc-sync")
        self.assertEqual(stop(s), {})

    def test_check_commands_count_as_proof_and_reads_do_not(self) -> None:
        for command, is_proof in (
            ("uv run python scripts/validate_skills.py", True),
            ("npm run build", True),
            ("cargo test", True),
            ("cat tests/test_export.py", False),
            ("git diff --check", False),
        ):
            with self.subTest(command=command):
                s = self.fresh()
                s.prompt("Bump it.")
                s.load(ROUTER)
                s.say("goated-route: direct")
                s.load("doc-sync")
                s.run("sed -i 's/1/2/' src/export.py")
                s.run(command)
                held = stop(s)
                self.assertEqual("Proof" not in held.get("reason", ""), is_proof)

    def test_loading_verification_alone_is_not_proof(self) -> None:
        s = self.changed()
        s.load("doc-sync")
        s.load("verification-before-completion")

        self.assertIn("Proof", stop(s)["reason"])

    def test_proof_before_the_last_change_is_not_fresh(self) -> None:
        s = self.changed()
        s.run("pytest -q")
        s.call("Edit", {"file_path": "src/export.py", "old_string": "a", "new_string": "b"})
        s.load("doc-sync")

        self.assertIn("Proof", stop(s)["reason"])

    def test_skip_lines_pass_every_closeout_item(self) -> None:
        s = self.changed()
        final = (
            "Done.\n\ngoated-skip: verification-before-completion: no test harness exists here\n"
            "goated-skip: doc-sync: internal constant with no documented behavior"
        )

        self.assertEqual(stop(s, final), {})

    def test_a_skip_line_already_in_the_transcript_counts(self) -> None:
        s = self.changed()
        s.run("pytest -q")
        s.say("goated-skip: doc-sync: internal constant with no documented behavior")

        self.assertEqual(stop(s), {})

    def test_a_failing_last_check_needs_a_handoff(self) -> None:
        s = self.changed()
        s.run("pytest -q", success=False)
        s.load("doc-sync")

        held = stop(s)
        self.assertIn("handoff", held["reason"])
        s.load("handoff")
        self.assertEqual(stop(s), {})

    def test_test_only_changes_do_not_need_doc_sync(self) -> None:
        s = self.changed("tests/test_export.py")
        s.run("pytest -q")

        self.assertEqual(stop(s), {})

    def test_a_held_edit_is_not_a_change(self) -> None:
        s = self.routed()
        self.assertEqual(decision(s.call("Write", write("src/export.py"))), "deny")

        self.assertEqual(stop(s), {})

    def test_a_shell_write_to_code_is_a_change(self) -> None:
        s = self.routed()
        s.run("sed -i 's/1/2/' src/export.py")

        self.assertIn("Proof", stop(s)["reason"])

    def test_applied_design_needs_the_red_flags_read_after_the_last_change(self) -> None:
        s = self.routed()
        s.load("software-design-principles")
        red_flags = "/opt/goated/skills/software-design-principles/references/red-flags.md"
        s.read(red_flags)
        s.call("Write", write("src/export.py"))
        s.run("pytest -q")
        s.load("doc-sync")

        held = stop(s)
        self.assertIn("red-flags.md", held["reason"])
        s.read(red_flags)
        self.assertEqual(stop(s), {})

    def test_a_user_typed_skill_skip_stands_its_item_down(self) -> None:
        s = self.session
        s.prompt("Bump the constant, and skip doc-sync.")
        s.load(ROUTER)
        s.say("goated-route: direct")
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.call("Write", write("src/export.py"))
        s.run("pytest -q")

        self.assertEqual(stop(s), {})

    def test_the_closeout_does_not_carry_into_the_next_turn(self) -> None:
        s = self.changed()
        self.assertTrue(stop(s))

        s.prompt("Thanks. What does the exporter do?")
        self.assertEqual(stop(s), {})


class HoldFormatTests(AdapterTestCase):
    """Every hold's first line follows the format the skill-usage mod parses."""

    FORMAT = re.compile(
        r"^goated-hold: (router-first|route-line|pipeline|commit|pull-request|spawn"
        r"|design|security|closeout) \| (strict|justified-skip)$"
    )

    def test_every_hold_message_starts_with_the_documented_line(self) -> None:
        s = self.session
        s.prompt("Do the task.")
        lines = [hold_line(s.call("Bash"))]
        s.load(ROUTER)
        lines.append(hold_line(s.call("Edit")))
        s.say("goated-route: standard | requires: tdd")
        lines.append(hold_line(s.call("Edit")))
        s.load("tdd")
        lines.append(hold_line(s.call("Bash", commit("Add export"))))
        lines.append(hold_line(s.call("Bash", {"command": "gh pr create"})))
        lines.append(hold_line(s.call("Agent", {"prompt": BRIEF})))
        lines.append(hold_line(s.call("Write", write("src/export.py"))))
        lines.append(hold_line(s.call("Edit", {"file_path": ".env", "new_string": "x"})))
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.call("Write", write("src/export.py"))
        lines.append(closeout_line(stop(s)))

        self.assertEqual(len(set(lines)), 9)
        for line in lines:
            self.assertRegex(line, self.FORMAT)
