# Ticket 062: Parallel Holds Share One Full Unseen-Line Advice

## Parent Spec

`docs/specs/2026-11-17-adapter-written-line-holds.md` (R2, R9; AC3)

## Type

AFK.

## Problem

Ticket 060 gives the full unseen-line advice, about 95 words, once per turn
by looking for it in the turn's earlier held results. Calls held in
parallel have no result yet when their hooks run, so each carries the full
text. Four parallel edits meant four copies.

## What To Build

- At most one hold in a turn carries the full advice, holds on parallel
  calls included. The first hold claims a per-turn marker atomically, so
  two hooks running at once cannot both claim it. Every other hold in that
  turn carries the one-sentence form, with the typed override it names
  today.
- The marker replaces the read from held results, so the advice has one
  mechanism. It lives with the adapter's session state and is cleared with
  it.
- When the marker cannot be claimed or read, the hold carries the full
  advice.
- The next turn's first such hold carries the full text again. Hold first
  lines and holds that never carried the advice don't change.
- Update the README's Hold messages and State sections and regenerate
  `adapters/claude-code/skill-usage/tests/adapter-texts.ts` if a text
  changed.

## Recommended First Reads

- The parent spec, R2.
- `adapters/claude-code/goated_adapter/gates.py` (`unseen_line_advice`,
  `FULL_ADVICE_OPENING`) and each caller.
- `adapters/claude-code/goated_adapter/state.py` (where session state
  lives, and how it is cleared).
- `adapters/claude-code/README.md`: Hold messages, State, and the Known
  Limits note on parallel hooks racing on the state file.
- `tickets/060-adapter-unseen-line-advice-once-per-turn.md`.

## Acceptance Criteria

- [ ] Of four such holds made for one turn before any has a result, exactly
      one carries the full advice.
- [ ] A later hold in the same turn carries the one-sentence form and the
      typed override.
- [ ] The first such hold of the next turn carries the full text again.
- [ ] With the marker's folder unwritable, each hold carries the full text
      and no hook fails.
- [ ] A hold that never carried the advice is unchanged.

## Expected Proof

- Adapter tests for each criterion, each with a near miss; the parallel
  case runs the hook entry point concurrently.
- The mod's tests pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- A live check: one real session that makes parallel held calls.

## Blocked By

None.

## Scope Exclusions

- The advice's wording.
- Hold first lines.
- Merging parallel holds into one hold.
