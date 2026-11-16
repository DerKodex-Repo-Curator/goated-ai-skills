"""Keeps the skill-usage mod's copy of the marker fixtures in step with the grammar.

The mod's tests run inside Claude Code's plugin test kit, which has no file
system or YAML parser, so they read `stack/fixtures/markers/lines.yaml`
through a generated TypeScript module. This test fails when that module no
longer matches the fixtures. Regenerate it with:

    uv run python tests/test_skill_usage_mod.py --write
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
MARKER_FIXTURES = REPO_ROOT / "stack" / "fixtures" / "markers" / "lines.yaml"
MOD_ROOT = REPO_ROOT / "adapters" / "claude-code" / "skill-usage"
GENERATED = MOD_ROOT / "tests" / "marker-fixtures.ts"

HEADER = (
    "// Generated from stack/fixtures/markers/lines.yaml by\n"
    "// `uv run python tests/test_skill_usage_mod.py --write`; do not edit by hand.\n"
    "// tests/test_skill_usage_mod.py fails when this copy drifts from the fixtures.\n"
)


def render_fixture_module() -> str:
    fixtures = yaml.safe_load(MARKER_FIXTURES.read_text(encoding="utf-8"))
    body = json.dumps(fixtures, indent=2, ensure_ascii=False)
    return f"{HEADER}\nexport const MARKER_FIXTURES = {body} as const\n"


class SkillUsageModFixtureTests(unittest.TestCase):
    def test_generated_marker_fixtures_match_lines_yaml(self) -> None:
        self.assertTrue(GENERATED.is_file(), f"missing {GENERATED.relative_to(REPO_ROOT)}")
        self.assertEqual(
            GENERATED.read_text(encoding="utf-8"),
            render_fixture_module(),
            "the mod's marker fixtures are stale; run "
            "`uv run python tests/test_skill_usage_mod.py --write`",
        )

    def test_mod_manifest_names_its_type_contract(self) -> None:
        manifest = json.loads((MOD_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "skill-usage")
        self.assertTrue((MOD_ROOT / manifest["types"]).is_file())


if __name__ == "__main__":
    if "--write" in sys.argv:
        GENERATED.write_text(render_fixture_module(), encoding="utf-8", newline="\n")
        print(f"wrote {GENERATED.relative_to(REPO_ROOT)}")
    else:
        unittest.main()
