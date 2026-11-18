"""The enforcement contract names every gate, kind and closeout item the shared
core (`adapters/core/`) can return, and the clear ways its scenarios prove (Ticket 079,
spec AC2).

The core's gates and kinds are read from its source: every `Hold(...)` it
builds, and a `Hold` subclass's `super().__init__(...)`, with the gate and
kind given by position or keyword. A value is read as a literal, a module
constant, either branch of a conditional, or a parameter, which is followed
to every call of its function. Anything else is unreadable and fails the
check, so a new gate cannot slip past it. Closeout labels are read from the
text each `_Item(...)` opens with, `- <Label>: `.
"""

from __future__ import annotations

import ast
import re
import unittest

from enforcement_support import (
    REPO_ROOT, contract_closeout_labels, contract_gates, contract_kinds, scenario_files,
)

CORE = REPO_ROOT / "adapters" / "core" / "goated_core"
ITEM_LABEL = re.compile(r"^- ([A-Z][a-z]+): ")
# How far a parameter is followed back through its callers.
MAX_FORWARDS = 6


class _Package:
    """The core package's source, for reading the values a hold is built with."""

    def __init__(self) -> None:
        self.modules = [ast.parse(path.read_text(encoding="utf-8"))
                        for path in sorted(CORE.glob("*.py"))]
        self.constants: dict[str, str] = {}
        for module in self.modules:
            for node in module.body:
                if (isinstance(node, ast.Assign) and len(node.targets) == 1
                        and isinstance(node.targets[0], ast.Name)
                        and isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, str)):
                    self.constants[node.targets[0].id] = node.value.value
        # Every call, with the function it sits in and whether that is in a Hold subclass.
        self.calls: list[tuple[ast.Call, ast.FunctionDef | None, bool]] = []
        for module in self.modules:
            self._visit(module, None, False)

    def _visit(self, node: ast.AST, function, in_hold_class: bool) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function = node
        elif isinstance(node, ast.ClassDef):
            in_hold_class = any(isinstance(b, ast.Name) and b.id == "Hold" for b in node.bases)
        elif isinstance(node, ast.Call):
            self.calls.append((node, function, in_hold_class))
        for child in ast.iter_child_nodes(node):
            self._visit(child, function, in_hold_class)

    def holds(self) -> list[tuple[ast.Call, ast.FunctionDef | None]]:
        """Each call that builds a hold, with the function it sits in."""

        found = []
        for call, function, in_hold_class in self.calls:
            func = call.func
            builds = isinstance(func, ast.Name) and func.id == "Hold"
            builds = builds or (in_hold_class and isinstance(func, ast.Attribute)
                                and func.attr == "__init__" and isinstance(func.value, ast.Call)
                                and getattr(func.value.func, "id", None) == "super")
            if builds:
                found.append((call, function))
        return found

    def values(self, expr, function, depth: int = 0) -> tuple[set[str], list[str]]:
        """The strings `expr` can be, and the expressions that could not be read."""

        if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
            return {expr.value}, []
        if isinstance(expr, ast.IfExp):
            body, bad = self.values(expr.body, function, depth)
            other, worse = self.values(expr.orelse, function, depth)
            return body | other, bad + worse
        if isinstance(expr, ast.Name):
            params = _params(function)
            if expr.id in params and depth < MAX_FORWARDS:
                return self._forwarded(function, params.index(expr.id), expr.id, depth)
            if expr.id not in params and expr.id in self.constants:
                return {self.constants[expr.id]}, []
        return set(), [ast.unparse(expr)]

    def _forwarded(self, function, index: int, name: str, depth: int):
        """The values every call of `function` passes for its parameter `name`."""

        values, bad, callers = set(), [], 0
        for call, caller, _ in self.calls:
            func = call.func
            called = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if called != function.name:
                continue
            callers += 1
            argument = _argument(call, index, name)
            if argument is None:
                bad.append(f"{function.name}() called without {name}")
                continue
            found, unread = self.values(argument, caller, depth + 1)
            values |= found
            bad += unread
        if not callers:
            bad.append(f"{function.name}() forwards {name} but is never called")
        return values, bad


def _params(function) -> list[str]:
    if function is None:
        return []
    return [a.arg for a in function.args.posonlyargs + function.args.args + function.args.kwonlyargs]


def _argument(call: ast.Call, index: int, name: str):
    """The argument `call` passes in position `index` or as keyword `name`."""

    keyword = next((k.value for k in call.keywords if k.arg == name), None)
    if keyword is not None:
        return keyword
    return call.args[index] if index < len(call.args) else None


def core_holds() -> tuple[dict[str, set[str]], list[str]]:
    """Each gate the core can return, with the kinds it can give it, and
    every hold built with a gate or kind the check cannot read."""

    package = _Package()
    gates: dict[str, set[str]] = {}
    unreadable: list[str] = []
    for call, function in package.holds():
        gate = _argument(call, 0, "gate")
        kind = _argument(call, 1, "kind")
        if gate is None or kind is None:
            unreadable.append(ast.unparse(call)[:80])
            continue
        names, bad = package.values(gate, function)
        kinds, worse = package.values(kind, function)
        unreadable += bad + worse
        for name in names:
            gates.setdefault(name, set()).update(kinds)
    return gates, unreadable


def core_closeout_labels() -> tuple[set[str], list[str]]:
    """The labels the closeout's items open with, and any item text the
    check cannot read."""

    labels, unreadable = set(), []
    module = ast.parse((CORE / "actions.py").read_text(encoding="utf-8"))
    for node in ast.walk(module):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "_Item"):
            continue
        text = node.args[0] if node.args else None
        if isinstance(text, ast.JoinedStr) and text.values:
            text = text.values[0]
        found = (ITEM_LABEL.match(text.value) if isinstance(text, ast.Constant)
                 and isinstance(text.value, str) else None)
        if found:
            labels.add(found[1])
        else:
            unreadable.append(ast.unparse(node)[:80])
    return labels, unreadable


def scenario_kinds() -> dict[str, set[str]]:
    """The kinds the scenarios expect each gate to hold with."""

    kinds: dict[str, set[str]] = {}
    for document in scenario_files().values():
        for scenario in document["scenarios"]:
            for step in scenario["steps"]:
                for hold in step.get("expect", {}).get("holds", []):
                    kinds.setdefault(hold["gate"], set()).add(hold["kind"])
    return kinds


def scenario_clear_ways() -> dict[str, set[str]]:
    ways: dict[str, set[str]] = {}
    for document in scenario_files().values():
        for scenario in document["scenarios"]:
            for cover in scenario["covers"]:
                if cover["case"] == "clears":
                    ways.setdefault(cover["gate"], set()).add(cover.get("way", ""))
    return ways


class ContractCoversTheCoreTests(unittest.TestCase):
    def test_the_check_reads_every_hold_the_core_builds(self) -> None:
        gates, unreadable = core_holds()
        self.assertEqual(unreadable, [])
        # A floor, so a scan that finds nothing cannot pass.
        self.assertGreaterEqual(len(gates), 16)

    def test_every_gate_the_core_can_return_is_in_the_contract(self) -> None:
        gates, _ = core_holds()
        self.assertEqual(sorted(set(gates) - set(contract_gates())), [])

    def test_the_contract_names_no_gate_the_core_never_returns(self) -> None:
        gates, _ = core_holds()
        self.assertEqual(sorted(set(contract_gates()) - set(gates)), [])

    def test_each_gate_has_the_kind_the_core_gives_it(self) -> None:
        gates, _ = core_holds()
        observed = scenario_kinds()
        for gate, kind in contract_kinds().items():
            with self.subTest(gate):
                # The source allows it, and the scenarios, run against the
                # core, show it is the one the core gives.
                self.assertIn(kind, gates.get(gate, set()))
                self.assertEqual(observed.get(gate), {kind})

    def test_each_gate_clears_exactly_the_ways_its_scenarios_prove(self) -> None:
        proved = scenario_clear_ways()
        for gate, ways in contract_gates().items():
            with self.subTest(gate):
                self.assertEqual(proved.get(gate, set()), ways)

    def test_the_closeout_labels_are_the_contract_items(self) -> None:
        labels, unreadable = core_closeout_labels()
        self.assertEqual(unreadable, [])
        self.assertEqual(sorted(labels), sorted(contract_closeout_labels()))


if __name__ == "__main__":
    unittest.main()
