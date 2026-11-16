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

- [x] The adapter and mod are installed from the repo, and the personal scripts
      are disabled but restorable. (2026-11-16: the adapter's hooks in the
      user settings point at the main checkout, and the mod is installed from
      its folder there. The two personal scripts were renamed, not deleted,
      and the settings file was backed up first. A probe session was held by
      `router-first`, and the mod recorded it.)
- [x] Data from several real sessions is summarised against each AC9 target.
      (13 sessions, 166 holds; spec, Trial Result.)
- [x] The maintainer's keep, revise, or revert decision is recorded in the
      spec. (Revise: fixes in Tickets 041–046, before 035.)

## Expected Proof

- The mod's session data summary and the recorded decision.

## Blocked By

- `tickets/archive/028-discoverable-skill-descriptions.md`
- `tickets/archive/034-skill-usage-mod-action-holds.md`

## Scope Exclusions

- Adapters for other frameworks.

## Closeout

Completed, merged and archived on 2026-11-16. Decision: revise.

- Merged as `78e89aa`: the spec's Trial Result (13 sessions, 166 holds, all
  three AC9 targets met), Tickets 042-046 for the revise fixes, and the
  skill-usage mod's removal of the retired hooks' reading.
- An independent review of the removal found that a session running across
  the update would misread its old events. The fix bumped the mod's events
  shape tag, restored tests for compaction and for stored older summaries,
  and fixed wording.
- Every check passed on a scratch merge: the validator, unit tests on Python
  3.14 and 3.11, the V1/V2 context comparison, plugin validate, 136 mod
  tests, and a TypeScript check that added no errors.
- The maintainer checked the pane live after the merge: the Session tab
  started empty, as the bumped shape tag intends, and its animations played
  cleanly.
