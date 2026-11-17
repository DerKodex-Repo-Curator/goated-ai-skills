# Ticket 063: Small Edits Select No Reference By File Kind

## Parent Spec

`docs/specs/2026-11-17-adapter-written-line-holds.md` (R5, R9; AC8)

## Type

AFK.

## Problem

The design-reads signals select a reference for the kind of file or text an
edit touches, whatever its size. Any edit of a test file selects
`coding.md`, so a one-line fix of an escaped `\n` in a test was held for a
reference read, and the reference then needed a citation at closeout. The
`design` gate already treats an edit under five added lines as too small to
hold.

## What To Build

- An edit that adds fewer than five lines selects no reference for:
  - being a test file (`coding.md`);
  - being a configuration file, or the third code file of the turn
    (`decoupling.md`);
  - adding a comment or docstring (`readability.md`).
- Signals read from the added code apply at any size: a new code file or a
  public top-level definition, error handling, and concurrency.
- A design-reads line still requires every reference it names.
- The threshold is the `design` gate's, kept in one place. An edit whose
  added lines cannot be counted is not small.
- A small edit that requires nothing adds nothing to the turn's required
  set, so it needs no citation.
- State the small-edit rule where `software-design-principles` says which
  references to read at which moment, inside its context budget, so the
  adapter enforces a rule the skill owns.
- Update the README's Design references section and its signal table.

## Recommended First Reads

- The parent spec, R5.
- `adapters/claude-code/goated_adapter/design_reads.py` (`_signals`,
  `_Added`, `required`).
- `adapters/claude-code/goated_adapter/actions.py` (`_design_hold`, for the
  five-line threshold).
- `adapters/claude-code/README.md`: Design references.

## Acceptance Criteria

- [ ] A one-line edit of a test file requires no reference; a twenty-line
      one requires `coding.md`.
- [ ] A two-line edit of a configuration file, a two-line edit to the
      turn's third code file, and a one-line added comment each require
      nothing.
- [ ] A one-line edit adding `except` requires `errors.md`, and a
      three-line new public function requires its three references.
- [ ] In a turn whose design-reads line names a reference, a small edit
      still requires that reference.
- [ ] A small edit that requires nothing raises no citation at closeout.

## Expected Proof

- Adapter tests for each criterion, each with a near miss at the threshold
  (four lines and five).
- The mod's design-reads fixtures and tests pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.

## Blocked By

None.

## Scope Exclusions

- The code-content signals.
- The `design` gate's own trigger.
- New signals or references.
