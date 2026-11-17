# Ticket 060: Read-Only Subagents Pass The Pipeline And Spawn Holds

## Parent Spec

`docs/specs/2026-11-17-adapter-hook-friction.md` (R13; AC15)

## Type

AFK.

## Problem

A spawn counts as a write, so starting a read-only research subagent meets
the same holds as starting an implementer. While the planning session that
wrote the parent spec was checking claims, an `Explore` spawn was held three
times:

- by `route-line`;
- by `pipeline`, for skills of a later phase (`write-a-spec`,
  `spec-to-tickets`);
- by `spawn`, which asked for the handoff brief template for a short search
  brief.

Doing the reads inline was cheaper than meeting the holds, which defeats
delegation of bounded reads.

## What To Build

- A spawn of a read-only subagent type (`Explore`, `Plan`,
  `claude-code-guide`) passes `pipeline` and `spawn`. It still needs a route
  line, as any first spawn does.
- Keep the read-only types in one named table with a comment on why. Any
  other subagent type, including `general-purpose` and a missing type, and
  side sessions are unchanged.
- Update the README's spawn and pipeline text.

## Recommended First Reads

- The parent spec, R13.
- `adapters/claude-code/goated_adapter/gates.py` (`check_routing`,
  `writes_like_an_edit`, `HELD_LIKE_WRITES`).
- `adapters/claude-code/goated_adapter/actions.py` (`_spawn_hold`,
  `SPAWN_BRIEF_FIELDS`).
- `adapters/claude-code/README.md`: What It Holds (spawn, pipeline).

## Acceptance Criteria

- [ ] An `Explore` spawn with required skills not loaded and no handoff
      template passes `pipeline` and `spawn`.
- [ ] A `general-purpose` spawn with the same brief is still held.
- [ ] An `Explore` spawn with no route line in the turn is held by
      `route-line`.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.

## Blocked By

- `tickets/055-adapter-router-first-read-only-commands.md` (same routing
  function).

## Scope Exclusions

- Exempting read-only subagents from `route-line`.
- Side sessions.
