# Ticket 057: TDD Meets No Hold Meant For Other Work

## Parent Spec

`docs/specs/2026-11-17-adapter-hook-friction.md` (R4, R7; AC4, AC8)

## Type

AFK.

## Problem

Two gates fire on TDD's normal steps:

- **Repeated failure.** The gate holds the next write once the same check
  command has failed twice in a row in a turn, and only a pass resets the
  count. TDD meets this on purpose: the first run fails because the module
  under test doesn't exist yet, a stub follows, the planned red run fails on
  the assertion, and then the implementation write is held. The agent
  already knows both causes.
- **Design.** The `design` gate holds a turn's first substantial code edit
  until `software-design-principles` loads and its design-reads line and
  references are in. Test files count as code. In TDD the test is usually the
  first substantial edit, so the gate fires on the test, and the
  implementation that follows, which is where the design happens, counts as
  a later edit.

Both are small changes, verified in the same red-green run.

## What To Build

- **Repeated failure.** A failing run whose output shows an import or
  collection error doesn't count toward the gate. Examples are pytest's
  `ERROR collecting` or `ImportError while importing test module`,
  `ModuleNotFoundError`, unittest's `Failed to import test module`, and
  jest's `Cannot find module`. Such a run neither adds to the count nor
  resets it. Keep the patterns in one named table with a comment on why.
- **Design.** A test file never triggers the `design` gate, and it doesn't
  count as an earlier substantial edit when the gate looks for the turn's
  first one. The turn's first substantial non-test code edit is what
  triggers it. Once the skill is loaded, a test file still meets the
  `design-reads` gate (`coding.md`) as today. Use the test-path rule the
  closeout already owns.
- Update the README's repeated-failure and design gate text.

## Recommended First Reads

- The parent spec, R4 and R7.
- `adapters/claude-code/goated_adapter/actions.py`
  (`_repeated_failure_hold`, `_check_key`, `FAILURE_SIGNS_RE`,
  `_design_hold`, `_project_code_writes`, `TEST_PATH_RE`).
- `adapters/claude-code/goated_adapter/design_reads.py` (`applies`,
  `required`).
- `tickets/archive/036-adapter-repeated-failure-gate.md`.
- `adapters/claude-code/README.md`: the repeated-failure row and Design
  references.

## Acceptance Criteria

- [ ] An import-error run followed by a real failure of the same check
      doesn't hold the next write.
- [ ] Two real failures in a row still hold it.
- [ ] Real failure, import error, real failure still holds, because the
      import error doesn't reset the count.
- [ ] A piped run (`pytest | tail`) is judged the same way.
- [ ] A 20-line test-file edit as the turn's first edit is not held by
      `design`. A 20-line non-test edit after it is.
- [ ] With the skill loaded, a test edit still needs `coding.md` read.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.

## Blocked By

- None.

## Scope Exclusions

- Resetting the count on a project write between runs: edit, fail, edit,
  fail is the thrashing the gate exists to catch.
- Raising the threshold.
- Exempting test files from `design-reads` or the closeout's Design item.
