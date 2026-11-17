# Ticket 057: Repeated-Failure Ignores Import And Collection Errors

## Parent Spec

`docs/specs/2026-11-17-adapter-hook-friction.md` (R4; AC4)

## Type

AFK.

## Problem

The repeated-failure gate holds the next write once the same check command
has failed twice in a row in a turn. Only a pass resets the count. TDD meets
this on purpose: the first run fails because the module under test doesn't
exist yet, a stub follows, the planned red run fails on the assertion, and
then the implementation write is held. The agent already knows both causes.

## What To Build

- A failing run whose output shows an import or collection error doesn't
  count toward the gate. Examples are pytest's `ERROR collecting` or
  `ImportError while importing test module`, `ModuleNotFoundError`,
  unittest's `Failed to import test module`, and jest's `Cannot find module`.
- Such a run neither adds to the count nor resets it.
- Keep the patterns in one named table with a comment on why, and update the
  README's repeated-failure description.

## Recommended First Reads

- The parent spec, R4.
- `adapters/claude-code/goated_adapter/actions.py`
  (`_repeated_failure_hold`, `_check_key`, `FAILURE_SIGNS_RE`).
- `tickets/archive/036-adapter-repeated-failure-gate.md`.
- `adapters/claude-code/README.md`: the repeated-failure row.

## Acceptance Criteria

- [ ] An import-error run followed by a real failure of the same check
      doesn't hold the next write.
- [ ] Two real failures in a row still hold it.
- [ ] Real failure, import error, real failure still holds, because the
      import error doesn't reset the count.
- [ ] A piped run (`pytest | tail`) is judged the same way.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.

## Blocked By

- None.

## Scope Exclusions

- Resetting the count on a project write between runs: edit, fail, edit,
  fail is the thrashing the gate exists to catch.
- Raising the threshold.
