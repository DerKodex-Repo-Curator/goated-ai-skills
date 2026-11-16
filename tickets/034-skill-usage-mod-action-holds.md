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

Found in the 2026-11-16 live checks of Tickets 031 and 032:

- One strict spawn hold showed as one followed and two ignored nudges, and a
  strict commit hold as one followed and one ignored. The mod seems to read
  the new holds a second time as older hook messages.
- The end-of-turn (closeout) hold, a blocked `Stop`, does not appear in the
  pane.

## Recommended First Reads

- The hold-message format documented by Ticket 031 in
  `adapters/claude-code/README.md`.
- Ticket 032's mod structure and tests.

## Acceptance Criteria

- [x] Mod tests cover each Ticket 031 hold type and outcome, including
      strict holds, which a skip line never satisfies.
- [ ] One live session with the adapter enabled shows a strict hold, a
      justified-skip hold that was declined, and the end-of-turn hold in the
      pane. (Headless runs show all three in the mod's store; the
      maintainer's pane check is pending.)
- [ ] The decision on retiring the personal hooks' hold texts is recorded.
- [ ] An adapter test shows a typed override yields the override sentence in
      `additionalContext`, and the live session shows the override in the
      pane. (The adapter test passes, and a headless run counts the
      override; the pane check is pending.)

## Progress (2026-11-16)

What the two live-check findings turned out to be:

- **The extra "ignored" skills.** They were not a second read through the
  personal-hook marker table. Strict hold texts say a `` `goated-skip` ``
  line does not clear them, and the mod took that backticked word for a
  skill, which never loads. The `spawn` hold also names `handoff` and
  `subagent-driven-development` as alternatives, so the one not loaded was
  counted as ignored. The mod now leaves the grammar's own words out, and
  treats the spawn hold's skills as alternatives.
- **The missing closeout hold.** A blocked `Stop` reaches a mod as
  `Stop hook blocking error from command: "<command>": <reason>` inside a
  reminder, in live rows and in history, so the hold line was not the first
  line. The mod now reads it there. Claude Code also writes the reason as a
  `note` row; the mod does not observe that door, so the hold counts once.

Also changed: a `route-line` hold that repeats after a route line written in
the same message (the known transcript-timing limit) now counts as followed.
The adapter's `UserPromptSubmit` hook returns the override sentence as
`additionalContext`. `tests/adapter-texts.ts` now carries every hold text the
adapter emits, and `tests/adapter-holds.test.tsx` covers each gate's
outcomes.

Left as known limits (mod README): holds that name no skill by its bare name
(the spawn template-read and heading holds) count by gate and kind only, and
the closeout proof item, which asks for a check run, has no per-skill result.

Found, outside this ticket's scope: in headless Haiku runs the closeout
gate's proof item blocked `Stop` up to Claude Code's limit of nine in a row,
even after the agent ran `python -c` checks and wrote a
`goated-skip: verification-before-completion:` line. The adapter ignores
`stop_hook_active` (a Ticket 031 decision). This needs a look before or
during Ticket 033.

## Expected Proof

- Mod test output.
- A screenshot or description of the live pane.

## Blocked By

- `tickets/archive/031-claude-code-adapter-action-and-closeout-gates.md`
- `tickets/archive/032-skill-usage-mod-in-repo.md`

## Scope Exclusions

- Enforcement logic. The mod displays only.
- A standalone, non-GOATED release of the mod.
