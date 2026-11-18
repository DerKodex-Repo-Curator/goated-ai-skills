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

- **Counting friction.** The adapter keeps no history of holds today. The
  saved state gains a count of the session's holds that were declined or
  left unanswered, and whether the retrospective notice was shown.
  - A hold is declined when a skip line cleared it.
  - A hold is unanswered when no load, read or skip line answered it
    before the next typed prompt.
  - A hold the user's typed override stood down counts as neither.
  - A hold answered by a load or a read counts as neither.
- **Retrospective notice.** When the count reaches three, the adapter says
  once per session, at the next prompt, that `retrospective` can turn the
  friction into improvements. It is context for the agent and a line the
  user sees. It never blocks.
- **Retrospective placement.** The skill's description and the router's
  map name the moment after a wave of delegated tickets is merged. The
  skill takes the skill-usage mod's numbers as an input when they exist.
- **Onboarding notice.** At a session start the adapter says, once per
  project, when the project lacks any of these, and names the onboarding
  skill for each:
  - an agent instruction file, `AGENTS.md` or `CLAUDE.md` at the project
    root: `agent-instructions-integrator`;
  - a context map, `docs/agents/context-matrix.md`: `context-matrix-map`;
  - a standards document, `docs/agents/project-standards.md`:
    `project-standards-calibration`.
  Confirm those paths against what the three skills write by default, and
  use the skills' paths if they differ.
  - That the notice was shown is recorded outside the project folder,
    keyed by the project. It shows again only when the set of missing
    files changes.
  - The rule, with the file paths, is stated in the shared policy's
    onboarding section or the three skills, inside the word budgets. The
    adapter enforces that statement.
- **Router wording.** The router's lines for `source-grounded-research`,
  `documentation-writer`, `documentation-cleanup` and `goated-prompt` are
  checked against each skill's description and corrected where the router
  would not select the skill for work its description names.
- The router and shared policy stay inside their word budgets.
- Update the README's Session Start Notices and State sections.

## Recommended First Reads

- The parent spec, R6, R9 and its Constraints.
- `adapters/claude-code/goated_adapter/hooks.py` (session start and
  user-prompt handling), `policy.py` (the existing notices) and `state.py`
  (`SessionState`, `policy_notice_shown`).
- `adapters/claude-code/README.md`: Session Start Notices, State.
- `skills/agent-workflows/retrospective/SKILL.md`, the three onboarding
  skills' output paths, and the router's skill map.
- The router as Ticket 072 left it.

## Acceptance Criteria

- [ ] A session with three declined or unanswered holds gets the
      retrospective notice once, at the next prompt. One with two gets
      none, and a fourth hold brings no second notice.
- [ ] A hold answered by a load or a read, and one stood down by a typed
      override, do not count.
- [ ] A project with no agent instruction file gets the start notice
      naming `agent-instructions-integrator`. A second session in the same
      project gets none. A project with all three files gets none.
- [ ] When a second file goes missing, the notice shows again, once.
- [ ] No notice blocks a call or a `Stop`, and nothing is written inside
      the project folder.
- [ ] The router's fixtures select each of the four research and
      doc-writing skills for a prompt its description names.
- [ ] The router and shared policy stay inside their budgets.

## Expected Proof

- Adapter tests for each notice criterion, each with a near miss.
- The routing fixtures and the skill validator pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, including the
  context comparison.

## Blocked By

- `tickets/archive/072-orientation-and-plans-in-routes.md` (both edit the router,
  which is at its word budget).

## Scope Exclusions

- Holds for any of these skills.
- Running a retrospective automatically.
- Detecting the quality of existing instruction or context files.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `3e3fcb9` (`fd96778`, review fix `a766182`).
- Exercised in later sessions; no separate live-check record.
