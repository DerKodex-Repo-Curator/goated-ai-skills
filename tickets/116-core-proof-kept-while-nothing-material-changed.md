# Ticket 116: Proof Kept While Nothing Material Changed

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-5.md` (R7; AC9, AC10, AC5,
AC6)

## Type

AFK. Decision N, option 1, and the restated decision O, option 1 (the
maintainer, 2026-11-18).

## What To Build

The closeout's Proof item stops asking for a new check when nothing that
runs has changed, and stops counting a check that has not finished.

- **Comment-only edits (N).** A comment-only edit, as the core's
  comment-only rule reads it, of any size, made after the last check, is
  already proved: it does not make Proof needed. A file whose comment
  syntax the core does not know is never comment-only, as today. The
  Docs item still fires after a docstring-only edit of a non-test code
  file, by intent.
- **A background launch is not a check (O1).** Today `actions._checks`
  reads only the command's text, so a shell call with `background` true
  meets Proof at its launch, at a commit and at the turn's end, and its
  failure is never seen. After this ticket such a call meets Proof at
  neither. The contract's "not in the background" (Closeout Items, and
  Shell Reading's paragraph on the Proof item) covers a harness
  background run as well as `pytest &`, so the contract and the code
  agree.
- **Waiting (any O).** The Proof text names two waits: on the user, and
  on a background check. For either, the skip line naming
  `verification-before-completion`, with what is awaited as its reason,
  clears it, as for waiting on another session (Ticket 102).

Option O2 (a running check deferring Proof, its result judged when it
arrives) was not chosen; it would have needed an event model change.

The rules live in the shared core at `adapters/core/goated_core/`: the
Proof and Unfinished items in `actions._closeout_items`, and
`actions._checks`. The contract's Closeout Items (the Proof row and the
paragraph after the table), Shell Reading's Proof paragraph, and
conformance scenarios under `stack/fixtures/enforcement/` change with the
code, as `AGENTS.md` requires. Under O1 the event model does not change:
the shell call's `background` field already exists.

**`shell.py`'s pull request reading:** not touched. Whether a command is
a check uses the shell reading that already finds checks.

## Recommended First Reads

- The parent spec, R7, the Problem's item 10, and decisions N and O.
- `stack/enforcement-contract.md`: Terms (Check), Closeout Items,
  Comment-Only Edits, and Shell Reading's paragraph on the Proof item.
- The core's `actions.py` (`_closeout_items`, the Proof and Unfinished
  items, `_checks`, `_proves_itself`, `_short_comment_edit`) and
  `design_reads.comment_only`.
- `stack/schemas/enforcement-event-model.schema.json`, the shell call's
  `background` field.
- `tickets/archive/102-core-session-messages-continue-the-task.md`.

## Acceptance Criteria

- [x] After a passing check, a docstring-only edit of a Python file, of
      any size, meets no Proof item; an edit changing one code line does.
- [x] O1: a check run with `background` true after the last change does
      not meet Proof at a commit or at the turn's end; the same check in
      the foreground does; `pytest &` inside one command still does not.
- [x] The Proof text names waiting on the user and on a background
      check, and the skip line for each.
- [x] The contract states each rule, and conformance scenarios cover the
      hold and each near miss.
- [x] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The core's closeout tests; the Claude Code adapter's tests through its
  hook.
- The repo checks in `AGENTS.md`.

## Blocked By

- `tickets/archive/114-core-large-writes-land-and-read-after.md` (ordering: both
  change `_closeout_items` and the Closeout Items table).

## Scope Exclusions

- A status line that defers the closeout.
- Under O1, reading a background check's later result.
