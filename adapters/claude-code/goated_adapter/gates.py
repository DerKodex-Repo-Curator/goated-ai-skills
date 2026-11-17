"""The routing gates, and the hold type and load naming every gate shares.

This module owns which tools the routing gates hold, which skill loads count,
and when a routing hold clears; `actions.py` owns the action and closeout
gates. The rules enforce contracts defined elsewhere, never new ones
(ADR 0003):

- router first: `using-goated-ai-skills` says to load it before the first edit
  or command of a task;
- route line: the router's output contract ends routing with a
  `goated-route:` line;
- pipeline: a route's `requires:` skills "must load before the first write".
  The shared policy says to drop a skill that does not apply by writing a
  corrected route line (the last one wins), so this hold is strict.
"""

from __future__ import annotations

from . import design_reads, shell
from .state import SessionState, Task
from .transcript import Turn

ROUTER_SKILL = "using-goated-ai-skills"

WRITE_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
# Spawning hands work to another agent or session, so it is held like a write.
SPAWN_TOOLS = frozenset(
    {"Agent", "Task", "mcp__ccd_session__start_session", "mcp__ccd_session__hand_off_to_session"}
)
COMMAND_TOOLS = frozenset({"Bash", "PowerShell"})
HELD_LIKE_WRITES = WRITE_TOOLS | SPAWN_TOOLS
GATED_TOOLS = HELD_LIKE_WRITES | COMMAND_TOOLS
# Subagent types Claude Code ships with no edit, write, or shell tool, so a
# spawn of one only delegates reads: `claude-code-guide` has Glob, Grep, Read,
# WebFetch, and WebSearch. The holds that guard writes and handed-off work
# (`pipeline`, and `spawn` in actions.py) do not apply to it; it still needs
# the router and a route line. `Explore` and `Plan` are not here: they keep
# Bash and PowerShell, and a subagent's own calls meet no routing gate. The
# name is trusted: a project or user agent file of the same name replaces the
# built-in. Names match exactly, so any other type, or none, is held as before.
READ_ONLY_SUBAGENTS = frozenset({"claude-code-guide"})

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


def unseen_line_advice(line: str, way_out: str) -> str:
    """Recovery advice for a hold that a route or skip line can clear.

    `line` names the line ("route line", "skip line"); `way_out` is the typed
    override that stands the hold down. A line in reply text may never be seen
    (README "Known Limits"), so the advice points to the fields of a tool call
    the adapter reads (`transcript.call_line_text`), then to the user's way
    out. It names those fields without backticks, since the skill-usage mod
    reads every backticked bare word in a hold as a skill.
    """

    return (
        f"A {line} in reply text may not be seen: Claude Code records a message only "
        "after this check, and can store the text of a message that makes a tool call "
        "as a summary that drops the line. A line in the description field of a shell "
        "or agent call, or in a Skill call's args, is read as written and counts from "
        f"that call on. Put the {line} on its own line there, in this call's description "
        "if it has one or else in a call made in an earlier message of this turn (a call "
        "in the same message is not seen yet), and make the call again. If that is held "
        f"again, tell the user they can type `{way_out}` in their prompt."
    )


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

    if turns and turns[0].opens_transcript:
        # Every turn of the session is in hand, so whether it has a task is
        # known again even if saved state was missing or reset.
        state.task_unknown = False
    for turn in turns:
        loads = [n for n in (goated_skill_name(raw, namespaces) for raw in turn.loads) if n]
        if ROUTER_SKILL in loads:
            state.router_loaded = True
        started = _task_started_in(turn)
        if started is not None:
            route, task_loads = started
            state.task = Task(
                route=route,
                started_turn=turn.key,
                loads=_unique(goated_skill_name(raw, namespaces) for raw in task_loads),
            )
            state.task_unknown = False
        elif turn.route is not None and state.task is None and not state.task_unknown:
            # Only `continue` lines, in a session with no task, such as one
            # started from another session: they start a task with no skills.
            state.task = Task(
                route={"form": "continue"}, started_turn=turn.key, loads=_unique(loads)
            )
        elif state.task is not None:
            state.task.loads = _unique([*state.task.loads, *loads])
        state.reference_reads = _unique(
            [*state.reference_reads, *design_reads.reads_in(turn.calls)]
        )
        state.last_turn = turn.key


def _task_started_in(turn: Turn) -> tuple[dict, list[str]] | None:
    """Return the route and raw loads of the task `turn` starts, or None.

    Every route line that is not `continue` starts a task, but lines with no
    write or spawn between them (see `_did_work`) are one task, corrected; the
    last line is its route. Its loads are the skill the prompt invoked plus
    this turn's loads since the previous task's last route line, or since the
    turn began. A `continue` line keeps whatever task the turn already started.
    """

    starts = [mark for mark in turn.route_marks if mark.route["form"] != "continue"]
    if not starts:
        return None
    first = 0  # Index in `starts` of the current task's first route line.
    for index in range(1, len(starts)):
        between = turn.calls[starts[index - 1].calls_before:starts[index].calls_before]
        if any(_did_work(call) for call in between):
            first = index
    since = starts[first - 1].loads_before if first else 0
    loads = turn.loads[since:]
    if turn.invoked_load:
        loads = [turn.invoked_load, *loads]
    return starts[-1].route, loads


def _did_work(call) -> bool:
    """True for a write or spawn that ran, so a later route line is a new task.

    A failed edit wrote nothing, but a shell command or spawn that ended in an
    error may still have written or handed off work. A call this adapter held
    never ran.
    """

    if call.held or not writes_like_an_edit(call.name, call.input):
        return False
    return call.ok or call.name not in WRITE_TOOLS


def writes_like_an_edit(tool_name: str, tool_input: dict) -> bool:
    """True for a write or spawn tool, or a shell command that writes files."""

    if tool_name in HELD_LIKE_WRITES:
        return True
    if tool_name in COMMAND_TOOLS:
        return shell.analyze(str(tool_input.get("command") or "")).writes
    return False


def spawns_a_reader(tool_name: str, tool_input: dict) -> bool:
    """True for a subagent spawn whose type is in `READ_ONLY_SUBAGENTS`.

    Side sessions are never readers: they run with every tool.
    """

    return tool_name in ("Agent", "Task") and tool_input.get("subagent_type") in READ_ONLY_SUBAGENTS


def check_routing(
    state: SessionState, tool_name: str, tool_input: dict, turn: Turn, overrides: dict
) -> Hold | None:
    """Return the first routing hold that applies to this main-agent call, if any.

    `turn` is the current turn, already folded into `state`. `overrides` are
    the ones the user typed for this turn (see `overrides.parse_overrides`).
    Commands meet only router-first unless they write files, and a command
    made only of plain reads (`shell.ShellCommand.read_only`) passes it too.
    A spawn of a read-only subagent type passes pipeline.
    """

    if tool_name not in GATED_TOOLS or overrides.get("routing"):
        return None
    user_skipped = set(overrides.get("skills") or ())
    if not state.router_loaded and ROUTER_SKILL not in user_skipped:
        if tool_name in COMMAND_TOOLS and shell.analyze(str(tool_input.get("command") or "")).read_only:
            return None
        return Hold(
            "router-first",
            STRICT,
            f"Load the `{ROUTER_SKILL}` skill with the Skill tool before the first "
            "write, spawn, or command of a task, and follow the route it selects. "
            "Reads stay free, and so does a shell command made only of read-only "
            "commands, such as cat, grep, ls, or git diff, with no redirect into a "
            "file. If that skill is not installed, tell the user: they "
            "can type `skip routing` in their prompt to proceed without it.",
        )
    if not writes_like_an_edit(tool_name, tool_input):
        return None
    if turn.route is None:
        return Hold("route-line", STRICT, _route_line_instruction(turn))
    if turn.route["form"] == "continue" and state.task is None:
        # Only when saved state was missing or reset: otherwise folding the
        # turn started a task.
        return Hold(
            "route-line",
            STRICT,
            "`goated-route: continue` was written, but the adapter's saved state for "
            "this session was missing or reset, so it cannot tell which task "
            "continues. Write the route line the router selects for this task.",
        )
    task = state.task
    if task is None or task.route["form"] != "route":
        return None  # `direct` exempts the task.
    if spawns_a_reader(tool_name, tool_input):
        return None
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
        "Load each with the Skill tool and follow it. A load earlier in this turn "
        "counts unless another task's route line came after it; route lines with "
        "no write or spawn between them are one task, corrected. A load in an "
        "earlier turn does not count, so load it again. If one does not apply, "
        "write a corrected route line without it; the last route line wins. "
        + unseen_line_advice("route line", "skip routing"),
    )


def _route_line_instruction(turn: Turn) -> str:
    text = (
        "Before the first write or spawn after a user prompt, end routing with a "
        "route line on its own line, as the router's output contract defines: "
        "`goated-route: direct`, `goated-route: <intensity> | requires: <skills>`, "
        "or `goated-route: continue` when this prompt continues the current task "
        "or, in a session with no task yet, work begun elsewhere. "
        + unseen_line_advice("route line", "skip routing")
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
