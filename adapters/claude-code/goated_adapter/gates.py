"""The adapter's rule table and its routing-gate decisions.

This module owns which tools each gate holds, which skill loads count, and
when a hold clears. The rules enforce contracts defined elsewhere, never new
ones (ADR 0003):

- router first: `using-goated-ai-skills` says to load it before the first edit
  or command of a task;
- route line: the router's output contract ends routing with a
  `goated-route:` line;
- pipeline: a route's `requires:` skills "must load before the first write".
  The shared policy says to drop a skill that does not apply by writing a
  corrected route line (the last one wins), so this hold is strict.
"""

from __future__ import annotations

from .state import SessionState, Task
from .transcript import Turn

ROUTER_SKILL = "using-goated-ai-skills"

WRITE_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
# Spawning hands work to another agent or session, so it is held like a write.
SPAWN_TOOLS = frozenset(
    {"Agent", "mcp__ccd_session__start_session", "mcp__ccd_session__hand_off_to_session"}
)
COMMAND_TOOLS = frozenset({"Bash", "PowerShell"})
HELD_LIKE_WRITES = WRITE_TOOLS | SPAWN_TOOLS
GATED_TOOLS = HELD_LIKE_WRITES | COMMAND_TOOLS

STRICT = "strict"


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


def goated_skill_name(raw: str, namespaces: tuple[str, ...]) -> str | None:
    """Return the GOATED skill a loaded name refers to, or None for another skill.

    A bare name counts; `ns:name` counts only when `ns` is a configured GOATED
    namespace, so another plugin's `tdd` never satisfies `requires: tdd`.
    """

    namespace, _, name = raw.rpartition(":")
    if not namespace:
        return name or None
    return name if namespace in namespaces else None


def fold_turns(
    state: SessionState, turns: list[Turn], namespaces: tuple[str, ...] = ()
) -> None:
    """Bring `state` up to date with turns read from the transcript, oldest first.

    Re-folding a turn already seen is harmless, so callers pass the last seen
    turn again to pick up anything written after they last looked.
    """

    for turn in turns:
        loads = [n for n in (goated_skill_name(raw, namespaces) for raw in turn.loads) if n]
        if ROUTER_SKILL in loads:
            state.router_loaded = True
        route = turn.route
        if route is not None and route["form"] != "continue":
            # A new route starts a new task. Only loads after its route line
            # (or a skill the prompt invoked) count; earlier proof is dropped.
            task_loads = [goated_skill_name(raw, namespaces) for raw in turn.task_loads]
            state.task = Task(route=route, started_turn=turn.key, loads=_unique(task_loads))
        elif state.task is not None:
            state.task.loads = _unique([*state.task.loads, *loads])
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
            "write, spawn, or command of a task, and follow the route it selects. "
            "Reads stay free. If that skill is not installed, tell the user: they "
            "can type `skip routing` in their prompt to proceed without it.",
        )
    if tool_name not in HELD_LIKE_WRITES:
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
        if skill not in task.loads and skill not in user_skipped
    ]
    if not missing:
        return None
    names = ", ".join(f"`{skill}`" for skill in missing)
    return Hold(
        "pipeline",
        STRICT,
        f"The current route requires {names} before the first write or spawn. "
        "Load each with the Skill tool and follow it; only loads after the route "
        "line that started this task count, so load again if you loaded it "
        "earlier. If one does not apply, write a corrected route line without "
        "it; the last route line wins.",
    )


def _route_line_instruction(turn: Turn) -> str:
    text = (
        "Before the first write or spawn after a user prompt, end routing with a "
        "route line on its own line, as the router's output contract defines: "
        "`goated-route: direct`, `goated-route: <intensity> | requires: <skills>`, "
        "or `goated-route: continue` when this prompt continues the current task."
    )
    if turn.malformed:
        quoted = "; ".join(f"`{line}`" for line in turn.malformed)
        text += f" These lines in this turn do not match the grammar: {quoted}."
    return text


def _unique(names) -> list[str]:
    seen: list[str] = []
    for name in names:
        if name and name not in seen:
            seen.append(name)
    return seen
