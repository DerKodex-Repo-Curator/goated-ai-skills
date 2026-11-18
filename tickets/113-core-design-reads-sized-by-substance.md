# Ticket 113: Design Reads Sized By Substance

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-5.md` (R2; AC2, AC5, AC6)

## Type

AFK. Decisions K1 and K2, option 1 each (the maintainer, 2026-11-18).
Review asked whether K2.1 should stand, since the second source credited
`test-design.md`; it stands unless the maintainer changes it.

## What To Build

Two triggers of the design references follow what an edit adds, not its
raw line count.

- **A comment on a short code edit (K1).** An edit that adds fewer than
  five code lines (comments, docstrings and blank lines left out, as the
  comment-only rule reads them) and fewer than twenty comment lines
  selects no `readability.md` for its comment. A new code file or public
  definition still selects it. The `design` gate, `decoupling.md` and the
  closeout's Design item keep today's size rule. A file whose comment
  syntax the core does not know is judged as today.
- **New cases in an existing test (K2).** In an edit to a test file the
  edit does not create, an added line that only holds case data does not
  count toward the registry's `min_added_lines` for test files, the one
  rule that selects `coding.md` and `tdd`'s `test-design.md`. A case-data
  line holds, once comments are left out, only string and number
  literals, `True`, `False`, `None`, `true`, `false`, `null`, `nil`,
  brackets, commas, colons, `=` between a keyword and a literal, and a
  case wrapper (`pytest.param(`, `param(`). A new test file selects as
  today.

The rules live in the shared core at `adapters/core/goated_core/`:
`design_reads._signals` and the sizing it is given, and the counting of
`edit-of-file-kind` signals in `design_reads` and `reference_reads`. The
contract changes with the code, as `AGENTS.md` requires: the design
references table (`readability.md` and `coding.md` rows) and the
`edit-of-file-kind` row of Registry Reference Signals; `skills/README.md`
if it states how the signal counts lines; and a conformance scenario under
`stack/fixtures/enforcement/`.

**`shell.py`'s pull request reading:** not touched. A shell write's text
is not read for signals, so this ticket does not touch `shell.py` at all.

## Recommended First Reads

- The parent spec, R2 and decision K.
- `stack/enforcement-contract.md`: the `design` and `design-reads` rows,
  Comment-Only Edits, the design references table, and Registry Reference
  Signals.
- The core's `design_reads.py` (`_signals`, `comment_only`, `_code_lines`,
  `_Added`), `actions.py` (`_small_edit`, `_short_comment_edit`) and
  `reference_reads.py` (the `edit-of-file-kind` signal).
- `stack/goated-stack.yaml`, `tdd`'s `test-design.md` signal.
- `tickets/archive/100-core-narrower-reference-triggers.md` and
  `tickets/archive/090-adapter-test-edit-reference-thresholds.md`.

## Acceptance Criteria

- [ ] K1: in a Python file, an edit adding three code lines and a
      two-line comment selects no `readability.md`; one adding five code
      lines and a comment does; one adding three code lines and twenty
      comment lines does.
- [ ] K1: the same three-plus-two edit still meets the `design` gate when
      the skill is not loaded, as today.
- [ ] K2: 24 added case-data lines (tuples of literals, `pytest.param(`
      rows) in an existing test file select no `coding.md` or
      `test-design.md`; 24 lines of a new test function in that file do;
      a new test file does.
- [ ] The contract states both rules, and a conformance scenario covers a
      hold and the near miss of each.
- [ ] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The core's design-reads and reference-reads tests, with the new cases.
- The repo checks in `AGENTS.md`, including the registry validation.

## Blocked By

- `tickets/114-core-large-writes-land-and-read-after.md` (ordering: both
  change the `design-reads` and `reference-reads` contract rows; 114 is
  ranked first).

## Overlaps

- `reference_reads.py` with Ticket 115 (`PATTERNS`, another part).
- `design_reads.py` was last changed by Tickets 099 to 101 and 106, all
  merged.

## Scope Exclusions

- Which references a typical change needs (kept in round 3).
- The size rule of the `design` gate and the Design item (option K1.2).
- Pointing a hold at a section of a reference (feedback item 6).
