"""The enforcement contract names every gate and closeout item the Claude Code
adapter can return (Ticket 079, spec AC2).

The adapter's gates are read from its source: the first argument of every
`Hold(...)` it builds, of `_change_read_hold(...)`, which builds one for the
gate it is given, and of a `Hold` subclass's `super().__init__(...)`, as a
literal or a module constant. A gate named any other way fails the check, so
a new gate cannot slip past it. The closeout's labels are read from the item
texts, which open `- <Label>: `.
"""

from __future__ import annotations

import ast
import re
import unittest

from enforcement_support import CONTRACT, REPO_ROOT, contract_gates

ADAPTER = REPO_ROOT / "adapters" / "claude-code" / "goated_adapter"
HOLD_BUILDERS = frozenset({"Hold", "_change_read_hold"})
ITEM_LABEL = re.compile(r"^- ([A-Z][a-z]+): ")


def _modules() -> list[ast.Module]:
    return [ast.parse(path.read_text(encoding="utf-8")) for path in sorted(ADAPTER.glob("*.py"))]


def _constants(modules: list[ast.Module]) -> dict[str, str]:
    """Module-level `NAME = "text"` assignments, across the package."""

    found = {}
    for module in modules:
        for node in module.body:
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
                found[node.targets[0].id] = node.value.value
    return found


def _gate_arguments(modules: list[ast.Module]) -> list[tuple[ast.expr, set[str]]]:
    """The first argument of each call that builds a hold, with the
    parameter names of the function it sits in."""

    found = []

    def visit(node: ast.AST, params: set[str], in_hold_class: bool) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = {a.arg for a in node.args.args + node.args.kwonlyargs}
        elif isinstance(node, ast.ClassDef):
            in_hold_class = any(isinstance(b, ast.Name) and b.id == "Hold" for b in node.bases)
        elif isinstance(node, ast.Call) and node.args:
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            super_init = (name == "__init__" and in_hold_class and isinstance(func, ast.Attribute)
                          and isinstance(func.value, ast.Call)
                          and getattr(func.value.func, "id", None) == "super")
            if name in HOLD_BUILDERS or super_init:
                found.append((node.args[0], params))
        for child in ast.iter_child_nodes(node):
            visit(child, params, in_hold_class)

    for module in modules:
        visit(module, set(), False)
    return found


def adapter_gates() -> tuple[set[str], list[str]]:
    """The gates the adapter can return, and any hold built with a gate the
    check cannot read."""

    modules = _modules()
    constants = _constants(modules)
    gates, unreadable = set(), []
    for argument, params in _gate_arguments(modules):
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
            gates.add(argument.value)
        elif isinstance(argument, ast.Name) and argument.id in constants:
            gates.add(constants[argument.id])
        elif not (isinstance(argument, ast.Name) and argument.id in params):
            # A parameter is forwarded: its callers are checked where they pass it.
            unreadable.append(ast.unparse(argument))
    return gates, unreadable


def adapter_closeout_labels() -> set[str]:
    labels = set()
    for node in ast.walk(ast.parse((ADAPTER / "actions.py").read_text(encoding="utf-8"))):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found = ITEM_LABEL.match(node.value)
            if found:
                labels.add(found[1])
    return labels


def contract_closeout_labels() -> set[str]:
    section = CONTRACT.read_text(encoding="utf-8").split("\n## Closeout Items\n", 1)[1]
    section = section.split("\n## ", 1)[0]
    return set(re.findall(r"^\| `([A-Z][a-z]+)` \|", section, re.M))


class ContractCoversTheAdapterTests(unittest.TestCase):
    def test_the_check_reads_every_gate_the_adapter_builds(self) -> None:
        gates, unreadable = adapter_gates()
        self.assertEqual(unreadable, [])
        # A floor, so a scan that finds nothing cannot pass.
        self.assertGreaterEqual(len(gates), 16)

    def test_every_gate_the_adapter_can_return_is_in_the_contract(self) -> None:
        gates, _ = adapter_gates()
        self.assertEqual(sorted(gates - set(contract_gates())), [])

    def test_the_contract_names_no_gate_the_adapter_never_returns(self) -> None:
        gates, _ = adapter_gates()
        self.assertEqual(sorted(set(contract_gates()) - gates), [])

    def test_every_closeout_label_the_adapter_shows_is_in_the_contract(self) -> None:
        labels = adapter_closeout_labels()
        self.assertGreaterEqual(len(labels), 8)
        self.assertEqual(sorted(labels - contract_closeout_labels()), [])
        self.assertEqual(sorted(contract_closeout_labels() - labels), [])


if __name__ == "__main__":
    unittest.main()
