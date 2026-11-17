"""Tests for the registry's reference declarations (ticket 066).

Each failure the validator reports has a near miss beside it: the smallest
change that makes the same registry valid again.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

import yaml

from scripts.validate_skills import (
    validate_reference_fixtures,
    validate_registry,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
TDD_DIR = Path("skills") / "engineering" / "tdd"
FIXTURE = Path("stack") / "fixtures" / "reference-reads" / "entries.yaml"


def load_registry(root: Path) -> dict:
    return yaml.safe_load(
        (root / "stack" / "goated-stack.yaml").read_text(encoding="utf-8")
    )


def skill_entry(registry: dict, name: str) -> dict:
    return next(entry for entry in registry["skills"] if entry["name"] == name)


def run_with(change: Callable[[Path, dict], None]) -> list[str]:
    """Copy the stack and skills, apply a change, and validate the registry."""

    with tempfile.TemporaryDirectory() as temporary_directory:
        root = Path(temporary_directory)
        shutil.copytree(REPO_ROOT / "stack", root / "stack")
        shutil.copytree(REPO_ROOT / "skills", root / "skills")
        registry = load_registry(root)
        change(root, registry)
        (root / "stack" / "goated-stack.yaml").write_text(
            yaml.safe_dump(registry, sort_keys=False),
            encoding="utf-8",
        )
        return [finding.message for finding in validate_registry(root)]


def add_reference_file(root: Path, name: str) -> None:
    (root / TDD_DIR / "references" / name).write_text(
        "# New Reference\n", encoding="utf-8"
    )


def link_reference(root: Path, name: str) -> None:
    skill_path = root / TDD_DIR / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    skill_path.write_text(
        text + f"\nRead [New](references/{name}) when testing.\n",
        encoding="utf-8",
    )


def declare(registry: dict, entry: dict) -> None:
    skill_entry(registry, "tdd")["references"].append(entry)


def add_linked_and_declare(entry: dict) -> Callable[[Path, dict], None]:
    """A new tdd reference, linked from SKILL.md and declared as given."""

    def change(root: Path, registry: dict) -> None:
        add_reference_file(root, "new-ref.md")
        link_reference(root, "new-ref.md")
        declare(registry, entry)

    return change


ADVISORY = {"file": "new-ref.md", "advisory": "No tool call shows when it applies."}


class CurrentRegistryTests(unittest.TestCase):
    def test_every_reference_file_is_declared_with_a_signal_or_reason(self) -> None:
        registry = load_registry(REPO_ROOT)
        declared: dict[str, dict] = {}
        for skill in registry["skills"]:
            skill_dir = Path(skill["path"]).parent
            for entry in skill.get("references", []):
                declared[(skill_dir / "references" / entry["file"]).as_posix()] = entry

        on_disk = sorted(
            path.relative_to(REPO_ROOT).as_posix()
            for path in (REPO_ROOT / "skills").glob("*/*/references/**/*")
            if path.is_file()
        )
        self.assertTrue(on_disk)
        for path in on_disk:
            with self.subTest(path=path):
                self.assertIn(path, declared)
                entry = declared[path]
                self.assertTrue(
                    "signal" in entry or str(entry.get("advisory", "")).strip()
                )
        self.assertEqual([], validate_registry(REPO_ROOT))

    def test_first_enforced_set_is_declared_as_enforced(self) -> None:
        registry = load_registry(REPO_ROOT)
        expected = {
            ("tdd", "mocking-and-seams.md"): {
                "kind": "edit-adds-pattern",
                "pattern": "mock-or-patch",
                "file_kind": "test",
            },
            ("tdd", "test-design.md"): {
                "kind": "edit-of-file-kind",
                "file_kind": "test",
                "min_added_lines": 5,
            },
            ("diagnose", "root-cause-tracing.md"): {
                "kind": "gate-fires",
                "gate": "repeated-failure",
            },
            ("diagnose", "condition-based-waiting.md"): {
                "kind": "edit-adds-pattern",
                "pattern": "sleep-retry-or-timeout",
            },
            ("code-security-review", "security-review-checklist.md"): {
                "kind": "sensitive-category-count",
                "min_categories": 2,
            },
            ("write-a-spec", "spec-template.md"): {
                "kind": "write-under-path",
                "path": "docs/specs/",
            },
            ("spec-to-tickets", "ticket-slicing-templates.md"): {
                "kind": "write-under-path",
                "path": "tickets/",
            },
        }
        for (skill, file_name), signal in expected.items():
            with self.subTest(skill=skill, file=file_name):
                entries = {
                    entry["file"]: entry
                    for entry in skill_entry(registry, skill)["references"]
                }
                self.assertEqual(signal, entries[file_name].get("signal"))

    def test_references_enforced_today_name_their_existing_rule(self) -> None:
        registry = load_registry(REPO_ROOT)
        design = skill_entry(registry, "software-design-principles")["references"]
        for entry in design:
            gate = "closeout" if entry["file"] == "red-flags.md" else "design-reads"
            with self.subTest(file=entry["file"]):
                self.assertEqual(
                    {"kind": "existing-rule", "gate": gate}, entry.get("signal")
                )
        for skill in ("handoff", "subagent-driven-development"):
            for entry in skill_entry(registry, skill)["references"]:
                with self.subTest(skill=skill, file=entry["file"]):
                    self.assertEqual(
                        {"kind": "existing-rule", "gate": "spawn"},
                        entry.get("signal"),
                    )

    def test_maintainer_docs_state_the_reference_standard(self) -> None:
        agents = " ".join(
            (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8").split()
        )
        skills_readme = " ".join(
            (REPO_ROOT / "skills" / "README.md").read_text(encoding="utf-8").split()
        )
        self.assertIn(
            "When adding, renaming, or removing a file under a skill's "
            "`references/`, update that skill's `references` entry in "
            "`stack/goated-stack.yaml` in the same change",
            agents,
        )
        self.assertIn(
            "Adding, renaming, or removing a reference file updates its "
            "registry entry in the same change.",
            skills_readme,
        )

    def test_no_installed_skill_needs_the_registry_at_runtime(self) -> None:
        """Only the instructions integrator names the registry, as an optional
        install it looks for and falls back from."""

        mentions = sorted(
            path.relative_to(REPO_ROOT).as_posix()
            for path in (REPO_ROOT / "skills").glob("*/*/**/*.md")
            if "goated-stack.yaml" in path.read_text(encoding="utf-8")
        )
        self.assertEqual(
            ["skills/agent-workflows/agent-instructions-integrator/SKILL.md"],
            mentions,
        )
        text = (REPO_ROOT / mentions[0]).read_text(encoding="utf-8")
        self.assertIn("use standalone skill instructions", text)


class ReferenceDeclarationFailureTests(unittest.TestCase):
    def test_undeclared_reference_file_fails(self) -> None:
        def change(root: Path, registry: dict) -> None:
            add_reference_file(root, "new-ref.md")
            link_reference(root, "new-ref.md")

        self.assertEqual(
            [
                "reference file is not declared in the registry: "
                "skills/engineering/tdd/references/new-ref.md"
            ],
            run_with(change),
        )

    def test_near_miss_declared_linked_reference_passes(self) -> None:
        self.assertEqual([], run_with(add_linked_and_declare(dict(ADVISORY))))

    def test_entry_for_missing_file_fails(self) -> None:
        def change(root: Path, registry: dict) -> None:
            link_reference(root, "new-ref.md")
            declare(registry, dict(ADVISORY))

        self.assertEqual(
            [
                "declared reference does not exist: "
                "skills/engineering/tdd/references/new-ref.md"
            ],
            run_with(change),
        )

    def test_unknown_signal_kind_fails(self) -> None:
        messages = run_with(
            add_linked_and_declare(
                {"file": "new-ref.md", "signal": {"kind": "edit-feels-risky"}}
            )
        )
        self.assertEqual(1, len(messages), messages)
        self.assertTrue(messages[0].startswith("registry schema violation"))
        self.assertIn("'edit-feels-risky' is not one of", messages[0])

    def test_near_miss_known_signal_kind_passes(self) -> None:
        messages = run_with(
            add_linked_and_declare(
                {"file": "new-ref.md", "signal": {"kind": "spawn-with-brief"}}
            )
        )
        self.assertEqual([], messages)

    def test_signal_missing_its_parameter_fails(self) -> None:
        messages = run_with(
            add_linked_and_declare(
                {"file": "new-ref.md", "signal": {"kind": "write-under-path"}}
            )
        )
        self.assertEqual(1, len(messages), messages)
        self.assertIn("'path' is a required property", messages[0])

    def test_advisory_entry_without_a_reason_fails(self) -> None:
        for advisory in ("", "   ", None):
            with self.subTest(advisory=advisory):
                messages = run_with(
                    add_linked_and_declare(
                        {"file": "new-ref.md", "advisory": advisory}
                    )
                )
                self.assertEqual(1, len(messages), messages)
                self.assertTrue(messages[0].startswith("registry schema violation"))
                self.assertIn(".advisory:", messages[0])

    def test_entry_with_neither_signal_nor_advisory_fails(self) -> None:
        messages = run_with(add_linked_and_declare({"file": "new-ref.md"}))
        self.assertEqual(1, len(messages), messages)
        self.assertTrue(messages[0].startswith("registry schema violation"))

    def test_undefined_pattern_fails(self) -> None:
        messages = run_with(
            add_linked_and_declare(
                {
                    "file": "new-ref.md",
                    "signal": {"kind": "edit-adds-pattern", "pattern": "vibes"},
                }
            )
        )
        self.assertEqual(
            ["reference signal names an undefined pattern: vibes"], messages
        )

    def test_near_miss_defined_pattern_passes(self) -> None:
        messages = run_with(
            add_linked_and_declare(
                {
                    "file": "new-ref.md",
                    "signal": {"kind": "edit-adds-pattern", "pattern": "mock-or-patch"},
                }
            )
        )
        self.assertEqual([], messages)

    def test_skill_linking_an_undeclared_reference_fails(self) -> None:
        def change(root: Path, registry: dict) -> None:
            link_reference(root, "ghost.md")

        self.assertEqual(
            [
                "SKILL.md links a reference the registry does not declare: "
                "skills/engineering/tdd/references/ghost.md"
            ],
            run_with(change),
        )

    def test_registry_declaring_an_unlinked_reference_fails(self) -> None:
        def change(root: Path, registry: dict) -> None:
            add_reference_file(root, "new-ref.md")
            declare(registry, dict(ADVISORY))

        self.assertEqual(
            [
                "registry declares a reference SKILL.md never links: "
                "skills/engineering/tdd/references/new-ref.md"
            ],
            run_with(change),
        )

    def test_duplicate_declaration_fails(self) -> None:
        def change(root: Path, registry: dict) -> None:
            declare(
                registry,
                {"file": "test-design.md", "advisory": "Declared twice by mistake."},
            )

        self.assertEqual(
            [
                "duplicate reference declaration: "
                "skills/engineering/tdd/references/test-design.md"
            ],
            run_with(change),
        )


    def test_gate_fires_with_an_unknown_gate_fails(self) -> None:
        messages = run_with(
            add_linked_and_declare(
                {
                    "file": "new-ref.md",
                    "signal": {"kind": "gate-fires", "gate": "repeated-failur"},
                }
            )
        )
        self.assertEqual(1, len(messages), messages)
        self.assertIn("'repeated-failur' is not one of", messages[0])

    def test_near_miss_gate_fires_with_a_real_gate_passes(self) -> None:
        messages = run_with(
            add_linked_and_declare(
                {
                    "file": "new-ref.md",
                    "signal": {"kind": "gate-fires", "gate": "repeated-failure"},
                }
            )
        )
        self.assertEqual([], messages)

    def test_reference_style_and_angle_bracket_links_are_checked(self) -> None:
        for link in (
            "[ghost]: references/ghost.md",
            "[ghost]: ./references/ghost.md",
            "Read [Ghost](<references/ghost.md>) first.",
        ):
            with self.subTest(link=link):

                def change(root: Path, registry: dict, link: str = link) -> None:
                    skill_path = root / TDD_DIR / "SKILL.md"
                    text = skill_path.read_text(encoding="utf-8")
                    skill_path.write_text(text + f"\n{link}\n", encoding="utf-8")

                self.assertEqual(
                    [
                        "SKILL.md links a reference the registry does not declare: "
                        "skills/engineering/tdd/references/ghost.md"
                    ],
                    run_with(change),
                )

    def test_near_miss_reference_style_link_to_a_declared_file_passes(self) -> None:
        def change(root: Path, registry: dict) -> None:
            add_reference_file(root, "new-ref.md")
            skill_path = root / TDD_DIR / "SKILL.md"
            text = skill_path.read_text(encoding="utf-8")
            skill_path.write_text(
                text + "\n[new]: references/new-ref.md\n", encoding="utf-8"
            )
            declare(registry, dict(ADVISORY))

        self.assertEqual([], run_with(change))

    def test_os_junk_and_dotfiles_in_references_are_ignored(self) -> None:
        def change(root: Path, registry: dict) -> None:
            for name in (".DS_Store", "Thumbs.db", "desktop.ini", ".hidden.md"):
                add_reference_file(root, name)

        self.assertEqual([], run_with(change))

    def test_near_miss_ordinary_undeclared_file_is_still_reported(self) -> None:
        def change(root: Path, registry: dict) -> None:
            add_reference_file(root, "notes.txt")

        self.assertEqual(
            [
                "reference file is not declared in the registry: "
                "skills/engineering/tdd/references/notes.txt"
            ],
            run_with(change),
        )

    def test_duplicate_reference_pattern_fails(self) -> None:
        def change(root: Path, registry: dict) -> None:
            registry["reference_patterns"].append(
                {"name": "mock-or-patch", "description": "Defined twice by mistake."}
            )

        self.assertEqual(
            ["duplicate reference pattern: mock-or-patch"], run_with(change)
        )


class ReferenceFixtureTests(unittest.TestCase):
    def test_current_reference_fixtures_are_valid(self) -> None:
        self.assertEqual([], validate_reference_fixtures(REPO_ROOT))

    def test_fixture_whose_expectation_is_wrong_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            shutil.copytree(REPO_ROOT / "stack", root / "stack")
            fixture_path = root / FIXTURE
            fixture = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
            flipped = fixture["cases"][0]
            flipped["valid"] = not flipped["valid"]
            fixture_path.write_text(
                yaml.safe_dump(fixture, sort_keys=False), encoding="utf-8"
            )

            messages = [
                finding.message for finding in validate_reference_fixtures(root)
            ]

        self.assertEqual(1, len(messages), messages)
        self.assertIn(flipped["name"], messages[0])

    def test_fixtures_cover_every_signal_kind_and_a_near_miss(self) -> None:
        schema = json.loads(
            (REPO_ROOT / "stack" / "schemas" / "stack-registry.schema.json").read_text(
                encoding="utf-8"
            )
        )
        kinds = set(schema["$defs"]["referenceSignal"]["properties"]["kind"]["enum"])
        fixture = yaml.safe_load((REPO_ROOT / FIXTURE).read_text(encoding="utf-8"))
        valid_kinds = {
            case["entry"]["signal"]["kind"]
            for case in fixture["cases"]
            if case["valid"] and "signal" in case["entry"]
        }
        self.assertEqual(kinds, valid_kinds)
        self.assertTrue(any(not case["valid"] for case in fixture["cases"]))
        self.assertTrue(
            any(case["valid"] and "advisory" in case["entry"] for case in fixture["cases"])
        )


if __name__ == "__main__":
    unittest.main()
