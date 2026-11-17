# Ticket 062: Closeout Items Are Held At The Commit

## Parent Spec

`docs/specs/2026-11-17-adapter-hook-friction.md` (R1; AC1, AC14)

## Type

AFK.

## Problem

The closeout hold runs only from the `Stop` hook, after the agent has written
its final report. All three agents that gave feedback hit this. Their report
was split in two, and the part after the hold can fall outside the 400
characters a parent session sees of a side session's report. Agents almost
always commit before they report, so the commit is the natural point to meet
the closeout.

## What To Build

- A commit (a git commit in a shell call, or a commit tool) whose own commit
  hold is met is held while the turn has unmet closeout items. Those are
  Proof, Unfinished, Docs, Design (with Ticket 052's citations), Security and
  Setup.
- The hold uses the closeout's first line,
  `goated-hold: closeout | justified-skip`, and the closeout's item texts.
  Each item accepts its usual skip line.
- The `Stop` closeout stays as a backstop. An item met before the commit
  stays met, since a commit changes no file. A turn that never commits meets
  the closeout only at `Stop`.
- The skill-usage mod counts a closeout hold on a commit call as it counts
  one at `Stop`.
- Update the README's closeout and commit text.

## Recommended First Reads

- The parent spec, R1.
- `adapters/claude-code/goated_adapter/actions.py` (`check_action`,
  `_commit_hold`, `check_closeout`).
- `adapters/claude-code/goated_adapter/hooks.py` (`_pre_tool_use`, `_stop`,
  for the subagent list and `last_assistant_message` the closeout takes).
- `adapters/claude-code/skill-usage/` hook classification, for how a
  closeout hold is counted.
- `adapters/claude-code/README.md`: closeout, commit and Hold messages.

## Acceptance Criteria

- [ ] A commit made while a closeout item is unmet is held with the closeout
      first line, listing that item.
- [ ] Meeting or skipping the item lets the commit through, and the `Stop`
      that follows passes.
- [ ] A commit whose own commit-message hold is unmet gets that hold first,
      unchanged.
- [ ] A turn that changes code and never commits is held at `Stop` as
      today.
- [ ] Ticket 052's citation item appears in the commit-time list when it is
      unmet.
- [ ] The mod counts the commit-time closeout hold.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The mod's tests pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- A live check: one real session that commits after code changes.

## Blocked By

- `tickets/061-adapter-change-reads-without-rereads.md` (the commit hold and
  closeout items).
- `tickets/052-adapter-design-citations-at-closeout.md` (its item joins the
  list).

## Scope Exclusions

- Moving the closeout of turns that never commit.
- A non-blocking reminder after the commit.
