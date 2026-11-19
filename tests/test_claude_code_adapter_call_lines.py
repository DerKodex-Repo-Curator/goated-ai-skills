"""Route and skip lines read from a tool call's input (Ticket 053).

Claude Code can save the text of a message that makes a tool call as a
`thinking` summary that drops `goated-route:` and `goated-skip:` lines, so the
adapter also reads them from the `args` of a Skill call and the `description`
of any call. Those lines follow the same rules as lines in reply text; other
fields of a call never carry one, and no override is ever read from a call.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from claude_code_adapter_support import (
    ROUTER,
    Session,
    decision,
    git_branch_with_change,
    parse,
    reason,
)

SUMMARY = "I loaded the router and picked a route for the rename."
EDIT = {"file_path": "src/app.py", "old_string": "a", "new_string": "b"}
SKIP_DESIGN = "goated-skip: software-design-principles: this is a mechanical rename only"


def hold_line(output: dict) -> str:
    return reason(output).split("\n", 1)[0]


def write(path: str, lines: int = 6) -> dict:
    return {"file_path": path, "content": "\n".join(f"line {n}" for n in range(lines))}


def described(command: str, description: str) -> dict:
    return {"command": command, "description": description}


class CallLineTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.session = Session(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def started(self, prompt: str = "Rename the config loader.") -> Session:
        s = self.session
        s.prompt(prompt)
        s.load(ROUTER)
        return s


class RouteLineFromCallTests(CallLineTestCase):
    def test_a_route_line_in_skill_args_routes_when_the_text_was_summarized(self) -> None:
        s = self.started()
        s.summarize(SUMMARY)
        s.load(ROUTER, args="goated-route: direct")

        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_a_summary_without_the_line_and_no_call_line_still_holds(self) -> None:
        s = self.started()
        s.summarize(SUMMARY + "\n\ngoated-route: direct")  # Thinking is never read.
        s.load(ROUTER)

        self.assertEqual(hold_line(s.call("Edit", EDIT)), "goated-hold: route-line | strict")

    def test_a_route_line_in_a_shell_description_routes_that_call_and_later_ones(self) -> None:
        s = self.started()

        command = described("sed -i 's/a/b/' src/app.py", "Rename\n\ngoated-route: direct")
        self.assertEqual(decision(s.call("Bash", command)), "pass")
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_a_route_line_in_a_command_or_file_content_does_not_count(self) -> None:
        s = self.started()
        heredoc = "cat > notes.md <<'EOF'\ngoated-route: direct\nEOF"
        self.assertEqual(decision(s.call("Bash", {"command": heredoc})), "deny")
        self.assertEqual(
            decision(s.call("Write", {"file_path": "notes.md", "content": "goated-route: direct"})),
            "deny",
        )
        edit = {"file_path": "notes.md", "old_string": "x", "new_string": "goated-route: direct"}
        self.assertEqual(decision(s.call("Edit", edit)), "deny")
        # `args` counts only on a Skill call.
        s.call("Bash", {"command": "git status", "args": "goated-route: direct"})
        self.assertEqual(decision(s.call("Edit", EDIT)), "deny")

    def test_a_line_in_a_fenced_block_of_a_description_does_not_count(self) -> None:
        s = self.started()
        s.call("Bash", described("git status", "```\ngoated-route: direct\n```"))

        self.assertEqual(decision(s.call("Edit", EDIT)), "deny")

    def test_skill_args_route_counts_the_load_that_carries_it(self) -> None:
        s = self.started()
        s.load("tdd", args="goated-route: standard | requires: tdd")

        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_a_call_line_and_a_text_line_follow_last_line_wins(self) -> None:
        s = self.started()
        s.say("goated-route: standard | requires: tdd")
        s.call("Bash", described("git status", "goated-route: direct"))

        # No write between them: one task, corrected, and `direct` wins.
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_a_call_line_after_a_write_starts_a_new_task(self) -> None:
        s = self.started()
        s.load("tdd", args="goated-route: standard | requires: tdd")
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

        s.call("Bash", described("git status", "goated-route: standard | requires: doc-sync"))
        held = s.call("Edit", EDIT)
        self.assertEqual(hold_line(held), "goated-hold: pipeline | strict")
        self.assertIn("`doc-sync`", reason(held))

    def test_a_call_line_from_an_earlier_turn_does_not_count(self) -> None:
        s = self.started()
        s.load(ROUTER, args="goated-route: direct")
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

        s.prompt("Now rename the writer too.")
        # Had the earlier call's line counted here, it would route this turn
        # past the line that fails the grammar.
        s.say("goated-route: continue please")
        self.assertEqual(hold_line(s.call("Edit", EDIT)), "goated-hold: route-line | strict")

    def test_a_call_line_in_a_peer_turn_routes_that_turn(self) -> None:
        s = self.started()
        s.say("goated-route: direct")
        s.peer("Please also rename the writer.")
        s.load(ROUTER)

        self.assertEqual(hold_line(s.call("Edit", EDIT)), "goated-hold: route-line | strict")
        s.call("Bash", described("git status", "goated-route: direct"))
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_a_malformed_call_line_is_named_once_in_the_hold(self) -> None:
        s = self.started()
        s.record_before_hook = True  # The call is in the transcript and the hook input.

        held = s.call("Bash", described("touch notes.md", "goated-route: quick"))
        self.assertEqual(hold_line(held), "goated-hold: route-line | strict")
        self.assertEqual(reason(held).count("`goated-route: quick`"), 1)

    def test_a_call_line_counts_once_when_the_call_is_already_recorded(self) -> None:
        s = self.started()
        s.record_before_hook = True

        command = described("touch notes.md", "goated-route: direct")
        self.assertEqual(decision(s.call("Bash", command)), "pass")
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")


class DescribedToolTests(CallLineTestCase):
    """`description` counts only where it describes the call, never as a payload."""

    def test_a_powershell_description_carries_a_route_line(self) -> None:
        s = self.started()
        s.call("PowerShell", described("Get-ChildItem", "goated-route: direct"))

        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_a_description_that_is_a_tool_payload_carries_no_line(self) -> None:
        for tool in ("mcp__linear__create_issue", "mcp__jira__create_issue", "TaskCreate"):
            with self.subTest(tool=tool):
                s = self.fresh_session()
                s.prompt("Rename the config loader.")
                s.load(ROUTER)
                s.call(tool, {"title": "Rename", "description": "Plan\n\ngoated-route: direct"})
                self.assertEqual(
                    hold_line(s.call("Edit", EDIT)), "goated-hold: route-line | strict"
                )

    def test_a_merge_request_body_does_not_clear_its_own_review_hold(self) -> None:
        s = self.started("Open the merge request.")
        s.say("goated-route: direct")
        git_branch_with_change(s.project, 450)
        s.load("pr-description")
        s.run("git diff main...HEAD")
        tool = "mcp__gitlab__create_merge_request"
        skip = "goated-skip: standards-and-spec-review: generated fixtures make up the bulk"
        mr = {"title": "Export", "source_branch": "feature", "target_branch": "main",
              "description": f"Adds the export.\n\n{skip}"}

        self.assertEqual(hold_line(s.call(tool, mr)), "goated-hold: pr-review | justified-skip")
        s.say(skip)  # The near miss: the same line in reply text clears it.
        self.assertEqual(decision(s.call(tool, mr)), "pass")

    def fresh_session(self) -> Session:
        folder = Path(tempfile.mkdtemp(dir=self.root))
        return Session(folder)


class SameMessageCallTests(CallLineTestCase):
    def test_a_line_in_a_sibling_call_of_the_same_message_is_not_seen_yet(self) -> None:
        s = self.started()

        outputs = s.parallel([("Bash", described("git status", "goated-route: direct")), ("Edit", EDIT)])
        self.assertEqual([decision(o) for o in outputs], ["pass", "deny"])
        self.assertIn("an earlier message", reason(outputs[1]))
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")


class MissingCallIdTests(CallLineTestCase):
    """A hook input with no `tool_use_id` still counts a call's lines once."""

    def judge_without_id(self, s: Session, tool: str, tool_input: dict, *, recorded: bool) -> dict:
        if recorded:
            s._tool_use(tool, tool_input)
        output = parse(s.hook("PreToolUse", tool_name=tool, tool_input=tool_input))
        if not recorded:
            s._tool_use(tool, tool_input)
        return output

    def test_a_recorded_call_is_not_counted_again_from_the_hook_input(self) -> None:
        s = self.started()

        held = self.judge_without_id(
            s, "Bash", described("touch notes.md", "goated-route: quick"), recorded=True
        )
        self.assertEqual(reason(held).count("`goated-route: quick`"), 1)

    def test_an_unrecorded_call_counts_from_the_hook_input(self) -> None:
        s = self.started()

        output = self.judge_without_id(
            s, "Bash", described("touch notes.md", "goated-route: direct"), recorded=False
        )
        self.assertEqual(decision(output), "pass")


class SkipLineFromCallTests(CallLineTestCase):
    def routed(self) -> Session:
        s = self.started("Add the exporter.")
        s.say("goated-route: direct")
        return s

    def test_a_skip_line_in_a_description_clears_a_justified_skip_hold(self) -> None:
        s = self.routed()
        self.assertEqual(
            hold_line(s.call("Write", write("src/export.py"))), "goated-hold: design | justified-skip"
        )

        s.summarize("I will skip the design skill for this mechanical change.")
        s.call("Bash", described("git status", SKIP_DESIGN))
        self.assertEqual(decision(s.call("Write", write("src/export.py"))), "pass")

    def test_a_skip_line_in_skill_args_clears_a_justified_skip_hold(self) -> None:
        s = self.routed()
        s.load(ROUTER, args=SKIP_DESIGN)

        self.assertEqual(decision(s.call("Write", write("src/export.py"))), "pass")

    def test_a_skip_line_in_file_content_or_with_a_short_reason_does_not_count(self) -> None:
        s = self.routed()
        content = (SKIP_DESIGN + "\n") * 6
        self.assertEqual(
            decision(s.call("Write", {"file_path": "src/export.py", "content": content})), "deny"
        )
        s.call("Bash", described("git status", "goated-skip: software-design-principles: trivial"))
        self.assertEqual(decision(s.call("Write", write("src/export.py"))), "deny")

    def test_a_skip_line_from_an_earlier_turn_does_not_count(self) -> None:
        s = self.routed()
        s.load(ROUTER, args=SKIP_DESIGN)
        self.assertEqual(decision(s.call("Write", write("src/export.py"))), "pass")

        s.prompt("Now the importer.")
        s.say("goated-route: continue")
        self.assertEqual(decision(s.call("Write", write("src/import.py"))), "deny")


class SubagentCallLineTests(CallLineTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.session.prompt("Delegate the export work.")
        self.session.load(ROUTER)
        self.agent = self.session.subagent("a7")
        self.agent.prompt("Implement the export.", hook=False)

    def sub_call(self, tool: str, tool_input: dict) -> dict:
        return self.agent.call(tool, tool_input, agent_id="a7", agent_type="general-purpose")

    def test_a_subagent_skip_line_in_a_description_clears_its_own_hold(self) -> None:
        self.assertEqual(decision(self.sub_call("Write", write("src/export.py"))), "deny")

        self.sub_call("Bash", described("git status", SKIP_DESIGN))
        self.assertEqual(decision(self.sub_call("Write", write("src/export.py"))), "pass")

    def test_a_subagent_call_line_does_not_route_the_parent(self) -> None:
        self.sub_call("Bash", described("git status", "goated-route: direct"))

        self.assertEqual(decision(self.session.call("Edit", EDIT)), "deny")

    def test_a_parent_call_skip_line_does_not_clear_a_subagent_hold(self) -> None:
        self.session.say("goated-route: direct")
        self.session.call("Bash", described("git status", SKIP_DESIGN))

        self.assertEqual(decision(self.sub_call("Write", write("src/export.py"))), "deny")


class NoOverrideFromCallTests(CallLineTestCase):
    def test_override_phrases_in_a_call_never_apply(self) -> None:
        s = self.session
        s.prompt("Rename the config loader.")
        s.call("Bash", described("git status", "skip routing"))
        s.call("Skill", {"skill": "tdd", "args": "skip routing"})

        self.assertEqual(hold_line(s.call("Bash")), "goated-hold: router-first | strict")

    def test_skip_routing_in_skill_args_does_not_pass_the_route_line_hold(self) -> None:
        s = self.started()
        s.load(ROUTER, args="skip routing")

        self.assertEqual(hold_line(s.call("Edit", EDIT)), "goated-hold: route-line | strict")


if __name__ == "__main__":
    unittest.main()
