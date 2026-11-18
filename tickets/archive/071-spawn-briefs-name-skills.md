# Ticket 071: A Spawn Brief Names The Skills To Read

## Parent Spec

`docs/specs/2026-11-17-skill-placement-gates.md` (R7, R10; AC7)

## Type

AFK.

## Problem

No hold reaches inside a subagent, and a brief does not say which skills
apply to the work it hands over. In 84 recorded sessions, 41 subagent
spawns led to 11 reads of a `SKILL.md`. A subagent that implements or
reviews code does so without the skills the parent had to load.

## What To Build

- Each brief template the `spawn` gate knows gains a line naming the
  skills the new agent should read before it starts, or none with a
  reason: `handoff`'s spawn brief, and the implementer and reviewer
  prompts of `subagent-driven-development`.
- The templates say how a subagent reads a skill it cannot load with a
  skill tool: by reading its `SKILL.md`.
- The `spawn` gate's content check requires the line. A brief without it,
  with an empty list, or with none and no reason fails the check, and the
  hold says what is missing.
- The line's form is defined once, where the brief templates are, and the
  adapter's check follows it.
- Update the README's Content checks section and regenerate
  `adapters/claude-code/skill-usage/tests/adapter-texts.ts`.

## Recommended First Reads

- The parent spec, R7.
- `skills/agent-workflows/handoff/references/spawn-brief.md`.
- `skills/engineering/subagent-driven-development/references/implementer-prompt.md`
  and `reviewer-prompt.md`.
- `adapters/claude-code/goated_adapter/contracts.py` (`BriefTemplate`,
  `BRIEF_TEMPLATES`) and `actions.py` (`_spawn_hold`).
- `adapters/claude-code/README.md`: Content checks.
- Ticket 056, for the route line a brief already carries.

## Acceptance Criteria

- [ ] A brief with the line naming one or more skills passes the content
      check.
- [ ] A brief with none and a reason passes; none with no reason does not.
- [ ] A brief without the line is held, and the hold names the missing
      line.
- [ ] The three templates carry the line and stay inside the context
      comparison's budgets.
- [ ] A card with a brief (Ticket 064) meets the same check.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The mod's tests pass against regenerated texts.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, including the
  context comparison.
- A live check: one real spawn whose subagent reads a named skill.

## Blocked By

None.

## Scope Exclusions

- Checking that the subagent read the skills.
- Checking that the named skills are the right ones.
- Holds inside a subagent.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `edb5bdf` (`52ce49f`, follow-up `a3e1e8d`).
- Maintainer decision: the brief's skills line stays strict, with
  `goated-skills: none: <reason>` as the justified skip.
- Exercised in later sessions; no separate live-check record.
