# Ticket 034: Skill-Usage Mod Reads Action And Closeout Holds

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (the rest of R11 and AC7)

Split from Ticket 032 on 2026-11-16 (maintainer decision): the part that
depends on Ticket 031's hold formats.

## Type

HITL. The maintainer checks one live session with the adapter enabled for that
session.

## What To Build

Teach the in-repo skill-usage mod to read the holds that Ticket 031 adds:

- commit, PR, and spawn holds, which are strict;
- design and security holds, which accept a justified skip;
- the end-of-turn (closeout) hold, which accepts a justified skip;
- the shell-write hold.

Make overrides visible to the mod (added 2026-11-16 from Ticket 032): the
adapter's `UserPromptSubmit` hook also returns its sentence `recorded your
override for this prompt: "<phrase>"` as `additionalContext`. A notice
reaches a mod with no text; hook context arrives with it, and the mod already
reads the sentence from there (`overrideEvents` in `hooks/classify.ts`).

The mod records each hold's type and outcome: followed, declined with a
reason, or ignored. It should parse the documented hold-message format that
Ticket 031 fixes, not guess at wording. It also settles when the personal
hooks' hold texts can be retired: after Ticket 033 swaps those hooks out, or
in this ticket if 033 lands first.

## Recommended First Reads

- The hold-message format documented by Ticket 031 in
  `adapters/claude-code/README.md`.
- Ticket 032's mod structure and tests.

## Acceptance Criteria

- [ ] Mod tests cover each Ticket 031 hold type and outcome, including
      strict holds, which a skip line never satisfies.
- [ ] One live session with the adapter enabled shows a strict hold, a
      justified-skip hold that was declined, and the end-of-turn hold in the
      pane.
- [ ] The decision on retiring the personal hooks' hold texts is recorded.
- [ ] An adapter test shows a typed override yields the override sentence in
      `additionalContext`, and the live session shows the override in the
      pane.

## Expected Proof

- Mod test output.
- A screenshot or description of the live pane.

## Blocked By

- `tickets/031-claude-code-adapter-action-and-closeout-gates.md`
- `tickets/032-skill-usage-mod-in-repo.md`

## Scope Exclusions

- Enforcement logic. The mod displays only.
- A standalone, non-GOATED release of the mod.
