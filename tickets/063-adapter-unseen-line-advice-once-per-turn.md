# Ticket 063: The Unseen-Line Advice Is Given In Full Once Per Turn

## Parent Spec

`docs/specs/2026-11-17-adapter-hook-friction.md` (R8, R14; AC9)

## Type

AFK.

## Problem

Every hold that a route, skip or design-reads line can clear ends with the
same advice, about 95 words, on why a line in reply text may not be seen and
where to put it instead. Those holds are pipeline, route-line, security,
conflict-resolution, repeated-failure, design, design-reads, and the
skippable change-read holds. An agent that meets three holds in a turn reads
it three times.

## What To Build

- The first hold in a turn that carries the advice gives it in full. Later
  holds in that turn give one sentence pointing to the call fields, such as
  "Put the line in a shell or agent call's description or a Skill call's
  args."
- Whether the full text was shown is read from the turn's earlier held
  results, not new state. The full text returns in the next turn.
- Hold first lines don't change. The short form keeps the typed override
  (`skip routing`, `skip <skill>`) the full form names.
- Update the README's Hold messages section and regenerate
  `adapters/claude-code/skill-usage/tests/adapter-texts.ts`.

## Recommended First Reads

- The parent spec, R8.
- `adapters/claude-code/goated_adapter/gates.py` (`unseen_line_advice`) and
  each of its callers.
- `adapters/claude-code/goated_adapter/transcript.py` (`Call.held`,
  `HOLD_RESULT_RE`).
- `adapters/claude-code/README.md`: Hold messages.

## Acceptance Criteria

- [ ] A turn's first such hold carries the full advice.
- [ ] A second such hold in the same turn carries the one-sentence form and
      the typed override.
- [ ] The first such hold of the next turn carries the full text again.
- [ ] A hold that never carried the advice is unchanged.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- `adapters/claude-code/skill-usage/tests/adapter-texts.ts` regenerated; the mod's tests pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- A live check: one real session that meets two such holds in a turn.

## Blocked By

- `tickets/054-adapter-overrides-pasted-text-and-commit-skip.md`
- `tickets/055-adapter-router-first-read-only-commands.md`
- `tickets/057-adapter-repeated-failure-ignores-import-errors.md`
- `tickets/058-adapter-design-gate-skips-test-files.md`
- `tickets/060-adapter-read-only-subagents-pass-spawn-gates.md`
- `tickets/061-adapter-change-reads-without-rereads.md`
- `tickets/062-adapter-closeout-items-at-commit.md`

These change hold texts and their callers, so this ticket runs last.

## Scope Exclusions

- Hold first lines.
- Other hold wording.
