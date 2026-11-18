# Ticket 090: Test Edits Ask For Test References Only When A Test Is Designed

## Parent Spec

`docs/specs/2026-11-17-adapter-low-signal-holds.md` (R9, R15; AC10, AC16,
AC17)

## Type

AFK.

## Problem

A test-file edit that adds five or more lines asks for two references:

- `coding.md`, by the `design-reads` gate, once
  `software-design-principles` counts as loaded;
- `test-design.md`, by the `reference-reads` gate, once `tdd` counts as
  loaded. The registry's signal for it is an edit of a test file with
  `min_added_lines: 5`.

In TDD a test file is edited many times. Both references are about how a
test is designed, which is decided when the test file is created or grows
a lot. All three agents of the last wave called these holds low signal.
The two gates also count "five lines" differently: one counts every line
the edit writes, the other only the lines it adds.

The adapter README's Known Limits also says the `reference-reads` gate
judges only edits by a write tool. The code judges shell writes too, for
the signals that need no added text.

## What To Build

- **One rule for both.** A test-file edit selects `coding.md` and
  `test-design.md` only when it creates the test file or adds twenty or
  more lines. Both gates count added lines the same way, as the design
  gate's `_Added` does today: an added line is any line of the new text
  whose text is not in the old text, so a changed line and a new line
  each count, and unchanged context does not. An `Edit` whose old and new
  strings share thirty unchanged lines and add four is not asked.
- **The registry states it.** The `tdd` entry's signal for
  `test-design.md` expresses "creates the file, or adds at least twenty
  lines". Extend the signal kind, the registry schema, the validator and
  the adapter's registry reader together; the validator's check that the
  reader and a full YAML parser agree must still pass. The adapter reads
  the threshold from the registry, not from a constant of its own.
- **The skills state it.** `software-design-principles` says when a test
  edit calls for `coding.md`, beside its small-edit rule. `tdd` says the
  same for `test-design.md` in its "read when" text. Both stay inside
  their context budgets.
- `mocking-and-seams.md` keeps its pattern signal, at any size.
- **README.** Update Design references, Registry references and the
  `design-reads` and `reference-reads` rows, and correct the Known Limits
  sentence on shell writes to match the code. Regenerate the hold texts
  for the skill-usage mod.

## Recommended First Reads

- The parent spec: Problem, R9, Constraints.
- `adapters/claude-code/goated_adapter/design_reads.py`: `_signals`,
  `_Added`, the small-edit rule.
- `adapters/claude-code/goated_adapter/reference_reads.py`: the signal
  kinds and how an edit is matched.
- `stack/goated-stack.yaml`: the `tdd` entry's `references`;
  `stack/schemas/stack-registry.schema.json`; `skills/README.md` on
  reference signals.
- `stack/fixtures/reference-reads/README.md`.
- `adapters/claude-code/README.md`: Design references, Registry
  references, and the `reference-reads` item of Known Limits.
- Tickets 063, 066 and 067, for how the signals came to be.

## Acceptance Criteria

- [ ] A ten-line edit of an existing test file requires no reference,
      with both skills counted as loaded.
- [ ] A `Write` creating a three-line test file requires `coding.md` and
      `test-design.md`.
- [ ] An edit adding twenty lines to an existing test file requires both;
      one adding nineteen requires neither.
- [ ] An `Edit` whose old and new strings share thirty unchanged lines
      and add four lines not in the old text requires neither. One that
      changes the text of twenty lines requires both, since a changed
      line counts as added.
- [ ] A test edit adding a mock or patch still requires
      `mocking-and-seams.md` at any size.
- [ ] The registry validates, the reader and a full YAML parser agree on
      it, and a signal of the extended kind with a wrong-typed value
      fails validation.
- [ ] Known Limits no longer says `reference-reads` ignores shell writes.
- [ ] Existing tests pass unchanged except where one asserted the
      five-line trigger for a test file; each such change is named in the
      closeout.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The registry, schema and skill validators and the context comparison.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, and the mod's
  tests.

## Blocked By

- `tickets/archive/089-adapter-design-holds-without-written-text.md` (both change
  the design signals and the Design references section).

## Scope Exclusions

- Signals for non-test code files.
- Which gates a test file meets otherwise: `security` and `review-intake`
  hold a test file as today.
- Making `reference-reads` read the text a shell write adds.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `6736d87` (`78c7b54`, review fixes `7e12d5a`).
- Maintainer decision: an added line means a changed line plus a new line.
- Exercised in later sessions; no separate live-check record.
