# Ticket 094: A Report From The Session's Own Subagent Continues The Turn

## Parent Spec

`docs/specs/2026-11-17-adapter-hold-delivery-and-coverage.md` (R7, R9;
AC10, AC11, AC13, AC15)

## Type

AFK.

## Problem

The adapter folds a transcript into turns, and most of what it checks is
per turn: the route line, skip lines, typed overrides, checks, change
reads and the closeout.

A background subagent's report can reach the session as a prompt that
Claude Code records as a message from another session. The adapter treats
that prompt as machine-written and opens a new turn. The session did not
start new work; its own helper answered. But from then on:

- a write needs a new route line;
- earlier skip lines and change reads no longer count;
- the `Stop` closeout sees only the calls after the report, so code
  changed before it is never closed out;
- in a session routed by its brief, the brief's route can end, and
  `router-first` asks for the router.

A report delivered as a queued attachment already stays in the turn.

## What To Build

- **Find the shape.** From a real recorded session in which a background
  subagent reported back as a prompt, establish how Claude Code records
  that prompt and what ties it to a spawn the session made (the agent's
  id, the spawn call's result, the entry's origin fields). Cut a fixture
  from it with private content removed.
- **Continue the turn.** A prompt that is the report of a subagent this
  session started does not open a turn. The route line, skip lines,
  overrides, checks, change reads and the brief's route all stand, and
  the closeout judges the whole turn.
- **Fail toward a new turn.** A prompt the adapter cannot tie to one of
  the session's own spawns opens a turn as today: a message from an
  unrelated session, a scheduler, or a shape the adapter does not know.
- The user-prompt hook agrees with the transcript reader: it announces no
  override and resets nothing for such a report.
- Update the README's Subagents section and the Known Limits item on
  prompt classification.

## Recommended First Reads

- The parent spec: Problem, R7, Constraints, Risks.
- `adapters/claude-code/goated_adapter/transcript.py`: `_opener_kind`,
  the prompt wrappers and origins it lists, and how a brief is confirmed.
- `adapters/claude-code/goated_adapter/gates.py`: `fold_turns`;
  `hooks.py`: the user-prompt handling and `_overrides_for`.
- `adapters/claude-code/README.md`: Subagents, and the Known Limits item
  that opens "Prompt classification relies on".
- The tests that model a background report as a queued attachment, in
  `tests/test_claude_code_adapter_review.py`.

## Acceptance Criteria

- [ ] After a background subagent's report arrives as a prompt, a write
      needs no new route line.
- [ ] A skip line and a change read from before the report still count.
- [ ] The `Stop` closeout lists code changed before the report.
- [ ] In a session routed by its brief, the report does not end the
      brief's route: no `router-first` hold follows it.
- [ ] A message from a session this one did not start opens a new turn,
      and so does a report-shaped prompt naming no spawn of this session.
- [ ] The `review-intake` gate sees a reviewer's report delivered this
      way, as it does one delivered as an attachment.
- [ ] The fixture comes from a real recording and holds no private path,
      name or session id.

## Expected Proof

- Adapter tests on the recorded fixture for each criterion, with the near
  misses above.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- A live check: one session that spawns a background subagent, changes
  code, receives the report and ends its turn, showing one closeout over
  the whole turn.

## Blocked By

None.

## Scope Exclusions

- Messages from other sessions, which open a turn as today.
- What a typed prompt does to the brief's route.
- Holds inside the subagent itself.
- Recording shapes of Claude Code versions the adapter does not already
  read.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `55d3c73` (`59d54d8`, follow-up `21bb8e7`).
- Maintainer decision: a late report after Stop continues the turn, but
  typed overrides end at Stop.
- Exercised in later sessions; no separate live-check record.
