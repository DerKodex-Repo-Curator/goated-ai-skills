# Ticket 027: Handoff Spawn-Brief Mode

## Parent Spec

None. Maintainer-requested on 2026-11-15 after an analysis found no skill
that owns the first message an agent sends to a new subagent or session.

## Type

HITL — the maintainer judges the result after a period of real use and records
keep, revise, or revert.

## What To Build

Give `handoff` a spawn-brief mode: when the work is about to start in a fresh
agent or session now, the output is a self-contained brief sent as that
agent's first message instead of a resume file. Add the brief template as a
directly linked reference and point implementation briefs at the existing
`subagent-driven-development` implementer prompt. Leave the change uncommitted.

## Recommended First Reads

- `skills/agent-workflows/handoff/SKILL.md`
- `skills/engineering/subagent-driven-development/references/implementer-prompt.md`
- `stack/AGENTS.md` — "Ownership And Delegation".

## Acceptance Criteria

- [ ] `handoff` Step 1 routes a live delegation to spawn-brief mode, and the
      description names briefs for a new agent or session.
- [ ] `references/spawn-brief.md` covers goal, scope and write ownership, done
      criteria, settled decisions and ruled-out paths, sources, constraints,
      stop conditions, and the evidence the child returns.
- [ ] The brief tells the author not to restate rules the child already gets
      from its own instructions or setup.
- [ ] `SKILL.md` stays under the 300-line soft cap.
- [ ] Observations from real use are collected for the keep, revise, or revert
      decision.

## Expected Proof

- Validator, unit-test, and context-comparison output.

## Blocked By

- None

## Scope Exclusions

- Enforcement hooks and the maintainer's personal hook and settings files.
- Registry schema changes and new skills.
- Commits, pushes, and merging into `main`.
