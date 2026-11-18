"""Readers for the harness-neutral enforcement artifacts under `stack/`: the
contract's Gates table, the event model schema, and the conformance
scenarios. Nothing here knows a harness."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPO_ROOT / "stack" / "enforcement-contract.md"
SCHEMA = REPO_ROOT / "stack" / "schemas" / "enforcement-event-model.schema.json"
SCENARIOS = REPO_ROOT / "stack" / "fixtures" / "enforcement"

_CODE = re.compile(r"`([^`]+)`")


def _table_rows(heading: str) -> list[list[str]]:
    """The cells of each row of the table under the contract's `heading`
    whose first cell is code, such as a gate or an item label."""

    section = CONTRACT.read_text(encoding="utf-8").split(f"\n## {heading}\n", 1)[1]
    rows = []
    for line in section.split("\n## ", 1)[0].splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.startswith("|") and cells[0].startswith("`"):
            rows.append(cells)
    return rows


def contract_gates() -> dict[str, set[str]]:
    """Each gate the contract's Gates table names, with its clear ways."""

    return {cells[0].strip("`"): set(_CODE.findall(cells[4])) for cells in _table_rows("Gates")}


def contract_kinds() -> dict[str, str]:
    """Each gate the contract's Gates table names, with its kind."""

    return {cells[0].strip("`"): cells[1] for cells in _table_rows("Gates")}


def contract_closeout_labels() -> set[str]:
    """The labels of the contract's Closeout Items table."""

    return {cells[0].strip("`") for cells in _table_rows("Closeout Items")}


def validator(definition: str | None = None) -> Draft202012Validator:
    """A validator for the event model's root (a request), or for one of its
    `$defs`, such as `decision` or `scenario_file`."""

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    if definition is not None:
        schema = {"$ref": f"#/$defs/{definition}", "$defs": schema["$defs"]}
    return Draft202012Validator(schema)


def scenario_files() -> dict[Path, dict]:
    """Every scenario file, parsed, by path."""

    return {path: yaml.safe_load(path.read_text(encoding="utf-8"))
            for path in sorted(SCENARIOS.glob("*.yaml"))}


# How a runner compares a decision with a step's expectation. The
# conformance runner an adapter's author uses owns it, so every runner in
# the tests judges a step as theirs does.
from scripts.run_conformance import (  # noqa: E402,F401
    FAILURE_NOTICES, ITEM_LABEL, expectation_mismatch, item_labels,
)
