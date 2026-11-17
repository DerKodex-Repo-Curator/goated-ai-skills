# Ticket 061: Change Reads Without Needless Re-Reads

## Parent Spec

`docs/specs/2026-11-17-adapter-hook-friction.md` (R2, R3; AC2, AC3)

## Type

AFK.

## Problem

Two rules ask an agent to read a change again when nothing new has
happened:

- **Load order.** The commit, pull request and Docs checks count a change
  read only when it follows both the skill load and the turn's last project
  change. An agent that read its diff, then loaded `commit-message` with no
  change between, must read the same diff again.
- **Comment-only edits.** The Design item's red-flags read must follow the
  last change, and any edit to a code file counts as a change. Fixing a
  comment the red-flags scan pointed out reopens the item, so the agent has
  to read the red flags and the change again.

## What To Build

- For the commit, pull request and Docs checks, a change read counts when it
  follows the turn's last project change, before or after the skill load.
- The Design item keeps its order, red flags then change read. This is one
  of the parts the agents said to keep.
- An edit whose added and removed text is only comments and docstrings
  doesn't move the last change that the Design item's red-flags read must
  follow. Use the comment rules `design_reads.py` already has; an edit those
  rules can't read counts as a change.
- Proof and Docs still treat a comment-only edit as a change.
- Update the hold and item texts that say "after loading", and the README's
  Change reads section.

## Recommended First Reads

- The parent spec, R2 and R3.
- `adapters/claude-code/goated_adapter/actions.py` (`_change_read_hold`,
  `_code_items`, `_Changes`).
- `adapters/claude-code/goated_adapter/design_reads.py` (`_Added`, comment
  stripping).
- `adapters/claude-code/README.md`: Change reads.

## Acceptance Criteria

- [ ] A diff read, then a `commit-message` load, with no change between,
      passes the commit's change-read step. The same holds for
      `pr-description` and the Docs item.
- [ ] A change after the read still needs a new read.
- [ ] After the red flags and change reads, a comment-only `Edit` doesn't
      reopen the Design item. An edit that also changes code does, and so
      does a comment-only `Write` that replaces a file's code.
- [ ] Proof still needs a check after a comment-only edit that is the turn's
      only change.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- `adapters/claude-code/skill-usage/tests/adapter-texts.ts` regenerated if hold texts change; the mod's tests
  pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.

## Blocked By

- `tickets/054-adapter-overrides-pasted-text-and-commit-skip.md` (the commit
  hold).
- `tickets/052-adapter-design-citations-at-closeout.md` (the Design item).

## Scope Exclusions

- The Design item's order.
- Comment-only edits for Proof or Docs.
