# Ticket 116: Proof Kept While Nothing Material Changed

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-5.md` (R7; AC9, AC10, AC5,
AC6)

## Type

AFK. Decisions N and O, option 1 each (the maintainer, 2026-11-18).

## What To Build

The closeout's Proof item stops asking for a new check when nothing that
runs has changed, or when the check is still running.

- **Comment-only edits (N).** A comment-only edit, as the core's
  comment-only rule reads it, of any size, made after the last check,
  is already proved: it does not make Proof needed. A file whose comment
  syntax the core does not know is never comment-only, as today.
- **A check still running (O).** At the turn's end, not at a commit, a
  check started in the background after the last code change, whose
  result the turn has not seen, meets Proof, with a notice naming the
  check. When its result arrives in a later turn, that turn's closeout
  judges it as a check: Proof, and Unfinished if it failed.
- **Waiting on the user (O).** The Proof text names the case: the skip
  line naming `verification-before-completion`, with what is awaited as
  its reason, clears it, as for waiting on another session (Ticket 102).

The rules live in the shared core at `adapters/core/goated_core/`: the
Proof and Unfinished items in `actions._closeout_items` and the code that
finds the turn's last check and last code change. The contract's Closeout
Items (the Proof row and the paragraph after the table) and conformance
scenarios under `stack/fixtures/enforcement/` change with the code, as
`AGENTS.md` requires.

**`shell.py`'s pull request reading:** not touched. Whether a background
command is a check uses the shell reading that already finds checks.

## Recommended First Reads

- The parent spec, R7 and decisions N and O.
- `stack/enforcement-contract.md`: Terms (Check), Closeout Items, and
  Comment-Only Edits.
- The core's `actions.py` (`_closeout_items`, the Proof and Unfinished
  items, `_short_comment_edit`) and `design_reads.comment_only`.
- `stack/schemas/enforcement-event-model.schema.json`, the shell call's
  `background` field and how a background result arrives.
- `tickets/archive/102-core-session-messages-continue-the-task.md`.

## Acceptance Criteria

- [ ] After a passing check, a docstring-only edit of a Python file, of
      any size, meets no Proof item; an edit changing one code line does.
- [ ] A background check started after the last change, with no result
      in the turn, meets Proof at the turn's end with a notice, and does
      not meet it at a commit.
- [ ] A failed background check's result arriving in a later turn makes
      Unfinished needed there.
- [ ] The Proof text names waiting on the user and the skip line for it.
- [ ] The contract states each rule, and conformance scenarios cover the
      hold and each near miss.
- [ ] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The core's closeout tests; the Claude Code adapter's tests through its
  hook.
- The repo checks in `AGENTS.md`.

## Blocked By

- `tickets/114-core-large-writes-land-and-read-after.md` (ordering: both
  change `_closeout_items` and the Closeout Items table).

## Scope Exclusions

- A status line that defers the closeout (option O3).
- Proof at a commit, which still needs a finished check.
