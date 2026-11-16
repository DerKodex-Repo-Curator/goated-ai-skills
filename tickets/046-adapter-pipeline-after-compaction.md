# Ticket 046: Pipeline Hold Keeps An Earlier Task After Compaction

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (Trial Result; AC11)

## Type

AFK. Diagnose first.

## Problem

Seen once in the Ticket 033 trial. After a compaction, a pipeline hold kept
asking for an earlier task's required skill (`commit-message`) after the
agent wrote `goated-route: continue` and then `goated-route: direct` in later
messages. It cleared only after a third route-line message. The README says
the route carries over a compaction and the last route line wins, so a
`direct` line should have exempted the task.

## What To Build

- Reproduce it with a recorded-shape transcript: a task with `requires:`, a
  compaction, then `continue`, then `direct` in a separate message, then a
  write.
- Find the cause in the routing gates or the state carried over the
  compaction, and fix it so the last route line wins as documented.
- If the cause is the same-message limit rather than the adapter, record that
  in the README's Known Limits instead.

## Recommended First Reads

- `adapters/claude-code/README.md`: What It Holds (Compaction, task rules).
- `adapters/claude-code/goated_adapter/gates.py`, `state.py`,
  `transcript.py`, and `tests/test_claude_code_adapter.py`.

## Acceptance Criteria

- [ ] A regression test reproduces the trial case and fails before the fix.
- [ ] After the fix, a `direct` route line in a separate message clears the
      earlier task's pipeline hold; other compaction tests still pass.

## Expected Proof

- The failing-then-passing test, and the repo checks in `AGENTS.md` on
  Python 3.11 and 3.14.

## Blocked By

- `tickets/045-route-and-skip-lines-before-the-call.md` (same files)

## Scope Exclusions

- Changing what a compaction clears (the router and required loads).
