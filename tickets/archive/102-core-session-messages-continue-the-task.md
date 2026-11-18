# Ticket 102: Messages From Other Sessions Continue The Task

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-4.md` (R5, R6; AC5, AC6, AC7,
AC8)

## Type

AFK. The maintainer decided D1 and D2 on 2026-11-18: D1 option 2 (R5)
and D2 option 1 (R6) in the parent spec.

## What To Build

- **Another session's message (R5).** In a session with a task, a prompt
  with `author: session` opens a turn whose route is `continue` until a
  route line in the turn says otherwise. The `route-line` gate does not
  hold that turn. The turn is still new: it carries no override, and its
  skip lines, checks and change reads start empty. A person's prompt, a
  session with no task yet, and a briefed session's first prompt are
  unchanged.
- **A session waiting on another (R6).** No rule change. The closeout's
  Proof text says that a session waiting on another session's result may
  write `goated-skip: verification-before-completion: <what it waits
  for>`.

They share a ticket because both decide how a session-to-session exchange
meets the routing and closeout rules, and both are small.

The rules live in the shared core at `adapters/core/` after Ticket 081:
today's route-line check (`gates.check_routing`, `_task_route_in`) and the
Proof item in `actions._closeout_items`, which may have moved or been
renamed. The event model needs no change: `author: session` already marks
these prompts. The contract and conformance scenarios change with the
code, as `AGENTS.md` requires: "Prompts, Turns, And Tasks", the
`route-line` row, and Hold Messages if it states the Proof text; scenarios
in `stack/fixtures/enforcement/routing.yaml` and `closeout.yaml`.

## Recommended First Reads

- The parent spec, R5, R6 and decisions D1 and D2.
- `stack/enforcement-contract.md`: "Prompts, Turns, And Tasks", Lines,
  the `route-line` row and the `Proof` closeout row.
- The core's routing gates and closeout Proof item.
- `tickets/archive/094-adapter-own-subagent-reports-continue-the-turn.md`,
  the nearest earlier change to turn boundaries.

## Acceptance Criteria

- [x] After a person's prompt starts a task, a later `author: session`
      prompt's first write meets no `route-line` hold.
- [x] That turn carries no override from the earlier turn, and its Proof
      starts unmet.
- [x] A route line in that turn replaces the carried route.
- [x] A person's prompt in the same session is still held until a route
      line.
- [x] A session-authored prompt in a session with no task is held as
      today.
- [x] The Proof item's text names the waiting case.
- [x] The contract states the rule, and conformance scenarios cover the
      continued turn and the person's prompt near miss.
- [x] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The Claude Code adapter's tests with a cross-session message prompt.
- The repo checks in `AGENTS.md`.

## Blocked By

- `tickets/archive/081-shared-enforcement-core.md`

## Scope Exclusions

- Overrides from any prompt a person did not type.
- A status-line grammar (D2 option 2, not chosen).
- How the Claude Code adapter tells a session's message from a person's,
  which stays as it is.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `a8c6b61` (`9539c5f`, follow-up `4a27af4`).
- Maintainer decisions: D1 option 2 and D2 option 1. The lead narrowed
  the continued route to peer messages only.
- Exercised in later sessions; no separate live-check record.
