# Placing Rarely Used Skills In The Workflow

## Status

Approved by the maintainer on 2026-11-17 in a
grill-with-docs session. Ticket ready.
Builds on
[the skill enforcement spec](2026-11-15-skill-enforcement-adapter.md),
[the activation gates spec](2026-11-16-adapter-skill-activation-gates.md),
[the written-line holds spec](2026-11-17-adapter-written-line-holds.md) and
[ADR 0003](../adr/0003-opt-in-framework-enforcement-adapters.md).

## Mode

Compact.

## Problem

The skill-usage mod's data, 84 sessions from 15 to 17 November 2026, shows
that a skill loads when a hold or the router asks for it and rarely
otherwise. Of 40 registry skills, 12 never loaded and 14 more loaded in one
or two sessions. The gaps that matter:

- **Review.** The `pr-review` gate never fired, because work is merged
  locally with no pull request. `standards-and-spec-review` loaded in one
  session. A reviewer, not a hold, caught Ticket 059's high-severity bug.
- **Review intake.** `receiving-code-review` loaded once, though every
  ticket went through review and fixes.
- **Verification.** `verification-before-completion` loaded in four
  sessions. Its description covers complex, high-risk, delegated and
  multi-surface work, which describes most tickets here.
- **Orientation.** `session-start-progressive-disclosure` never loaded,
  though the router's table says it is always selected, and side sessions
  start in areas they do not know.
- **Plans.** `writing-plans` loaded in one session; tickets went straight
  to code.
- **Retrospective.** `retrospective` never loaded. The planning rounds that
  turn agent feedback into specs are retrospectives done by hand.
- **Subagents.** 41 spawns led to 11 reads of a `SKILL.md`. No hold reaches
  inside a subagent, and a brief does not say which skills apply.
- **Design principles.** `software-design-principles` is new, and only six
  skills name it. Skills that judge or produce design, such as
  `verification-before-completion`, do not.
- **Onboarding, research and doc-writing skills.** Ten of them never
  loaded in any stored session, including the maintainer's sessions in
  another project.

## Goals

- A large change is reviewed before it is committed, whether or not a pull
  request exists.
- Review findings are handled through `receiving-code-review`.
- Work that fits `verification-before-completion`'s description loads it
  before the turn ends.
- A briefed side session orients itself before its first write.
- Ticket work gets a plan, and a wave of tickets ends with a
  retrospective.
- A subagent's brief names the skills it should read.
- Skills that judge or produce design point to
  `software-design-principles`.

## Non-Goals

- Holds for the onboarding, research and doc-writing skills. They get a
  notice and router wording only, until usage data exists.
- Changing the `pr-review` gate.
- Enforcement inside a subagent.
- Judging the quality of a review, a plan or a retrospective.
- Checking any new line the agent writes, beyond the brief's content
  check, which already exists.

## Requirements

- **R1, review at commit.** The closeout gains a Review item when the
  branch's work is large: 400 or more changed lines between the branch it
  will merge into and the working tree. That counts committed work on the
  branch, staged and unstaged changes, and new untracked files that git
  does not ignore. The base is found as the `pr-review` gate finds it, and
  the size measure gains a mode for this, since today it compares two
  committed refs. Measuring the branch, not the commit, means a large
  ticket split across commits is still caught; it also means later
  commits on a large branch raise the item again. The item is met by a
  reviewer subagent that finished after the last code change, or by
  `standards-and-spec-review` counting as loaded and a change read after
  it. Its skip line names `standards-and-spec-review`. It joins the
  commit-time list. When git cannot measure the change, or the checkout is
  on the base branch with nothing to compare, the item is not raised.
  Where the base exists both locally and on `origin`, the work is measured
  from the fork point closer to the branch, so local merges prefer the
  local base.
- **Reviewer subagents.** For R1 and R2, a reviewer subagent is a finished
  spawn whose brief follows `subagent-driven-development`'s reviewer
  prompt. The `spawn` gate records which template a brief matched, by the
  call's id, as the design gates record an edit's references. A review
  briefed any other way, the `handoff` spawn brief included, does not
  count, and the Review item's text says to use the reviewer prompt.
- **R2, review intake.** After a reviewer subagent's result arrives in a
  turn, the first write to a code file is held until
  `receiving-code-review` counts as loaded. The hold is justified-skip.
  The trigger is stated in that skill's own text, not in the router.
- **R3, verification.** The closeout gains a Verification item when any of
  these holds: the task's route is `full`; a subagent changed code; a
  security-sensitive file changed; or the branch's work is large, as in
  R1. It is
  met when `verification-before-completion` counts as loaded. Its skip
  line names that skill; the Proof item keeps the same skip line, so one
  line answers both, and the README says so.
- **R4, orientation.** In a session routed by its brief, on a `standard` or
  `full` route, the first write is held by `pipeline` until
  `session-start-progressive-disclosure` loads, when that skill is
  installed. A `direct` or `lightweight` route needs no orientation, as the
  registry's `profile_eligibility` for the skill lists. The router's table
  stops saying the skill is always selected: it is selected for unfamiliar,
  cross-area, stale or boundary-uncertain work, and on a `standard` or
  `full` route from a brief.
- **R5, plans.** The router requires `writing-plans` in the route of a task
  that implements a ticket at `standard` or `full` intensity.
- **R6, retrospective.**
  - The adapter gives a notice, not a hold, when a session has had three or
    more holds that were declined or left unanswered: it names
    `retrospective`. A hold is declined when a skip line cleared it, and
    unanswered when no load, read or skip line answered it before the
    next typed prompt. A hold the user's typed override stood down counts
    as neither. The saved state gains a count of such holds and whether
    the notice was shown. The notice appears once per session, at the
    next prompt.
  - The `retrospective` skill's description and the router's map name the
    moment after a wave of delegated tickets is merged. The skill takes the
    skill-usage mod's numbers as an input when they exist.
- **R7, skills in a brief.** Each brief template the `spawn` gate knows
  (`handoff`'s spawn brief, and the implementer and reviewer prompts of
  `subagent-driven-development`) gains a line naming the skills the new
  agent should read, or none with a reason. The gate's content check
  requires the line.
- **R8, design principles as a dependency.** Every skill is audited, and
  `software-design-principles` is added as a soft dependency wherever a
  skill judges or produces design. The maintainer reviews the proposed
  list before it lands.
- **R9, notices for unused skills.** At a session start the adapter says,
  once per project, when the project lacks any of these, and names the
  onboarding skill for each:
  - an agent instruction file, `AGENTS.md` or `CLAUDE.md` at the project
    root: `agent-instructions-integrator`;
  - a context map, `docs/agents/context-matrix.md`: `context-matrix-map`;
  - a standards document, `docs/agents/project-standards.md`:
    `project-standards-calibration`.
  Those are the paths the three skills write by default. The rule is
  stated in the shared policy's onboarding section or those skills, inside
  the word budgets. That the notice was shown is recorded outside the
  project folder, keyed by the project, and it shows again only when the
  set of missing files changes. The router's wording for the research and
  doc-writing skills is checked against their descriptions and corrected
  where it would not select them.
- **R10, documentation.** The adapter README, the router, the registry and
  its fixtures, and the catalog lists match the changes. Changed hold
  texts are regenerated for the skill-usage mod.

## Acceptance Criteria

- [ ] AC1: A commit on a branch whose work against its base is 400 or
      more lines, with no review, is held by the closeout's Review item. A
      finished reviewer subagent, or the skill load and a change read,
      clears it. A 399-line branch raises no item, and two 300-line
      commits on one branch raise it at the second.
- [ ] AC2: After a reviewer subagent returns, the first code edit is held
      until `receiving-code-review` loads or a skip line names it. An
      implementer subagent's return, and a subagent briefed from the
      `handoff` spawn brief, hold nothing.
- [ ] AC3: Each of the four Verification triggers raises the item alone,
      and a turn with none of them does not.
- [ ] AC4: A briefed side session with a `standard` or `full` brief route is
      held on its first write until the orientation skill loads, when it is
      installed. One with a `direct` or `lightweight` brief route is not.
- [ ] AC5: The router's fixtures select `writing-plans` for a ticket
      implementation at `standard`, and not for a `lightweight` task.
- [ ] AC6: A session with three declined holds gets the retrospective
      notice once. One with two gets none.
- [ ] AC7: A brief without the skills line fails the `spawn` content
      check; one with skill names, or none and a reason, passes.
- [ ] AC8: The audit's list is recorded with the maintainer's decision, and
      each skill on it names `software-design-principles` as a soft
      dependency.
- [ ] AC9: A project with no agent instruction file gets the start notice
      once; a second session there gets none, and a project that has all
      three files gets none.
- [ ] AC10: The kept holds behave as before, and the repo checks in
      `AGENTS.md` pass on Python 3.11 and 3.14, with the router and shared
      policy inside their word budgets.

## Proof Surface

The adapter's hook entry points, driven by transcript fixtures, for R1 to
R4, R6, R7 and R9. The router's routing fixtures under `stack/fixtures/`
for R4 and R5. The skill validator for R8. A live check in one real session
that commits a large change.

## Constraints

- Every new rule (a signal, a trigger, a threshold, an item's wording of
  what is required) is stated in the registry, the shared policy or a skill.
  The adapter maps Claude Code's events to those rules and adds none of its
  own, as ADR 0003 requires, so another harness's adapter can enforce the
  same rules ([portable enforcement spec](2026-11-17-portable-enforcement-core.md)).
- Every hold added here is justified-skip, except the orientation
  requirement, which is strict like the rest of `pipeline` and is dropped
  only when the task's route is `direct` or `lightweight`, or the skill is
  not installed.
- The router and shared policy are at their word budgets (Ticket 053's
  notes), so R4, R5 and R9 must trade words, not add them.
- The spawn-brief template must still fit the context comparison.
- R2 and R3 rely on Ticket 065's rule for when a skill counts as loaded.
- A notice never blocks.

## Open Questions

None.

## Risks

- More closeout items mean longer holds at commit. This is mitigated
  because Review and Verification fire only on large, delegated, `full` or
  sensitive work, and each accepts a skip line.
- Agents may answer Review with a thin reviewer brief. The `spawn` gate's
  content check applies to that brief.
- The audit in R8 touches many skills at once. It is one reviewed change,
  with the validator and the context comparison run on the result.

## Sources

- `adapters/claude-code/goated_adapter/actions.py`: `check_closeout`,
  `_pr_review_hold`, `changed_lines`, `_spawn_hold`.
- `adapters/claude-code/goated_adapter/gates.py`: `check_routing`.
- `adapters/claude-code/goated_adapter/contracts.py`: `BRIEF_TEMPLATES`.
- `adapters/claude-code/README.md`: Large pull requests, Session Start
  Notices, the closeout table.
- `skills/agent-workflows/using-goated-ai-skills/SKILL.md`,
  `skills/agent-workflows/handoff/references/spawn-brief.md`,
  `skills/agent-workflows/retrospective/SKILL.md`,
  `skills/engineering/verification-before-completion/SKILL.md`.
- The skill-usage mod's stored summaries, 15 to 17 November 2026.
