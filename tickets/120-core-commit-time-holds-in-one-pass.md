# Ticket 120: Commit-Time Holds In One Pass

## Parent Spec

`docs/specs/2026-11-19-hook-friction-round-6.md` (R4 to R9; AC5 to AC10,
AC14)

## Type

AFK. Decisions V1, V2, X1, X2 and X3 (the maintainer, 2026-11-19), and one
bug fix. V1 reverses Ticket 095's choice that the closeout at a commit may
arrive on the retry.

## What To Build

A commit shows everything it still needs at once, and the commit and
closeout asks stop firing where they can find nothing. The separate change
read before a commit, the red-flags read and its question, and doc-sync
and verification at closeout all stay. One agent can do this in three
phases; each phase lands green.

- **Phase 1, one message and a steadier change read.**
  - **One message (R4).** A held commit reports, in one message, every
    unmet ask it has: the `commit-message` load, the message contract, the
    change read, and each closeout item.
  - **Non-code changes keep the change read (R5).** A comment-only edit,
    as the core's comment-only rule reads it, or a change to a file that
    is not code, made after a change read, does not reset the `commit`
    gate's change read. A diff chained before the commit in the same
    command still does not count.
- **Phase 2, the Design item's small follow-up (R6, a bug).** After a
  red-flags read, later changes adding fewer than five lines need only a
  new change read. The count today includes the edit's unchanged context
  lines, so a two-line fix sent with three lines of context re-arms the
  read. Count only lines the edit adds that its removed text did not hold,
  as the reference gates do.
- **Phase 3, asks that fire where they can find something.**
  - **Docs accepts a doc change (R7).** Docs is met without a `doc-sync`
    load when the turn changed a documentation file after its last code
    change and a change read follows that doc change. A doc changed only
    before the last code change does not meet it.
  - **A conflict's commit asks for less (R8).** A commit that ends a
    conflict, in a session with `resolving-merge-conflicts` loaded, asks
    for the change read and Proof. Docs, Design and Security are not asked
    at that commit. Without the load it gets the full closeout, and so
    does the next ordinary commit.
  - **Test files are not security-sensitive (R9).** A test path, as the
    core already tells test files from code, does not match the security
    path patterns.

The rules live in the shared core at `adapters/core/goated_core/`. The
contract's Holds, Closeout Items, Change Reads, Conflicts and
Security-Sensitive Paths sections, and conformance scenarios under
`stack/fixtures/enforcement/`, change with the code.

## Recommended First Reads

- The parent spec: R4 to R9, the matching Problem items, and decisions V
  and X.
- `stack/enforcement-contract.md`: Holds (several holds in one message),
  Closeout Items, Change Reads, Conflicts, Commits And Pull Requests, and
  Security-Sensitive Paths.
- `tickets/archive/095-adapter-joint-holds-in-one-message.md` and
  `tickets/archive/116-core-proof-kept-while-nothing-material-changed.md`.
- The core's commit hold, change-read and closeout item rules in
  `actions.py`, and `design_reads.py` for the comment-only and test-path
  rules.

## Acceptance Criteria

- [x] A commit with no `commit-message` load, no change read and an unmet
      Proof item returns one message naming all three.
- [x] After a change read, a Markdown edit and a comment-only edit leave
      the commit unheld; a one-line code edit holds it.
- [x] A diff chained before the commit in one command still does not meet
      the change read.
- [x] After a red-flags read, a 2-line replacement sent with 3 unchanged
      context lines needs only a change read; a 5-line addition needs the
      red-flags read again.
- [x] A turn that changes code, then a doc, then reads the change meets
      Docs with no load; with the doc changed before the code, it does
      not.
- [x] With `resolving-merge-conflicts` loaded, a commit ending a conflict
      asks for the change read and Proof only; the same commit without the
      load, and the next ordinary commit, ask for the full closeout.
- [x] An edit to `tests/test_session_x.py` meets no security hold; an edit
      to `src/session.py` does.
- [x] The contract states each rule, and conformance scenarios cover each
      hold, each way it clears, and a near miss.
- [x] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The core's commit and closeout tests; the Claude Code adapter's tests
  through its hook, including its generated text fixture.
- The repo checks in `AGENTS.md`.

## Blocked By

- None. It changes the closeout items beside Ticket 118, which changes
  only the Reads item; whichever merges second resolves the overlap.

## Scope Exclusions

- A chained diff counting as the change read (rejected in decision V).
- A Design skip line that lasts the task (decision X4, not chosen).
- The Docs change read resetting after a docstring-only edit: kept, by
  round 5's intent.
- Treating `git merge --continue` as a commit.
- The order of words inside each item: Ticket 121 owns hold text.
