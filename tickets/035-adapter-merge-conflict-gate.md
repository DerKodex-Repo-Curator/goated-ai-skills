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
- `tickets/046-adapter-pipeline-after-compaction.md`, the last of the trial's
  revise fixes (041–046), which edit the same files
- `tickets/052-adapter-design-citations-at-closeout.md`, the last of the
  design reference reads tickets (051–052), which edit the same files
  (`actions.py` and the hold texts)

## Scope Exclusions

- Conflict detection from repository state on disk, unless the G1 decision adds it.
- Changes to any existing gate's behaviour or to the hold format.
