"""Keeps the skill-usage mod's copies of the grammar and adapter texts current.

The mod's tests run inside Claude Code's plugin test kit, which has no file
system, YAML parser, or Python, so they read two generated TypeScript modules:

- `marker-fixtures.ts`, the marker fixtures in `stack/fixtures/markers/lines.yaml`;
- `adapter-texts.ts`, the hold reasons and the override notice the Claude Code
  adapter actually produces, from driving it with synthetic sessions.

This test fails when either module no longer matches its source. Regenerate
both with:

    uv run python tests/test_skill_usage_mod.py --write
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from claude_code_adapter_support import BRIEF, ROUTER, Session, parse, reason

REPO_ROOT = Path(__file__).resolve().parents[1]
MARKER_FIXTURES = REPO_ROOT / "stack" / "fixtures" / "markers" / "lines.yaml"
MOD_ROOT = REPO_ROOT / "adapters" / "claude-code" / "skill-usage"
GENERATED_MARKERS = MOD_ROOT / "tests" / "marker-fixtures.ts"
GENERATED_ADAPTER_TEXTS = MOD_ROOT / "tests" / "adapter-texts.ts"


def _module(source: str, name: str, value: object) -> str:
    header = (
        f"// Generated from {source} by\n"
        "// `uv run python tests/test_skill_usage_mod.py --write`; do not edit by hand.\n"
        "// tests/test_skill_usage_mod.py fails when this copy drifts from its source.\n"
    )
    body = json.dumps(value, indent=2, ensure_ascii=False)
    return f"{header}\nexport const {name} = {body} as const\n"


def render_marker_fixtures() -> str:
    fixtures = yaml.safe_load(MARKER_FIXTURES.read_text(encoding="utf-8"))
    return _module("stack/fixtures/markers/lines.yaml", "MARKER_FIXTURES", fixtures)


def _write(path: str, lines: int = 6) -> dict:
    """A write tool's input adding enough lines to count as a substantial change."""

    return {"file_path": path, "content": "\n".join(f"line {n}" for n in range(lines))}


def _adapter_texts() -> dict[str, str]:
    """Drive the adapter through one synthetic session per text and keep what it says.

    A hold's text is its reason, as a denied tool call or a blocked `Stop`
    carries it; the override text is the hook context the mod reads.
    """

    texts: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as tmp:
        def session(name: str) -> Session:
            folder = Path(tmp) / name
            folder.mkdir()
            return Session(folder)

        def routed(name: str, route: str = "goated-route: direct") -> Session:
            s = session(name)
            s.prompt("Add CSV export.")
            s.load(ROUTER)
            s.say(route)
            return s

        first = session("router-first")
        first.prompt("Add CSV export.")
        texts["routerFirst"] = reason(first.call("Edit"))

        unrouted = session("route-line")
        unrouted.prompt("Add CSV export.")
        unrouted.load(ROUTER)
        texts["routeLine"] = reason(unrouted.call("Edit"))

        piped = routed("pipeline", "goated-route: standard | requires: tdd, doc-sync")
        texts["pipeline"] = reason(piped.call("Edit"))

        texts["commit"] = reason(routed("commit").call("Bash", {"command": 'git commit -m "Add export"'}))
        texts["pullRequest"] = reason(
            routed("pull-request").call("Bash", {"command": 'gh pr create --title "Add export" --body "Adds it."'})
        )

        spawn = routed("spawn")
        texts["spawn"] = reason(spawn.call("Agent", {"prompt": BRIEF}))
        spawn.load("subagent-driven-development")
        texts["spawnRead"] = reason(spawn.call("Agent", {"prompt": BRIEF}))

        texts["design"] = reason(routed("design").call("Write", _write("src/export.py")))
        texts["security"] = reason(routed("security").call("Write", _write("src/auth.py")))
        # A shell write is held like a write tool's: here, to a dependency manifest.
        texts["shellWrite"] = reason(
            routed("shell-write").call("Bash", {"command": "echo requests >> requirements.txt"})
        )

        closing = routed("closeout")
        closing.say("goated-skip: software-design-principles: one mechanical constant change")
        closing.call("Write", _write("src/export.py"))
        texts["closeout"] = parse(closing.hook("Stop", stop_hook_active=False, last_assistant_message="")).get(
            "reason", ""
        )

        overridden = session("override")
        context = parse(overridden.prompt("Skip routing and add CSV export."))["hookSpecificOutput"]
        texts["overrideNotice"] = context["additionalContext"]
    return texts


def render_adapter_texts() -> str:
    return _module(
        "the Claude Code adapter's output (goated_adapter), driven with synthetic sessions",
        "ADAPTER_TEXTS",
        _adapter_texts(),
    )


GENERATED = {GENERATED_MARKERS: render_marker_fixtures, GENERATED_ADAPTER_TEXTS: render_adapter_texts}


class SkillUsageModFixtureTests(unittest.TestCase):
    def test_generated_modules_match_their_sources(self) -> None:
        for path, render in GENERATED.items():
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file(), f"missing {path.relative_to(REPO_ROOT)}")
                self.assertEqual(
                    path.read_text(encoding="utf-8"),
                    render(),
                    f"{path.name} is stale; run `uv run python tests/test_skill_usage_mod.py --write`",
                )

    def test_adapter_texts_are_the_holds_and_notice_the_mod_reads(self) -> None:
        texts = _adapter_texts()
        self.assertTrue(texts["routerFirst"].startswith("goated-hold: router-first | strict\n"))
        self.assertTrue(texts["routeLine"].startswith("goated-hold: route-line | strict\n"))
        self.assertTrue(texts["pipeline"].startswith("goated-hold: pipeline | strict\n"))
        self.assertIn('recorded your override for this prompt: "Skip routing"', texts["overrideNotice"])
        gates = {
            "commit": "commit | strict",
            "pullRequest": "pull-request | strict",
            "spawn": "spawn | strict",
            "spawnRead": "spawn | strict",
            "design": "design | justified-skip",
            "security": "security | justified-skip",
            "shellWrite": "security | justified-skip",
            "closeout": "closeout | justified-skip",
        }
        for key, line in gates.items():
            with self.subTest(key=key):
                self.assertTrue(texts[key].startswith(f"goated-hold: {line}\n"), texts[key])

    def test_mod_manifest_names_its_type_contract(self) -> None:
        manifest = json.loads((MOD_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "skill-usage")
        self.assertTrue((MOD_ROOT / manifest["types"]).is_file())


if __name__ == "__main__":
    if "--write" in sys.argv:
        for path, render in GENERATED.items():
            path.write_text(render(), encoding="utf-8", newline="\n")
            print(f"wrote {path.relative_to(REPO_ROOT)}")
    else:
        unittest.main()
