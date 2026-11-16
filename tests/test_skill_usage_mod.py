"""Keeps the skill-usage mod's copies of the grammar and adapter texts current.

The mod's tests run inside Claude Code's plugin test kit, which has no file
system, YAML parser, or Python, so they read two generated TypeScript modules:

- `marker-fixtures.ts`, the marker fixtures in `stack/fixtures/markers/lines.yaml`;
- `design-reads-fixtures.ts`, the design-reads line fixtures in
  `stack/fixtures/markers/design-reads.yaml`;
- `adapter-texts.ts`, the hold reasons and the override context the Claude Code
  adapter actually produces, from driving it with synthetic sessions.

It also checks the one adapter fact the mod copies by hand: which file
extensions are code. This test fails when a module no longer matches its
source. Regenerate them with:

    uv run python tests/test_skill_usage_mod.py --write
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from claude_code_adapter_support import BRIEF, ROUTER, Session, parse, reason

REPO_ROOT = Path(__file__).resolve().parents[1]
# A whole backticked token shaped like a skill name, as the mod reads one from a hold.
BARE_BACKTICKED = re.compile(r"`([a-z0-9]+(?:-[a-z0-9]+)*)`")
MARKER_FIXTURES = REPO_ROOT / "stack" / "fixtures" / "markers" / "lines.yaml"
DESIGN_READS_FIXTURES = REPO_ROOT / "stack" / "fixtures" / "markers" / "design-reads.yaml"
MOD_ROOT = REPO_ROOT / "adapters" / "claude-code" / "skill-usage"
GENERATED_MARKERS = MOD_ROOT / "tests" / "marker-fixtures.ts"
GENERATED_DESIGN_READS = MOD_ROOT / "tests" / "design-reads-fixtures.ts"
# The mod's copies of the adapter's code-file extensions and edit tools, in hooks/classify.ts.
MOD_CODE_EXTENSIONS = re.compile(r"const CODE_EXTENSIONS = new Set\(\s*'([^']*)'")
MOD_FILE_EDIT_TOOLS = re.compile(r"const FILE_EDIT_TOOLS: Record<string, string> = \{([^}]*)\}")
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


def render_design_reads_fixtures() -> str:
    fixtures = yaml.safe_load(DESIGN_READS_FIXTURES.read_text(encoding="utf-8"))
    return _module("stack/fixtures/markers/design-reads.yaml", "DESIGN_READS_FIXTURES", fixtures)


def _write(path: str, lines: int = 6) -> dict:
    """A write tool's input adding enough lines to count as a substantial change."""

    return {"file_path": path, "content": "\n".join(f"line {n}" for n in range(lines))}


def _stop_reason(s: Session) -> str:
    """The reason the closeout gate blocks `Stop` with, or "" when it lets the turn end."""

    return parse(s.hook("Stop", stop_hook_active=False, last_assistant_message="")).get("reason", "")


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
        texts["closeout"] = _stop_reason(closing)

        # The other closeout items: a failed last check (Unfinished) and the design skill's red flags.
        unfinished = routed("closeout-unfinished")
        unfinished.load("software-design-principles")
        unfinished.call("Write", _write("src/export.py"))
        unfinished.run("pytest -q", success=False)
        texts["closeoutUnfinished"] = _stop_reason(unfinished)

        contract = routed("commit-contract")
        contract.load("commit-message")
        texts["commitContract"] = reason(contract.call("Bash", {"command": f'git commit -m "{"x" * 80}"'}))

        # Holds whose step reviews or describes the change, once the skill is loaded: they ask for a change read.
        texts["commitRead"] = reason(contract.call("Bash", {"command": 'git commit -m "Add export"'}))
        described = routed("pull-request-read")
        described.load("pr-description")
        texts["pullRequestRead"] = reason(
            described.call("Bash", {"command": 'gh pr create --title "Add export" --body "Adds it."'})
        )
        reviewed = routed("closeout-change-read")
        reviewed.load("software-design-principles")
        reviewed.load("code-security-review")
        reviewed.load("doc-sync")
        reviewed.call("Write", _write("src/auth.py"))
        reviewed.run("pytest -q")
        reviewed.read("/skills/software-design-principles/references/red-flags.md")
        texts["closeoutChangeRead"] = _stop_reason(reviewed)

        headings = routed("spawn-headings")
        headings.brief_with_handoff()
        texts["spawnHeadings"] = reason(headings.call("Agent", {"prompt": "Audit the exporter."}))

        texts["securityNoExtension"] = reason(routed("security-no-extension").call("Write", _write(".env")))

        overridden = session("override")
        context = parse(overridden.prompt("Skip routing and add CSV export."))["hookSpecificOutput"]
        texts["overrideContext"] = context["additionalContext"]
    return texts


def render_adapter_texts() -> str:
    return _module(
        "the Claude Code adapter's output (goated_adapter), driven with synthetic sessions",
        "ADAPTER_TEXTS",
        _adapter_texts(),
    )


GENERATED = {
    GENERATED_MARKERS: render_marker_fixtures,
    GENERATED_DESIGN_READS: render_design_reads_fixtures,
    GENERATED_ADAPTER_TEXTS: render_adapter_texts,
}


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
        self.assertIn('recorded your override for this prompt: "Skip routing"', texts["overrideContext"])
        gates = {
            "commit": "commit | strict",
            "pullRequest": "pull-request | strict",
            "spawn": "spawn | strict",
            "spawnRead": "spawn | strict",
            "design": "design | justified-skip",
            "security": "security | justified-skip",
            "shellWrite": "security | justified-skip",
            "closeout": "closeout | justified-skip",
            "closeoutUnfinished": "closeout | justified-skip",
            "commitContract": "commit | strict",
            "spawnHeadings": "spawn | strict",
            "securityNoExtension": "security | justified-skip",
        }
        for key, line in gates.items():
            with self.subTest(key=key):
                self.assertTrue(texts[key].startswith(f"goated-hold: {line}\n"), texts[key])
        self.assertIn("- Unfinished:", texts["closeoutUnfinished"])
        self.assertIn("- Design:", texts["closeoutUnfinished"])

    def test_holds_a_line_can_clear_give_the_bare_retry_and_the_user_way_out(self) -> None:
        # A route or skip line written in the held call's own message is recorded only after the
        # hook returns, and Claude Code may store it as a narration summary that drops it (README
        # "Known Limits"), so the hint is a bare retry, not a promise, and the user can stand it down.
        texts = _adapter_texts()
        ways_out = {
            "routeLine": "skip routing",
            "pipeline": "skip routing",
            "design": "skip software-design-principles",
            "security": "skip code-security-review",
            "shellWrite": "skip code-security-review",
            "securityNoExtension": "skip code-security-review",
        }
        for key, way_out in ways_out.items():
            with self.subTest(key=key):
                self.assertIn("make the call again without repeating the line", texts[key])
                self.assertIn("may not be seen", texts[key])
                self.assertIn(f"`{way_out}`", texts[key])

    def test_holds_backtick_only_skill_names(self) -> None:
        # The mod reads every bare backticked name in a hold as a skill it asks for (README "Hold messages"),
        # so a backticked file name, such as a security hold's `credentials`, would read as a phantom skill.
        registry = yaml.safe_load((REPO_ROOT / "stack" / "goated-stack.yaml").read_text(encoding="utf-8"))
        skills = {entry["name"] for entry in registry["skills"]}
        for key, text in _adapter_texts().items():
            if not text.startswith("goated-hold: "):
                continue
            with self.subTest(key=key):
                names = set(BARE_BACKTICKED.findall(text.split("\n", 1)[1]))
                self.assertEqual(names - skills, set(), text)

    def test_a_security_hold_on_a_file_named_like_a_word_names_no_extra_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            s = Session(Path(tmp))
            s.prompt("Add CSV export.")
            s.load(ROUTER)
            s.say("goated-route: direct")
            held = reason(s.call("Write", _write("src/credentials")))
        self.assertTrue(held.startswith("goated-hold: security | justified-skip\n"), held)
        self.assertEqual(set(BARE_BACKTICKED.findall(held)), {"code-security-review"})

    def test_mod_counts_the_same_files_as_code_as_the_adapter(self) -> None:
        # The mod times reference reads against code changes, which it must judge as the adapter does.
        from goated_adapter.actions import CODE_EXTENSIONS, FILE_WRITE_TOOLS

        source = (MOD_ROOT / "hooks" / "classify.ts").read_text(encoding="utf-8")
        found = MOD_CODE_EXTENSIONS.search(source)
        self.assertIsNotNone(found, "hooks/classify.ts no longer declares CODE_EXTENSIONS as this test reads it")
        self.assertEqual(set(found.group(1).split()), set(CODE_EXTENSIONS))
        tools = MOD_FILE_EDIT_TOOLS.search(source)
        self.assertIsNotNone(tools, "hooks/classify.ts no longer declares FILE_EDIT_TOOLS as this test reads it")
        self.assertEqual(dict(re.findall(r"(\w+): '([^']+)'", tools.group(1))), FILE_WRITE_TOOLS)

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
