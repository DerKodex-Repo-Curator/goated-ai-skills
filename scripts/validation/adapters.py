"""Boundary checks for the opt-in framework adapters under `adapters/`.

ADR 0003 makes adapters optional layers: no skill may depend on one, and the
repo's adapters use only the Python standard library so they install without a
package manager. Adapter behavior itself is covered by the unit tests; this
module checks those two boundaries, and that the Claude Code adapter's own
registry reader reads the source registry as a full YAML parser does.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import sys
from pathlib import Path

import yaml

from .shared import Finding, read_text, relative

REGISTRY_PATH = Path("stack") / "goated-stack.yaml"
# The Claude Code adapter's registry reader: standard library only, so it
# reads a YAML subset, which this check keeps in step with the registry.
REGISTRY_READER_PATH = Path("adapters") / "claude-code" / "goated_adapter" / "reference_reads.py"

ADAPTER_REFERENCE_RE = re.compile(r"(?<![\w-])adapters/[a-z0-9-]+|goated_adapter")


def validate_adapter_boundary(repo: Path) -> list[Finding]:
    """Return findings for adapter code with non-stdlib imports or skills that cite adapters."""

    findings: list[Finding] = []
    adapters_root = repo / "adapters"
    if adapters_root.is_dir():
        for path in sorted(adapters_root.rglob("*.py")):
            findings.extend(_non_stdlib_imports(path, repo))

    skills_root = repo / "skills"
    if skills_root.is_dir():
        for path in sorted(skills_root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".md", ".yaml", ".yml"}:
                continue
            text = read_text(path)
            match = ADAPTER_REFERENCE_RE.search(text)
            if match:
                findings.append(
                    Finding(
                        relative(path, repo),
                        "skills must not depend on an opt-in adapter "
                        f"(found {match.group(0)!r})",
                        line=text.count("\n", 0, match.start()) + 1,
                    )
                )
    return findings


def validate_registry_reader(repo: Path) -> list[Finding]:
    """Return a finding when the adapter's registry reader and `yaml.safe_load`
    disagree on the references the source registry declares with a signal.

    The adapter fails open on a registry it cannot read, so a registry edit
    its reader refuses would silently switch the `reference-reads` gate off.
    Nothing is reported without the reader or a registry that YAML parses;
    the registry check owns reporting those.
    """

    reader_path, registry_path = repo / REGISTRY_READER_PATH, repo / REGISTRY_PATH
    if not reader_path.is_file() or not registry_path.is_file():
        return []
    try:
        data = yaml.safe_load(read_text(registry_path))
    except yaml.YAMLError:
        return []
    skills = data.get("skills") if isinstance(data, dict) else None
    if not isinstance(skills, list):
        return []
    expected = [
        (skill.get("name"), entry.get("file"), entry["signal"])
        for skill in skills if isinstance(skill, dict)
        for entry in skill.get("references") or [] if isinstance(entry, dict) and "signal" in entry
    ]
    label = REGISTRY_PATH.as_posix()
    spec = importlib.util.spec_from_file_location("_goated_registry_reader", reader_path)
    reader = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reader
    try:
        spec.loader.exec_module(reader)
        found = [(r.skill, r.file, r.signal) for r in reader.load(registry_path)]
    except reader.RegistryUnreadable as exc:
        return [Finding(label, f"the Claude Code adapter's registry reader cannot read it: {exc}")]
    finally:
        sys.modules.pop(spec.name, None)
    if found != expected:
        first = next((pair for pair in zip(found, expected) if pair[0] != pair[1]), None)
        detail = f": {first[0]!r} where YAML gives {first[1]!r}" if first else ""
        return [Finding(label, "the Claude Code adapter's registry reader reads its references "
                               f"differently from YAML{detail}")]
    return []


def _non_stdlib_imports(path: Path, repo: Path) -> list[Finding]:
    try:
        tree = ast.parse(read_text(path), filename=str(path))
    except SyntaxError as exc:
        return [Finding(relative(path, repo), f"adapter file does not parse: {exc.msg}")]

    local = _local_module_names(path)
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        else:
            continue
        for name in names:
            top = name.split(".", 1)[0]
            if top not in sys.stdlib_module_names and top not in local:
                findings.append(
                    Finding(
                        relative(path, repo),
                        f"adapters use only the standard library; {top!r} is not",
                        line=node.lineno,
                    )
                )
    return findings


def _local_module_names(path: Path) -> set[str]:
    """Modules and packages importable by absolute name from the adapter's own folder."""

    names: set[str] = set()
    for directory in (path.parent, *path.parents):
        if not (directory / "__init__.py").exists():
            names.update(
                child.stem if child.is_file() else child.name
                for child in directory.iterdir()
                if child.suffix == ".py" or (child / "__init__.py").exists()
            )
            break
    return names
