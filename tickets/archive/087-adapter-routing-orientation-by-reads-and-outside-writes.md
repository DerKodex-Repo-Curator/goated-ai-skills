# Ticket 087: Routing Counts Reads As Orientation And Passes Outside Writes

## Parent Spec

`docs/specs/2026-11-17-adapter-low-signal-holds.md` (R3, R4, R15; AC4, AC5,
AC16, AC17)

## Type

AFK.

## Problem

Two routing holds fire where they say little about the work:

- **Orientation.** A session started from a brief, on a `standard` or
  `full` route, must load `session-start-progressive-disclosure` before
  its first write or spawn (Ticket 072). All three agents of the last wave
  had already read their ticket, spec and code, so the load was ritual.
  The skill's own work is targeted reading.
- **Writes outside the project.** `router-first`, `route-line` and
  `pipeline` hold a write wherever its file is. A copy into a temp scratch
  folder was held by `pipeline`. The design, security and closeout checks
  already ignore a file the adapter is certain is outside the project.

## What To Build

- **Orientation by reads.** The orientation requirement is met by the
  skill load, as today, or by three finished `Read` calls of distinct
  files, anywhere, since the session started or the last compaction. The
  count survives turns the way loads do, and a compaction clears it. The
  hold's text names both ways.
- **Rule owners.** `handoff`'s spawn-brief template and
  `session-start-progressive-disclosure` say that a briefed session
  orients before its first write by reading the sources its brief names,
  at least three files, or by loading the skill when the area is
  unfamiliar. The router's orientation row changes only if it would
  otherwise contradict this, and then by replacing words: it has about
  six words of headroom.
- **Outside writes.** A write whose every file is certainly outside the
  project passes `router-first`, `route-line` and `pipeline`. Use the rule
  the action gates use, where a file is inside when in doubt. A write with
  any file inside, or unplaced, is held as today. Spawns and commands that
  are not writes are unchanged.
- Update the README's What It Holds text on briefed sessions, the three
  routing rows and Known Limits, and regenerate the hold texts for the
  skill-usage mod.

## Recommended First Reads

- The parent spec: Problem, R3, R4, Constraints.
- `adapters/claude-code/goated_adapter/gates.py`: `check_routing`,
  `_brief_orientation`, `writes_like_an_edit`, `fold_turns`.
- `adapters/claude-code/goated_adapter/actions.py`: `_in_project`,
  `find_project`, for the outside-the-project rule.
- `adapters/claude-code/goated_adapter/state.py`: `SessionState`,
  `forget_context`.
- `adapters/claude-code/README.md`: What It Holds, from "A session started
  from another session" through the gate table.
- `skills/agent-workflows/handoff/references/spawn-brief.md`, the
  `session-start-progressive-disclosure` skill, and the router's
  orientation row.
- `tickets/archive/072-orientation-and-plans-in-routes.md`, for what shipped.

## Acceptance Criteria

- [ ] A briefed session on a `full` route that made three `Read` calls of
      distinct files writes with no orientation hold.
- [ ] With two reads, or three reads of one file, it is held, and the hold
      names the load and the reads.
- [ ] Reads made in an earlier turn count; after a compaction they do not.
- [ ] Before the router loads, a `cp` into a temp folder outside the
      project is not held. A `cp` into the project is, and so is a write
      whose folder cannot be read.
- [ ] With the router loaded and no route line in the turn, a `Write` to a
      file outside the project is not held by `route-line`.
- [ ] A spawn is held by the routing gates as before.
- [ ] The router and the shared policy stay inside their word budgets,
      and the routing fixtures pass.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The skill validators, routing fixtures and context comparison.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, and the mod's
  tests.

## Blocked By

None.

## Scope Exclusions

- Which files the reads must be. Any three distinct files count.
- The `spawn` gate and the skills line in a brief, which stay as shipped.
- Read-only subagents: `Explore` and `Plan` are held as spawns as today.
- Plain reads before the router loads (Ticket 088).

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `3d0cbc6` (`6671e91`, follow-up `fed7118`).
- Maintainer decision: "outside" means outside the project, not in any git
  checkout, and not in `~/.claude`.
- Exercised in later sessions; no separate live-check record.
