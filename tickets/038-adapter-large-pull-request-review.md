# Ticket 038: Adapter Review Item For Large Pull Requests

## Parent Spec

`docs/specs/2026-11-16-adapter-skill-activation-gates.md` (G4)

## Type

HITL. The maintainer decides how the adapter learns a change's size.

## What To Build

Give the `pull-request` gate a second, justified-skip item: when the change
the pull request opens is large, it also needs `standards-and-spec-review`
loaded in the turn, or a skip line naming it. The existing `pr-description`
requirement stays strict.

Settle the spec's G4 open question with the maintainer first: how the adapter
learns the change's size, within the hook latency budget. Provisional
threshold: 400 or more changed lines against the base branch.

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

- [ ] A pull request over the threshold with `pr-description` loaded is
      held for the review item; one under it is not.
- [ ] The strict `pr-description` requirement is unchanged.
- [ ] The review item's hold has the first line
      `goated-hold: pull-request | justified-skip` and backticks only
      `standards-and-spec-review`.
- [ ] The size check stays within the adapter's measured latency budget.
- [ ] The adapter README's gate table describes the new item.
- [ ] Loading `standards-and-spec-review` in the turn, a skip line naming it, and a typed
      `skip standards-and-spec-review` override each clear it.
- [ ] `tests/adapter-texts.ts` is regenerated with the new hold text, and the
      skill-usage mod records the outcome for `standards-and-spec-review`.

## Expected Proof

- Adapter tests driving the hook with recorded-shape transcripts: a hold on
  the trigger, none on each near miss, and each way to clear it.
- `uv run python -m unittest discover -s tests`,
  `uv run python scripts/validate_skills.py`, and `claude plugin test .` in
  the mod folder.

## Blocked By

- `tickets/033-adapter-real-use-trial.md` (the trial's keep decision)

## Scope Exclusions

- Reviewing the pull request itself: that is the skill's work.
- Changes to any existing gate's behaviour or to the hold format.
