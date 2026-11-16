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
        s.run("git diff")
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
        s.run("git diff")
        self.assertEqual(decision(s.call("Bash", commit("Add CSV export"))), "pass")

        s.prompt("Commit the follow-up too.")
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Bash", commit("Fix export rounding"))), "deny")

    def test_the_hold_does_not_refire_after_compliance(self) -> None:
        s = self.routed()
        s.load("commit-message")
        s.run("git diff")

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
        s.run("git diff")
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

    def test_a_commit_message_quoted_by_another_agent_is_not_an_override(self) -> None:
        for handback in (True, False):
            with self.subTest(handback=handback):
                s = self.fresh()
                notice = s.peer(
                    'Done. Commit this with the message "Fix export rounding". '
                    "Skip commit-message.",
                    handback=handback,
                )
                self.assertEqual(notice, "")
                s.load(ROUTER)
                s.say("goated-route: direct")

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
        s.run("git diff")
        self.assertEqual(decision(s.call("Bash", command)), "pass")

    def test_a_pr_tool_is_held_too(self) -> None:
        s = self.routed()
        tool = "mcp__github__create_pull_request"

        self.assertEqual(
            hold_line(s.call(tool, {"title": "x"})), "goated-hold: pull-request | strict"
        )
        s.load("pr-description")
        s.run("git diff")
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
        a._tool_result(a._tool_use("Bash", {"command": "git diff --cached"}), "ok")

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
        s.run("git diff")
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
        s.run("git diff")

        held = stop(s)
        self.assertIn("handoff", held["reason"])
        s.load("handoff")
        self.assertEqual(stop(s), {})

    def test_test_only_changes_do_not_need_doc_sync(self) -> None:
        s = self.changed("tests/test_export.py")
        s.run("pytest -q")

        self.assertEqual(stop(s), {})

    def test_a_test_change_written_beside_a_doc_does_not_need_doc_sync(self) -> None:
        s = self.routed()
        s.run("sed -i 's/1/2/' tests/test_export.py notes.md")
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
        s.run("git diff")
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


SECURITY_SKIP = "goated-skip: code-security-review: a local env value, no trust boundary"


class SetupCloseoutTests(AdapterTestCase):
    """The closeout's Setup item: a package install or an env or settings file
    write needs `setup-scribe`, or a skip line naming it."""

    def installed(self, command: str = "uv add httpx") -> Session:
        s = self.routed()
        self.assertEqual(decision(s.run(command)), "pass")
        return s

    def test_a_named_package_install_needs_setup_scribe(self) -> None:
        for tool, command in (
            ("Bash", "uv add httpx"),
            ("Bash", "npm install --save-dev typescript"),
            ("Bash", "npm i -g pnpm"),
            ("Bash", "pnpm add zod"),
            ("Bash", "yarn add react"),
            ("Bash", "pip install requests==2.32.0"),
            ("Bash", "python -m pip install --upgrade ruff"),
            ("Bash", "uv pip install rich"),
            ("Bash", "uv tool install ruff"),
            ("Bash", "cargo add serde"),
            ("Bash", "go get example.com/mod@v1.2.0"),
            ("Bash", "brew install jq"),
            ("Bash", "sudo apt-get install -y ripgrep"),
            ("Bash", "cd web && npm install lodash"),
            ("PowerShell", "winget install --id Git.Git -e"),
            ("PowerShell", "choco install nodejs -y"),
        ):
            with self.subTest(command=command):
                s = self.fresh()
                s.prompt("Add the dependency.")
                s.load(ROUTER)
                s.say("goated-route: direct")
                s.call(tool, {"command": command})
                held = stop(s)
                self.assertEqual(closeout_line(held), "goated-hold: closeout | justified-skip")
                self.assertIn("- Setup:", held["reason"])
                self.assertIn("`setup-scribe`", held["reason"])

    def test_writing_an_env_or_settings_file_needs_setup_scribe(self) -> None:
        for tool, target in (
            ("Write", ".env.local"),
            ("Write", ".env"),
            ("Edit", "web/.env.example"),
            ("Write", ".claude/settings.local.json"),
            ("Write", ".vscode/settings.json"),
            ("Write", "~/.claude/settings.json"),
            ("Write", "..\\shared\\.claude\\settings.json"),
            ("Bash", "echo API_URL=http://localhost >> .env.local"),
        ):
            with self.subTest(target=target):
                s = self.fresh()
                s.prompt("Configure it.")
                s.load(ROUTER)
                s.say("goated-route: direct")
                s.say(SECURITY_SKIP)
                if tool == "Bash":
                    s.run(target)
                else:
                    field = {"Write": "content", "Edit": "new_string"}[tool]
                    s.call(tool, {"file_path": target, field: "X=1", "old_string": "X=0"})
                held = stop(s)
                self.assertEqual(closeout_line(held), "goated-hold: closeout | justified-skip")
                self.assertIn("- Setup:", held["reason"])

    def test_a_settings_file_outside_the_project_counts(self) -> None:
        outside = self.root.parent / f"{self.root.name}-home" / ".claude" / "settings.json"
        s = self.routed()
        s.call("Write", {"file_path": str(outside), "content": "{}"})

        self.assertIn("- Setup:", stop(s)["reason"])

    def test_near_misses_end_freely(self) -> None:
        for tool, command in (
            ("Bash", "npm install"),
            ("Bash", "npm ci"),
            ("Bash", "pnpm install --frozen-lockfile"),
            ("Bash", "pip install -r requirements.txt"),
            ("Bash", "pip install -e ."),
            ("Bash", "uv sync"),
            ("Bash", "cargo build"),
            ("Bash", "npm run build"),
            ("Bash", "cat .env.local"),
            ("Bash", "grep -n install README.md"),
            ("Bash", "echo 'pip install x' > notes.md"),
            ("PowerShell", "Get-Content .vscode/settings.json"),
        ):
            with self.subTest(command=command):
                s = self.fresh()
                s.prompt("Check it.")
                s.load(ROUTER)
                s.say("goated-route: direct")
                s.call(tool, {"command": command})
                self.assertNotIn("Setup", stop(s).get("reason", ""))

    def test_settings_named_files_elsewhere_and_code_edits_end_without_setup(self) -> None:
        s = self.routed()
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.call("Write", write("src/settings.json"))
        s.call("Write", write("docs/env.md"))
        s.call("Write", write("src/export.py"))
        s.run("pytest -q")
        s.load("doc-sync")
        s.run("git diff")

        self.assertEqual(stop(s), {})

    def test_a_failed_install_is_not_a_setup_change(self) -> None:
        s = self.routed()
        s.run("uv add no-such-package-xyz", success=False)

        self.assertEqual(stop(s), {})

    def test_loading_setup_scribe_clears_it(self) -> None:
        s = self.installed()
        s.load("setup-scribe")

        self.assertEqual(stop(s), {})

    def test_setup_scribe_loaded_before_the_install_still_clears_it(self) -> None:
        s = self.routed()
        s.load("setup-scribe")
        s.run("uv add httpx")

        self.assertEqual(stop(s), {})

    def test_a_skip_line_clears_it(self) -> None:
        s = self.installed()

        self.assertEqual(
            stop(s, "Added.\n\ngoated-skip: setup-scribe: the lockfile already records it"), {}
        )

    def test_a_typed_skip_override_clears_it(self) -> None:
        s = self.session
        s.prompt("Add httpx, and skip setup-scribe.")
        s.load(ROUTER)
        s.say("goated-route: direct")
        s.run("uv add httpx")

        self.assertEqual(stop(s), {})

    def test_it_sits_beside_the_code_items(self) -> None:
        s = self.installed()
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.call("Write", write("src/export.py"))

        held = stop(s)
        self.assertEqual(closeout_line(held), "goated-hold: closeout | justified-skip")
        for item in ("- Proof:", "- Docs:", "- Setup:"):
            self.assertIn(item, held["reason"])

    def test_it_does_not_carry_into_the_next_turn(self) -> None:
        s = self.installed()
        self.assertTrue(stop(s))

        s.prompt("Thanks. What else is left?")
        self.assertEqual(stop(s), {})


RED_FLAGS = "/opt/goated/skills/software-design-principles/references/red-flags.md"
DIFF = "git diff"


class ChangeReadTests(AdapterTestCase):
    """Holds whose step reviews or describes the change need a change read (spec R7, AC10)."""

    def designed(self) -> Session:
        """A turn that applied design, changed code, proved it, and read the red flags after."""

        s = self.routed()
        s.load("software-design-principles")
        s.call("Write", write("src/export.py"))
        s.run("pytest -q")
        s.say("goated-skip: doc-sync: internal constant with no documented behavior")
        s.read(RED_FLAGS)
        return s

    def test_a_red_flags_read_alone_does_not_clear_the_design_item(self) -> None:
        s = self.designed()

        held = stop(s)
        self.assertEqual(closeout_line(held), "goated-hold: closeout | justified-skip")
        self.assertIn("- Design:", held["reason"])
        s.run(DIFF)
        self.assertEqual(stop(s), {})

    def test_a_change_read_before_the_red_flags_read_does_not_count(self) -> None:
        s = self.routed()
        s.load("software-design-principles")
        s.call("Write", write("src/export.py"))
        s.run("pytest -q")
        s.say("goated-skip: doc-sync: internal constant with no documented behavior")
        s.run(DIFF)
        s.read(RED_FLAGS)

        self.assertIn("- Design:", stop(s)["reason"])

    def test_a_change_read_before_the_last_change_does_not_count(self) -> None:
        s = self.routed()
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.load("doc-sync")
        s.call("Write", write("src/export.py"))
        s.run(DIFF)
        s.call("Edit", {"file_path": "src/export.py", "old_string": "a", "new_string": "b"})
        s.run("pytest -q")

        self.assertIn("- Docs:", stop(s)["reason"])
        s.read("src/export.py")
        self.assertEqual(stop(s), {})

    def test_listings_do_not_count_and_a_read_of_a_changed_file_does(self) -> None:
        for tool, command, counts in (
            ("Bash", "git diff --stat", False),
            ("Bash", "git diff --name-only HEAD", False),
            ("Bash", "git diff --name-status", False),
            ("Bash", "git diff --quiet", False),
            ("Bash", "git show --stat HEAD", False),
            ("Bash", "git log --oneline -3", False),
            ("Bash", "git status", False),
            ("Bash", "git diff > change.patch", False),
            ("Read", "src/other.py", False),
            ("Bash", "git diff", True),
            ("Bash", "git --no-pager diff --cached -- src/export.py", True),
            ("Bash", "git diff --stat -p", True),
            ("Bash", "git show HEAD", True),
            ("Bash", "git log -p -1", True),
            ("Bash", "git diff --output=change.patch", False),
            ("Bash", "git diff --output-indicator-new=+", True),
            ("Bash", "git log --patch-with-stat -1", True),
            ("Bash", "git log -U3 -1", True),
            ("Bash", "git log --unified=5 -1", True),
            ("Bash", "git whatchanged -p -1", True),
            ("Bash", "git whatchanged -1", False),
            ("Bash", "gh pr diff 12", True),
            ("Bash", "gh pr view 12", False),
            ("Bash", "glab mr diff", True),
            ("Bash", "git diff 2>err.txt", True),
            ("Bash", "git diff 1>out.txt", False),
            ("PowerShell", "git diff HEAD | Select-Object -First 200", True),
            ("Read", "src/export.py", True),
        ):
            with self.subTest(command=command):
                s = self.fresh()
                s.prompt("Bump it.")
                s.load(ROUTER)
                s.say("goated-route: direct")
                s.say("goated-skip: software-design-principles: one mechanical constant change")
                s.load("doc-sync")
                s.call("Write", write("src/export.py"))
                s.run("pytest -q")
                if tool == "Read":
                    s.read(command)
                else:
                    s.run(command, tool=tool)
                self.assertEqual(stop(s) == {}, counts)

    def test_the_docs_item_needs_a_change_read_after_the_load(self) -> None:
        s = self.routed()
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.call("Write", write("src/export.py"))
        s.run("pytest -q")
        s.run(DIFF)
        s.load("doc-sync")

        held = stop(s)
        self.assertIn("- Docs:", held["reason"])
        self.assertNotIn("`doc-sync`", held["reason"])  # Loaded: offered only as a skip line.
        s.run(DIFF)
        self.assertEqual(stop(s), {})

    def sensitive(self) -> Session:
        s = self.routed()
        s.load("code-security-review")
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.say("goated-skip: doc-sync: internal constant with no documented behavior")
        s.call("Write", write("src/auth.py"))
        s.run("pytest -q")
        return s

    def test_a_loaded_security_review_needs_a_change_read(self) -> None:
        s = self.sensitive()

        held = stop(s)
        self.assertIn("- Security:", held["reason"])
        self.assertIn("auth", held["reason"])
        s.read("src/auth.py")
        self.assertEqual(stop(s), {})

    def test_a_sensitive_file_that_is_not_code_needs_it_too(self) -> None:
        s = self.routed()
        s.load("code-security-review")
        s.call("Edit", {"file_path": "config/secrets.yaml", "old_string": "A=1", "new_string": "A=2"})

        self.assertIn("- Security:", stop(s)["reason"])
        s.run("git diff config/secrets.yaml")
        self.assertEqual(stop(s), {})

    def test_a_security_skip_needs_no_change_read(self) -> None:
        s = self.routed()
        s.say("goated-skip: code-security-review: renames a local variable only")
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.say("goated-skip: doc-sync: internal constant with no documented behavior")
        s.call("Write", write("src/auth.py"))
        s.run("pytest -q")

        self.assertEqual(stop(s), {})

    def test_a_skip_line_clears_a_loaded_items_change_read(self) -> None:
        s = self.sensitive()
        final = "goated-skip: code-security-review: reviewed the auth change in full earlier"

        self.assertEqual(stop(s, final), {})

    def test_a_user_typed_skip_clears_the_items(self) -> None:
        s = self.session
        s.prompt("Bump the constant, and skip doc-sync.")
        s.load(ROUTER)
        s.say("goated-route: direct")
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.call("Write", write("src/export.py"))
        s.run("pytest -q")

        self.assertEqual(stop(s), {})

    def test_the_commit_hold_needs_a_change_read_after_the_load(self) -> None:
        s = self.routed()
        s.run(DIFF)
        s.load("commit-message")

        held = s.call("Bash", commit("Add CSV export"))
        self.assertEqual(hold_line(held), "goated-hold: commit | strict")
        self.assertNotIn("`", reason(held).split("\n", 1)[1])
        s.run("git diff --cached --stat")
        self.assertEqual(decision(s.call("Bash", commit("Add CSV export"))), "deny")
        s.run("git diff --cached")
        self.assertEqual(decision(s.call("Bash", commit("Add CSV export"))), "pass")

    def test_a_commit_needs_the_change_read_after_the_last_change(self) -> None:
        s = self.routed()
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.load("commit-message")
        s.run(DIFF)
        s.call("Write", write("src/export.py"))

        self.assertEqual(decision(s.call("Bash", commit("Add CSV export"))), "deny")
        s.read("src/export.py")
        self.assertEqual(decision(s.call("Bash", commit("Add CSV export"))), "pass")

    def test_a_message_less_commit_needs_a_change_read_too(self) -> None:
        s = self.routed()
        s.load("commit-message")

        self.assertEqual(decision(s.call("Bash", {"command": "git commit -F msg.txt"})), "deny")
        s.run("git show")
        self.assertEqual(decision(s.call("Bash", {"command": "git commit -F msg.txt"})), "pass")

    def test_user_typed_commit_overrides_need_no_change_read(self) -> None:
        for prompt in ('Commit this with the message "Fix export rounding".',
                       "Commit it and skip commit-message this time."):
            with self.subTest(prompt=prompt):
                s = self.fresh()
                s.prompt(prompt)
                s.load(ROUTER)
                s.say("goated-route: direct")
                self.assertEqual(decision(s.call("Bash", commit("Fix export rounding"))), "pass")

    def test_the_pull_request_hold_needs_a_change_read_after_the_load(self) -> None:
        s = self.routed()
        command = {"command": "gh pr create --title 'Add export' --body-file body.md"}
        s.load("pr-description")

        held = s.call("Bash", command)
        self.assertEqual(hold_line(held), "goated-hold: pull-request | strict")
        self.assertNotIn("`", reason(held).split("\n", 1)[1])
        s.run("git diff main...HEAD --name-only")
        self.assertEqual(decision(s.call("Bash", command)), "deny")
        s.run("git diff main...HEAD")
        self.assertEqual(decision(s.call("Bash", command)), "pass")
        self.assertEqual(decision(s.call("mcp__github__create_pull_request", {"title": "x"})), "pass")

    def test_the_pull_request_text_says_a_chained_or_parallel_read_does_not_count(self) -> None:
        s = self.routed()
        s.load("pr-description")

        text = reason(s.call("Bash", {"command": "gh pr create --title x --body y"}))
        self.assertIn("chained", text)
        self.assertIn("parallel", text)

    def test_a_turn_that_changed_nothing_is_told_a_diff_is_the_way(self) -> None:
        s = self.routed()
        s.load("commit-message")

        text = reason(s.call("Bash", commit("Add CSV export")))
        self.assertIn("changed no file", text)
        self.assertNotIn("Read a file you changed", text)

    def test_mcp_commit_and_pr_tools_pass_when_the_turn_changed_no_project_file(self) -> None:
        # Outside a git checkout no diff can run and no changed file exists to Read, so a strict hold
        # with no exit would be a dead end; the change is in the tool's own input.
        for tool, tool_input, skill in (
            ("mcp__github__push_files", {"message": "Add export", "files": []}, "commit-message"),
            ("mcp__github__create_or_update_file", {"message": "Add export", "path": "a.py"},
             "commit-message"),
            ("mcp__github__create_pull_request", {"title": "x"}, "pr-description"),
        ):
            with self.subTest(tool=tool):
                s = self.fresh()
                s.prompt("Push it.")
                s.load(ROUTER)
                s.say("goated-route: direct")
                s.load(skill)
                self.assertEqual(decision(s.call(tool, tool_input)), "pass")
                s.say("goated-skip: software-design-principles: one mechanical constant change")
                s.call("Write", write("src/export.py"))
                self.assertEqual(decision(s.call(tool, tool_input)), "deny")
                s.read("src/export.py")
                self.assertEqual(decision(s.call(tool, tool_input)), "pass")

    def test_a_read_before_a_later_non_code_change_does_not_clear_a_commit(self) -> None:
        s = self.routed()
        s.load("commit-message")
        s.read("README.md")
        s.call("Edit", {"file_path": "README.md", "old_string": "a", "new_string": "b"})

        self.assertEqual(decision(s.call("Bash", commit("Update the readme"))), "deny")
        s.read("README.md")
        self.assertEqual(decision(s.call("Bash", commit("Update the readme"))), "pass")

    def test_the_security_item_counts_from_the_last_sensitive_change(self) -> None:
        s = self.routed()
        s.load("code-security-review")
        s.call("Edit", {"file_path": "config/secrets.yaml", "old_string": "A=1", "new_string": "A=2"})
        s.read("config/secrets.yaml")
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        s.call("Write", write("src/util.py"))
        s.run("pytest -q")
        s.say("goated-skip: doc-sync: internal constant with no documented behavior")

        self.assertEqual(stop(s), {})

    def test_a_subagents_changes_count_for_the_commit_hold(self) -> None:
        s = self.routed()
        s.load("commit-message")
        s.run(DIFF)
        s.brief_with_handoff()
        agent = s.subagent("c1")
        agent.prompt("Implement it.", hook=False)
        agent.call("Edit", {"file_path": "src/app.py", "old_string": "a", "new_string": "b"},
                   agent_id="c1", agent_type="general-purpose")
        self.assertEqual(decision(s.spawn("c1", BRIEF)), "pass")

        self.assertEqual(decision(s.call("Bash", commit("Add export"))), "deny")
        s.read("src/app.py")
        self.assertEqual(decision(s.call("Bash", commit("Add export"))), "pass")


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


class ReviewRegressionTests(AdapterTestCase):
    """Regression tests for the independent review of ticket 031."""

    LONG = "A" * 80

    def loaded(self, prompt: str = "Do the task.") -> Session:
        s = self.routed(prompt=prompt)
        s.load("commit-message")
        s.run("git diff")
        return s

    def held_line(self, tool: str, command: str, setup=None) -> str:
        s = self.fresh()
        s.prompt("Do the task.")
        s.load(ROUTER)
        s.say("goated-route: direct")
        if setup:
            setup(s)
        return hold_line(s.call(tool, {"command": command}))

    # Item 1: the message is read from the commit's own segment.
    def test_a_chained_commit_message_is_checked_and_matched(self) -> None:
        for command in (
            f'python -m pytest -q && git commit -m "{self.LONG}"',
            f'grep -m1 x a; git commit -m "{self.LONG}"',
        ):
            with self.subTest(command=command):
                line = self.held_line("Bash", command, lambda s: s.load("commit-message"))
                self.assertEqual(line, "goated-hold: commit | strict")

        s = self.session
        s.prompt('Commit with the message "Fix export rounding".')
        s.load(ROUTER)
        s.say("goated-route: direct")
        command = 'python -m pytest -q && git commit -m "Fix export rounding"'
        self.assertEqual(decision(s.call("Bash", {"command": command})), "pass")

    # Item 2: combined short flags carry the message.
    def test_combined_short_flags_carry_the_message(self) -> None:
        for flags in ("-am", "-sm"):
            with self.subTest(flags=flags):
                command = f'git commit {flags} "{self.LONG}"'
                line = self.held_line("Bash", command, lambda s: s.load("commit-message"))
                self.assertEqual(line, "goated-hold: commit | strict")

        s = self.session
        s.prompt('Commit with the message "Fix export rounding".')
        s.load(ROUTER)
        s.say("goated-route: direct")
        command = 'git commit -am "Fix export rounding"'
        self.assertEqual(decision(s.call("Bash", {"command": command})), "pass")

    # Item 3: dependency manifests ending in .txt are sensitive, by edit or shell.
    def test_requirements_files_meet_the_security_hold(self) -> None:
        s = self.routed()
        for path in ("requirements.txt", "requirements-dev.txt"):
            with self.subTest(path=path):
                edit = {"file_path": path, "old_string": "a", "new_string": "b"}
                self.assertEqual(hold_line(s.call("Edit", edit)), "goated-hold: security | justified-skip")
        held = s.call("Bash", {"command": "echo requests >> requirements.txt"})
        self.assertEqual(hold_line(held), "goated-hold: security | justified-skip")

    # Item 4: only write targets inside the project count as changed code.
    def test_only_written_project_code_counts_for_closeout(self) -> None:
        for command in ("python scripts/report.py > report.txt", "cp src/app.py /tmp/app_backup.py"):
            with self.subTest(command=command):
                s = self.fresh()
                s.prompt("Report.")
                s.load(ROUTER)
                s.say("goated-route: direct")
                s.run(command)
                self.assertEqual(stop(s), {})

    def test_a_check_that_tees_its_log_is_proof_not_a_change(self) -> None:
        s = self.changed_app()
        s.run("python -m pytest tests/test_app.py 2>&1 | tee test.log")

        self.assertEqual(stop(s), {})

    def test_an_edit_outside_the_project_is_not_a_change(self) -> None:
        s = self.routed()
        s.say("goated-skip: software-design-principles: throwaway scratch script only")
        s.call("Write", write("/tmp/scratch/probe.py"))

        self.assertEqual(stop(s), {})

    def changed_app(self) -> Session:
        s = self.routed()
        s.call("Edit", {"file_path": str(s.project / "src" / "app.py"),
                        "old_string": "a", "new_string": "b"})
        s.load("doc-sync")
        s.run("git diff")
        return s

    # Item 5: proof is a check command, not any command naming "test" or "build".
    def test_commands_that_only_mention_checks_are_not_proof(self) -> None:
        for command in ("rm -rf build", "uv sync --extra test", "mkdir tests"):
            with self.subTest(command=command):
                s = self.fresh()
                s.prompt("Bump it.")
                s.load(ROUTER)
                s.say("goated-route: direct")
                s.call("Edit", {"file_path": "src/app.py", "old_string": "a", "new_string": "b"})
                s.load("doc-sync")
                s.run(command)
                self.assertIn("Proof", stop(s).get("reason", ""))

    # Item 6: common spellings of commit and PR commands are still held.
    def test_common_command_spellings_meet_the_strict_holds(self) -> None:
        commits = (
            ("Bash", 'git \\\n  commit -m "Add export"'),
            ("PowerShell", 'git `\n  commit -m "Add export"'),
            ("Bash", '"git" commit -m "Add export"'),
            ("PowerShell", '& "C:\\Program Files\\Git\\cmd\\git.exe" commit -m "Add export"'),
            ("Bash", 'timeout 60 git commit -m "Add export"'),
            ("Bash", 'nice git commit -m "Add export"'),
            ("PowerShell", 'cmd /c git commit -m "Add export"'),
            ("Bash", 'sudo -u bob git commit -m "Add export"'),
        )
        for tool, command in commits:
            with self.subTest(command=command):
                self.assertEqual(self.held_line(tool, command), "goated-hold: commit | strict")
        for command in ("gh pr new --fill", "gh \\\n  pr create --fill", "gh -R o/r pr create"):
            with self.subTest(command=command):
                self.assertEqual(
                    self.held_line("Bash", command), "goated-hold: pull-request | strict"
                )

    def test_a_continued_shell_write_meets_the_route_line_hold(self) -> None:
        s = self.session
        s.prompt("Apply it.")
        s.load(ROUTER)

        held = s.call("Bash", {"command": "git \\\n  apply fix.patch"})
        self.assertEqual(hold_line(held), "goated-hold: route-line | strict")

    # Item 7: more write commands.
    def test_more_write_commands_meet_the_route_line_hold(self) -> None:
        for tool, command in (
            ("PowerShell", "'x' | sc notes.txt"),
            ("PowerShell", "ac log.txt 'line'"),
            ("PowerShell", "clc log.txt"),
            ("PowerShell", "Get-Process | Export-Csv procs.csv"),
            ("Bash", "curl -o src/vendor.py https://example.invalid/x.py"),
            ("Bash", "curl -sSLo src/vendor.py https://example.invalid/x.py"),
            ("Bash", "wget https://example.invalid/x.tar.gz"),
            ("Bash", "patch -p1 < fix.patch"),
            ("Bash", "git checkout HEAD~1 src/app.py"),
        ):
            with self.subTest(command=command):
                s = self.fresh()
                s.prompt("Do it.")
                s.load(ROUTER)
                held = s.call(tool, {"command": command})
                self.assertEqual(hold_line(held), "goated-hold: route-line | strict")

    # Item 8: comparisons, comments, and mentions are not writes or actions.
    def test_comparisons_comments_and_mentions_stay_free(self) -> None:
        for command in (
            '[[ "$a" > "$b" ]] && echo yes',
            "echo $((2 > 1))",
            "ls # list > files",
            "echo gh pr create",
            "git commit --dry-run",
            "curl -s https://example.invalid/x | head",
        ):
            with self.subTest(command=command):
                s = self.fresh()
                s.prompt("Look.")
                s.load(ROUTER)
                self.assertEqual(decision(s.call("Bash", {"command": command})), "pass")

    # Item 9: sensitive words must stand alone in the path.
    def test_security_words_must_stand_alone_in_the_path(self) -> None:
        s = self.routed()
        for path, held in (
            ("src/tokenizer.py", False),
            ("src/author.py", False),
            ("src/api_token.py", True),
            ("src/userAuth.ts", True),
            ("src/auth/views.py", True),
        ):
            with self.subTest(path=path):
                edit = {"file_path": path, "old_string": "a", "new_string": "b"}
                self.assertEqual(decision(s.call("Edit", edit)) == "deny", held)

    # Item 10: `-F -` reads the heredoc fed to the commit itself.
    def test_the_commit_reads_its_own_heredoc(self) -> None:
        s = self.loaded()
        command = (
            "cat <<'EOF' > notes.md\nshort\nEOF\ngit commit -F - <<'EOF'\n"
            + "B" * 90 + "\nEOF"
        )
        self.assertEqual(hold_line(s.call("Bash", {"command": command})), "goated-hold: commit | strict")

    def test_a_commit_body_ending_lines_in_backticks_is_read_whole(self) -> None:
        s = self.loaded()
        command = (
            'git commit -m "$(cat <<\'EOF\'\nUpdate `gates.py`\n\nExplain `x`\nand `y`\nEOF\n)"'
        )
        self.assertEqual(decision(s.call("Bash", {"command": command})), "pass")

    # Item 11: code a subagent changed counts toward the parent's closeout.
    def test_subagent_code_changes_need_the_parents_closeout(self) -> None:
        s = self.routed()
        s.brief_with_handoff()
        agent = s.subagent("b1")
        agent.prompt("Implement it.", hook=False)
        agent.call("Edit", {"file_path": "src/app.py", "old_string": "a", "new_string": "b"},
                   agent_id="b1", agent_type="general-purpose")
        self.assertEqual(decision(s.spawn("b1", BRIEF)), "pass")

        held = stop(s)
        self.assertIn("Proof", held["reason"])
        self.assertIn("doc-sync", held["reason"])
        s.run("pytest -q")
        s.load("doc-sync")
        s.run("git diff")
        self.assertEqual(stop(s), {})

    def test_a_subagent_that_ran_its_own_check_proved_its_change(self) -> None:
        s = self.routed()
        s.brief_with_handoff()
        agent = s.subagent("b2")
        agent.prompt("Implement it.", hook=False)
        agent.call("Edit", {"file_path": "src/app.py", "old_string": "a", "new_string": "b"},
                   agent_id="b2", agent_type="general-purpose")
        agent.run("pytest -q")
        s.spawn("b2", BRIEF)

        held = stop(s)
        self.assertNotIn("Proof", held["reason"])
        self.assertIn("doc-sync", held["reason"])

    # Item 12: the older spawn tool name and MCP commit tools.
    def test_the_task_spawn_tool_is_held(self) -> None:
        s = self.routed()

        self.assertEqual(hold_line(s.call("Task", {"prompt": BRIEF})), "goated-hold: spawn | strict")
        s.brief_with_handoff()
        self.assertEqual(decision(s.call("Task", {"prompt": BRIEF})), "pass")

    def test_mcp_tools_that_commit_meet_the_commit_hold(self) -> None:
        s = self.routed()
        tool = "mcp__github__push_files"

        held = s.call(tool, {"message": "Add export", "files": []})
        self.assertEqual(hold_line(held), "goated-hold: commit | strict")
        s.load("commit-message")
        s.run("git diff")
        self.assertEqual(decision(s.call(tool, {"message": self.LONG, "files": []})), "deny")
        self.assertEqual(decision(s.call(tool, {"message": "Add export", "files": []})), "pass")


class InteractiveRecordingTests(AdapterTestCase):
    """In an interactive session Claude Code records the assistant message
    holding a call only after PreToolUse returns, so the hook judges the call
    from its input alone. Headless runs often record it first; both orders
    must give the same answers."""

    def gate_lines(self, record_before_hook: bool) -> list[str]:
        s = self.fresh()
        s.record_before_hook = record_before_hook
        s.prompt("Do the task.")
        lines = [hold_line(s.call("Bash"))]
        s.load(ROUTER)
        lines.append(hold_line(s.call("Edit")))
        s.say("goated-route: standard | requires: tdd")
        lines.append(hold_line(s.call("Edit")))
        s.load("tdd")
        lines.append(hold_line(s.call("Bash", commit("Add export"))))
        lines.append(hold_line(s.call("Bash", {"command": "gh pr create --fill"})))
        lines.append(hold_line(s.call("Agent", {"prompt": BRIEF})))
        lines.append(hold_line(s.call("Write", write("src/export.py"))))
        lines.append(hold_line(s.call("Edit", {"file_path": ".env", "new_string": "x"})))
        s.say("goated-skip: software-design-principles: one mechanical constant change")
        self.assertEqual(decision(s.call("Write", write("src/export.py"))), "pass")
        lines.append(closeout_line(stop(s)))
        return lines

    def test_every_gate_holds_a_call_the_transcript_does_not_show_yet(self) -> None:
        lines = self.gate_lines(record_before_hook=False)

        self.assertEqual(lines, [
            "goated-hold: router-first | strict",
            "goated-hold: route-line | strict",
            "goated-hold: pipeline | strict",
            "goated-hold: commit | strict",
            "goated-hold: pull-request | strict",
            "goated-hold: spawn | strict",
            "goated-hold: design | justified-skip",
            "goated-hold: security | justified-skip",
            "goated-hold: closeout | justified-skip",
        ])
        self.assertEqual(lines, self.gate_lines(record_before_hook=True))

    def test_parallel_calls_recorded_after_both_hooks_are_each_judged(self) -> None:
        s = self.routed()

        commit_out, design_out = s.parallel([
            ("Bash", commit("Add export")),
            ("Write", write("src/export.py")),
        ])
        self.assertEqual(hold_line(commit_out), "goated-hold: commit | strict")
        self.assertEqual(hold_line(design_out), "goated-hold: design | justified-skip")
        for output in (commit_out, design_out):
            self.assertNotIn("systemMessage", output)

    def test_a_sibling_load_in_the_same_message_does_not_count(self) -> None:
        s = self.routed()

        _, held = s.parallel([
            ("Skill", {"skill": "commit-message"}),
            ("Bash", commit("Add export")),
        ])
        self.assertEqual(hold_line(held), "goated-hold: commit | strict")

    def test_a_subagent_call_not_yet_recorded_is_judged(self) -> None:
        self.session.prompt("Delegate it.")
        agent = self.session.subagent("c1")
        agent.prompt("Implement it.", hook=False)

        held = agent.call("Bash", commit("Add export"), agent_id="c1", agent_type="general-purpose")
        self.assertEqual(hold_line(held), "goated-hold: commit | strict")

    def test_a_stop_without_its_prompt_recorded_fails_open(self) -> None:
        s = self.routed()
        s.call("Edit", {"file_path": "src/app.py", "old_string": "a", "new_string": "b"})

        output = parse(s.hook("Stop", stop_hook_active=False, prompt_id="prompt-not-recorded"))
        self.assertNotIn("decision", output)
        self.assertIn("allowed without checks", output.get("systemMessage", ""))


class SkillSkipPhraseTests(AdapterTestCase):
    """`skip <name>` is an override only when `<name>` is a skill."""

    def test_skip_followed_by_an_ordinary_word_is_not_an_override(self) -> None:
        from goated_adapter.overrides import parse_overrides

        for prompt in (
            "If it does not apply, decline it with a goated-skip line instead of loading the skill.",
            "Skip the first two lines of the log.",
            "skip line 3",
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual(parse_overrides(prompt)["skills"], [])

    def test_a_prompt_naming_no_skill_records_no_override(self) -> None:
        s = self.session
        notice = s.prompt("Decline it with a goated-skip line instead of loading the skill.")

        self.assertEqual(notice, "")

    def test_installed_skills_decide_which_names_count(self) -> None:
        skill = self.session.config.home / ".claude" / "skills" / "my-review"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("# My Review\n", encoding="utf-8")
        s = self.session

        self.assertIn("Skip my-review", s.prompt("Skip my-review this time."))
        # With skills found, a GOATED name that is not installed does not count.
        self.assertEqual(s.prompt("Skip tdd this time."), "")

    def test_the_fallback_list_matches_the_registry(self) -> None:
        import yaml
        from claude_code_adapter_support import REPO_ROOT
        from goated_adapter.overrides import GOATED_SKILLS

        registry = yaml.safe_load(
            (REPO_ROOT / "stack" / "goated-stack.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(GOATED_SKILLS, {skill["name"] for skill in registry["skills"]})
