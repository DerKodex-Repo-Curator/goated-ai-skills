# Ticket 101: Read Skips Last The Task

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-4.md` (R4; AC4, AC7, AC8)

## Type

AFK. The maintainer decided C on 2026-11-18: option 2, the parent spec's
R4. On the same day they chose a new notice kind, `skip_carried`, for the
covered hold's pass, which moves the event model to version 3 (see the
spec's decision C).

## What To Build

A skip line that clears a `design-reads` or `reference-reads` hold lasts
for the references that hold named and the same kind of file (test file,
configuration file, other code file) until the task ends or the next
compaction. The reads those gates ask for already count until the
compaction; a reasoned skip of the same read lasts as long. A later hold
of the same gate that asks only for references the lasting skip covers,
on a file of the same kind, passes with a notice naming the skip.

Every other skip keeps lasting one turn, including a skip line that
clears `design` (a load) or a closeout item in the same turn. A new task
(a route line that is not `continue`) and a compaction end every lasting
skip.

The rule lives in the shared core at `adapters/core/` after Ticket 081:
today's skip lookup (`actions._Proof.skips`) and the session state, which
keeps the task's lasting skips. The contract and conformance scenarios
change with the code, as `AGENTS.md` requires: the Holds section ("Route
and skip lines ... count only in their turn"), the `design-reads` and
`reference-reads` rows, and Notices; scenarios in
`stack/fixtures/enforcement/`.

## Recommended First Reads

- The parent spec, R4 and decision C.
- `stack/enforcement-contract.md`: Holds, the two rows, Notices, and
  "Prompts, Turns, And Tasks".
- The core's skip lookup, session state and the two gates' code.
- `tickets/099-core-fixture-data-is-test-data.md` and
  `tickets/100-core-narrower-reference-triggers.md`, which change the
  same rows first.

## Acceptance Criteria

- [ ] A skip that cleared a `design-reads` hold for `decoupling.md` on a
      configuration file covers a later turn's hold for the same
      reference on another configuration file in the same task, with a
      notice.
- [ ] It does not cover another reference, a code or test file, a new
      task, or a turn after a compaction.
- [ ] A skip line clearing `design` or a closeout item still lasts one
      turn.
- [ ] The contract states the rule, and conformance scenarios cover the
      lasting skip and each near miss above.
- [ ] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The Claude Code adapter's tests across two turns.
- The repo checks in `AGENTS.md`.

## Blocked By

- `tickets/081-shared-enforcement-core.md`
- `tickets/099-core-fixture-data-is-test-data.md`
- `tickets/100-core-narrower-reference-triggers.md`

## Scope Exclusions

- The skip line's grammar: it still names a skill and a reason.
- Skips of any gate other than `design-reads` and `reference-reads`.
- A person's `skip <skill>` override, which keeps lasting one turn.
