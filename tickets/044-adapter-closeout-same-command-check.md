# Ticket 044: Closeout Counts A Check In The Same Command As The Write

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (Trial Result; AC11)

## Type

AFK.

## Problem

In the Ticket 033 trial, the closeout's Proof item held a turn whose only
code change was written by a shell command that ran a check right after the
write, in the same command (for example `cp fixture.ts tests/ && npm test`).
Proof counts only checks in a call after the last changing call, so the
agent had to run the check again.

## What To Build

- A check that runs later in the same command than the write, as the shell
  analysis orders its simple commands, proves that write.
- An ad-hoc `python -c` (or similar inline interpreter code) still does not
  count as a check. The maintainer decided this on 2026-11-16: it can do
  anything, and a `goated-skip: verification-before-completion: <reason>`
  line already clears the item.
- Update the README's closeout Proof row.

## Recommended First Reads

- `adapters/claude-code/README.md`: What It Holds (closeout items).
- `adapters/claude-code/goated_adapter/actions.py` (`check_closeout`,
  `_code_changes`, `_checks`) and `goated_adapter/shell.py` (`is_check`).
- `tests/test_claude_code_adapter_actions.py`.

## Acceptance Criteria

- [ ] `cp a.py src/ && python -m pytest` proves its write at closeout.
- [ ] `python -m pytest && cp a.py src/` does not: the check ran first.
- [ ] `python -c "..."` after a write does not prove it.
- [ ] A failing same-command check still asks for `handoff` as today.

## Expected Proof

- Adapter tests for each criterion.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.

## Blocked By

- `tickets/archive/043-adapter-out-of-project-holds.md` (same files)

## Scope Exclusions

- Reading a command's exit status per simple command; the call's result
  stays the signal for the whole command.
