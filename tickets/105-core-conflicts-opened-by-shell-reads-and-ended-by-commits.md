# Ticket 105: Conflicts Opened By Shell Reads And Ended By Commits

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-4.md` (addendum R10; AC12,
AC7, AC8)

## Type

HITL: decision G in the parent spec's addendum must be made before the
shell-read half starts. Recommended: G option 1. The commit half needs no
decision. If G is option 3, the ticket is AFK and only the commit half
remains.

## What To Build

Both halves change when the `conflict-resolution` gate thinks a merge
conflict is open, in one function and one contract section, so they
share a ticket.

- **A `commit` call ends a conflict.** A finished `commit` call ends an
  open conflict and drops the reads before it, as a finished shell
  `git commit` does today.
- **Markers a shell command shows (decision G).** Under option 1, a
  plain-read command (`cat`, `head`, `tail`, `type`, `Get-Content`) whose
  finished output has a marker at a line start opens the conflict for
  writes to the files it names, as a file read does; a `git diff` whose
  output shows a marker after the combined-diff prefix (`++<<<<<<<`,
  `+<<<<<<<`) opens it for that section's path. Today only `file_read`
  calls open a conflict by markers.

`git pull --abort` is not part of this ticket: git has no such option, so
it can end nothing. The contract's sentence naming it goes when this
paragraph changes.

The rule lives in the shared core at `adapters/core/goated_core/`:
`actions._open_conflict` and the marker and git patterns beside it
(`CONFLICT_MARKER_RE`, `GIT_CONFLICT_*_RE`). The contract and conformance
scenarios change with the code, as `AGENTS.md` requires:

- `stack/enforcement-contract.md`, Conflicts: the bullet that says only a
  file read opens a conflict by markers, and the paragraph that says a
  `commit` call and `git pull --abort` end nothing; the
  `conflict-resolution` row only if its wording no longer fits;
- `stack/fixtures/enforcement/writes.yaml` (the conflict scenarios): a
  conflict ended by a `commit` call; under G, a `cat` of a marked file
  then an edit of it, held, beside a near miss (an edit of another file,
  or a `cat` of a file with no markers).

## Recommended First Reads

- The parent spec's addendum: R10 and decision G.
- `stack/enforcement-contract.md`, Conflicts and the
  `conflict-resolution` row.
- The core's `_open_conflict` and `_conflict_hold`, and the shell
  reading's plain-read check in `shell.py`.
- The existing conflict scenarios in `stack/fixtures/enforcement/`.

## Acceptance Criteria

- [ ] After a merge reports a conflict, a finished `commit` call ends it:
      a later write in the turn meets no `conflict-resolution` hold.
- [ ] A held or failed `commit` call ends nothing.
- [ ] Under G option 1: a `cat` of a file showing a `<<<<<<<` line opens
      the conflict for a write to that file and not for a write to
      another; a `git diff` showing `++<<<<<<<` in a path's section opens
      it for that path.
- [ ] The contract states each rule, and conformance scenarios cover each
      hold and near miss above.
- [ ] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The core's conflict tests, with the new cases.
- The repo checks in `AGENTS.md`.

## Blocked By

- `tickets/081-shared-enforcement-core.md` (merged)
- Maintainer decision G, for the shell-read half only.

## Overlaps

- No code shared with 099, 100 or 102 (`actions.py` is shared, not the
  functions). Shares `writes.yaml` with 099 and 104.

## Scope Exclusions

- The Read line-number prefix `CONFLICT_MARKER_RE` accepts (Ticket 081's
  concern 3, a separate follow-up).
- Conflicts opened in an earlier turn, and stash pop or apply.
- Reading the repository's state instead of the turn.
