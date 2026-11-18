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


def contract_gates() -> dict[str, set[str]]:
    """Each gate the contract's Gates table names, with its clear ways."""

    section = CONTRACT.read_text(encoding="utf-8").split("\n## Gates\n", 1)[1].split("\n## ", 1)[0]
    gates: dict[str, set[str]] = {}
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 5 or not cells[0].startswith("`"):
            continue
        gates[cells[0].strip("`")] = set(_CODE.findall(cells[4]))
    return gates


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
