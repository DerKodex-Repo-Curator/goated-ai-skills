# Ticket 038: Adapter Review Item For Large Pull Requests

## Parent Spec

`docs/specs/2026-11-16-adapter-skill-activation-gates.md` (G4)

## Type

HITL. The maintainer decides how the adapter learns a change's size.

## What To Build

Add the `pr-review` action gate, justified-skip. It holds the pull-request
commands the `pull-request` gate holds, once that gate has passed, when the
change the pull request opens is large; it clears when
`standards-and-spec-review` loads in the turn, or on a skip line naming it.
The `pull-request` gate and its strict `pr-description` requirement stay as
they are.

Settle the spec's G4 open question with the maintainer first: how the adapter
learns the change's size, within the hook latency budget. Provisional
threshold: 400 or more changed lines against the base branch. The portable
text says "large" with no number (spec G4): either put the threshold into the
skill's description or the shared policy first, or record it in the adapter
README as a documented stand-in, as the design gate's five lines are.

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
      held by `pr-review`; one under it is not.
- [ ] The `pull-request` gate and its strict `pr-description` requirement are
      unchanged.
- [ ] Like the other review holds (ticket 041), `pr-review` also needs a
      read of the change after `standards-and-spec-review` loads.
- [ ] The hold's first line is `goated-hold: pr-review | justified-skip`, and
      its text backticks only `standards-and-spec-review`.
- [ ] The threshold is grounded in portable text or recorded as a documented
      stand-in, as the spec's G4 says.
- [ ] The size check stays within the adapter's measured latency budget.
- [ ] The adapter README's gate table and hold-message gate list name it, and
      the mod shows it as "pr-review hold".
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

- `tickets/archive/033-adapter-real-use-trial.md` (the trial's keep decision)
- `tickets/041-adapter-review-holds-read-the-change.md` (the change read
  this gate also requires)

## Scope Exclusions

- Reviewing the pull request itself: that is the skill's work.
- Changes to the hold format, or to the `pull-request` gate.
