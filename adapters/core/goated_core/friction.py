"""The session's friction count: main-agent holds declined or left unanswered.

The retrospective notice reads this count (Ticket 073). A hold is
- declined when a skip line naming one of its skills follows it, unless the
  hold is strict, which no skip line clears;
- answered when the same gate later lets the same action through, or when
  every skill it names is loaded and every reference it names is read. A
  `scripted-edit` hold, which asks for a file edit tool, is also answered by
  a later write tool call that goes through to a file its script named, or
  to any file when the script named one only at run time. A
  closeout hold, on a `Stop` or a commit, is answered by any later `Stop` or
  commit the closeout gate lets through;
- stood down when the next typed prompt's overrides cover it;
- unanswered when it is still open at the next typed prompt.
Declined and unanswered holds count; answered and stood-down ones do not. Each
gate counts once per turn, however often it holds again in that turn; its open
hold follows the latest action the gate held.

A hold's asks come from its text, as the contract's Hold Text reads them: each bare
backticked name is a skill to load, each backticked `.md` path a reference to
read, and each `goated-skip: <skill>:` a skill whose skip line declines it.
Subagents keep no state, so only the main agent's holds count.
"""

from __future__ import annotations

import re

from . import events, shell
from .events import Call, Turn
from .gates import ROUTER_SKILL, STRICT

# The count at which the retrospective notice is due, once per session.
RETROSPECTIVE_THRESHOLD = 3
# The action of a `Stop`, as `observe` takes it.
STOP = "stop"

_SKILL_RE = re.compile(r"`([a-z0-9]+(?:-[a-z0-9]+)*)`")
_REFERENCE_RE = re.compile(r"`([^`\s]+\.md)`")
_SKIPPABLE_RE = re.compile(r"goated-skip: ([a-z0-9]+(?:-[a-z0-9]+)*):")
# The gates `skip routing` stands down.
_ROUTING_GATES = frozenset({"router-first", "route-line", "pipeline"})
_CLOSEOUT_GATE = "closeout"
_SCRIPTED_EDIT_GATE = "scripted-edit"
_ANY_FILE = "*"
_COMMIT = "commit"
_COUNTED_TURN_PARTS = ("loads", "skips", "calls")


def action_of(call: Call) -> str:
    """The action a gated call takes, as a later call repeating it would: the
    file a write or read names, a commit or pull request whatever its
    message, the command, or else the harness's own key for the call
    (`Call.action`), or its kind."""

    if call.kind in (events.FILE_WRITE, events.FILE_READ) and call.path:
        return "file:" + call.path.replace("\\", "/").lower()
    if call.kind == events.SHELL_COMMAND:
        found = shell.analyze(call.command, call.shell)
        if found.commit:
            return _COMMIT
        if found.opens_pr:
            return "pull-request"
        return "command:" + call.command.strip()
    return call.action or "call:" + call.kind


def observe(state, turn: Turn, action: str, holds: list) -> None:
    """Take one judged action of `turn` (already folded): `holds` are what
    held it, each as if shown alone (Ticket 095), or [] when it went through.
    Each open hold whose gate let the action through is answered; then each
    of `holds` opens for settling, unless its gate already held in the turn,
    whose open hold then follows this action."""

    held_gates = {hold.gate for hold in holds}
    state.open_holds = [
        h for h in state.open_holds
        if not ((_repeats(h, action) and h["gate"] not in held_gates)
                or (not holds and _rewrites(h, action)))
    ]
    for hold in holds:
        _open(state, turn, action, hold)


def _open(state, turn: Turn, action: str, hold) -> None:
    """Open `hold` for settling, or move its gate's open hold in the turn to `action`."""

    if state.held_gates.get("turn") != turn.key:
        state.held_gates = {"turn": turn.key, "gates": []}
    if hold.gate in state.held_gates["gates"]:
        for open_hold in state.open_holds:
            if open_hold["gate"] == hold.gate and open_hold["turn"] == turn.key:
                open_hold["action"] = action
        return
    state.held_gates["gates"].append(hold.gate)
    text = hold.instruction
    state.open_holds.append({
        "gate": hold.gate,
        "turn": turn.key,
        "action": action,
        "strict": hold.kind == STRICT,
        "skills": sorted(set(_SKILL_RE.findall(text))),
        "references": sorted({ref.lower() for ref in _REFERENCE_RE.findall(text)}),
        "skippable": sorted(set(_SKIPPABLE_RE.findall(text))),
        "seen": {part: len(getattr(turn, part)) for part in _COUNTED_TURN_PARTS},
    })


def settle(state, turns: list[Turn], skill_name) -> None:
    """Settle the open holds against `turns`, the turns just read, oldest first:
    drop each one whose every ask is met, and count and drop each one declined.
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


def forget_open(state) -> None:
    """Drop the open holds uncounted: at a compaction or `/clear`, reading
    restarts after the boundary, so what answered them can no longer be seen."""

    state.open_holds = []


def claim_retrospective_notice(state) -> bool:
    """True once per session, when the friction count first reaches the threshold."""

    if state.retrospective_notice_shown or state.friction < RETROSPECTIVE_THRESHOLD:
        return False
    state.retrospective_notice_shown = True
    return True


def _repeats(hold: dict, action: str) -> bool:
    """Whether `action` is the one `hold` held, so its gate passing it answers the
    hold. A closeout's `Stop` and commit are one action: either passing answers it."""

    if hold["gate"] == _CLOSEOUT_GATE:
        return action in (STOP, _COMMIT)
    return hold.get("action") == action


def _script_files(action: str) -> list[str]:
    """The files the inline script of a held command writes, in comparable
    form, or `_ANY_FILE` when it names one only at run time. The action keeps
    the command but not its shell, so both readings count."""

    command = action.partition(":")[2]
    found = [shell.analyze(command, kind) for kind in (events.POSIX, events.POWERSHELL)]
    if any(f.script_unknown_writes for f in found):
        return [_ANY_FILE]
    return sorted({_comparable(t) for f in found for t in f.script_targets})


def _rewrites(hold: dict, action: str) -> bool:
    """Whether `action`, a write tool's file, is one the script of a held
    `scripted-edit` command named; the hold keeps the command as its action."""

    if hold["gate"] != _SCRIPTED_EDIT_GATE or not action.startswith("file:"):
        return False
    files = _script_files(hold["action"])
    path = action.partition(":")[2]
    return _ANY_FILE in files or any(path == f or path.endswith("/" + f) for f in files)


def _comparable(path: str) -> str:
    path = path.replace("\\", "/").lower()
    return path[2:] if path.startswith("./") else path


def _outcome(hold: dict, turns: list[Turn], skill_name) -> str | None:
    """"answered" when every ask is met, "declined", or None while nothing that
    follows the hold settles it. A hold with no skill or reference to ask is
    answered only by its gate letting the action through (`observe`)."""

    loaded: set = set()
    read: list[str] = []
    declined = False
    for turn, seen in _after(hold, turns):
        loaded |= {skill_name(raw) for raw in turn.loads[seen["loads"]:]}
        # Only a whole read answers a hold's reference, as the gates judge it (Ticket 092).
        read += [
            path.replace("\\", "/").lower()
            for call in turn.calls[seen["calls"]:] if (path := call.whole_read_path())
        ]
        if not hold["strict"] and any(
            skip["skill"] in hold["skippable"] for skip in turn.skips[seen["skips"]:]
        ):
            declined = True
    asks = hold["skills"] or hold["references"]
    if asks and set(hold["skills"]) <= loaded and all(
        any(path.endswith(ref) for path in read) for ref in hold["references"]
    ):
        return "answered"
    return "declined" if declined else None


def _after(hold: dict, turns: list[Turn]):
    """Each turn of `turns` from the hold's own on, with how much of it to pass
    over: what came before the hold in its own turn, nothing in a later one.
    Reading starts at the last turn seen, which is never older than the hold's."""

    later = dict.fromkeys(_COUNTED_TURN_PARTS, 0)
    start = next((i for i, turn in enumerate(turns) if turn.key == hold["turn"]), 0)
    return [(turn, hold["seen"] if turn.key == hold["turn"] else later) for turn in turns[start:]]


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
