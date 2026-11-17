"""Behavior tests for the validator's opt-in adapter boundary checks."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.validate_skills import validate_adapter_boundary, validate_registry_reader


REPO_ROOT = Path(__file__).resolve().parents[1]


class AdapterBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        package = self.repo / "adapters" / "example" / "example_adapter"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text(
            "from __future__ import annotations\nimport json\nfrom . import rules\n",
            encoding="utf-8",
        )
        (package / "rules.py").write_text("import re\n", encoding="utf-8")
        (self.repo / "adapters" / "example" / "hook.py").write_text(
            "import sys\nfrom example_adapter import rules\n", encoding="utf-8"
        )
        skill = self.repo / "skills" / "engineering" / "demo"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("# Demo\n\nPortable text.\n", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def messages(self) -> list[str]:
        return [finding.format() for finding in validate_adapter_boundary(self.repo)]

    def test_standard_library_adapter_with_independent_skills_passes(self) -> None:
        self.assertEqual(self.messages(), [])

    def test_the_real_repository_passes(self) -> None:
        self.assertEqual(
            [finding.format() for finding in validate_adapter_boundary(REPO_ROOT)], []
        )

    def test_a_third_party_import_in_an_adapter_is_an_error(self) -> None:
        rules = self.repo / "adapters" / "example" / "example_adapter" / "rules.py"
        rules.write_text("import re\nimport yaml\n", encoding="utf-8")

        messages = self.messages()
        self.assertEqual(len(messages), 1)
        self.assertIn("rules.py", messages[0])
        self.assertIn("yaml", messages[0])

    def test_a_skill_that_references_an_adapter_is_an_error(self) -> None:
        skill = self.repo / "skills" / "engineering" / "demo" / "SKILL.md"
        skill.write_text(
            "# Demo\n\nRequires `adapters/claude-code/` to be installed.\n",
            encoding="utf-8",
        )

        messages = self.messages()
        self.assertEqual(len(messages), 1)
        self.assertIn("SKILL.md", messages[0])


class RegistryReaderTests(unittest.TestCase):
    """The Claude Code adapter reads the registry with its own YAML subset
    reader; the validator fails when that reader and a full YAML parser
    disagree on the source registry's references."""

    READER = Path("adapters") / "claude-code" / "goated_adapter" / "reference_reads.py"
    ENTRY = (
        "  - name: tdd\n    path: skills/engineering/tdd/SKILL.md\n    references:\n"
        "      - file: test-design.md\n        signal:\n          kind: edit-of-file-kind\n"
        "          file_kind: test\n          min_added_lines: 5\n"
    )

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        (self.repo / self.READER).parent.mkdir(parents=True)
        shutil.copy(REPO_ROOT / self.READER, self.repo / self.READER)
        (self.repo / "stack").mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def messages(self, registry: str) -> list[str]:
        (self.repo / "stack" / "goated-stack.yaml").write_text(registry, encoding="utf-8")
        return [finding.format() for finding in validate_registry_reader(self.repo)]

    def indentless(self) -> str:
        """The entry with its sequence not indented under its key."""

        return "\n".join(line[2:] for line in self.ENTRY.split("\n"))

    def test_the_real_repository_passes(self) -> None:
        self.assertEqual([f.format() for f in validate_registry_reader(REPO_ROOT)], [])

    def test_a_registry_both_read_alike_passes(self) -> None:
        self.assertEqual(self.messages("skills:\n" + self.ENTRY), [])

    def test_a_registry_the_reader_cannot_parse_is_an_error(self) -> None:
        # An indentless sequence is valid YAML the adapter's reader refuses.
        messages = self.messages("skills:\n" + self.indentless())
        self.assertEqual(len(messages), 1)
        self.assertIn("goated-stack.yaml", messages[0])
        self.assertIn("adapter", messages[0])

    def test_a_registry_the_two_read_differently_is_an_error(self) -> None:
        # A plain `-1` is an integer to YAML and a string to the adapter's reader.
        messages = self.messages("skills:\n" + self.ENTRY.replace("min_added_lines: 5", "min_added_lines: -1"))
        self.assertEqual(len(messages), 1)

    def test_no_reader_or_no_registry_reports_nothing_here(self) -> None:
        (self.repo / self.READER).unlink()
        self.assertEqual(self.messages("skills:\n" + self.indentless()), [])


if __name__ == "__main__":
    unittest.main()
