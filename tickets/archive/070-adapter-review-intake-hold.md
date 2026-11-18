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
- A reviewer subagent is what Ticket 069 defines and records: a finished
  spawn whose brief matched the reviewer prompt. An implementer subagent,
  a read-only subagent, a subagent briefed from the `handoff` spawn brief,
  and a side session trigger nothing.
- The hold has its own gate name, added the way Ticket 067 added
  `reference-reads`: to the adapter's gate list, the README's gate table,
  and the skill-usage mod's reading of first lines.
- The trigger is stated in `receiving-code-review`'s own text, not in the
  router, which Tickets 072 and 073 edit at its word budget. The adapter
  enforces that statement.
- Update the README's gate table and Hold messages, and regenerate
  `adapters/claude-code/skill-usage/tests/adapter-texts.ts`.

## Recommended First Reads

- The parent spec, R2, the Reviewer subagents paragraph and its
  Constraints.
- The matched-template record from Ticket 069.
- The `reference-reads` gate from Ticket 067, as the pattern for adding a
  gate.
- `adapters/claude-code/goated_adapter/actions.py` (`check_action`, how a
  finished spawn is read from the turn).
- `skills/engineering/receiving-code-review/SKILL.md`.
- `adapters/claude-code/README.md`: the gate table, Subagents.

## Acceptance Criteria

- [ ] After a reviewer subagent returns, the first code edit is held until
      the skill counts as loaded.
- [ ] A skip line naming the skill clears the hold for the turn.
- [ ] An edit of a docs file after the review is not held.
- [ ] An implementer subagent's return, a `handoff`-briefed subagent's
      return, and a reviewer spawn that was held or failed, hold nothing.
- [ ] A skill load from an earlier turn, still counted, meets the hold.
- [ ] The skill's own text states the trigger, inside the context
      comparison's budgets.
- [ ] The mod counts the new gate and its outcome.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- `adapters/claude-code/skill-usage/tests/adapter-texts.ts` regenerated; the
  mod's tests pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.

## Blocked By

- `tickets/archive/069-adapter-closeout-review-and-verification.md` (the record of
  which template a spawn's brief matched).
- `tickets/archive/067-adapter-reference-reads-gate-edit-signals.md` (both add a
  gate to the action check, the README's gate table and the mod's
  first-line reading).

## Scope Exclusions

- Review feedback that arrives another way: typed by the user, or from a
  pull request.
- Judging how the feedback was classified.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `c4cf242` (`585500f`, follow-up `461e87d`).
- Exercised in later sessions; no separate live-check record.
