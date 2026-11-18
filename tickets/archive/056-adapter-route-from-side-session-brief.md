# Ticket 056: A Side Session's Brief Carries Its Route

## Parent Spec

`docs/specs/2026-11-17-adapter-hook-friction.md` (R6, R14; AC6, AC7)

## Type

AFK.

## Problem

A session started from another session gets a full brief as its first
prompt, but it still has to load the router and write a route line before
its first write. Route lines are read only from assistant text and call
fields, never from a prompt, and `router-first` needs the router loaded once
per session. Subagents already skip routing, because the parent's brief
carries the route. Side sessions don't.

The check for this ticket also found that harness nudges, such as "The user
hasn't heard from you in a while", are recorded as `attachment` entries
(`silent_turn_reminder`) and never open a turn. No test pins that yet.

## What To Build

- A session's first prompt may be a brief from the session that started it:
  a prompt the adapter already classes as machine-written, opening with
  "Background (from the session that started this one)" or "Task (from the
  session that started this one)". A valid route line on its own line in
  that brief becomes the turn's route and meets `router-first`.
- The route's required skills still load in the new session before its first
  write (`pipeline`). A brief never carries an override.
- The handoff skill's spawn-brief template says where the parent puts the
  route line. Keep the wording within the context comparison's budgets.
- A regression test: an `attachment` entry never opens a turn.
- Update the README's routing and Known Limits text.

## Recommended First Reads

- The parent spec, R6.
- `adapters/claude-code/goated_adapter/transcript.py` (`_opener_kind`,
  `_build_turn`, `MACHINE_PREFIXES`).
- `adapters/claude-code/goated_adapter/gates.py` (`fold_turns`,
  `check_routing`).
- `skills/agent-workflows/handoff/references/spawn-brief.md`.
- `tickets/archive/053-adapter-route-and-skip-lines-from-tool-input.md`, for
  the word budgets.

## Acceptance Criteria

- [ ] A side session whose brief carries a route line passes `router-first`
      and `route-line` on its first write. It is held by `pipeline` until the
      required skills load.
- [ ] A brief with no route line is held as today.
- [ ] A route line in a typed prompt, or in a later machine prompt, does not
      count.
- [ ] An `attachment` entry never opens a turn.
- [ ] The validator and the context comparison pass with the spawn-brief
      change.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- A live check: one side session started with a route line in its brief.

## Blocked By

- None.

## Scope Exclusions

- Overrides from briefs.
- Changing how subagents are routed.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `a32c217` (`3357dd5`, review fixes `7117916` and `c605f2a`).
- Exercised in later sessions; no separate live-check record.
