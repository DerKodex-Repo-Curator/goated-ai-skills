# Ticket 078: The Mod Counts Each Declared Reference

## Parent Spec

`docs/specs/2026-11-17-skill-usage-data-detail.md` (R9, R10; AC9)

## Type

AFK.

## Problem

The registry declares when each skill reference must be read, and the
adapter's `reference-reads` gate enforces it. Tuning those signals needs
numbers: a signal that fires often and is always skipped is noise, and an
advisory reference that is never read may need a signal. The mod counts
reads per file but not how often a reference was asked for or skipped.

## What To Build

- For each reference the registry declares as enforced: times its hold
  fired, times it was then read, and times it was skipped.
- For each advisory reference: reads, and loads of its skill, so the read
  rate can be seen.
- The mod takes the list of references and their status from the
  registry, read the way it already finds skill files, not from a copy.
- All time shows the counts by skill. A reference the registry no longer
  declares stays in stored data and is shown as retired.
- Update the mod's README table of what it records.

## Recommended First Reads

- The parent spec, R9.
- `docs/specs/2026-11-17-registry-reference-reads.md` and the registry
  entries from Ticket 066.
- The `reference-reads` hold text as Tickets 067 and 068 left it.
- `adapters/claude-code/skill-usage/hooks/holds.ts` and `classify.ts`
  (how `design-reads` holds and reference reads are counted today).

## Acceptance Criteria

- [ ] A `reference-reads` hold that is then read adds one fired and one
      read for that reference.
- [ ] One declined with a skip line adds one fired and one skipped.
- [ ] An advisory reference shows its reads beside its skill's loads.
- [ ] With no readable registry, the mod shows reads as it does today and
      does not fail.

## Expected Proof

- Mod tests for each criterion, each with a near miss.
- The mod's type check adds no errors.
- The repo checks in `AGENTS.md`.

## Blocked By

- `tickets/archive/068-adapter-reference-reads-turn-signals.md` (the gate and its
  final hold texts).
- `tickets/archive/076-skill-usage-routes-sessions-projects-versions.md` (the
  stored shape).

## Scope Exclusions

- Changing any signal.
- Recommending signals automatically.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `e25176d` (`4258e03`, review fix `0892f09`).
- Exercised in later sessions; no separate live-check record.
