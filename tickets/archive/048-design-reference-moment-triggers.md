# Ticket 048: Design References Named At Their Moment

## Parent Spec

`docs/specs/2026-11-16-design-reference-reads.md` (R1, R2, R3; AC1 to AC3)

## Type

AFK.

## Problem

`software-design-principles` names only `references/red-flags.md`
unconditionally, so in real use it is the only reference read. The rules cite
bare section ids that point to no file, and the workflow tells the agent to read
a reference only when it feels it needs the reasoning. Skills that cite this one
also cite bare ids.

## What To Build

- In `SKILL.md`, each moment ("Before changing code", "While writing code",
  "Before reporting the work as done") lists the references to read now, each
  as a condition and a file. Every reference is linked to at least one moment;
  `differences.md` is linked to its condition (two rules pulling apart) at any
  moment. Base the conditions on each reference's "Read this when" opening and
  on the spec's moment table.
- Replace the workflow step that says to read a reference only when the
  reasoning is needed with the triggers. Keep the closing `red-flags.md` step.
- Add a "Read when" column to the section index, and make rule citations name
  the file (`file#id` or a link).
- Define the portable design-reads line
  (`goated-design-reads: <file>, <file>` or
  `goated-design-reads: none: <reason>`, on its own line, written at the start
  of design work in a turn and again when the work changes) and the citation
  convention (the report cites at least one id from each reference read, with
  how it shaped the change or why it did not apply). Both must make sense
  without any adapter.
- Make the citing skills (`tdd`, `design-codebase-architecture`,
  `review-codebase-architecture`, `writing-plans`, `code-refinement`) name the
  reference file with each id they cite, keeping their own fallbacks.
- If a reference's opening disagrees with its new trigger, align the opening.

## Recommended First Reads

- The parent spec, Problem and R1 to R3.
- `skills/engineering/software-design-principles/SKILL.md` and the first lines
  of each file in its `references/`.
- `skills/README.md` (frontmatter, required sections) and `AGENTS.md` (Editing
  Rules, Validation).

## Acceptance Criteria

- [ ] Each moment in `SKILL.md` names the references to read and the condition
      for each; all nine references are linked to a moment.
- [ ] The design-reads line and the citation convention are defined in
      `SKILL.md` and read sensibly with no adapter installed.
- [ ] Every section id cited in `SKILL.md` and in the five citing skills names
      its file.
- [ ] `SKILL.md` stays under 300 lines; the skill keeps its required sections.

## Expected Proof

- The repo checks in `AGENTS.md`.
- A grep showing no bare section-id citations of this skill remain in the
  citing skills.

## Blocked By

- None.

## Scope Exclusions

- The reader-first comment profile (Ticket 049).
- Any adapter or mod change (Tickets 050 to 052).
- Rewriting the references' content beyond their openings.

## Closeout

Completed, merged and archived on 2026-11-16.

- Merged as `632f98d`, with the review fixes in `5a4fe91`: the design-reads
  line's grammar lives in `stack/fixtures/markers/README.md` with its own
  fixtures, the line lists every file whose condition holds, review-only work
  is covered, trigger gaps are filled, and the section-id test rejects
  path-prefixed citations and checks every reference sits in a moment.
- Every check passed on a scratch merge with Ticket 047: the validator, unit
  tests on Python 3.14 and 3.11, and the V1/V2 context comparison.
  `SKILL.md` is 273 lines and stays above the validator's report-only
  1,500-word threshold by design.
- The installed skill and stack copies were synced from main after the
  merge.
