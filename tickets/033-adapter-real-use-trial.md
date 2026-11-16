# Ticket 033: Adapter Real-Use Trial And Decision

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (AC9, Rollout)

## Type

HITL. The maintainer installs the adapter on their own machine, runs real
sessions, and records keep, revise, or revert.

## What To Build

Swap the maintainer's personal hook scripts for the repo adapter and mod using
the documented install steps. Keep the old scripts restorable. After several
real sessions, compare the mod's data against AC9:

- zero holds passed without a load, a logged skip, or a user override;
- every hook-required skill loaded in the turn it applied;
- a route line on every turn that writes.

Review the justified-skip reasons for throwaway answers, and record the
decision in the spec.

Once the personal hooks are gone, remove `LEGACY_MARKERS` and the rest of the
legacy hook handling from the skill-usage mod's `hooks/classify.ts`, with its
tests and README mentions (maintainer decision recorded in Ticket 034,
2026-11-16).

## Recommended First Reads

- The spec's Acceptance Criteria, Rollout, and Risks sections.
- The adapter and mod install docs from Tickets 030–032 and 034.

## Acceptance Criteria

- [ ] The adapter and mod are installed from the repo, and the personal scripts
      are disabled but restorable.
- [ ] Data from several real sessions is summarised against each AC9 target.
- [ ] The maintainer's keep, revise, or revert decision is recorded in the
      spec.

## Expected Proof

- The mod's session data summary and the recorded decision.

## Blocked By

- `tickets/archive/028-discoverable-skill-descriptions.md`
- `tickets/archive/034-skill-usage-mod-action-holds.md`

## Scope Exclusions

- Adapters for other frameworks.
