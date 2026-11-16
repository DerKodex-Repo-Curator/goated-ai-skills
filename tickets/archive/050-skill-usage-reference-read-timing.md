# Ticket 050: Skill-Usage Mod Records When References Are Read

## Parent Spec

`docs/specs/2026-11-16-design-reference-reads.md` (R7; AC8, its timing and
declaration parts)

## Type

AFK.

## Problem

The mod counts reference reads per skill, which showed that only
`red-flags.md` is read. It cannot show whether a read came at the right moment
(before the code it should shape, or only at the end), so the new triggers and
signals cannot be tuned from data.

## What To Build

- Record each reference read with its moment in the turn: before the turn's
  first code change, between code changes, or after the last one. Use the
  adapter's notion of a code change where the mod can reach it.
- Show per-reference counts by moment in the pane, for the session and all
  time, merging older summaries that lack the moment.
- Record `goated-design-reads:` lines per session: the files declared and the
  count of `none` declarations.

## Recommended First Reads

- The parent spec, R7.
- `adapters/claude-code/skill-usage/` (how `refs` and `refsUnloaded` are
  recorded, summarised and merged) and its tests.
- `tickets/archive/032-skill-usage-mod-in-repo.md` and
  `tickets/archive/040-skill-usage-all-time-picture-badges.md` for the mod's
  conventions.

## Acceptance Criteria

- [ ] A read before, between, and after code changes is recorded with that
      moment; a turn with no code change is recorded as such.
- [ ] Session and all-time views show per-reference counts by moment; older
      summaries still merge.
- [ ] Design-reads lines are recorded, including `none` declarations.

## Expected Proof

- Mod tests for each criterion, including merging an older summary.
- The repo checks in `AGENTS.md` and the mod's own test command.

## Blocked By

- `tickets/archive/047-adapter-overrides-from-other-agents.md` (also edits the mod)

## Scope Exclusions

- The `design-reads` hold name (Ticket 051).
- Any adapter change.

## Closeout

Completed, merged and archived on 2026-11-16.

- Merged as `0969b8b`: `86897b9`, with review fixes in `9e0171e`. Reads made
  in turns stored before this version count with no moment (prompts carry
  `isTimed`); a reply's design-reads lines count as the union of their files,
  as the fixtures define; the events shape stays `events-2`.
- Every check passed on a scratch merge with Tickets 042 and 049: 149 mod
  tests, `claude plugin validate`, the TypeScript check with only the 5 known
  errors in `tests/register.test.tsx`, and the repo checks.
- Known limits, in the mod's README: the mod does not see shell writes or
  out-of-project files the way the adapter does, a late-joining mod rebuilds
  no subagent calls, and a background subagent's change can land in the next
  turn.
