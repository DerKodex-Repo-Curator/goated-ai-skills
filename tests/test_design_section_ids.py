"""Prove that every cited software-design section id points at real text.

Skills cite sections of `software-design-principles` as `file#id`, for example
`process.md#design-twice`, instead of copying its rules. A renamed, moved, or
removed id would leave a dead pointer that nothing else notices, so these tests
fail instead.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "software-design-principles"
SKILL_DIR = REPO_ROOT / "skills" / "engineering" / SKILL_NAME

# A section is declared by this comment on its own line in a reference file.
ID_DECLARATION = re.compile(r"^<!-- id: #([a-z-]+) -->$", re.MULTILINE)
# A citation is an id in backticks, named with its reference file, such as
# `process.md#design-twice`. Bare ids appear only where the file is already
# known: Section Index rows and each reference's own contents list.
ID_CITATION = re.compile(r"`([a-z-]+\.md)?#([a-z-]+)`")
# One row of the Section Index table: a linked reference file, then its ids.
INDEX_ROW = re.compile(r"^\| \[[^\]]+\]\((references/[a-z-]+\.md)\) \| (.+) \|$")


def declared_ids_by_file() -> dict[str, set[str]]:
    """Map each reference file's path, relative to the skill, to its ids."""

    declared: dict[str, set[str]] = {}
    for reference in sorted((SKILL_DIR / "references").glob("*.md")):
        text = reference.read_text(encoding="utf-8")
        declared[f"references/{reference.name}"] = set(
            ID_DECLARATION.findall(text)
        )
    return declared


class DesignSectionIdTests(unittest.TestCase):
    def setUp(self) -> None:
        self.declared_by_file = declared_ids_by_file()
        self.all_declared = set().union(*self.declared_by_file.values())

    def assert_citations_point_at_files(
        self, text: str, where: str, *, allow_bare: bool = False
    ) -> int:
        """Fail on an id its named file does not declare, or on a bare id.

        `allow_bare` admits bare ids, which must still be declared somewhere;
        reference files list their own sections that way. Returns how many
        citations the text holds.
        """

        citations = ID_CITATION.findall(text)
        for file_name, section_id in citations:
            if not file_name and allow_bare:
                self.assertIn(
                    section_id,
                    self.all_declared,
                    f"{where} cites undeclared #{section_id}",
                )
                continue
            self.assertTrue(
                file_name, f"{where} cites #{section_id} without its file"
            )
            self.assertIn(
                section_id,
                self.declared_by_file.get(f"references/{file_name}", set()),
                f"{where} cites {file_name}#{section_id}, which that file "
                "does not declare",
            )
        return len(citations)

    def test_each_id_is_declared_once(self) -> None:
        seen: dict[str, str] = {}
        for file_name, ids in self.declared_by_file.items():
            text = (SKILL_DIR / file_name).read_text(encoding="utf-8")
            for section_id in ids:
                self.assertEqual(
                    len(re.findall(f"<!-- id: #{section_id} -->", text)),
                    1,
                    f"#{section_id} is declared more than once in {file_name}",
                )
                self.assertNotIn(
                    section_id,
                    seen,
                    f"#{section_id} is declared in two reference files",
                )
                seen[section_id] = file_name

    def test_index_rows_name_the_file_that_holds_each_id(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        rows = [
            match
            for line in skill.splitlines()
            if (match := INDEX_ROW.match(line))
        ]

        # Every reference file has exactly one row in the index.
        self.assertEqual(
            sorted(row.group(1) for row in rows),
            sorted(self.declared_by_file),
        )
        for row in rows:
            file_name = row.group(1)
            for _, section_id in ID_CITATION.findall(row.group(2)):
                self.assertIn(
                    section_id,
                    self.declared_by_file[file_name],
                    f"index lists #{section_id} under {file_name}",
                )

    def test_ids_cited_inside_the_skill_exist_where_named(
        self,
    ) -> None:
        for path in sorted(SKILL_DIR.rglob("*.md")):
            lines = path.read_text(encoding="utf-8").splitlines()
            # Index rows name the file in their first cell, so skip them.
            text = "\n".join(line for line in lines if not INDEX_ROW.match(line))
            self.assert_citations_point_at_files(
                text,
                str(path.relative_to(REPO_ROOT)),
                allow_bare=path.parent.name == "references",
            )

    def test_ids_cited_by_other_skills_name_the_file_that_holds_them(
        self,
    ) -> None:
        sources = [REPO_ROOT / "stack" / "AGENTS.md"]
        sources += [
            path
            for path in sorted((REPO_ROOT / "skills").rglob("*.md"))
            if SKILL_DIR not in path.parents
        ]

        citing_files = 0
        for path in sources:
            for line in path.read_text(encoding="utf-8").splitlines():
                # Only lines that name this skill are pointers into it.
                if SKILL_NAME not in line:
                    continue
                if self.assert_citations_point_at_files(
                    line, str(path.relative_to(REPO_ROOT))
                ):
                    citing_files += 1

        # Guards against the scan silently matching nothing.
        self.assertGreater(citing_files, 0)

    def test_checklist_cited_by_writing_plans_exists(self) -> None:
        plans = (
            REPO_ROOT / "skills" / "engineering" / "writing-plans" / "SKILL.md"
        ).read_text(encoding="utf-8")
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn('checklist "Before you start"', plans)
        self.assertIn("**Before you start**", skill)


if __name__ == "__main__":
    unittest.main()
