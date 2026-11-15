"""The adapter's rule table and its routing-gate decisions.

This module owns which tools each gate holds and when a hold clears. The
rules enforce contracts defined elsewhere, never new ones (ADR 0003):

- router first: `using-goated-ai-skills` says to load it before the first edit
  or command of a task;
- route line: the router's output contract ends routing with a
  `goated-route:` line;
- pipeline: a route's `requires:` skills "must load before the first write",
  and the shared policy says to write `goated-skip: <skill>: <reason>` when a
  route names a skill that does not apply.
"""

from __future__ import annotations

from .state import SessionState, Task
from .transcript import Turn

ROUTER_SKILL = "using-goated-ai-skills"

WRITE_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
COMMAND_TOOLS = frozenset({"Bash", "PowerShell"})
GATED_TOOLS = WRITE_TOOLS | COMMAND_TOOLS

STRICT = "strict"
JUSTIFIED_SKIP = "justified-skip"


class Hold:
    """A held tool call: which gate, what kind, and what the agent must do."""

    __slots__ = ("gate", "kind", "instruction")

    def __init__(self, gate: str, kind: str, instruction: str) -> None:
        self.gate = gate
        self.kind = kind
        self.instruction = instruction

    def message(self) -> str:
        """The hold text shown to the agent; its first line is machine-readable."""

        return f"goated-hold: {self.gate} | {self.kind}\n{self.instruction}"


def fold_turns(state: SessionState, turns: list[Turn]) -> None:
    """Bring `state` up to date with turns read from the transcript, oldest first.

    Re-folding a turn already seen is harmless, so callers pass the last seen
    turn again to pick up anything written after they last looked.
    """

    for turn in turns:
        if ROUTER_SKILL in turn.loads:
            state.router_loaded = True
        route = turn.route
        if route is not None and route["form"] != "continue":
            # A new route starts a new task; proof from earlier tasks is dropped.
            state.task = Task(route=route, started_turn=turn.key)
        task = state.task
        if task is not None:
            for skill in turn.loads:
                if skill not in task.loads:
                    task.loads.append(skill)
            for skip in turn.skips:
                task.skips[skip["skill"]] = skip["reason"]
        state.last_turn = turn.key


def check_routing(state: SessionState, tool_name: str, turn: Turn, overrides: dict) -> Hold | None:
    """Return the first routing hold that applies to this main-agent call, if any.

    `turn` is the current turn, already folded into `state`. `overrides` are
    the ones the user typed for this turn (see `overrides.parse_overrides`).
    """

    if tool_name not in GATED_TOOLS or overrides.get("routing"):
        return None
    user_skipped = set(overrides.get("skills") or ())
    if not state.router_loaded and ROUTER_SKILL not in user_skipped:
        return Hold(
            "router-first",
            STRICT,
            f"Load the `{ROUTER_SKILL}` skill with the Skill tool before the first "
            "write or command of a task, and follow the route it selects. Reads stay free.",
        )
    if tool_name not in WRITE_TOOLS:
        return None
    if turn.route is None:
        return Hold("route-line", STRICT, _route_line_instruction(turn))
    if turn.route["form"] == "continue" and state.task is None:
        return Hold(
            "route-line",
            STRICT,
            "`goated-route: continue` was written, but this session has no current "
            "task to continue. Write the route line the router selects for this task.",
        )
    task = state.task
    if task is None or task.route["form"] != "route":
        return None  # `direct` exempts the task.
    missing = [
        skill
        for skill in task.route["requires"]
        if skill not in task.loads and skill not in task.skips and skill not in user_skipped
    ]
    if not missing:
        return None
    names = ", ".join(f"`{skill}`" for skill in missing)
    return Hold(
        "pipeline",
        JUSTIFIED_SKIP,
        f"The current route requires {names} before the first write. Load each "
        "with the Skill tool and follow it. If one does not apply to this action, "
        "write `goated-skip: <skill>: <reason>` on its own line with an "
        "action-specific reason instead.",
    )


def _route_line_instruction(turn: Turn) -> str:
    text = (
        "Before the first write after a user prompt, end routing with a route line "
        "on its own line, as the router's output contract defines: "
        "`goated-route: direct`, `goated-route: <intensity> | requires: <skills>`, "
        "or `goated-route: continue` when this prompt continues the current task."
    )
    if turn.malformed:
        quoted = "; ".join(f"`{line}`" for line in turn.malformed)
        text += f" These lines in this turn do not match the grammar: {quoted}."
    return text
