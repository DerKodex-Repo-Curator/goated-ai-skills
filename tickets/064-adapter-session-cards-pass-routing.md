# Ticket 064: A Session Card Passes The Routing Gates

## Parent Spec

`docs/specs/2026-11-17-adapter-written-line-holds.md` (R7, R9; AC10)

## Type

AFK.

## Problem

A `mcp__ccd_session__start_session` call can show a card instead of
starting a session: an offer the user answers, or a proposal the user may
start later. Nothing runs until the user acts. The routing gates still hold
the call as a spawn, so an agent that only wants to propose a follow-up
must load the router and write a route line first.

## What To Build

- A `start_session` call whose `initiation` is `offer` or `own_initiative`,
  and that starts no saved proposal, passes `router-first`, `route-line`
  and `pipeline`.
- A card that carries a brief still meets `spawn`, with its skill load,
  template read and content check, since that brief runs when the user
  starts the card. A card with no brief meets no hold, as today.
- Any other `initiation`, a missing one, a call that starts a saved
  proposal, and `hand_off_to_session` are held as today.
- The skill-usage mod keeps counting such a call as it does now; say in its
  README if a card no longer counts as a spawn in a writing turn.
- Update the README's What It Holds text on spawns.

## Recommended First Reads

- The parent spec, R7.
- `adapters/claude-code/goated_adapter/gates.py` (`check_routing`,
  `SPAWN_TOOLS`, `spawns_a_reader`).
- `adapters/claude-code/goated_adapter/actions.py` (`SPAWN_BRIEF_FIELDS`,
  `_spawn_hold`).
- `adapters/claude-code/README.md`: What It Holds, the Writes and Spawns
  bullet.
- The mod's `hooks/classify.ts`, for how it counts writing turns.

## Acceptance Criteria

- [ ] Before the router loads, an `own_initiative` card with a brief passes
      `router-first`, `route-line` and `pipeline`, and is held by `spawn`.
- [ ] An `offer` card with no brief passes every hold.
- [ ] A `user_asked` start, a call with no `initiation`, and a start of a
      saved proposal are each held by `router-first` as today.
- [ ] `hand_off_to_session` is unchanged.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The mod's tests pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.

## Blocked By

None.

## Scope Exclusions

- The `spawn` gate's requirements.
- Other session tools.
