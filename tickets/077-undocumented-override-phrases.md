# Ticket 077: Stored Override Phrases Match The Documented Ones

## Parent Spec

`docs/specs/2026-11-17-skill-usage-data-detail.md` (R8; AC8)

## Type

AFK.

## Problem

The skill-usage mod's stored summaries list override phrases the adapter
does not document: `commit message`, three times, and ``skip `doc-sync``,
once. The documented overrides are `skip routing` and `skip <skill>`. The
cause is unknown. It may be how the adapter words the sentence it adds to
the hook context, how the mod reads that sentence, or an override the
adapter recorded that it should not have.

## What To Build

- Find the cause. Reproduce each phrase from the adapter's override
  parsing and announcement and the mod's reading of them.
- Fix it where it lies, in the adapter or the mod, so a stored phrase is
  always one the adapter's User Overrides section documents.
- If the cause is an override the adapter should not have applied, report
  that to the maintainer before changing the override rules.
- Pin the fix with a regression test on each side that changed.

## Recommended First Reads

- The parent spec, R8.
- `adapters/claude-code/goated_adapter/overrides.py` (`parse_overrides`)
  and where `hooks.py` announces a recorded override.
- `adapters/claude-code/README.md`: User Overrides.
- The mod's `hooks/classify.ts`, for how it reads the announcement.
- Tickets 047 and 054, which changed where overrides may come from.

## Acceptance Criteria

- [ ] The cause of each phrase is named in this ticket's closeout, with
      the input that produces it.
- [ ] After the fix, that input stores a documented phrase or none.
- [ ] A regression test pins the fix.
- [ ] The documented overrides still apply and are still counted.

## Expected Proof

- Tests for the fix, with a near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, and the mod's
  tests.

## Blocked By

None.

## Scope Exclusions

- New override phrases.
- Rewriting summaries already stored.
