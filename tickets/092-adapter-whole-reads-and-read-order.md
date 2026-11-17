# Ticket 092: Required Files Are Read Whole, And A Diff Read Counts Before The Load

## Parent Spec

`docs/specs/2026-11-17-adapter-low-signal-holds.md` (R12, R13, R15; AC13,
AC14, AC16, AC17)

## Type

AFK.

## Problem

Two rules about reads are uneven:

- **Partial reads.** Every hold that asks for a file to be read accepts
  any finished `Read` of its path. A `Read` with `limit: 20` of a
  required reference counts as reading it.
- **Read order.** A change read, such as `git diff`, made after the last
  change counts for commit, pull request and the Docs item whether it
  came before or after the skill load. For the Review and Security items
  and the `pr-review` gate it must come after the load, so an agent that
  read the diff and then loaded the skill reads the diff again.

## What To Build

- **Whole reads.** A `Read` whose input has `limit` or `offset` does not
  count for a required design reference, a registry reference, a spawn
  template (`spawn-brief.md` and the implementer and reviewer prompts) or
  `red-flags.md`. The hold says to read the whole file. A read whose
  range cannot be read from the call is partial.
- **Both red-flags readers.** `_red_flags_read` in `actions.py`
  duplicates `_Proof.read_index`. The whole-read rule must hold in both
  places; give them one reader if that is the smaller change.
- **Read order.** For Review, Security and `pr-review`, a change read
  after the last change counts whether it came before or after the load.
  State the rule once in the README's Change reads section, for every
  hold that asks for one.
- Change reads themselves are unaffected by the whole-read rule.
- Update the README (What It Holds on a required read, Change reads, the
  closeout table, Known Limits) and regenerate the hold texts for the
  skill-usage mod. The mod's count of reference reads follows the same
  rule, if it counts reads itself.

## Recommended First Reads

- The parent spec: R12, R13, Constraints.
- `adapters/claude-code/goated_adapter/design_reads.py` and
  `reference_reads.py`: `reads_in`; `contracts.py`: `templates_read`;
  `actions.py`: `_Proof.read_index`, `_red_flags_read`,
  `_change_read_hold`, `_review_item`,
  the Security item and the `pr-review` hold.
- `adapters/claude-code/README.md`: Change reads, "A required read" in
  What It Holds.
- `adapters/claude-code/skill-usage/hooks/`, where reference reads are
  counted.
- `tickets/059-adapter-closeout-reads-and-commit-timing.md`, which made
  the order rule for commit and Docs.

## Acceptance Criteria

- [ ] A `Read` with `limit: 20` of a required design reference leaves the
      hold in place, and the hold says to read the whole file. A whole
      read clears it.
- [ ] The same holds for a registry reference, `spawn-brief.md`, the
      implementer and reviewer prompt templates of
      `subagent-driven-development`, and `red-flags.md`, at the closeout
      and wherever else the red-flags read is judged.
- [ ] A `Read` with `offset` alone is partial.
- [ ] A whole read made in an earlier turn still counts until a
      compaction.
- [ ] A diff read after the last change and before the
      `standards-and-spec-review` load meets the Review item. The same
      holds for the Security item and `pr-review` with their skills.
- [ ] A diff read before the last change still does not count.
- [ ] Existing tests pass unchanged except where one asserted a partial
      read or the after-the-load order; each such change is named in the
      closeout.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, and the mod's
  tests.

## Blocked By

- `tickets/078-skill-usage-reference-counts.md` (adds the mod's count of
  reference reads, which this ticket may change).
- `tickets/089-adapter-design-holds-without-written-text.md` (changes the
  design reads and the Design red-flags item).
- `tickets/091-adapter-review-size-and-installs.md` (changes the Review
  item and the `pr-review` hold).

## Scope Exclusions

- Requiring several partial reads to add up to a whole one.
- The Design red-flags item's order: the red-flags read, then a change
  read.
- What counts as a change read.
