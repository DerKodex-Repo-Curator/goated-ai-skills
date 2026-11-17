# Skill-Usage Data That Answers The Next Questions

## Status

Draft. Decisions settled with the maintainer on 2026-11-17 in a
grill-with-docs session; awaiting the maintainer's review before tickets.
Builds on [the skill enforcement spec](2026-11-15-skill-enforcement-adapter.md)
and [the registry reference reads spec](2026-11-17-registry-reference-reads.md).

## Mode

Compact.

## Problem

The skill-usage mod is the measurement tool for the Claude Code adapter. An
analysis of its stored summaries, 84 sessions from 15 to 17 November 2026,
could not answer several questions the next planning round needed:

- **Closeout.** `closeout` is the most frequent hold, 179 of them, but the
  mod does not record which item was unmet: Proof, Docs, Design, Security
  or Setup.
- **Declines.** The `design` hold was declined 33 times in 72. The summary
  keeps no skip reasons, so the cause is unknown.
- **Unanswered holds.** 67 holds across gates are counted as ignored. That
  one word covers a typed override, a turn the user abandoned, and a hold
  the agent never answered.
- **Routes.** Route lines are counted by form, not by which skills each
  one requires, so the router's choices are invisible.
- **Side sessions.** The count of sessions started is 0, though the
  workflow runs on side sessions.
- **Projects.** Summaries carry no project, so sessions from different
  projects cannot be told apart.
- **Versions.** Summaries from older versions use retired gate names, such
  as `design-hold` and `commit-hold`, mixed with current ones.
- **Overrides.** The stored override phrases include `commit message` and
  ``skip `doc-sync``, which are not phrases the adapter documents.
- **Reference reads.** Reads are counted per file, but not how often a
  reference was asked for, read, or skipped.

## Goals

- The data shows which closeout item, which skip reason and which kind of
  non-answer lies behind each count.
- The data shows what the router chose and what side sessions were
  started.
- All-time data can be split by project and by mod version.
- Each registry-declared reference has counts that show whether its signal
  is tuned well.

## Non-Goals

- Changing what the adapter holds. The mod displays only.
- Recording prompt text, file contents or reply text beyond skip reasons,
  which the agent writes for this purpose.
- Token or cost accounting.
- Migrating summaries stored by earlier versions. They stay readable and
  are marked by version.
- New panes or a redesign of the existing ones.

## Requirements

- **R1, closeout items.** A closeout hold is counted per item it lists,
  with each item's outcome.
- **R2, skip reasons.** Each justified skip's reason is stored with its
  skill and gate, and All time can list them. A reason is cut at a fixed
  length, and a project's name is not stored with it.
- **R3, unanswered holds.** A hold with no load, read or skip line is
  counted as one of: overridden by the user, turn ended by a new prompt,
  or unanswered.
- **R4, routes.** Each routed line's `requires:` skills are counted, per
  skill.
- **R5, side sessions.** A session-start call that ran is counted, by
  tool and by whether it was a card or a start.
- **R6, projects.** Each session's summary carries a project key derived
  from the project folder in a form that does not reveal its path. All
  time can be filtered by it.
- **R7, versions.** Each summary carries the mod's data version. All time
  shows retired gate names under a heading that says they come from
  earlier versions.
- **R8, override phrases.** The cause of the undocumented phrases is found
  and fixed, in the mod or the adapter, with a regression test.
- **R9, reference counts.** For each reference the registry declares as
  enforced: times its hold fired, times it was then read, and times it was
  skipped. For advisory ones: reads, and loads of the skill.
- **R10, documentation.** The mod's README table of what it records
  matches the changes.

## Acceptance Criteria

- [ ] AC1: A closeout hold listing Proof and Docs adds one to each item's
      count, and each shows its own outcome.
- [ ] AC2: A skip line's reason appears in All time under its skill and
      gate; a 500-character reason is stored cut.
- [ ] AC3: The three kinds of unanswered hold are each counted from a
      fixture that shows only that kind.
- [ ] AC4: A route line requiring `tdd` and `doc-sync` adds one to each.
- [ ] AC5: A proposal card and a started side session are counted apart.
- [ ] AC6: Sessions from two project folders can be filtered apart, and
      the stored key does not contain either path.
- [ ] AC7: A summary stored by an earlier version shows under the
      earlier-versions heading and does not change current counts.
- [ ] AC8: The cause of `commit message` and ``skip `doc-sync`` as stored
      override phrases is named in the ticket's closeout, and a test pins
      the fix.
- [ ] AC9: A `reference-reads` hold that is then read adds one fired and
      one read for that reference.
- [ ] AC10: The mod's tests pass, its type check adds no errors, and the
      repo checks in `AGENTS.md` pass.

## Proof Surface

The mod's test suite, driven by event fixtures, and the adapter-text
fixtures it shares with the adapter. A look at the pane in one real session
by the maintainer.

## Constraints

- The mod keeps reading holds from their first line and backticked skill
  names; the adapter's hold texts are regenerated, not hand-copied.
- A change to the stored shape bumps the events shape tag, as Ticket 033's
  review required, so a session running across the update is not misread.
- R9 needs the `reference-reads` gate from the registry reference reads
  spec; the other requirements do not.
- Stored data stays on the user's machine.

## Open Questions

None.

## Risks

- Skip reasons can hold private detail an agent wrote. This is mitigated
  because the store is local, reasons are cut, and no path or project name
  is stored with them.
- More stored fields make older summaries look thinner. The version stamp
  explains the difference in the pane.

## Sources

- `adapters/claude-code/skill-usage/hooks/` (`classify.ts`, `holds.ts`,
  `meaning.ts`, `register.tsx`, `view.tsx`).
- `adapters/claude-code/skill-usage/README.md`: What It Records.
- `adapters/claude-code/goated_adapter/overrides.py`.
- The mod's stored summaries, 15 to 17 November 2026.
