# Ticket 075: The Mod Shows What Lies Behind Each Hold Count

## Parent Spec

`docs/specs/2026-11-17-skill-usage-data-detail.md` (R1, R2, R3, R10; AC1,
AC2, AC3)

## Type

AFK.

## Problem

An analysis of the mod's stored summaries could not answer three
questions:

- `closeout` is the most frequent hold, 179 in 84 sessions, but the mod
  does not record which item was unmet.
- The `design` hold was declined 33 times in 72, and the summary keeps no
  skip reasons, so the cause is unknown.
- 67 holds are counted as ignored. That covers a typed override, a turn
  ended by a new prompt, and a hold the agent never answered.

## What To Build

- **Closeout items.** A closeout hold is counted per item it lists (Proof,
  Unfinished work, Docs, Design red flags, Design citations, Security,
  Setup, and any item added later), each with its own outcome. Items are
  read from the hold text's item labels, which the adapter keeps stable
  for this purpose; say so in the adapter README's Hold messages.
- **Skip reasons.** Each justified skip's reason is stored with its skill
  and gate, cut at a fixed length. All time lists them by skill. No path
  or project name is stored with a reason.
- **Unanswered holds.** A hold with no load, read or skip line is counted
  as one of: overridden by the user, turn ended by a new prompt, or
  unanswered. The pane shows the three apart where it showed ignored.
- The stored shape changes, so bump the events shape tag, and keep
  summaries stored by earlier versions readable.
- Update the mod's README table of what it records.

## Recommended First Reads

- The parent spec, R1 to R3 and its Constraints.
- `adapters/claude-code/skill-usage/hooks/holds.ts`, `classify.ts`,
  `meaning.ts` and `view.tsx`.
- `adapters/claude-code/skill-usage/README.md`: What It Records.
- `adapters/claude-code/README.md`: Hold messages, the closeout table.
- Ticket 033's closeout, for why a shape change bumps the tag.

## Acceptance Criteria

- [ ] A closeout hold listing Proof and Docs adds one to each item's
      count, and each shows its own outcome.
- [ ] A closeout hold on a commit and one at `Stop` are split the same
      way.
- [ ] A skip line's reason appears in All time under its skill and gate; a
      500-character reason is stored cut.
- [ ] Each kind of unanswered hold is counted from a fixture that shows
      only that kind.
- [ ] A summary stored before this change still displays, and a session
      running across the update is not misread.

## Expected Proof

- Mod tests for each criterion, each with a near miss.
- The mod's type check adds no errors.
- The repo checks in `AGENTS.md`.
- The maintainer looks at the pane in one real session.

## Blocked By

None.

## Scope Exclusions

- Any change to what the adapter holds.
- Storing prompt text, reply text or file contents.
- A redesign of the pane.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `8181c9e` (`43d2598`, review fix `08ff809`).
- Exercised in later sessions; no separate live-check record.
