# Ticket 058: The Design Gate Skips Test Files

## Parent Spec

`docs/specs/2026-11-17-adapter-hook-friction.md` (R7; AC8)

## Type

AFK.

## Problem

The `design` gate holds a turn's first substantial code edit until
`software-design-principles` loads and its design-reads line and references
are in. Test files count as code. In TDD the test is usually the first
substantial edit, so the gate fires on the test, and the implementation that
follows, which is where the design happens, counts as a later edit.

## What To Build

- A test file never triggers the `design` gate, and it doesn't count as an
  earlier substantial edit when the gate looks for the turn's first one. The
  turn's first substantial non-test code edit is what triggers it.
- Once the skill is loaded, a test file still meets the `design-reads` gate
  (`coding.md`) as today.
- Use the test-path rule the closeout already owns. Update the README's
  design gate text.

## Recommended First Reads

- The parent spec, R7.
- `adapters/claude-code/goated_adapter/actions.py` (`_design_hold`,
  `_project_code_writes`, `TEST_PATH_RE`).
- `adapters/claude-code/goated_adapter/design_reads.py` (`applies`,
  `required`).
- `adapters/claude-code/README.md`: Design references.

## Acceptance Criteria

- [ ] A 20-line test-file edit as the turn's first edit is not held by
      `design`.
- [ ] A 20-line non-test edit after it is held by `design`.
- [ ] With the skill loaded, a test edit still needs `coding.md` read.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.

## Blocked By

- None.

## Scope Exclusions

- Exempting test files from `design-reads`.
- The closeout's Design item.
