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

- **Size of the branch's work.** The size measure gains a mode. Today
  `changed_lines` compares two committed refs. The new mode counts changed
  lines between the branch the work will merge into and the working tree:
  committed work on the branch, staged and unstaged changes, and new
  untracked files that git does not ignore. The base is found as the
  `pr-review` gate finds it. The change is large at 400 or more lines, the
  `pr-review` gate's threshold.
  - Measuring the branch, not the commit, means a large ticket split
    across commits is still caught. It also means later commits on a
    large branch raise the item again; the README says so.
  - When git cannot measure, or the checkout is on the base branch with
    nothing to compare, nothing is large.
- **Reviewer subagents.** The `spawn` gate records which brief template a
  spawn's brief matched, by the call's id, in the saved state, as the
  design gates record an edit's references. A reviewer subagent is a
  finished spawn whose brief matched `subagent-driven-development`'s
  reviewer prompt. A review briefed any other way, the `handoff` spawn
  brief included, is not one. Ticket 070 uses the same record.
- **Review item.** The closeout raises a Review item when the branch's
  work is large.
  - It is met by a reviewer subagent that finished after the turn's last
    code change, or by `standards-and-spec-review` counting as loaded and a
    change read after the last change.
  - Its text says to brief the reviewer from the reviewer prompt.
  - Its skip line names `standards-and-spec-review`.
- **Verification item.** The closeout raises a Verification item when any
  of these holds: the task's route is `full`; a subagent changed code; a
  security-sensitive file changed; or the branch's work is large.
  - It is met when `verification-before-completion` counts as loaded.
  - Its skip line names that skill. The Proof item uses the same skip
    line, so one line answers both; the README says so.
- Both items join the commit-time list, and the `Stop` closeout keeps them
  as a backstop.
- **Portable statement.** The threshold, what is measured, and the four
  triggers are stated in the two skills' own text or the shared policy,
  inside their word budgets, and the adapter enforces that statement.
- Update the README's closeout table, Large pull requests, State and Hold
  messages text, and regenerate
  `adapters/claude-code/skill-usage/tests/adapter-texts.ts`.

## Recommended First Reads

- The parent spec, R1, R3, the Reviewer subagents paragraph and its
  Constraints.
- `adapters/claude-code/goated_adapter/actions.py` (`check_closeout`,
  `_code_items`, `_pr_review_hold`, `changed_lines`, `_Changes`,
  `_spawn_hold`).
- `adapters/claude-code/goated_adapter/contracts.py` (`BRIEF_TEMPLATES`).
- `adapters/claude-code/goated_adapter/state.py` (`design_edits`, for how
  a per-call record is kept).
- `adapters/claude-code/README.md`: the closeout table, Large pull
  requests, Closeout at commit.
- `skills/engineering/verification-before-completion/SKILL.md` and
  `skills/engineering/standards-and-spec-review/SKILL.md`.

## Acceptance Criteria

- [ ] A commit on a branch whose work against its base is 400 or more
      lines, with no review, is held by the closeout, listing the Review
      item. A 399-line branch raises none.
- [ ] Uncommitted changes and new untracked files count toward the size;
      an ignored file does not.
- [ ] Two 300-line commits on one branch raise the item at the second.
- [ ] A reviewer subagent that finished after the last code change meets
      the item; one that finished before a later change does not, and a
      subagent briefed from the `handoff` spawn brief does not.
- [ ] The skill load and a change read after the last change meet it; the
      load alone does not.
- [ ] Each Verification trigger raises the item alone: a `full` route, a
      subagent's code change, a sensitive file change, a large branch. A
      turn with none of them raises none.
- [ ] A skip line naming `verification-before-completion` clears both the
      Verification and Proof items.
- [ ] With git unable to measure, or on the base branch, no Review item is
      raised and the other items are unchanged.
- [ ] The `pr-review` gate measures a pull request as before.
- [ ] The threshold and triggers appear in portable text, and the mod
      counts the closeout hold as before.

## Expected Proof

- Adapter tests for each criterion, each with a near miss; the size tests
  run against a real scratch repository.
- `adapters/claude-code/skill-usage/tests/adapter-texts.ts` regenerated; the
  mod's tests pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, including the
  context comparison.
- A live check: one real session that commits on a branch of 400 or more
  changed lines.

## Blocked By

- `tickets/065-adapter-loads-count-until-compaction.md` (when a skill
  counts as loaded, the closeout items, and the `spawn` gate it changes).

## Scope Exclusions

- The `pr-review` gate's behaviour.
- Judging the quality of a review.
- Review or verification inside a subagent.
- Recognising a review that does not use the reviewer prompt.
