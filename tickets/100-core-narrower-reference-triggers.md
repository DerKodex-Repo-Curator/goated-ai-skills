# Ticket 100: Narrower Mocking And Comment Triggers

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-4.md` (R2, R3; AC2, AC3, AC7,
AC8)

## Type

AFK.

## What To Build

Two triggers that fire on text that says little about the work.

- **Mocks and patches in code (R2).** The registry's `mock-or-patch`
  pattern matches `patch` only as a call or decorator: `patch(`, `@patch`,
  `mock.patch`, or `patch.<name>(` such as `patch.object(`.
  `monkeypatch` stays a word match. The other words (`mock`, `stub`,
  `spy`, `fake`, a name ending in `Mock`, `jest.fn`, `vi.fn`, `sinon`)
  match as today, except inside a quoted string on the added line. Where
  a line's strings cannot be read with certainty, the line selects, as
  today. The pattern's description in `stack/goated-stack.yaml` stays true
  of the narrower match.
- **Short comment-only edits (R3).** An edit that is comment-only (by
  today's `comment_only` rule, unchanged) and adds fewer than 20 lines is
  not substantial for the `design` gate, selects no reference by its
  comment (`readability.md`), and is not a code change the closeout's
  Design item counts: it neither makes the item needed nor needs a change
  read after it. A comment-only edit of 20 or more lines is judged as
  today.

The two share a ticket because both narrow what an edit's text selects,
each is small, and both change the same contract rows. The rules live in
the shared core at `adapters/core/` after Ticket 081: today's
`reference_reads.PATTERNS`, `design_reads._signals`,
`actions._design_need`, `actions._designing` and the Design item in
`actions._closeout_items`, which may have moved or been renamed.

The contract and conformance scenarios change with the code, as
`AGENTS.md` requires: the `design`, `design-reads` and `reference-reads`
rows, the `Design` closeout row, and Detection Detail where it states
the pattern; scenarios in `stack/fixtures/enforcement/writes.yaml` and
`closeout.yaml` (or wherever those gates' scenarios live).

## Recommended First Reads

- The parent spec, R2, R3 and their Problem items.
- `stack/enforcement-contract.md`: the rows above.
- The core's reference-reads and design-reads modules, and the closeout's
  Design item.
- `stack/goated-stack.yaml`, `reference_patterns` and the `tdd` skill's
  `mocking-and-seams.md` entry.

## Acceptance Criteria

- [ ] In a test file, with `tdd` loaded, an added line holding `"patch"`
      or `"MagicMock"` only inside a string, or the bare word `patch`,
      asks for no mocking reference.
- [ ] `@patch("x")`, `mock.patch(`, `patch.object(` and
      `m = MagicMock()` each ask for it.
- [ ] A comment-only edit of a Python file adding 19 lines meets no
      `design` or `design-reads` hold and, as the turn's only code
      change, no Design item.
- [ ] A comment-only edit adding 20 lines is judged as today.
- [ ] The contract states both rules, and conformance scenarios cover each
      hold and its near miss.
- [ ] The repo checks in `AGENTS.md` pass, including the context
      comparison if a skill or registry text changes.

## Expected Proof

- The conformance scenarios through the core.
- The Claude Code adapter's reference-read and design-hold tests, with
  the cases above.
- The repo checks in `AGENTS.md`.

## Blocked By

- `tickets/081-shared-enforcement-core.md`

## Scope Exclusions

- The `sleep-retry-or-timeout` pattern.
- What `comment_only` counts as a comment.
- Proof and Docs for comment-only edits.
- The red-flags read and its question.
