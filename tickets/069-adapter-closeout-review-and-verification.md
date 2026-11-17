# Ticket 069: The Closeout Asks For Review And Verification On Large Or Risky Work

## Parent Spec

`docs/specs/2026-11-17-skill-placement-gates.md` (R1, R3, R10; AC1, AC3)

## Type

AFK.

## Problem

- **Review.** The `pr-review` gate holds a large pull request, but work is
  often merged locally with no pull request, so the gate never fired in 84
  recorded sessions. `standards-and-spec-review` loaded in one of them. A
  reviewer, not a hold, caught Ticket 059's high-severity bug.
- **Verification.** `verification-before-completion` is for complex,
  high-risk, delegated or multi-surface work. It loaded in four sessions,
  nearly always by the agent's own choice.

Both are new closeout items judged on the same change, so they are built
together.

## What To Build

- **Review item.** The closeout raises a Review item when the change since
  the last commit is large: 400 or more changed lines, measured by git as
  the `pr-review` gate measures a pull request. One definition of large
  serves both.
  - It is met by a reviewer subagent that finished after the turn's last
    code change, or by `standards-and-spec-review` counting as loaded and a
    change read after the last change.
  - A reviewer subagent is a spawn whose brief the `spawn` gate's content
    check read as the reviewer template.
  - Its skip line names `standards-and-spec-review`.
  - When git cannot measure the change, the item is not raised.
- **Verification item.** The closeout raises a Verification item when any
  of these holds: the task's route is `full`; a subagent changed code; a
  security-sensitive file changed; or the change is large, as above.
  - It is met when `verification-before-completion` counts as loaded.
  - Its skip line names that skill. The Proof item uses the same skip
    line, so one line answers both; the README says so.
- Both items join the commit-time list, and the `Stop` closeout keeps them
  as a backstop.
- **Portable statement.** The threshold and the four triggers are stated in
  the two skills' own text or the shared policy, inside their word budgets,
  and the adapter enforces that statement.
- Update the README's closeout table, Large pull requests and Hold messages
  text, and regenerate
  `adapters/claude-code/skill-usage/tests/adapter-texts.ts`.

## Recommended First Reads

- The parent spec, R1, R3 and its Constraints.
- `adapters/claude-code/goated_adapter/actions.py` (`check_closeout`,
  `_code_items`, `_pr_review_hold`, `changed_lines`, `_Changes`,
  `_spawn_hold`).
- `adapters/claude-code/goated_adapter/contracts.py` (`BRIEF_TEMPLATES`).
- `adapters/claude-code/README.md`: the closeout table, Large pull
  requests, Closeout at commit.
- `skills/engineering/verification-before-completion/SKILL.md` and
  `skills/engineering/standards-and-spec-review/SKILL.md`.

## Acceptance Criteria

- [ ] A commit of a change of 400 or more lines with no review is held by
      the closeout, listing the Review item. A 399-line change raises none.
- [ ] A reviewer subagent that finished after the last code change meets
      the item; one that finished before a later change does not.
- [ ] The skill load and a change read after the last change meet it; the
      load alone does not.
- [ ] Each Verification trigger raises the item alone: a `full` route, a
      subagent's code change, a sensitive file change, a large change. A
      turn with none of them raises none.
- [ ] A skip line naming `verification-before-completion` clears both the
      Verification and Proof items.
- [ ] With git unable to measure the change, no Review item is raised and
      the other items are unchanged.
- [ ] The threshold and triggers appear in portable text, and the mod
      counts the closeout hold as before.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- `adapters/claude-code/skill-usage/tests/adapter-texts.ts` regenerated; the
  mod's tests pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, including the
  context comparison.
- A live check: one real session that commits a change of 400 or more
  lines.

## Blocked By

- `tickets/065-adapter-loads-count-until-compaction.md` (when a skill
  counts as loaded, and the closeout items it changes).

## Scope Exclusions

- The `pr-review` gate.
- Judging the quality of a review.
- Review or verification inside a subagent.
