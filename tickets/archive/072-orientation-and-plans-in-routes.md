# Ticket 072: Briefed Sessions Orient First, And Ticket Work Gets A Plan

## Parent Spec

`docs/specs/2026-11-17-skill-placement-gates.md` (R4, R5, R10; AC4, AC5)

## Type

AFK.

## Problem

- **Orientation.** The router's gate table says
  `session-start-progressive-disclosure` is always selected. It never
  loaded in 84 recorded sessions. Side sessions, which start from a brief
  in an area they have not seen, are where orientation matters most.
- **Plans.** `writing-plans` loaded in one session. The router routed it
  once, so tickets went from the route line to code.

Both change the router's selection text and what `pipeline` requires, so
they are built together.

## What To Build

- **Router text.**
  - The orientation row stops saying "Always". The skill is selected for
    unfamiliar, cross-area, stale or boundary-uncertain work, and in a
    session started from a brief.
  - `writing-plans` is required in the route of a task that implements a
    ticket at `standard` or `full` intensity.
  - The router stays inside its word budget, so words are traded, not
    added. Update the routing fixtures under `stack/fixtures/`.
- **Adapter.** In a session whose route came from its brief, the first
  write is held by `pipeline` until `session-start-progressive-disclosure`
  counts as loaded, unless the task's route is `direct`. A corrected
  `direct` route line therefore drops it, and so does a typed
  `skip session-start-progressive-disclosure`, as for any skill.
- **Brief template.** The spawn-brief template's note on the route line
  says the new session loads the orientation skill first.
- Update the README's text on briefs and the `pipeline` row, and
  regenerate `adapters/claude-code/skill-usage/tests/adapter-texts.ts`.

## Recommended First Reads

- The parent spec, R4, R5 and its Constraints.
- `skills/agent-workflows/using-goated-ai-skills/SKILL.md` (the gate
  table) and Ticket 053's notes on its word budget.
- `stack/fixtures/routing/` and `stack/fixtures/planning/`.
- `adapters/claude-code/goated_adapter/gates.py` (`check_routing`,
  `fold_turns`) and `state.py` (`brief_routed`).
- `adapters/claude-code/README.md`: the paragraph on a session started
  from another session.
- Ticket 056.

## Acceptance Criteria

- [ ] A briefed side session with a routed brief is held on its first
      write until the orientation skill loads, then passes.
- [ ] One whose brief's route is `direct` is not held for it.
- [ ] A session that was not started from a brief is not held for it.
- [ ] The routing fixtures select `writing-plans` for a ticket
      implementation at `standard`, and not for a `lightweight` task.
- [ ] The router and the spawn-brief template stay inside the context
      comparison's budgets.

## Expected Proof

- Adapter tests for each adapter criterion, each with a near miss.
- The routing fixtures and the skill validator pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, including the
  context comparison.
- A live check: one real briefed side session.

## Blocked By

- `tickets/archive/065-adapter-loads-count-until-compaction.md` (the routing check
  and when a skill counts as loaded).
- `tickets/archive/071-spawn-briefs-name-skills.md` (both edit the spawn-brief
  template, which has a context budget).

## Scope Exclusions

- Orientation holds in sessions the user starts.
- Enforcing `writing-plans` by anything but the route.
- The content of a plan.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `68ce811` (`6a78a1e`, review fix `4db7c62`).
- Maintainer decision: orientation is required only when the orientation
  skill is installed, and only on standard or full routes.
- Exercised in later sessions; no separate live-check record.
