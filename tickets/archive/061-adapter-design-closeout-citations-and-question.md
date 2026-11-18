# Ticket 061: Design Citations Count From Call Fields, And The Red Flags Ask A Question

## Parent Spec

`docs/specs/2026-11-17-adapter-written-line-holds.md` (R1, R6, R8, R9; AC1,
AC2, AC9, AC11)

## Type

AFK.

## Problem

- **Citations.** The closeout's Design citations item reads citations only
  from reply text. Before a commit, every message of the turn also makes a
  tool call, and Claude Code can store such a message's text as a summary
  with no `file#id` in it. The Ticket 060 session shows this: the agent
  cited in reply text, was held, cited in the commit call's `description`,
  was held again, and cleared the hold with a skip line. The hold never
  says a `description` does not count, and at commit it says "in your
  report", which is not written yet.
- **Red flags.** The Design red-flags item is met by reading a file and the
  diff. Nothing in it prompts a concrete finding. A reviewer, not a hold,
  caught Ticket 059's high-severity bug.
- **Restores.** Proof asks for a rerun after `git checkout -- <file>`
  restored unchanged content. The adapter cannot see content, and the
  README does not say so.

All three are the closeout's Design and Proof items and their texts, so
they change together.

## What To Build

- **Citations from call fields.** The Design citations item counts a
  `file#id` citation in the fields that carry route and skip lines
  (`LINE_FIELDS`): the `description` of a shell or agent call, and the
  `args` of a Skill call. Any call of the turn counts, the held commit call
  included, and a held call's field counts as its lines do. Reply text
  still counts. No other field counts.
- **Item text.** The item names those fields. Its commit-time text asks for
  the citation in the commit call's description and does not say "in your
  report". It names the fields without backticks, as the unseen-line advice
  does, so the skill-usage mod reads no skill from them.
- **The question.** `red-flags.md` ends with one question: name one input
  that would break this change, and say what happens. The Design red-flags
  item repeats it. Nothing checks an answer.
- **Restores.** Known Limits says a restore command counts as a change
  whatever it restores, so Proof asks for a check after it, and that a
  rerun or a skip line answers it.
- Update the README's closeout table, Design references, Hold messages and
  Known Limits text, the mod's README where it describes citations, and
  regenerate `adapters/claude-code/skill-usage/tests/adapter-texts.ts`.

## Recommended First Reads

- The parent spec, R1, R6 and R8.
- `adapters/claude-code/goated_adapter/actions.py` (`_uncited_references`,
  `_code_items`, `_Proof`, `check_closeout`).
- `adapters/claude-code/goated_adapter/transcript.py` (`LINE_FIELDS`,
  `call_line_text`, `Turn.add_call`).
- `adapters/claude-code/goated_adapter/design_reads.py` (`citations`).
- `skills/engineering/software-design-principles/references/red-flags.md`
  and the Section Index in that skill's `SKILL.md`.
- `adapters/claude-code/README.md`: the closeout table, Design references,
  Hold messages, Known Limits.

## Acceptance Criteria

- [ ] A commit held for an uncited reference passes when retried with a
      citation of that reference in its `description`.
- [ ] A citation in an earlier call's `description`, or in a Skill call's
      `args`, counts. One in a command, an edit's text, or an MCP tool's
      `description` does not.
- [ ] A citation in the final reply still clears the item at `Stop`.
- [ ] The item names the call fields, and its commit-time text does not say
      "in your report".
- [ ] `red-flags.md` and the Design red-flags item carry the question, and
      no hold depends on an answer.
- [ ] `red-flags.md` gains no section id, or the Section Index gains it too.
- [ ] Known Limits names the restore case.

## Expected Proof

- Adapter tests for each behaviour criterion, each with a near miss.
- `adapters/claude-code/skill-usage/tests/adapter-texts.ts` regenerated; the
  mod's tests pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, including the
  context comparison for the changed reference.
- A live check: one real session that commits after a design edit and
  clears the citations item from the commit call's description.

## Blocked By

None.

## Scope Exclusions

- Judging the quality of a citation or of an answer to the question.
- Reading file contents to tell whether a restore changed anything.
- Moving the citations item out of the commit-time list.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `dbd2575` (`36e8cd7`, follow-up `de41e8c`).
- Exercised in later sessions; no separate live-check record.
