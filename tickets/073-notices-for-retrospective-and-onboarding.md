# Ticket 073: Notices Point To Retrospective And Onboarding Skills

## Parent Spec

`docs/specs/2026-11-17-skill-placement-gates.md` (R6, R9, R10; AC6, AC9)

## Type

AFK.

## Problem

- **Retrospective.** `retrospective` never loaded in 84 recorded sessions.
  The rounds that turn agents' reports on the holds into specs are
  retrospectives done by hand, with no prompt to use the skill.
- **Onboarding, research and doc-writing skills.** Ten of them never
  loaded in any recorded session, in this project or another. Nothing
  tells a session that a project lacks the files those skills produce.

These skills fit a notice better than a hold: there is no usage data to
tune a hold with.

## What To Build

- **Retrospective notice.** When a session has had three or more holds
  that were declined with a skip line or left unanswered, the adapter says
  once, at the next prompt, that `retrospective` can turn the friction into
  improvements. It is context for the agent and a line the user sees. It
  never blocks.
- **Retrospective placement.** The skill's description and the router's
  map name the moment after a wave of delegated tickets is merged. The
  skill takes the skill-usage mod's numbers as an input when they exist.
- **Onboarding notice.** At the first session start the adapter says once
  when the project has no agent instruction file, no context map, or no
  standards document, and names the onboarding skill for each:
  `agent-instructions-integrator`, `context-matrix-map`,
  `project-standards-calibration`.
- **Router wording.** The router's lines for `source-grounded-research`,
  `documentation-writer`, `documentation-cleanup` and `goated-prompt` are
  checked against each skill's description and corrected where the router
  would not select the skill for work its description names.
- The router and shared policy stay inside their word budgets.
- Update the README's Session Start Notices section.

## Recommended First Reads

- The parent spec, R6, R9 and its Constraints.
- `adapters/claude-code/goated_adapter/hooks.py` (session start and
  user-prompt handling) and `policy.py` (the existing notices).
- `adapters/claude-code/README.md`: Session Start Notices.
- `skills/agent-workflows/retrospective/SKILL.md` and the router's skill
  map.
- The router as Ticket 072 left it.

## Acceptance Criteria

- [ ] A session with three declined or unanswered holds gets the
      retrospective notice once, at the next prompt. One with two gets
      none, and a fourth hold brings no second notice.
- [ ] A hold answered by a load or a read does not count toward the three.
- [ ] A project with no agent instruction file gets the start notice
      naming `agent-instructions-integrator`, once. A project with all
      three files gets none.
- [ ] No notice blocks a call or a `Stop`.
- [ ] The router's fixtures select each of the four research and
      doc-writing skills for a prompt its description names.
- [ ] The router and shared policy stay inside their budgets.

## Expected Proof

- Adapter tests for each notice criterion, each with a near miss.
- The routing fixtures and the skill validator pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, including the
  context comparison.

## Blocked By

- `tickets/072-orientation-and-plans-in-routes.md` (both edit the router,
  which is at its word budget).

## Scope Exclusions

- Holds for any of these skills.
- Running a retrospective automatically.
- Detecting the quality of existing instruction or context files.
