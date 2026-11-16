# Ticket 039: Skill-Usage Mod Hold Settlement Module

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (AC7, measurement).
Agreed by the maintainer on 2026-11-16 in the skill-usage mod's quality
check, and deferred until Ticket 033 removes the legacy hook handling, as the
033 session advised.

## Type

AFK.

## What To Build

Move the skill-usage mod's hold settlement out of `summarize` in
`hooks/classify.ts` into a module of its own with a small interface: a hold
asks, a load, read, skip or route line answers, and a turn ends. Today that
logic is spread through one long function with many shared variables:
asks, repeats, skip reasons, the reply a held call belongs to, and the
closeout's `Stop` rule. Every fix to hold outcomes has to work through it.

Behaviour stays exactly as it is: every outcome the mod's tests pin, the
repeat collapsing, failed loads, and closeout settlement after the last
blocked `Stop`.

## Recommended First Reads

- `adapters/claude-code/skill-usage/README.md`, the hold-reading section.
- `adapters/claude-code/skill-usage/hooks/classify.ts`: `summarize`.
- `adapters/claude-code/skill-usage/tests/adapter-holds.test.tsx`.

## Acceptance Criteria

- [ ] Hold settlement lives behind one interface that `summarize` calls, and
      `summarize` keeps only loads, routes, references, writing turns and
      subagents.
- [ ] Every existing mod test passes unchanged, apart from imports.
- [ ] No legacy hook handling is moved into the new module.

## Expected Proof

- `claude plugin test .` and `claude plugin validate .` in the mod folder.
- `uv run python -m unittest discover -s tests` from the repo root.

## Blocked By

- `tickets/033-adapter-real-use-trial.md`, and its removal of
  `LEGACY_MARKERS` and the legacy hook handling from `hooks/classify.ts`.
  If the trial decides to keep the legacy handling, settle with the
  maintainer whether this ticket still runs.

## Scope Exclusions

- Any change to what the pane shows or counts.
