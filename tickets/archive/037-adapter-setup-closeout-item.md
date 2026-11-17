# Ticket 037: Adapter Setup Closeout Item

## Parent Spec

`docs/specs/2026-11-16-adapter-skill-activation-gates.md` (G3)

## Type

AFK.

## What To Build

Add a **Setup** item to the closeout gate. It applies when the turn
installed or added a dependency or tool by a command that names a package, or
wrote an environment or settings file. It is met when `setup-scribe` loads in
the turn, or by a skip line naming it.

## Decisions

Settled with the maintainer on 2026-11-16:

- Spec open question G3: a bare install that names no package (`npm install`,
  `pip install -r requirements.txt`) is not a setup change.
- Env and settings files count wherever they are, inside the project or not,
  since machine and application settings are setup too.
- The env and settings files are the spec's list only: `.env` and `.env.*`,
  and `settings*.json` under `.claude/` or `.vscode/`.

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

- [ ] A turn that ran `uv add <package>`, or wrote `.env.local`, gets the
      Setup item at closeout.
- [ ] A turn that ran a bare `npm install`, or only edited code, does not.
- [ ] The item's text backticks only `setup-scribe`, and the closeout hold
      keeps its first line, `goated-hold: closeout | justified-skip`.
- [ ] The adapter README's closeout items table lists it.
- [ ] Loading `setup-scribe` in the turn, a skip line naming it, and a typed
      `skip setup-scribe` override each clear it.
- [ ] `tests/adapter-texts.ts` is regenerated with the new hold text, and the
      skill-usage mod records the outcome for `setup-scribe`.

## Expected Proof

- Adapter tests driving the hook with recorded-shape transcripts: a hold on
  the trigger, none on each near miss, and each way to clear it.
- `uv run python -m unittest discover -s tests`,
  `uv run python scripts/validate_skills.py`, and `claude plugin test .` in
  the mod folder.

## Blocked By

- `tickets/archive/033-adapter-real-use-trial.md` (the trial's keep decision)

## Scope Exclusions

- Recording the setup itself: that is `setup-scribe`'s work, not the gate's.
- Changes to the hold format, or to what the closeout gate already holds
  and how its other items clear.

## Closeout

Completed, merged and archived on 2026-11-17.

- Merged as `f9aef03` (`22e464b`, review fixes `cb51722`).
- The Setup item applies after a command that names a package to install, or
  a write to an environment or settings file, wherever the file is. Each
  package manager has its own value-taking options; a subagent's own
  `setup-scribe` load or skip line meets the setup it changed.
- Every check passed on the combined branch before the fast-forward: the validator, 473 unit tests on Python 3.14 and 3.11, the V1/V2 context comparison, `claude plugin validate`, 157 mod tests, and the TypeScript check with only the 5 known errors in `tests/register.test.tsx`.
- Known limits, in the README: an install inside `bash -c` is not seen, and
  one whose failure the command hides (`|| true`) still counts.
