"""Boundary checks for the opt-in framework adapters under `adapters/`.

ADR 0003 makes adapters optional layers: no skill may depend on one, and the
repo's adapters use only the Python standard library so they install without a
package manager. Adapter behavior itself is covered by the unit tests; this
module checks only those two boundaries.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

from .shared import Finding, read_text, relative

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
