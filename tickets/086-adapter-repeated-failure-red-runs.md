# Ticket 086: Repeated-Failure Skips Red And Shrinking Runs

## Parent Spec

`docs/specs/2026-11-17-adapter-low-signal-holds.md` (R1, R2, R15; AC1, AC2,
AC3, AC16, AC17)

## Type

AFK.

## Problem

The `repeated-failure` gate holds the next write once one check has failed
twice in a row in the turn, until `diagnose` loads. It counts every failed
run alike:

- In TDD the first run after writing a test is meant to fail. "Red, write
  the code, still red" is two failures, so the fix is held.
- A run that fails with fewer failures than the run before shows progress,
  and is counted like a run that shows none.
- The hold shows the first 80 characters of the command. With a leading
  `cd "<long path>" &&` the test command is cut off, and the same check run
  with and without the `cd` is two checks.

Only a red run whose test module could not load a missing module is
excused today.

## What To Build

- **Red runs.** A failed run of a check is not counted, and does not reset
  the count, when it is the first run of that check after a finished write
  to a test file in the turn. The write may be by a write tool or a shell
  command; a held or failed write does not count.
- **Shrinking runs.** A failed run is not counted, and does not reset the
  count, when its runner reports fewer failures than the previous run of
  that check in the turn. Failures are the failed and errored tests in the
  runner's summary. Read the count for the runners the gate already reads
  failure signs from. When either run's count cannot be read, the run
  counts.
- **The check.** "The same check" ignores a leading `cd` to a folder
  joined by `&&` or `;`. The hold shows the check's own command.
- **Rule owners.** Confirm that `tdd` says the first run after writing a
  test is expected to fail, and that `diagnose` names repeated failure of
  one check as its trigger. Tighten a sentence in either only if the rule
  is not stated, inside the skill's context budget.
- Update the `repeated-failure` row and its text in the adapter README,
  and regenerate the hold texts for the skill-usage mod.

## Recommended First Reads

- The parent spec: Problem, R1, R2, Constraints.
- `adapters/claude-code/goated_adapter/actions.py`: `_repeated_check`,
  `_check_key`, `_repeated_failure_hold`, `LOAD_ERROR_SIGNS`,
  `FAILURE_SIGNS_RE`.
- `adapters/claude-code/README.md`: the `repeated-failure` row of What It
  Holds.
- The existing `repeated-failure` tests under `tests/`.
- `skills/engineering/tdd/SKILL.md` and `skills/engineering/diagnose/SKILL.md`.

## Acceptance Criteria

- [ ] Test edit, failed run, code edit, failed run, code edit: the second
      code edit is not held. A third failed run with the same failure
      count then holds the next write.
- [ ] Runs reporting 5, 3 and 1 failures hold nothing. Runs reporting 3
      and 3 hold the next write.
- [ ] Two failed runs whose counts cannot be read hold the next write.
- [ ] A failed run after a held or failed test-file write counts.
- [ ] `cd "<long path>" && pytest -q` failing twice shows `pytest -q` in
      the hold, and counts as the same check as `pytest -q` run from that
      folder.
- [ ] The missing-module rule, the reset on a pass and the clearing by
      `diagnose` behave as before.
- [ ] Existing tests pass unchanged except where one asserted the friction
      removed here; each such change is named in the closeout.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, and the mod's
  tests.

## Blocked By

None.

## Scope Exclusions

- Telling a known failing test from a new failure by test name.
- Changing the threshold of two, or what `diagnose` must do.
- The `reference-reads` signal that fires with this gate.
