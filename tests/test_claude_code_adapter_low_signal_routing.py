"""Two routing holds that said little about the work (Ticket 087).

- Orientation by reads (spec R3): a session routed by its brief, on a
  `standard` or `full` route, orients by loading the orientation skill or by
  three finished Read calls of distinct files since the session started or
  the last compaction.
- Writes outside the project (spec R4): a write whose every file is
  certainly outside the project passes `router-first`, `route-line` and
  `pipeline`. When in doubt a file is inside, as for the action gates.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from claude_code_adapter_support import ROUTER, Session, decision
from goated_adapter.state import StateStore
from test_claude_code_adapter_briefs import ORIENTATION, BriefTestCase, hold_line, reason

EDIT = {"file_path": "src/app.py", "old_string": "a", "new_string": "b"}
PIPELINE = "goated-hold: pipeline | strict"


class OrientationByReadsTests(BriefTestCase):
    def setUp(self) -> None:
        super().setUp()
        folder = self.session.config.home / ".claude" / "skills" / ORIENTATION
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")

    def full_brief(self) -> Session:
        s = self.brief("goated-route: full | requires: tdd")
        s.load("tdd")
        return s

    def read_files(self, s: Session, *names: str) -> None:
        for name in names:
            s.read(str(self.session.project / name))

    def saved_reads(self) -> list[str]:
        store = StateStore(self.session.config.state_dir)
        return store.load(self.session.session_id)[0].files_read

    def test_three_reads_of_distinct_files_meet_orientation(self) -> None:
        s = self.full_brief()
        # Anywhere: one of the three is outside the project.
        self.read_files(s, "tickets/087.md", "src/app.py")
        s.read(str(self.session.root / "notes.md"))

        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_two_reads_are_held_and_the_hold_names_both_ways(self) -> None:
        s = self.full_brief()
        self.read_files(s, "tickets/087.md", "src/app.py")

        held = s.call("Edit", EDIT)
        self.assertEqual(hold_line(held), PIPELINE)
        self.assertIn(f"loads `{ORIENTATION}`", reason(held))
        self.assertIn("Read calls of three distinct files", reason(held))

    def test_three_reads_of_one_file_are_held(self) -> None:
        s = self.full_brief()
        self.read_files(s, "src/app.py", "src/app.py", "src/app.py")

        self.assertEqual(hold_line(s.call("Edit", EDIT)), PIPELINE)

    def test_a_failed_read_does_not_count(self) -> None:
        s = self.full_brief()
        self.read_files(s, "a.md", "b.md")
        s.read(str(self.session.project / "missing.md"), success=False)

        self.assertEqual(hold_line(s.call("Edit", EDIT)), PIPELINE)

    def test_reads_do_not_meet_the_routes_own_skills(self) -> None:
        s = self.brief("goated-route: full | requires: tdd")
        self.read_files(s, "a.md", "b.md", "c.md")

        held = s.call("Edit", EDIT)
        self.assertEqual(hold_line(held), PIPELINE)
        self.assertIn("`tdd`", reason(held))
        self.assertNotIn(f"`{ORIENTATION}`", reason(held))

    def test_reads_of_an_earlier_turn_count(self) -> None:
        s = self.full_brief()
        self.read_files(s, "a.md", "b.md")
        # A background task's notification opens a new turn and keeps the brief's route.
        s.notify("Agent finished.")
        self.read_files(s, "c.md")

        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_a_subagents_reads_do_not_count(self) -> None:
        s = self.full_brief()
        self.read_files(s, "a.md")
        agent = s.subagent("a1")
        for name in ("b.md", "c.md", "d.md"):
            agent.read(str(self.session.project / name))

        self.assertEqual(hold_line(s.call("Edit", EDIT)), PIPELINE)
        self.read_files(s, "b.md", "c.md")
        self.assertEqual(decision(s.call("Edit", EDIT)), "pass")

    def test_reads_before_a_compaction_do_not_count(self) -> None:
        """A compaction also ends the brief's route, so no hold can show the
        reads it dropped; the saved state does."""

        s = self.full_brief()
        self.read_files(s, "a.md", "b.md", "c.md")
        s.call("Bash", {"command": "ls"})
        self.assertEqual(len(self.saved_reads()), 3)

        s.compact()
        self.assertEqual(self.saved_reads(), [])
        s.load(ROUTER)
        s.call("Bash", {"command": "ls"})
        self.assertEqual(self.saved_reads(), [])


class OutsideWriteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.session = Session(Path(self._tmp.name))
        # Beside the project, in the temporary folder: certainly outside it.
        self.outside = (self.session.root / "scratch").as_posix()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_before_the_router_a_copy_outside_the_project_passes(self) -> None:
        s = self.session
        s.prompt("Tidy it.")

        self.assertEqual(decision(s.run(f'cp src/app.py "{self.outside}/app.py"')), "pass")

    def test_before_the_router_a_copy_into_the_project_is_held(self) -> None:
        s = self.session
        s.prompt("Tidy it.")

        held = s.run(f'cp "{self.outside}/app.py" src/app.py')
        self.assertEqual(hold_line(held), "goated-hold: router-first | strict")

    def test_before_the_router_a_write_whose_folder_cannot_be_read_is_held(self) -> None:
        s = self.session
        s.prompt("Tidy it.")

        held = s.run('cd "$SCRATCH" && cp a.py b.py')
        self.assertEqual(hold_line(held), "goated-hold: router-first | strict")

    def test_a_copy_with_one_file_inside_is_held(self) -> None:
        s = self.session
        s.prompt("Tidy it.")

        held = s.run(f'cp a.py "{self.outside}/a.py" && cp a.py src/b.py')
        self.assertEqual(hold_line(held), "goated-hold: router-first | strict")

    def test_with_no_route_line_a_write_outside_passes_route_line(self) -> None:
        s = self.session
        s.prompt("Tidy it.")
        s.load(ROUTER)

        outside = {"file_path": f"{self.outside}/probe.py", "content": "print(1)\n"}
        self.assertEqual(decision(s.call("Write", outside)), "pass")
        inside = {"file_path": "src/probe.py", "content": "print(1)\n"}
        self.assertEqual(hold_line(s.call("Write", inside)), "goated-hold: route-line | strict")

    def test_a_write_outside_passes_pipeline(self) -> None:
        s = self.session
        s.prompt("Tidy it.")
        s.load(ROUTER)
        s.say("goated-route: standard | requires: tdd")

        outside = {"file_path": f"{self.outside}/probe.md", "content": "x\n"}
        self.assertEqual(decision(s.call("Write", outside)), "pass")
        self.assertEqual(hold_line(s.call("Edit", EDIT)), PIPELINE)

    def test_a_spawn_is_held_as_before(self) -> None:
        s = self.session
        s.prompt("Tidy it.")
        brief = {"prompt": f"Write {self.outside}/probe.md."}
        self.assertEqual(hold_line(s.call("Agent", brief)), "goated-hold: router-first | strict")
        s.load(ROUTER)
        self.assertEqual(hold_line(s.call("Agent", brief)), "goated-hold: route-line | strict")
        s.say("goated-route: standard | requires: tdd")
        self.assertEqual(hold_line(s.call("Agent", brief)), PIPELINE)

    def routed_without_a_line(self) -> Session:
        s = self.session
        s.prompt("Tidy it.")
        s.load(ROUTER)
        return s

    def test_a_write_into_another_checkout_under_temp_is_routed(self) -> None:
        """A worktree under the temp folder is another repo's work, not scratch."""

        worktree = self.session.root / "scratch" / "wt"
        worktree.mkdir(parents=True)
        (worktree / ".git").write_text("gitdir: elsewhere\n", encoding="utf-8")
        s = self.routed_without_a_line()

        inside = {"file_path": (worktree / "src" / "x.py").as_posix(), "content": "x = 1\n"}
        self.assertEqual(hold_line(s.call("Write", inside)), "goated-hold: route-line | strict")
        # The near miss: a plain temp file beside it passes.
        plain = {"file_path": f"{self.outside}/x.py", "content": "x = 1\n"}
        self.assertEqual(decision(s.call("Write", plain)), "pass")

    def test_before_the_router_a_copy_into_another_checkout_is_held(self) -> None:
        sibling = self.session.root / "sibling"
        (sibling / ".git").mkdir(parents=True)
        s = self.session
        s.prompt("Tidy it.")

        held = s.run(f'cp src/app.py "{sibling.as_posix()}/app.py"')
        self.assertEqual(hold_line(held), "goated-hold: router-first | strict")

    def test_a_write_into_the_claude_folder_is_routed(self) -> None:
        s = self.routed_without_a_line()

        for path in ("~/.claude/settings.json", (self.session.config.home / ".claude" / "x.md").as_posix()):
            held = s.call("Write", {"file_path": path, "content": "{}\n"})
            self.assertEqual(hold_line(held), "goated-hold: route-line | strict", path)

    def test_removing_a_folder_that_holds_the_project_is_routed(self) -> None:
        s = self.session
        s.prompt("Tidy it.")

        held = s.run(f'rm -rf "{(self.session.root / "home" / "work").as_posix()}"')
        self.assertEqual(hold_line(held), "goated-hold: router-first | strict")

    def test_a_command_chained_to_an_outside_write_is_held(self) -> None:
        s = self.session
        s.prompt("Tidy it.")
        copy = f'cp a.py "{self.outside}/a.py"'

        for rest in ("./script.sh", "make deploy", "git push origin main", "npm publish",
                     "python tools/migrate.py", "npm install left-pad"):
            held = s.run(f"{copy} && {rest}")
            self.assertEqual(hold_line(held), "goated-hold: router-first | strict", rest)
        # The near miss: a plain read chained to it passes.
        self.assertEqual(decision(s.run(f"{copy} && cat f")), "pass")


if __name__ == "__main__":
    unittest.main()
