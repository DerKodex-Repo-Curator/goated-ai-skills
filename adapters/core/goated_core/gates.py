"""The routing gates, and the hold type, hold message, shared hold texts and
load naming every gate shares.

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
  corrected route line (the last one wins), so this hold is strict. A load
  counts from its call until the next compaction (spec R3), when its text
  leaves the context. In a session routed by its brief, the router's
  orientation skill, when installed, joins a `standard` or `full` route;
  whole reads of `ORIENTATION_READS` distinct files meet it as well as its
  load does (spec R3), since targeted reading is that skill's own work.

The routing gates judge file writes, shell commands, and spawns. A spawn
that only proposes work (`starts_now` false) runs nothing, so it passes
them all; a spawn of a read-only agent only delegates reads, so it passes
`pipeline` (and the `spawn` gate in actions.py) but still needs the router
and a route line.

A write whose every file is scratch, outside the project and any other checkout
(`actions.writes_only_scratch`), meets none of these holds (spec R4): routing
guards the project's work, not a scratch copy.
"""

from __future__ import annotations

import hashlib
import os
from typing import Callable, NamedTuple

from . import contracts, design_reads, events, reference_reads, shell, wording
from .events import Call, Turn
from .state import SessionState, Task
from .wording import NO_RANGE, READ, SKILL_TOOL, short_advice, unseen_line_advice

ROUTER_SKILL = "using-goated-ai-skills"
ORIENTATION_SKILL = "session-start-progressive-disclosure"
# How many distinct files a briefed session reads to orient without the skill.
ORIENTATION_READS = 3
# The call kinds the routing gates judge.
ROUTED_KINDS = frozenset({events.FILE_WRITE, events.SHELL_COMMAND, events.SPAWN})

STRICT = "strict"


class Hold:
    """A held tool call: which gate, what kind, and what the agent must do.

    `short` says the same in brief (`short_form`), for a later hold in the
    turn that asks the same (`text`). None when the full text is already as
    short.
    """

    __slots__ = ("gate", "kind", "instruction", "short")

    def __init__(self, gate: str, kind: str, instruction: str,
                 short: "ShortForm | None" = None) -> None:
        self.gate = gate
        self.kind = kind
        self.instruction = instruction
        self.short = short

    def text(self, claim: Callable[[str], bool]) -> str:
        """The text this hold shows: its short form once the turn has shown
        the same ask in full, else the full text. `claim` is as `shown_holds`
        takes it; the purpose is the gate and what is unmet (`ask_purpose`),
        so a gate's new ask, such as a change read after a load, comes in full."""

        if self.short and not claim(ask_purpose(self.gate, self.short.unmet)):
            return self.short.text
        return self.instruction


def ask_purpose(gate: str, ask: str) -> str:
    """The turn marker's purpose for one ask of `gate`, named by `ask`."""

    return f"{gate}-{hashlib.sha256(ask.encode('utf-8')).hexdigest()[:16]}"


class ShortForm(NamedTuple):
    """A hold's short form: `unmet`, what is still missing, which names the
    ask, and `text`, the whole short form, which also says every constraint
    needed to clear it and keeps each skill, reference and skip line the
    full text names."""

    unmet: str
    text: str


def short_form(unmet: str, clear: str) -> ShortForm:
    """The short form for `unmet` and `clear`, how to clear it, ending in a full stop."""

    return ShortForm(unmet, f"Still unmet: {unmet}. {clear}")


# The turn marker's purpose for the unseen-line advice; a hold's ask has its
# own purpose (`ask_purpose`).
ADVICE = "advice"

# Paragraphs several holds or closeout items share (Ticket 095). How a hold
# asks for a change read; no command is backticked, since a reader of hold
# texts takes a backticked name as a skill to load (contract, Hold Text).
CHANGE_READ = (
    f"print its diff with a git diff or git show command, or {READ} a file you changed; "
    "a listing of names or counts, such as --stat or --name-only, does not count"
)
CHAINED_STEPS = "The whole command was held, so rerun any steps chained before it too."
UNFINISHED_READ = ("A read chained in the same command, or made in parallel with this call, "
                   "has not finished, so it does not count.")
SKIP_LINE_RULE = "A skip line must name the skill and give a reason of three or more words."
# Each shared paragraph, with what its later copies in one message become.
_SHARED_TEXTS = (
    (CHANGE_READ, f"print the diff or {READ} a file you changed, as above"),
    (CHAINED_STEPS + " ", ""),
    (CHAINED_STEPS, ""),
    (UNFINISHED_READ + " ", ""),
    (SKIP_LINE_RULE, ""),
)


def _once(texts: list[str], full: str, again: str) -> list[str]:
    """`texts`, read in order as one text, with every copy of `full` after
    the first replaced by `again`. No copy spans two texts: no shared
    paragraph holds a hold line or the blank line between holds."""

    kept, seen = [], False
    for text in texts:
        if not seen and (first := text.find(full)) >= 0:
            seen, end = True, first + len(full)
            text = text[:end] + text[end:].replace(full, again)
        elif seen:
            text = text.replace(full, again)
        kept.append(text)
    return kept


class Shown(NamedTuple):
    """One hold as a decision shows it: its gate, its kind, and the text that
    follows its `goated-hold:` line, harness wording still in `wording` slots."""

    gate: str
    kind: str
    text: str

    def line(self) -> str:
        """The hold line, as the contract's Hold Messages section defines it."""

        return f"goated-hold: {self.gate} | {self.kind}"


def message(shown: list[Shown]) -> str:
    """The one message that carries `shown`, as `shown_holds` gives them:
    each hold's line and text, with a blank line between holds."""

    return "\n\n".join(f"{hold.line()}\n{hold.text}" for hold in shown)


def shown_holds(holds: list[Hold], claim: Callable[[str], bool], call: bool = False) -> list[Shown]:
    """How `holds`, every hold one call or turn end meets, in the order the
    gates fire, are shown in one message (Ticket 095): each with its own text,
    whose harness wording is still in `wording` slots.

    `claim(purpose)` claims the turn's marker for `purpose` and returns True
    only for its first claim in the turn, so calls held in parallel, which
    see no result of each other, still share one full text. It must return
    True when it cannot claim, so the full text is then given. Each hold
    chooses its full or short text (`Hold.text`): an ask's first hold in the
    turn is full, its later ones short. The
    unseen-line advice (purpose `ADVICE`) is given in full on one hold per
    turn; every other hold that carries it gets one sentence that keeps its
    typed override. Every other shared paragraph is given once per message:
    in the first hold that holds it, its later copies shortened.

    `call`: the holds are a call's. When a hold a line can clear holds it,
    the last hold's text ends with the carrier slot, where the harness names
    a call that can carry the line if this call has no field for one.
    """

    advice_given = line_clears = False
    texts = []
    for hold in holds:
        line_clears = line_clears or _full_advice(hold.instruction) is not None
        text = hold.text(claim)
        found = _full_advice(text)
        if found is not None:
            if advice_given or not claim(ADVICE):
                short = short_advice(found[2], found[3])
                text = text[:found.start()] + short + text[found.end():]
            advice_given = True
        texts.append(text)
    for full, again in _SHARED_TEXTS:
        texts = _once(texts, full, again)
    if line_clears and call and texts:
        texts[-1] += f"\n{wording.CARRIER}"
    return [Shown(hold.gate, hold.kind, text) for hold, text in zip(holds, texts)]


def _full_advice(text: str):
    """The first full unseen-line advice slot in `text`, as a match, or None."""

    return next((found for found in wording.ADVICE_RE.finditer(text)
                 if found[1] == wording.FULL_ADVICE), None)


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

    if turns and turns[0].opens_session:
        # Every turn of the session is in hand, so whether it has a task is
        # known again even if saved state was missing or reset.
        state.task_unknown = False
    for turn in turns:
        if turn.is_compaction:
            # The compaction's `SessionStart` clears these too, but that reset
            # may never have landed (a hook that failed open, a refused save,
            # an adapter installed mid-session), so the boundary itself does.
            state.forget_context(turn.key)
        loads = [n for n in (goated_skill_name(raw, namespaces) for raw in turn.loads) if n]
        if ROUTER_SKILL in loads:
            state.router_loaded = True
        if turn.brief_route is not None:
            # The session that started this one routed the brief's work, as a
            # subagent's parent does; its required skills must still load here.
            # A prompt a person types is new work, so the exemption ends there.
            state.brief_routed = True
            state.briefed = True
        elif turn.typed:
            state.brief_routed = False
        route = _task_route_in(turn)
        if route is not None:
            state.task = Task(route=route, started_turn=turn.key)
            state.task_unknown = False
            state.end_lasting_skips(turn.key)  # A new task ends them (spec R4).
        elif turn.route is not None and state.task is None and not state.task_unknown:
            # Only `continue` lines, in a session with no task, such as one
            # started from another session: they start a task with no skills.
            state.task = Task(route={"form": "continue"}, started_turn=turn.key)
        state.loads = _unique([*state.loads, *loads])
        state.reference_reads = _unique(
            [*state.reference_reads, *design_reads.reads_in(turn.calls)]
        )
        state.skill_reference_reads = _unique(
            [*state.skill_reference_reads, *reference_reads.reads_in(turn.calls)]
        )
        state.template_reads = _unique(
            [*state.template_reads, *contracts.templates_read(turn.calls)]
        )
        state.files_read = _unique([*state.files_read, *_files_read(turn.calls)])[:ORIENTATION_READS]
        state.shell = last_shell([turn]) or state.shell
        state.last_turn = turn.key


def last_shell(turns: list[Turn]) -> str | None:
    """The shell (`events.POSIX` or `events.POWERSHELL`) of the last shell
    command in `turns`, oldest first, or None when they hold none."""

    return next((call.shell for turn in reversed(turns) for call in reversed(turn.calls)
                 if call.kind == events.SHELL_COMMAND), None)


def _files_read(calls) -> list[str]:
    """A digest of each file a finished file read among `calls` read whole, in
    order. Partial reads never count, as for every read a hold asks for.

    Two spellings of one path (case and separators on Windows) give one digest.
    """

    return [
        hashlib.sha256(os.path.normcase(os.path.normpath(path)).encode("utf-8")).hexdigest()[:16]
        for call in calls
        if (path := call.whole_read_path())
    ]


def _task_route_in(turn: Turn) -> dict | None:
    """Return the route of the task `turn` starts, or None.

    Every route line that is not `continue` starts a task; the last one is its
    route. A `continue` line keeps whatever task the turn already started.
    """

    return next((route for route in reversed(turn.routes) if route["form"] != "continue"), None)


def _turn_route(state: SessionState, turn: Turn) -> dict | None:
    """The route `turn` runs under, or None when it needs a route line.

    That is the turn's winning route line; failing one, a message from
    another session in a session with a task runs as `goated-route: continue`
    (spec R5): nobody typed it, so it is not a new task the router must
    judge. Only the route carries over; overrides come only from a person's
    prompt, and skips, checks and change reads count within their turn. A
    route-like line that fails the grammar meant to route the turn, so it
    still needs a valid one and the hold quotes the bad line.
    """

    if turn.route is not None:
        return turn.route
    opener = turn.opener
    if (not turn.malformed and isinstance(opener, events.Prompt)
            and opener.author == events.SESSION
            and not opener.starts_session and state.task is not None):
        return {"form": "continue"}
    return None


def writes_like_an_edit(call: Call) -> bool:
    """True for a file write, a spawn that starts work now, or a shell command
    that writes files. A spawn that only proposes work runs nothing."""

    if call.kind == events.FILE_WRITE:
        return True
    if call.kind == events.SPAWN:
        return call.starts_now
    if call.kind == events.SHELL_COMMAND:
        return shell.analyze(call.command, call.shell).writes
    return False


def check_routing(
    state: SessionState,
    call: Call,
    turn: Turn,
    overrides: dict,
    orientation_installed: Callable[[], bool],
    writes_scratch: Callable[[], bool],
) -> list[Hold]:
    """Return the routing holds that apply to this main-agent call, in order.

    `router-first` and `route-line` are judged together (Ticket 095); only
    `pipeline` waits for the route, so it is judged once the router counts
    as loaded and the turn has a route line. `turn` is the current turn,
    already folded into `state`. `overrides` are the ones the user typed for
    this turn (see `overrides.parse_overrides`).
    Commands meet only router-first unless they write files, and a command
    made only of plain reads (`shell.ShellCommand.read_only`) passes it too.
    A spawn of a read-only agent passes pipeline, and a spawn that only
    proposes work passes every routing gate. `orientation_installed` says
    whether the orientation skill is installed; it is asked only when a
    briefed route would require that skill (`_brief_orientation`).
    `writes_scratch` says whether the call is a write whose every file is
    scratch (`actions.writes_only_scratch`); such a write passes every routing gate,
    and it is asked only of a call one of them would otherwise hold.
    """

    if (call.kind not in ROUTED_KINDS or overrides.get("routing")
            or (call.kind == events.SPAWN and not call.starts_now)):
        return []
    user_skipped = set(overrides.get("skills") or ())
    routed = state.router_loaded or state.brief_routed or ROUTER_SKILL in user_skipped
    holds = []
    if not routed:
        if call.kind == events.SHELL_COMMAND and shell.analyze(call.command, call.shell).read_only:
            return []
        if writes_scratch():
            return []
        holds.append(Hold(
            "router-first",
            STRICT,
            f"Load the `{ROUTER_SKILL}` skill with {SKILL_TOOL} before the first "
            "write, spawn, or command of a task, and follow the route it selects. "
            "Reads stay free, and so does a shell command made only of read-only "
            "commands, such as cat, grep, ls, git diff, or git branch, perhaps "
            "after a leading cd, with no output redirect but 2>/dev/null. If "
            "that skill is not installed, tell the user: they can type "
            "`skip routing` in their prompt to proceed without it.",
            short_form(f"the `{ROUTER_SKILL}` skill has not loaded",
                       f"Load it with {SKILL_TOOL}, or tell the user they can type "
                       "`skip routing` in their prompt."),
        ))
    if not writes_like_an_edit(call) or writes_scratch():
        return holds
    route = _turn_route(state, turn)
    if route is None:
        return holds + [Hold("route-line", STRICT, *_route_line_texts(turn))]
    if route["form"] == "continue" and state.task is None:
        # Only when saved state was missing or reset: otherwise folding the
        # turn started a task.
        return holds + [Hold(
            "route-line",
            STRICT,
            "`goated-route: continue` was written, but the adapter's saved state for "
            "this session was missing or reset, so it cannot tell which task "
            "continues. Write the route line the router selects for this task.",
        )]
    task = state.task
    if not routed or task is None or task.route["form"] != "route":
        return holds  # `direct` exempts the task; pipeline waits for the router.
    if call.kind == events.SPAWN and call.read_only:
        return holds

    def unmet(skill: str) -> bool:
        return skill not in state.loads and skill not in user_skipped

    orient = (
        _brief_orientation(state, task)
        and unmet(ORIENTATION_SKILL)
        and len(state.files_read) < ORIENTATION_READS
        and orientation_installed()
    )
    route_skills = [
        skill for skill in task.route["requires"] if unmet(skill) and not (orient and skill == ORIENTATION_SKILL)
    ]
    if not route_skills and not orient:
        return []
    parts, missing = [], []
    if route_skills:
        names = ", ".join(f"`{skill}`" for skill in route_skills)
        parts.append(f"The current route requires {names} before the first write or spawn.")
        missing.append(f"load {names}")
    if orient:
        parts.append(
            f"A session started from a brief loads `{ORIENTATION_SKILL}` before its "
            "first write or spawn when its route is standard or full, or orients by "
            f"finishing {READ} calls of three distinct files, each read whole {NO_RANGE}, "
            "such as the sources its brief names."
        )
        # A reader of hold texts takes this sentence's opening for the skill the
        # brief added.
        missing.append(f"A session started from a brief loads `{ORIENTATION_SKILL}` or "
                       f"finishes {READ} calls of three distinct files, each whole")
    parts.append(
        f"Load each with {SKILL_TOOL} and follow it. A load counts until the next "
        "compaction, in this turn or an earlier one"
        + (", and so does a read." if orient else ".")
    )
    if route_skills:
        parts.append(
            ("If a route skill" if orient else "If one")
            + " does not apply, write a corrected route line without it; the last route line wins."
        )
    drops_orientation = (
        "Only a corrected `goated-route: direct` line or a lightweight route line "
        "drops the orientation skill."
    )
    if orient:
        parts.append(drops_orientation)
    return [Hold(
        "pipeline",
        STRICT,
        " ".join(parts) + " " + unseen_line_advice("route line", "skip routing"),
        short_form("; ".join(missing), ("Or write a corrected route line without a skill "
                                        "that does not apply. " if route_skills else "")
                   + (drops_orientation + " " if orient else "")
                   + short_advice("route line", "skip routing")),
    )]


def _brief_orientation(state: SessionState, task: Task) -> bool:
    """True when the orientation skill joins the task's route because of its brief.

    The router selects orientation in a session started from a brief, and the
    spawn-brief template says that session loads it first (spec R4), on a
    `standard` or `full` route only, as the registry's `profile_eligibility`
    lists. It ends when the brief's route stops meeting router-first: at a
    typed prompt or a compaction. The caller also checks that it is installed.
    """

    return state.brief_routed and task.route.get("intensity") in ("standard", "full")


def _route_line_texts(turn: Turn) -> tuple[str, ShortForm]:
    """The route-line hold's full text and short form; both quote the turn's
    lines that do not match the grammar."""

    forms = ("`goated-route: direct`, `goated-route: <intensity> | requires: <skills>`, "
             "or `goated-route: continue`")
    text = (
        "Before the first write or spawn after a user prompt, end routing with a "
        f"route line on its own line, as the router's output contract defines: {forms} "
        "when this prompt continues the current task "
        "or, in a session with no task yet, work begun elsewhere. "
        + unseen_line_advice("route line", "skip routing")
    )
    short = f"Write one of {forms}. " + short_advice("route line", "skip routing")
    if turn.malformed:
        quoted = "; ".join(f"`{line}`" for line in turn.malformed)
        malformed = f" These lines in this turn do not match the grammar: {quoted}."
        text += malformed
        short += malformed
    return text, short_form("this turn has no route line", short)


def _unique(names) -> list[str]:
    seen: list[str] = []
    for name in names:
        if name and name not in seen:
            seen.append(name)
    return seen
