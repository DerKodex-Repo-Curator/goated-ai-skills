"""The session's friction count: main-agent holds declined or left unanswered.

The retrospective notice reads this count (Ticket 073). A hold is
- declined when a skip line naming one of its skills follows it, unless the
  hold is strict, which no skip line clears;
- answered when a load of a skill it names, a Read of a reference it names, or
  the line it asks for (a route line, a design-reads line) follows it;
- stood down when the next typed prompt's overrides cover it;
- unanswered when it is still open at the next typed prompt.
Declined and unanswered holds count; answered and stood-down ones do not. Each
gate counts once per turn, however often it holds again in that turn.

A hold's asks come from its text, as the skill-usage mod reads them: each bare
backticked name is a skill to load, each backticked `.md` path a reference to
read, and each `goated-skip: <skill>:` a skill whose skip line declines it.
Subagents keep no state, so only the main agent's holds count.
"""

from __future__ import annotations

import re

from .gates import ROUTER_SKILL, STRICT
from .transcript import Turn

# The count at which the retrospective notice is due, once per session.
RETROSPECTIVE_THRESHOLD = 3

_SKILL_RE = re.compile(r"`([a-z0-9]+(?:-[a-z0-9]+)*)`")
_REFERENCE_RE = re.compile(r"`([^`\s]+\.md)`")
_SKIPPABLE_RE = re.compile(r"goated-skip: ([a-z0-9]+(?:-[a-z0-9]+)*):")
# Gates a route line answers, and the gates `skip routing` stands down.
_ROUTE_GATES = frozenset({"route-line", "pipeline"})
_ROUTING_GATES = _ROUTE_GATES | {"router-first"}
_DESIGN_LINE_GATES = frozenset({"design"})
_COUNTED_TURN_PARTS = ("loads", "skips", "routes", "design_reads", "calls")


def record_hold(state, hold, turn: Turn) -> None:
    """Open `hold`, made in `turn` (already folded), for settling, unless its
    gate already held in that turn. Remembers how much of the turn came before
    it, so only what follows can answer or decline it."""

    if hold is None:
        return
    if state.held_gates.get("turn") != turn.key:
        state.held_gates = {"turn": turn.key, "gates": []}
    if hold.gate in state.held_gates["gates"]:
        return
    state.held_gates["gates"].append(hold.gate)
    text = hold.instruction
    state.open_holds.append({
        "gate": hold.gate,
        "turn": turn.key,
        "strict": hold.kind == STRICT,
        "skills": sorted(set(_SKILL_RE.findall(text))),
        "references": sorted({ref.lower() for ref in _REFERENCE_RE.findall(text)}),
        "skippable": sorted(set(_SKIPPABLE_RE.findall(text))),
        "seen": {part: len(getattr(turn, part)) for part in _COUNTED_TURN_PARTS},
    })


def settle(state, turns: list[Turn], skill_name) -> None:
    """Settle the open holds against `turns`, the turns just read, oldest first:
    drop each one answered, and count and drop each one declined.
    `skill_name` maps a raw loaded name to a GOATED skill, or None."""

    still_open = []
    for hold in state.open_holds:
        outcome = _outcome(hold, turns, skill_name)
        if outcome == "declined":
            state.friction += 1
        if outcome is None:
            still_open.append(hold)
    state.open_holds = still_open


def close_turn(state, overrides: dict) -> None:
    """At a typed prompt, count each hold still open as unanswered, unless the
    prompt's `overrides` (see `overrides.parse_overrides`) stand it down."""

    state.friction += sum(1 for hold in state.open_holds if not _stood_down(hold, overrides))
    state.open_holds = []


def claim_retrospective_notice(state) -> bool:
    """True once per session, when the friction count first reaches the threshold."""

    if state.retrospective_notice_shown or state.friction < RETROSPECTIVE_THRESHOLD:
        return False
    state.retrospective_notice_shown = True
    return True


def _outcome(hold: dict, turns: list[Turn], skill_name) -> str | None:
    """"answered", "declined", or None while nothing that follows the hold settles it."""

    declined = False
    for turn, seen in _after(hold, turns):
        loads = {skill_name(raw) for raw in turn.loads[seen["loads"]:]}
        read = [
            str(call.input.get("file_path") or "").replace("\\", "/").lower()
            for call in turn.calls[seen["calls"]:] if call.name == "Read" and call.ok
        ]
        if (
            loads & set(hold["skills"])
            or any(path.endswith(ref) for path in read for ref in hold["references"])
            or (hold["gate"] in _ROUTE_GATES and turn.routes[seen["routes"]:])
            or (hold["gate"] in _DESIGN_LINE_GATES and turn.design_reads[seen["design_reads"]:])
        ):
            return "answered"
        if not hold["strict"] and any(
            skip["skill"] in hold["skippable"] for skip in turn.skips[seen["skips"]:]
        ):
            declined = True
    return "declined" if declined else None


def _after(hold: dict, turns: list[Turn]):
    """Each turn of `turns` from the hold's own on, with how much of it to pass
    over: what came before the hold in its own turn, nothing in a later one.
    Reading starts at the last turn seen, which is never older than the hold's."""

    later = dict.fromkeys(_COUNTED_TURN_PARTS, 0)
    return [(turn, hold["seen"] if turn.key == hold["turn"] else later)
            for turn in turns[_own_turn_index(hold, turns):]]


def _own_turn_index(hold: dict, turns: list[Turn]) -> int:
    """The index of the hold's own turn in `turns`, or 0 when reading began after it."""

    return next((i for i, turn in enumerate(turns) if turn.key == hold["turn"]), 0)


def _stood_down(hold: dict, overrides: dict) -> bool:
    """Whether a typed override covers the hold, as the adapter's override
    table says: `skip routing` the routing gates, `skip <skill>` any hold
    naming that skill, and a typed commit message the commit hold."""

    if overrides.get("routing") and hold["gate"] in _ROUTING_GATES:
        return True
    if overrides.get("commit_message") and hold["gate"] == "commit":
        return True
    skipped = set(overrides.get("skills") or ())
    named = set(hold["skills"]) | set(hold["skippable"])
    if hold["gate"] == "router-first":
        named.add(ROUTER_SKILL)
    return bool(skipped & named)
