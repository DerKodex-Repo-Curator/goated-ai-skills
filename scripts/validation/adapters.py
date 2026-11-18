"""Boundary checks for the opt-in framework adapters under `adapters/`.

ADR 0003 makes adapters optional layers: no skill may depend on one, and the
repo's adapters use only the Python standard library so they install without a
package manager. Adapter behavior itself is covered by the unit tests; this
module checks those two boundaries, that the shared core (`adapters/core/`),
which every adapter may import, imports no adapter, that the core's own
registry reader reads the source registry as a full YAML parser does, and
that every `gate-fires` signal names a gate the core observes.
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
# The shared enforcement core every adapter may import (ADR 0004).
CORE_PACKAGE = Path("adapters") / "core" / "goated_core"
# The core's registry reader: standard library only, so it reads a YAML
# subset, which this check keeps in step with the registry.
REGISTRY_READER_PATH = CORE_PACKAGE / "reference_reads.py"

ADAPTER_REFERENCE_RE = re.compile(r"(?<![\w-])adapters/[a-z0-9-]+|goated_adapter")


def validate_adapter_boundary(repo: Path) -> list[Finding]:
    """Return findings for adapter code with non-stdlib imports or skills that cite adapters."""

    findings: list[Finding] = []
    adapters_root = repo / "adapters"
    if adapters_root.is_dir():
        # Every adapter may import the shared core (ADR 0004); the core
        # imports only itself, so it never learns an adapter's code.
        shared = {CORE_PACKAGE.name} if (repo / CORE_PACKAGE / "__init__.py").exists() else set()
        for path in sorted(adapters_root.rglob("*.py")):
            in_core = (repo / CORE_PACKAGE.parent) in path.parents
            findings.extend(_non_stdlib_imports(path, repo, set() if in_core else shared))

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
    the registry check owns reporting those. When the two agree, a finding is
    returned for each `gate-fires` signal naming a gate outside the reader's
    `OBSERVED_GATES`, which the adapter would never enforce, and one when
    more than one reference has an `edit-of-file-kind` signal for test files.
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
        return [Finding(label, f"the shared adapter core's registry reader cannot read it: {exc}")]
    finally:
        sys.modules.pop(spec.name, None)
    if found != expected:
        first = next((pair for pair in zip(found, expected) if pair[0] != pair[1]), None)
        detail = f": {first[0]!r} where YAML gives {first[1]!r}" if first else ""
        return [Finding(label, "the shared adapter core's registry reader reads its references "
                               f"differently from YAML{detail}")]
    # The schema allows a `gate-fires` signal to name any gate, but the adapter
    # observes only some; an entry naming another would never be enforced.
    observed = ", ".join(sorted(reader.OBSERVED_GATES))
    findings = [
        Finding(label, f"{skill}'s {file} has a gate-fires signal for the {signal['gate']} gate, "
                       f"which the shared adapter core does not observe (it observes: {observed})")
        for skill, file, signal in found
        if signal.get("kind") == "gate-fires" and signal.get("gate") not in reader.OBSERVED_GATES
    ]
    # The design gate also judges a test edit for `coding.md` by the test
    # file-kind signal (`file_kind_signal`), so a second one would decide it
    # silently by registry order.
    test_kind = [f"{skill}'s {file}" for skill, file, signal in found
                 if signal.get("kind") == "edit-of-file-kind" and signal.get("file_kind") == "test"]
    if len(test_kind) > 1:
        findings.append(Finding(label, "more than one reference has an edit-of-file-kind signal "
                                       f"for test files ({', '.join(test_kind)}); the shared "
                                       "adapter core's design gate reads only one"))
    return findings


def _non_stdlib_imports(path: Path, repo: Path, shared: set[str]) -> list[Finding]:
    """Findings for each import in `path` that is neither the standard
    library, a module beside it, nor one of the `shared` packages."""

    try:
        tree = ast.parse(read_text(path), filename=str(path))
    except SyntaxError as exc:
        return [Finding(relative(path, repo), f"adapter file does not parse: {exc.msg}")]

    local = _local_module_names(path) | shared
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        elif (name := _imported_by_name(node)) is not None:
            names = [name]
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


def _imported_by_name(node: ast.AST) -> str | None:
    """The module a run-time import call names with a literal, such as
    `importlib.import_module("x")` or `__import__("x")`, else None."""

    if not (isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)):
        return None
    func = node.func
    calls = ((isinstance(func, ast.Name) and func.id in ("__import__", "import_module"))
             or (isinstance(func, ast.Attribute) and func.attr == "import_module"))
    return node.args[0].value if calls else None


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
