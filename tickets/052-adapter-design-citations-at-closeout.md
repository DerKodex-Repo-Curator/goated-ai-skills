# Ticket 052: Closeout Needs A Citation From Each Design Reference Read

## Parent Spec

`docs/specs/2026-11-16-design-reference-reads.md` (R6; AC7)

## Type

AFK.

## Problem

A reference read can be skimmed and ignored, as real use showed with
`red-flags.md` before Ticket 041. Without a visible trace of how a reference
shaped the change, Ticket 051's reads prove only that a file was opened.

## What To Build

- The closeout Design item also needs, in the turn's text, including the reply
  being finished, at least one section id from each reference in the turn's
  required set (Ticket 051). A missing citation names the reference and asks
  for the id with how it applied or why it did not.
- Take each reference's ids from the skill's own files (the
  `<!-- id: #name -->` comments), not from a copy in the adapter. If the files
  cannot be read, fail open for this item and say so in the README.
- Keep the `red-flags.md` read and the change read as they are.
- Update the README's closeout table and hold text.
- Keep the item inside the closeout's item list. Ticket 059
  (`docs/specs/2026-11-17-adapter-hook-friction.md`, R1) also holds a commit
  on unmet closeout items, so the citation item joins that commit-time list
  with no extra work.

## Recommended First Reads

- The parent spec, R6.
- `adapters/claude-code/goated_adapter/actions.py` (`check_closeout`,
  `_code_items`) as Ticket 051 left it.
- `adapters/claude-code/README.md`: the closeout and change-read sections.

## Acceptance Criteria

- [ ] A turn whose required set has a reference with no cited id is held at
      closeout, naming the reference; citing one of its ids clears it.
- [ ] An id cited only in the final reply counts.
- [ ] An id from a different reference does not satisfy it.
- [ ] Unreadable skill files leave the item open, as documented.
- [ ] The existing red-flags and change-read behaviour is unchanged.

## Expected Proof

- Adapter tests for each criterion.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- A live check in one real session.

## Blocked By

- `tickets/051-adapter-design-reference-reads.md` (the required set; same
  files)

## Scope Exclusions

- Judging the quality of a citation.
