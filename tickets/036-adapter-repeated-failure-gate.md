# Ticket 036: Adapter Repeated-Failure Gate

## Parent Spec

`docs/specs/2026-11-16-adapter-skill-activation-gates.md` (G2)

## Type

AFK.

## What To Build

Add the `repeated-failure` action gate. It holds the next write after the same
check command, as the closeout gate recognises checks, has failed twice in the
turn.

Settle the spec's G2 open question first: whether "the same command" means
the same command text or the same check tool.

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

- [ ] Two failing runs of the same check, then a write: held.
- [ ] One failure, or two failures of different checks, then a write: not
      held.
- [ ] The hold's first line is `goated-hold: repeated-failure | justified-skip`, and
      its text backticks only `diagnose`.
- [ ] The adapter README's gate table and hold-message gate list name it, and
      the mod shows it as "repeated-failure hold", apart from the earlier
      hooks' `diagnose` counts.
- [ ] Loading `diagnose` in the turn, a skip line naming it, and a typed
      `skip diagnose` override each clear it.
- [ ] `tests/adapter-texts.ts` is regenerated with the new hold text, and the
      skill-usage mod records the outcome for `diagnose`.

## Expected Proof

- Adapter tests driving the hook with recorded-shape transcripts: a hold on
  the trigger, none on each near miss, and each way to clear it.
- `uv run python -m unittest discover -s tests`,
  `uv run python scripts/validate_skills.py`, and `claude plugin test .` in
  the mod folder.

## Blocked By

- `tickets/archive/033-adapter-real-use-trial.md` (the trial's keep decision)

## Scope Exclusions

- Flaky-test detection beyond the two-failure threshold.
- Changes to any existing gate's behaviour or to the hold format.
