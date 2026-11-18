"""Readers for the harness-neutral enforcement artifacts under `stack/`: the
contract's Gates table, the event model schema, and the conformance
scenarios. Nothing here knows a harness."""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

import usage_log_guard  # noqa: F401 - keeps the run's usage log out of the user's own

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


# A closeout item's line, as the contract's Hold Messages section defines it.
ITEM_LABEL = re.compile(r"^- ([A-Z][a-z]+): ", re.M)
# Notices that mean the adapter could not judge: never expected unless named.
FAILURE_NOTICES = frozenset({"fail_open", "warning"})


def item_labels(closeout_text: str) -> list[str]:
    """The labels of the items a closeout hold's text lists, sorted."""

    return sorted(set(ITEM_LABEL.findall(closeout_text)))


def expectation_mismatch(expect: dict | None, got: dict) -> tuple[dict, dict] | None:
    """What a step `expect`ed and what it `got`, when they differ, else None.

    `got` is a decision as a runner observed it: `decision`, `holds` as
    (gate, kind) pairs in firing order, `items`, the closeout hold's item
    labels, and `notices`, their kinds. With no `expect`, the step is not
    checked, but a decision that could not judge never passes. Holds match
    by gate and kind; items only when the expectation names them; notices
    exactly when it names them, and otherwise only the failure kinds count.
    """

    if expect is None:
        expect = {"decision": got["decision"], "holds": [
            {"gate": gate, "kind": kind} for gate, kind in got["holds"]]}
    holds = expect.get("holds", [])
    wanted = {"decision": expect["decision"],
              "holds": [(h["gate"], h["kind"]) for h in holds]}
    found = {"decision": got["decision"], "holds": got["holds"]}
    labels = next((h["items"] for h in holds if "items" in h), None)
    if labels is not None:
        wanted["items"], found["items"] = sorted(labels), got["items"]
    if "notices" in expect:
        wanted["notices"] = sorted(expect["notices"])
        found["notices"] = sorted(got["notices"])
    else:
        wanted["failures"] = []
        found["failures"] = sorted(FAILURE_NOTICES.intersection(got["notices"]))
    return None if wanted == found else (wanted, found)
