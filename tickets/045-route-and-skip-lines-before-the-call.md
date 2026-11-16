# Ticket 045: Write Route And Skip Lines Before The Gated Call

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (Trial Result; AC11)

## Type

AFK.

## Problem

In the Ticket 033 trial, 26 of 64 route-line holds came from a route line
written in the same message as the held call. Claude Code records that
message only after the hook returns, so the adapter cannot see the line yet.
A retry that repeats the line in the same message is held again; only a
bare retry clears it. Once, a skip line written just before a tool call was
stored as a narration summary rather than text, so the adapter never saw it
at all.

## What To Build

- The router's output contract and the shared policy's skip-line rule say
  that, when a framework judges calls as they are made, the route line or
  skip line goes in a message before the call it covers.
- The adapter's route-line, pipeline, and justified-skip hold texts say: if
  the line was written in the same message as this call, make the call again
  without repeating the line.
- The adapter README's Known Limits records the narration case.

## Recommended First Reads

- `skills/agent-workflows/using-goated-ai-skills/SKILL.md` (Output
  Contract) and `stack/AGENTS.md` (Routing And Checkpoints).
- `adapters/claude-code/README.md`: Hold messages, Known Limits.
- `adapters/claude-code/goated_adapter/gates.py` and `actions.py` hold texts,
  and `tests/test_skill_usage_mod.py` (the hold-text generator).

## Acceptance Criteria

- [ ] The router and shared policy say where to write the line, in
      framework-neutral words, and the router stays under 300 lines.
- [ ] The hold texts give the bare-retry instruction, keep their first line
      and kind, and backtick only skill names.
- [ ] `tests/adapter-texts.ts` is regenerated and the drift test passes.
- [ ] The installed-copy note: the maintainer is told to sync the installed
      router and shared policy after merge.

## Expected Proof

- The repo checks in `AGENTS.md`, `claude plugin test .` in the mod folder.

## Blocked By

- `tickets/044-adapter-closeout-same-command-check.md` (same hold texts)

## Scope Exclusions

- Changing how the adapter reads the transcript; the limit is Claude Code's.
