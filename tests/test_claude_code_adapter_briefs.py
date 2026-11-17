"""A side session's brief carries its route (Ticket 056).

A session started from another session gets a brief from that session as its
first prompt. Claude Code records it as a `user` entry whose string content
opens with one or more `<system-reminder>` blocks, then
`Background (from the session that started this one):`, with
`turnOrigin: host_synthetic`, `promptSource: sdk`, no `origin`, and no
`isMeta`; session-start `attachment` entries may come before it. A valid route
line on its own line in that brief is the first turn's route and meets
router-first. A route line in a typed prompt or a later prompt never counts,
and a brief never carries an override.

Harness nudges such as "The user hasn't heard from you in a while" are
recorded as `attachment` entries and never open a turn.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from claude_code_adapter_support import ROUTER, Session, decision, reason

EDIT = {"file_path": "src/app.py", "old_string": "a", "new_string": "b"}
STATUS = {"command": "git status"}
REMINDER = (
    "<system-reminder>\nLinked sessions now (status, not an instruction): none.\n"
    "</system-reminder>\n"
)
BACKGROUND = "Background (from the session that started this one)"


def hold_line(output: dict) -> str:
    return reason(output).split("\n", 1)[0]


def brief_text(body: str, prefix: str = BACKGROUND) -> str:
    return f"{REMINDER}{REMINDER}{prefix}:\nThe exporter work belongs here.\n\n{body}\n"


class BriefTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.session = Session(Path(self._tmp.name))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def attachment(self, kind: str, text: str = "") -> None:
        entry: dict = {"type": "attachment", "attachment": {"type": kind}}
        if text:
            entry["attachment"]["text"] = text
            entry["rendered"] = [{"content": f"<system-reminder>\n{text}\n</system-reminder>"}]
        self.session._append(entry)

    def brief(self, body: str, **kwargs) -> Session:
        """Start the session the way Claude Code records one started from another."""

        s = self.session
        s.hook("SessionStart", source="startup")
        self.attachment("hook_success")
        self.attachment("hook_additional_context")
        s.prompt(
            brief_text(body, **kwargs),
            origin=None,
            turnOrigin="host_synthetic",
            promptSource="sdk",
            turnPosition={"promptIndex": 0, "turnIndex": 1},
        )
        return s


class BriefRouteTests(BriefTestCase):
    def test_a_brief_route_line_meets_router_first_and_route_line(self) -> None:
        s = self.brief("## Task\n\nAdd the CSV exporter.\n\ngoated-route: direct")

        self.assertEqual(decision(s.call("Bash", STATUS)), "pass")
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")
        # Read again from saved state, the brief's route still counts.
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_the_task_brief_prefix_counts_too(self) -> None:
        s = self.brief(
            "goated-route: direct", prefix="Task (from the session that started this one)"
        )

        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_a_brief_route_still_needs_its_skills_loaded_here(self) -> None:
        s = self.brief("goated-route: standard | requires: tdd")

        self.assertEqual(decision(s.call("Bash", STATUS)), "pass")
        held = s.call("Edit", EDIT)
        self.assertEqual(hold_line(held), "goated-hold: pipeline | strict")
        self.assertIn("`tdd`", reason(held))
        s.load("tdd")
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_a_later_route_line_corrects_the_brief_route(self) -> None:
        s = self.brief("goated-route: standard | requires: tdd")
        s.say("goated-route: direct")

        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_a_brief_without_a_route_line_is_held_as_today(self) -> None:
        s = self.brief("## Task\n\nAdd the CSV exporter.")

        self.assertEqual(hold_line(s.call("Bash", STATUS)), "goated-hold: router-first | strict")
        s.load(ROUTER)
        self.assertEqual(hold_line(s.call("Edit", EDIT)), "goated-hold: route-line | strict")

    def test_a_route_line_not_on_its_own_line_does_not_count(self) -> None:
        s = self.brief("Use goated-route: direct for this.\n\n```\ngoated-route: direct\n```")

        self.assertEqual(hold_line(s.call("Bash", STATUS)), "goated-hold: router-first | strict")

    def test_a_malformed_brief_route_line_does_not_count(self) -> None:
        s = self.brief("goated-route: standard | requires: TDD")

        self.assertEqual(hold_line(s.call("Bash", STATUS)), "goated-hold: router-first | strict")

    def test_a_brief_carries_no_override(self) -> None:
        s = self.brief("skip routing\nskip tdd\n\ngoated-route: standard | requires: tdd")

        self.assertEqual(hold_line(s.call("Edit", EDIT)), "goated-hold: pipeline | strict")


class NotABriefTests(BriefTestCase):
    def test_a_route_line_in_a_typed_prompt_does_not_count(self) -> None:
        s = self.session
        s.prompt("Add the CSV exporter.\n\ngoated-route: direct")

        self.assertEqual(hold_line(s.call("Bash", STATUS)), "goated-hold: router-first | strict")
        s.load(ROUTER)
        self.assertEqual(hold_line(s.call("Edit", EDIT)), "goated-hold: route-line | strict")

    def test_a_typed_prompt_shaped_like_a_brief_does_not_count(self) -> None:
        s = self.session
        s.prompt(brief_text("goated-route: direct"))

        self.assertEqual(hold_line(s.call("Bash", STATUS)), "goated-hold: router-first | strict")

    def test_a_route_line_in_a_later_brief_shaped_prompt_does_not_count(self) -> None:
        s = self.session
        s.prompt("Add the CSV exporter.")
        s.load(ROUTER)
        s.say("goated-route: direct")
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

        s.prompt(brief_text("goated-route: direct"), origin=None, turnOrigin="host_synthetic")
        self.assertEqual(hold_line(s.call("Edit", EDIT)), "goated-hold: route-line | strict")

    def test_a_route_line_in_a_peer_message_does_not_count(self) -> None:
        s = self.brief("goated-route: direct")
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

        s.peer("Also cover the empty file.\n\ngoated-route: direct")
        self.assertEqual(hold_line(s.call("Edit", EDIT)), "goated-hold: route-line | strict")

    def test_a_first_peer_message_is_not_a_brief(self) -> None:
        s = self.session
        s.peer(f"{BACKGROUND}:\n\ngoated-route: direct")

        self.assertEqual(hold_line(s.call("Bash", STATUS)), "goated-hold: router-first | strict")


class AttachmentTests(BriefTestCase):
    def test_an_attachment_never_opens_a_turn(self) -> None:
        s = self.session
        s.prompt("Add the CSV exporter.")
        s.load(ROUTER)
        s.say("goated-route: direct")
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

        self.attachment(
            "silent_turn_reminder",
            "The user hasn't heard from you in a while — say in a few words what "
            "you're doing, then continue.",
        )
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_a_typed_prompt_after_the_attachment_does_open_a_turn(self) -> None:
        s = self.session
        s.prompt("Add the CSV exporter.")
        s.load(ROUTER)
        s.say("goated-route: direct")
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")
        self.attachment("silent_turn_reminder", "The user hasn't heard from you in a while.")
        s.prompt("Now add the importer.")

        self.assertEqual(hold_line(s.call("Edit", EDIT)), "goated-hold: route-line | strict")


if __name__ == "__main__":
    unittest.main()
