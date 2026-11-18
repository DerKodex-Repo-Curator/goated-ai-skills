# Ticket 117: Continue Meets Router-First In A Briefed Task

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-5.md` (R8; AC11, AC5, AC6)

## Type

AFK. Decision P, option 1 (the maintainer, 2026-11-18).

## What To Build

A briefed session that a person types into does not load the router only
to write `continue`. Today `router-first` is met by a router load, or by
the brief's route line only "until a person's prompt opens a turn". So a
session started from a brief that never loaded the router is held on the
first write or command after a typed prompt.

In a session whose brief's route line set its task, a turn opened by a
person's prompt whose route line is `goated-route: continue` meets
`router-first` without a router load. A route line that starts a new
task, or a turn with no route line yet, still needs the router; a command
made only of plain reads passes, as today. Overrides and every other
gate are unchanged.

This is its own state, not a return of `brief_routed`: that flag also
switches on briefed-session orientation (`gates._brief_orientation`), so
setting it again would bring back the `pipeline` gate's orientation hold.
Name a separate fact, such as the task's route having come from the brief,
and read only it in the `router-first` check.

The rule lives in the shared core at `adapters/core/goated_core/`:
`gates.check_routing`, the `router-first` check and its `brief-route`
clear, and the hold text where it says what clears it. The contract's
`router-first` row and "Prompts, Turns, And Tasks", and a conformance
scenario, change with the code, as `AGENTS.md` requires.

**`shell.py`'s pull request reading:** not touched.

## Recommended First Reads

- The parent spec, R8 and decision P.
- `stack/enforcement-contract.md`: the `router-first` and `route-line`
  rows and "Prompts, Turns, And Tasks".
- The core's `gates.py` (`check_routing`, `_routing_holds`,
  `_task_route_in`).
- `tickets/archive/102-core-session-messages-continue-the-task.md`, which
  made another session's message run as `continue`.

## Acceptance Criteria

- [ ] In a briefed session that never loaded the router, a person's
      prompt and then `goated-route: continue` meet no `router-first`
      hold on the next write or command.
- [ ] That turn brings back neither briefed-session orientation nor any
      `pipeline` hold that the person's prompt had ended.
- [ ] The same prompt with a new route line (`goated-route: standard ...`)
      is held until the router loads.
- [ ] Before any route line in that turn, a non-read command is held as
      today.
- [ ] A session not started from a brief is unchanged.
- [ ] The contract states the rule, and a conformance scenario covers the
      hold and each near miss.
- [ ] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The core's routing tests; the Claude Code adapter's tests through its
  hook.
- The repo checks in `AGENTS.md`.

## Blocked By

- None.

## Overlaps

- `gates.py` with Tickets 110 (orientation) and 111 (`shown_holds`),
  other functions.

## Scope Exclusions

- The `route-line` gate, which still asks for the line.
- Sessions not started from a brief.
