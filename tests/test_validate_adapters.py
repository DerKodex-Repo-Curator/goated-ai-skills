"""Behavior tests for the validator's opt-in adapter boundary checks."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.validate_skills import validate_adapter_boundary


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


if __name__ == "__main__":
    unittest.main()
