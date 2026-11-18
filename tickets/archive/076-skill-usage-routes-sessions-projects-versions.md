# Ticket 076: The Mod Records Routes, Side Sessions, Projects And Versions

## Parent Spec

`docs/specs/2026-11-17-skill-usage-data-detail.md` (R4, R5, R6, R7, R10;
AC4, AC5, AC6, AC7)

## Type

AFK.

## Problem

The mod's stored summaries leave four things invisible:

- Route lines are counted by form, not by which skills each requires, so
  the router's choices cannot be seen.
- The count of sessions started is 0, though the workflow runs on side
  sessions.
- Summaries carry no project, so sessions from different projects cannot
  be told apart. An analysis of 84 sessions could not separate the
  maintainer's sessions in a second project.
- Summaries from older versions use retired gate names, such as
  `design-hold` and `commit-hold`, mixed with current ones.

## What To Build

- **Routes.** Each routed line's `requires:` skills are counted, per
  skill, with the route's intensity.
- **Side sessions.** A session-start call that ran is counted, by tool and
  by whether it showed a card or started a session.
- **Projects.** Each session's summary carries a project key derived from
  the project folder in a form that does not reveal its path. All time
  can be filtered by it.
- **Versions.** Each summary carries the mod's data version. All time
  shows retired gate names under a heading that says they come from
  earlier versions, and they do not add to current gates' counts.
- The stored shape changes, so bump the events shape tag, and keep older
  summaries readable.
- Update the mod's README table of what it records.

## Recommended First Reads

- The parent spec, R4 to R7 and its Constraints.
- `adapters/claude-code/skill-usage/hooks/classify.ts`, `register.tsx`,
  `view.tsx` and `picture.tsx`.
- `stack/fixtures/markers/README.md` (the route line grammar) and the
  mod's `tests/marker-fixtures.ts`.
- The mod as Ticket 075 left it.

## Acceptance Criteria

- [ ] A route line requiring `tdd` and `doc-sync` adds one to each.
- [ ] A proposal card and a started side session are counted apart; a held
      or failed call is not counted.
- [ ] Sessions from two project folders can be filtered apart, and the
      stored key contains neither path.
- [ ] A summary stored by an earlier version shows under the
      earlier-versions heading and changes no current count.
- [ ] A session running across the update is not misread.

## Expected Proof

- Mod tests for each criterion, each with a near miss.
- The mod's type check adds no errors.
- The repo checks in `AGENTS.md`.
- The maintainer looks at the pane in one real session.

## Blocked By

- `tickets/archive/075-skill-usage-hold-detail.md` (both change the stored shape
  and the same summary code).

## Scope Exclusions

- Migrating old summaries to the new shape.
- Token or cost accounting.
- Sending data off the machine.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `da4046d` (`af8d72a`, follow-up `d723376`, review fix
  `cbb6fa8`).
- Exercised in later sessions; no separate live-check record.
