# Ticket 059: Closeout Before The Report, With No Needless Re-Reads

## Parent Spec

`docs/specs/2026-11-17-adapter-hook-friction.md` (R1, R2, R3; AC1, AC2, AC3,
AC14)

## Type

AFK.

## Problem

- **Timing.** The closeout hold runs only from the `Stop` hook, after the
  agent has written its final report. All three agents that gave feedback
  hit this. Their report was split in two, and the part after the hold can
  fall outside the 400 characters a parent session sees of a side session's
  report. Agents almost always commit before they report, so the commit is
  the natural point to meet the closeout.
- **Load order.** The commit, pull request and Docs checks count a change
  read only when it follows both the skill load and the turn's last project
  change. An agent that read its diff, then loaded `commit-message` with no
  change between, must read the same diff again.
- **Comment-only edits.** The Design item's red-flags read must follow the
  last change, and any edit to a code file counts as a change. Fixing a
  comment the red-flags scan pointed out reopens the item, so the agent has
  to read the red flags and the change again.

All three rules live in the commit hold and the closeout items, so they
change together.

## What To Build

- **Change reads in any order.** For the commit, pull request and Docs
  checks, a change read counts when it follows the turn's last project
  change, before or after the skill load. The Design item keeps its order,
  red flags then change read, which is one of the parts the agents said to
  keep.
- **Comment-only edits.** An edit whose added and removed text is only
  comments and docstrings doesn't move the last change that the Design
  item's red-flags read must follow. Use the comment rules `design_reads.py`
  already has; an edit those rules can't read counts as a change. Proof and
  Docs still treat a comment-only edit as a change.
- **Closeout at commit.** A commit (a git commit in a shell call, or a commit
  tool) whose own commit hold is met is held while the turn has unmet
  closeout items. Those are Proof, Unfinished, Docs, Design (with Ticket
  052's citations), Security and Setup.
  - The hold uses the closeout's first line,
    `goated-hold: closeout | justified-skip`, and the closeout's item texts.
    Each item accepts its usual skip line.
  - The `Stop` closeout stays as a backstop. An item met before the commit
    stays met, since a commit changes no file. A turn that never commits
    meets the closeout only at `Stop`.
  - The skill-usage mod counts a closeout hold on a commit call as it counts
    one at `Stop`.
- Update the hold and item texts that say "after loading", the README's
  closeout, commit, Change reads and Hold messages text, and regenerate
  `adapters/claude-code/skill-usage/tests/adapter-texts.ts`.

## Recommended First Reads

- The parent spec, R1 to R3.
- `adapters/claude-code/goated_adapter/actions.py` (`check_action`,
  `_commit_hold`, `_change_read_hold`, `check_closeout`, `_code_items`,
  `_Changes`).
- `adapters/claude-code/goated_adapter/design_reads.py` (`_Added`, comment
  stripping).
- `adapters/claude-code/goated_adapter/hooks.py` (`_pre_tool_use`, `_stop`,
  for the subagent list and `last_assistant_message` the closeout takes).
- `adapters/claude-code/skill-usage/` hook classification, for how a
  closeout hold is counted.
- `adapters/claude-code/README.md`: closeout, commit, Change reads and Hold
  messages.

## Acceptance Criteria

- [ ] A diff read, then a `commit-message` load, with no change between,
      passes the commit's change-read step. The same holds for
      `pr-description` and the Docs item. A change after the read still
      needs a new read.
- [ ] After the red flags and change reads, a comment-only `Edit` doesn't
      reopen the Design item. An edit that also changes code does, and so
      does a comment-only `Write` that replaces a file's code.
- [ ] Proof still needs a check after a comment-only edit that is the turn's
      only change.
- [ ] A commit made while a closeout item is unmet is held with the closeout
      first line, listing that item. Meeting or skipping the item lets the
      commit through, and the `Stop` that follows passes.
- [ ] A commit whose own commit-message hold is unmet gets that hold first,
      unchanged.
- [ ] A turn that changes code and never commits is held at `Stop` as today.
- [ ] Ticket 052's citation item appears in the commit-time list when it is
      unmet.
- [ ] The mod counts the commit-time closeout hold.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- `adapters/claude-code/skill-usage/tests/adapter-texts.ts` regenerated; the
  mod's tests pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- A live check: one real session that commits after code changes.

## Blocked By

- `tickets/archive/054-adapter-overrides-pasted-text-and-commit-skip.md` (the commit
  hold).
- `tickets/052-adapter-design-citations-at-closeout.md` (the Design item; its
  item joins the commit-time list).

## Scope Exclusions

- The Design item's order.
- Comment-only edits for Proof or Docs.
- Moving the closeout of turns that never commit.
- A non-blocking reminder after the commit.
