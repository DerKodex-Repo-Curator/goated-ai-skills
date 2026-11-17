# Ticket 035: Adapter Merge-Conflict Gate

## Parent Spec

`docs/specs/2026-11-16-adapter-skill-activation-gates.md` (G1)

## Type

AFK.

## What To Build

Add the `conflict-resolution` action gate. It holds a write to a file while a
conflict is open in the turn: an `Edit` whose old text holds conflict markers
at line starts, or any write after a merge, rebase, cherry-pick, revert, or
pull whose result in the turn reports a conflict. A conflicting stash pop or
apply is left alone: the skill's description does not cover it (spec G1).

Settle the spec's G1 open question first. Provisional default: no read of
repository state on disk, so the gate stays a pure function of the turn.

## Recommended First Reads

- The spec's Requirements, Constraints, and Open Questions.
- The adapter README (`adapters/claude-code/README.md`): What It Holds, Hold
  messages, User Overrides, State, Latency.
- The action and closeout gates in `adapters/claude-code/goated_adapter/actions.py`
  and their tests in `tests/test_claude_code_adapter_actions.py`.
- The skill-usage mod's gate names in
  `adapters/claude-code/skill-usage/hooks/meaning.ts`, and the hold-text
  generator `tests/test_skill_usage_mod.py`.

## Acceptance Criteria

- [ ] An `Edit` whose old text holds `<<<<<<<` and `>>>>>>>` lines is held;
      one that only mentions the markers mid-line is not.
- [ ] A write after a conflicting `git merge` result in the turn is held; a
      write after a clean merge is not.
- [ ] The hold's first line is `goated-hold: conflict-resolution | justified-skip`,
      and its text backticks only `resolving-merge-conflicts`.
- [ ] The adapter README's gate table and hold-message gate list name it, and
      the mod shows it as "conflict-resolution hold", apart from the earlier
      hooks' `merge-conflict` counts.
- [ ] Loading `resolving-merge-conflicts` in the turn, a skip line naming it, and a typed
      `skip resolving-merge-conflicts` override each clear it.
- [ ] `tests/adapter-texts.ts` is regenerated with the new hold text, and the
      skill-usage mod records the outcome for `resolving-merge-conflicts`.

## Expected Proof

- Adapter tests driving the hook with recorded-shape transcripts: a hold on
  the trigger, none on each near miss, and each way to clear it.
- `uv run python -m unittest discover -s tests`,
  `uv run python scripts/validate_skills.py`, and `claude plugin test .` in
  the mod folder.

## Blocked By

- `tickets/archive/033-adapter-real-use-trial.md` (the trial's keep decision)

Other adapter tickets edit the same files (`actions.py`, the README's gate
tables, the hold texts, the mod's gate names) but none is a dependency; the
gates are additive, so whichever merges later resolves the overlap.

## Scope Exclusions

- Conflict detection from repository state on disk, unless the G1 decision adds it.
- Changes to any existing gate's behaviour or to the hold format.

## Closeout

Completed, merged and archived on 2026-11-17.

- Merged as `ee47a71` (`8779920`, review fixes `89fbdc2`, `7ad9002`). G1 was
  settled as turn-only: no read of repository state on disk.
- The gate holds a write while a conflict is open in the turn, wherever the
  file is; `git checkout --theirs/--ours` counts as a write; a Write over a
  file a Read showed with markers is held; an abort, continue, skip or commit
  ends the conflict; label-less CRLF markers count.
- Every check passed on the combined branch before the fast-forward: the validator, 473 unit tests on Python 3.14 and 3.11, the V1/V2 context comparison, `claude plugin validate`, 157 mod tests, and the TypeScript check with only the 5 known errors in `tests/register.test.tsx`.
- Known limit, in the README: a lone `=======` in a file not read this turn
  is not held.
