# Ticket 042: Adapter Routing In A Session With No Task

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (Trial Result; AC11)

## Type

AFK.

## Problem

In the Ticket 033 trial, two routing rules caused about 33 of 166 holds
without any skill being skipped:

- 21 route-line holds came from `goated-route: continue` written in a
  session with no task yet, mostly a session started from another session
  whose brief continues work begun elsewhere. The agent then needed one or
  more further messages to write a full route line.
- About 12 pipeline holds asked for a skill the agent had loaded earlier in
  the same turn, before it wrote the route line. Only loads after the route
  line that starts a task count, so the agent loaded the skill twice.

## What To Build

- In a session whose adapter state has no task, `goated-route: continue`
  starts a task with no required skills instead of being held. A `continue`
  in a session that has a task keeps today's meaning.
- Loads made earlier in the same turn count for a task that the turn starts,
  as long as no other task started between the load and the route line. A
  load in an earlier turn still never counts, and nor does a load before a
  route line that started an earlier task in the same turn.
- Update the hold texts and the adapter README's What It Holds rules to
  match. Each hold keeps its first line and kind.

## Recommended First Reads

- `adapters/claude-code/README.md`: What It Holds (the task and dropping
  rules), Hold messages.
- `adapters/claude-code/goated_adapter/gates.py` (the `continue` check and
  the pipeline gate) and `goated_adapter/state.py`.
- `tests/test_claude_code_adapter.py`.

## Acceptance Criteria

- [ ] `goated-route: continue` in a session with no task passes the
      route-line gate and starts a task with no required skills.
- [ ] A skill loaded earlier in the turn, before the route line that starts
      the task, satisfies that task's pipeline; a load in an earlier turn,
      or before an earlier task's route line, does not.
- [ ] Every other AC4 behaviour is unchanged, and the README and hold texts
      say the new rules.
- [ ] `tests/adapter-texts.ts` is regenerated if any hold text changed.

## Expected Proof

- Adapter tests with recorded-shape transcripts for each criterion and its
  near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, and
  `claude plugin test .` in the mod folder.

## Blocked By

- `tickets/041-adapter-review-holds-read-the-change.md` (same files)

## Scope Exclusions

- Seeing a route line written in the same message as the held call: Claude
  Code records it only after the hook returns (Ticket 045 covers the
  guidance).
