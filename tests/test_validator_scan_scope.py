"""The validator's repo-wide scans cover public files, not agent or editor folders."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.validation.shared import iter_public_text_files
from scripts.validation.skill_packages import scan_docs_schema_drift, scan_public_path_leaks


DRIFT_LINE = "status: draft\n"
# Built at runtime so this file does not trip the repo's own leak scan.
LEAK_LINE = "See " + "/".join(["", "home", "someone", "notes.md"]) + "\n"


class ScanScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.write("docs/guide.md", "# Guide\n")
        self.write(".github/workflows/validate.yml", "name: Validate\n")
        self.write(".out-of-scope/deferred.md", "# Deferred\n")
        # A session worktree is a full second checkout nested inside the repo.
        self.write(".claude/worktrees/x/skills/demo/SKILL.md", "# Demo\n" + DRIFT_LINE)
        self.write(".claude/worktrees/x/docs/old.md", DRIFT_LINE + LEAK_LINE)
        for folder in (".codex", ".cursor", ".vscode", ".idea"):
            self.write(f"{folder}/notes.md", DRIFT_LINE + LEAK_LINE)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, relative: str, text: str) -> None:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def scanned(self) -> set[str]:
        return {
            path.relative_to(self.repo).as_posix()
            for path in iter_public_text_files(self.repo)
        }

    def test_agent_and_editor_folders_are_not_scanned(self) -> None:
        self.assertEqual(
            self.scanned(),
            {"docs/guide.md", ".github/workflows/validate.yml", ".out-of-scope/deferred.md"},
        )

    def test_nested_worktree_files_add_no_drift_or_leak_findings(self) -> None:
        self.assertEqual(scan_docs_schema_drift(self.repo, set()), [])
        self.assertEqual(scan_public_path_leaks(self.repo), [])

    def test_the_same_files_outside_those_folders_are_reported(self) -> None:
        self.write("docs/old.md", DRIFT_LINE + LEAK_LINE)

        self.assertEqual(len(scan_docs_schema_drift(self.repo, set())), 1)
        self.assertEqual(len(scan_public_path_leaks(self.repo)), 1)


if __name__ == "__main__":
    unittest.main()
