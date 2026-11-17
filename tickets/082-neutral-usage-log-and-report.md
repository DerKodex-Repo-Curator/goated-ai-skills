# Ticket 082: A Neutral Usage Log Every Harness Writes

## Parent Spec

`docs/specs/2026-11-17-portable-enforcement-core.md` (R8; AC8, AC9)

## Type

AFK.

## Problem

Measurement is a Claude desktop mod that reads Claude Code's events. A
session in any other harness leaves no record of which skills loaded,
which holds fired and what became of them, so the stack cannot be tuned
from that use.

## What To Build

- **The log.** The core appends to a local log, in a documented and
  versioned format: each hold with its gate, kind and the skills or
  references it asked for; each hold's outcome; each skill load with its
  cause; each route and skip line, with the skip's reason; and each
  reference read. Each entry carries the session id, the project key and
  the adapter's name. It holds what the skill-usage mod stores today and
  nothing more.
- **The report.** A command prints a summary of the log: loads by skill
  and cause, holds by gate and outcome, closeout items, routes, and
  reference counts. It can filter by project and adapter.
- **The mod.** The skill-usage mod reads the log when it exists and keeps
  its current reading when it does not, so its counts match either way.
- The log's location is documented, can be set by the caller, and is
  never inside a project folder by default.
- Document the format beside the event model, and update the mod's
  README.

## Recommended First Reads

- The parent spec, R8 and Constraints.
- The core as Ticket 081 left it.
- `adapters/claude-code/skill-usage/README.md`: What It Records.
- `adapters/claude-code/skill-usage/hooks/` (`classify.ts`, `holds.ts`),
  as Tickets 075 to 078 left them.
- `docs/specs/2026-11-17-skill-usage-data-detail.md`.

## Acceptance Criteria

- [ ] A hold and its clearing in a Claude Code session, and the same pair
      driven through the core directly, produce the same log entries
      apart from the adapter's name.
- [ ] The report summarises a log holding both, and filters them apart.
- [ ] The mod shows the same counts from the log as from its current
      reading for one recorded session.
- [ ] A log of an unknown version is refused with a clear message.
- [ ] A log that cannot be written never blocks a call.
- [ ] No path, prompt text or file content is written to the log.

## Expected Proof

- Core tests for the log and report, each with a near miss.
- The mod's tests and type check.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- The maintainer compares the pane and the report for one real session.

## Blocked By

- `tickets/081-shared-enforcement-core.md`
- `tickets/078-skill-usage-reference-counts.md` (the mod's final stored
  shape and counts).

## Scope Exclusions

- A viewer for other harnesses beyond the report command.
- Sending the log anywhere.
- Token or cost accounting.
