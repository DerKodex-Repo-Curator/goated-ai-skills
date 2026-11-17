# Ticket 070: Fixes After A Review Start With Receiving-Code-Review

## Parent Spec

`docs/specs/2026-11-17-skill-placement-gates.md` (R2, R10; AC2)

## Type

AFK.

## Problem

`receiving-code-review` classifies review feedback as accepted, rejected,
unclear or needing a user decision before anything is changed. It loaded
once in 84 recorded sessions, though tickets were routinely reviewed by a
subagent and then fixed. Agents went from the reviewer's report straight to
edits.

## What To Build

- After a reviewer subagent's result arrives in a turn, the first write to
  a code file inside the project is held until `receiving-code-review`
  counts as loaded. The gate is justified-skip: a skip line naming the
  skill clears it for the turn.
- A reviewer subagent is a spawn whose brief the `spawn` gate's content
  check read as the reviewer template. An implementer subagent, a
  read-only subagent, and a side session trigger nothing.
- The hold has its own gate name, which the README's gate list and the
  skill-usage mod's reading of first lines gain.
- The trigger is stated in the skill's description or the router's map,
  inside the word budgets, and the adapter enforces that statement.
- Update the README's gate table and Hold messages, and regenerate
  `adapters/claude-code/skill-usage/tests/adapter-texts.ts`.

## Recommended First Reads

- The parent spec, R2 and its Constraints.
- `adapters/claude-code/goated_adapter/actions.py` (`check_action`,
  `_spawn_hold`, how a finished spawn is read from the turn).
- `adapters/claude-code/goated_adapter/contracts.py` (`BRIEF_TEMPLATES`).
- `skills/engineering/receiving-code-review/SKILL.md`.
- `adapters/claude-code/README.md`: the gate table, Subagents.

## Acceptance Criteria

- [ ] After a reviewer subagent returns, the first code edit is held until
      the skill counts as loaded.
- [ ] A skip line naming the skill clears the hold for the turn.
- [ ] An edit of a docs file after the review is not held.
- [ ] An implementer subagent's return, and a reviewer spawn that was held
      or failed, hold nothing.
- [ ] A skill load from an earlier turn, still counted, meets the hold.
- [ ] The mod counts the new gate and its outcome.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- `adapters/claude-code/skill-usage/tests/adapter-texts.ts` regenerated; the
  mod's tests pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.

## Blocked By

- `tickets/065-adapter-loads-count-until-compaction.md` (when a skill
  counts as loaded).

## Scope Exclusions

- Review feedback that arrives another way: typed by the user, or from a
  pull request.
- Judging how the feedback was classified.
