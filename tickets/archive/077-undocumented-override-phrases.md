# Ticket 077: Stored Override Phrases Match The Documented Ones

## Parent Spec

`docs/specs/2026-11-17-skill-usage-data-detail.md` (R8; AC8)

## Type

AFK.

## Problem

The skill-usage mod's stored summaries list two override phrases that do
not read as the documented ones:

- `commit message`, three times. The adapter documents a commit-message
  override, `commit message: <text>` and its variants, and
  `overrides.parse_overrides` returns it as `commit_message`. The stored
  phrase is probably that override shown without its text. This is not
  confirmed.
- ``skip `doc-sync``, once, with a stray backtick. The documented form is
  `skip <skill>`. The cause is unknown: it may be how the adapter words
  the sentence it adds to the hook context, how the mod reads that
  sentence, or a phrase the adapter matched that it should not have.

Override counts cannot be trusted until both are explained.

## What To Build

- **`commit message`.** Confirm whether the stored phrase is the
  documented commit-message override in shortened form. If it is, make the
  mod show it under a label that says so, and close this part. If it is
  not, treat it as the second case.
- **``skip `doc-sync``.** Reproduce it from the adapter's override parsing
  and announcement and the mod's reading of them. Fix it where it lies, in
  the adapter or the mod, so the stored phrase is `skip doc-sync`.
- If either cause is an override the adapter should not have applied,
  report that to the maintainer before changing the override rules.
- Pin each fix with a regression test on the side that changed.

## Recommended First Reads

- The parent spec, R8.
- `adapters/claude-code/goated_adapter/overrides.py` (`parse_overrides`,
  `_commit_message`) and where `hooks.py` announces a recorded override.
- `adapters/claude-code/README.md`: User Overrides.
- The mod's `hooks/classify.ts`, for how it reads the announcement.
- Tickets 047 and 054, which changed where overrides may come from.

## Acceptance Criteria

- [ ] This ticket's closeout says whether `commit message` is the
      documented override, with the input that produces it.
- [ ] The cause of ``skip `doc-sync`` is named in the closeout, with the
      input that produces it.
- [ ] After the fix, that input stores `skip doc-sync` or nothing.
- [ ] A regression test pins each fix.
- [ ] The documented overrides still apply and are still counted.

## Expected Proof

- Tests for each fix, with a near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, and the mod's
  tests.

## Blocked By

None.

## Scope Exclusions

- New override phrases.
- Rewriting summaries already stored.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `b98d039` (`3ffa8ec`, follow-up `b535861`).
- Exercised in later sessions; no separate live-check record.
