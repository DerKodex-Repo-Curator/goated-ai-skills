"""Check that the registry declares every skill reference, and its fixtures.

Each skill's registry entry lists the files under its `references/` folder,
each with a signal that makes its read enforced or an advisory reason. The
registry schema owns the shape of an entry. This module owns what the schema
cannot see: that the declared files, the files on disk, and the files the
skill's `SKILL.md` links are one set, and that every named pattern is
defined. `SKILL.md` keeps its "read when" sentences; the registry entry is
the enforceable form, and neither may name a file the other lacks.
"""

from __future__ import annotations

import re
from pathlib import Path

from jsonschema import Draft202012Validator

from .shared import Finding, load_mapping, read_text, relative

REGISTRY_LABEL = "stack/goated-stack.yaml"
FIXTURE_PATH = Path("stack") / "fixtures" / "reference-reads" / "entries.yaml"
SCHEMA_PATH = Path("stack") / "schemas" / "stack-registry.schema.json"

# A Markdown link target inside the skill's own references folder, such as
# `](references/test-design.md)` or `](./references/test-design.md#id)`.
# A path in backticks is not a link, so prose about the folder never counts.
_REFERENCE_LINK_RE = re.compile(r"\]\((?:\./)?references/([^)#\s]+)")


def _files_on_disk(references_dir: Path) -> set[str]:
    if not references_dir.is_dir():
        return set()
    return {
        path.relative_to(references_dir).as_posix()
        for path in references_dir.rglob("*")
        if path.is_file()
    }


def validate_skill_references(
    repo: Path,
    skill_entries: list[dict],
    pattern_names: set[str],
) -> list[Finding]:
    """Compare each skill's declared references with its folder and links.

    Expects schema-valid entries. A skill whose `SKILL.md` is missing is
    skipped, because the registry check already reports it.
    """

    errors: list[Finding] = []
    for skill in skill_entries:
        skill_path = repo / str(skill["path"])
        if not skill_path.exists():
            continue
        skill_dir = skill_path.parent
        folder = f"{relative(skill_dir, repo)}/references"

        declared: set[str] = set()
        for entry in skill.get("references", []):
            name = entry["file"]
            if name in declared:
                errors.append(
                    Finding(
                        REGISTRY_LABEL,
                        f"duplicate reference declaration: {folder}/{name}",
                    )
                )
            declared.add(name)
            pattern = entry.get("signal", {}).get("pattern")
            if pattern is not None and pattern not in pattern_names:
                errors.append(
                    Finding(
                        REGISTRY_LABEL,
                        f"reference signal names an undefined pattern: {pattern}",
                    )
                )

        on_disk = _files_on_disk(skill_dir / "references")
        linked = set(_REFERENCE_LINK_RE.findall(read_text(skill_path)))
        # Each file gets one finding for its first mismatch: a missing declared
        # file is not also unlinked, and an undeclared file on disk is not also
        # a link the registry lacks.
        mismatches = (
            (declared - on_disk, "declared reference does not exist"),
            (on_disk - declared, "reference file is not declared in the registry"),
            (
                linked - declared - on_disk,
                "SKILL.md links a reference the registry does not declare",
            ),
            (
                (declared & on_disk) - linked,
                "registry declares a reference SKILL.md never links",
            ),
        )
        for names, message in mismatches:
            for name in sorted(names):
                errors.append(Finding(REGISTRY_LABEL, f"{message}: {folder}/{name}"))
    return errors


def validate_reference_fixtures(repo: Path) -> list[Finding]:
    """Check each fixture case against the schema's reference-entry shape.

    The fixture holds one valid entry per signal kind, an advisory entry, and
    near misses the schema must reject, so a schema change that loosens or
    tightens an entry fails here.
    """

    label = FIXTURE_PATH.as_posix()
    fixture, errors = load_mapping(repo / FIXTURE_PATH, label)
    # The registry check owns reporting a missing or unreadable schema.
    schema, _ = load_mapping(repo / SCHEMA_PATH, SCHEMA_PATH.as_posix())
    if fixture is None or schema is None:
        return errors

    validator = Draft202012Validator(
        {"$ref": "#/$defs/referenceEntry", "$defs": schema["$defs"]}
    )
    cases = fixture.get("cases")
    if not isinstance(cases, list) or not cases:
        return [*errors, Finding(label, "fixture must list cases")]
    for case in cases:
        name = case.get("name", "<unnamed>")
        expected = case.get("valid")
        violations = [
            error.message for error in validator.iter_errors(case.get("entry"))
        ]
        if expected not in (True, False):
            errors.append(Finding(label, f"case {name} must set valid to true or false"))
        elif expected and violations:
            errors.append(
                Finding(label, f"case {name} should be valid but: {violations[0]}")
            )
        elif not expected and not violations:
            errors.append(Finding(label, f"case {name} should be rejected but passed"))
    return errors
