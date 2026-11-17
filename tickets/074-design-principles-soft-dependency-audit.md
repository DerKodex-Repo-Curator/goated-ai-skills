# Ticket 074: Skills That Judge Design Point To Software-Design-Principles

## Parent Spec

`docs/specs/2026-11-17-skill-placement-gates.md` (R8; AC8)

## Type

HITL. The maintainer reviews the proposed list of skills before any skill
file changes.

## Problem

`software-design-principles` is a recent addition. Only six skills name
it: the router, `tdd`, `writing-plans`, `code-refinement`,
`design-codebase-architecture` and `review-codebase-architecture`. Skills
that judge or produce design, such as `verification-before-completion`,
`standards-and-spec-review`, `receiving-code-review`,
`subagent-driven-development` and `diagnose`, do not, so an agent
following them alone has no pointer to the design guidance.

## What To Build

- Audit every skill in the registry. For each, decide from its workflow
  whether it judges or produces module, interface, error-handling or
  configuration design.
- Present the list to the maintainer: each skill proposed, where in its
  workflow the dependency applies, and each skill considered and left out
  with the reason.
- For each approved skill, add `software-design-principles` as a soft
  dependency with the moment it applies, in the form the skill's
  Dependencies section already uses. Keep each skill's standalone
  fallback.
- Update the registry, fixtures and catalog lists only where the change
  affects them.

## Recommended First Reads

- The parent spec, R8.
- `skills/README.md` (the Dependencies section's rules).
- `skills/engineering/software-design-principles/SKILL.md`.
- The Dependencies section of each skill named in the Problem.
- `stack/goated-stack.yaml`.

## Acceptance Criteria

- [ ] The audit covers every registry skill, and the proposal lists
      included and excluded skills with reasons.
- [ ] The maintainer's decision is recorded in this ticket's closeout.
- [ ] Each approved skill names `software-design-principles` as a soft
      dependency with when it applies, and keeps a fallback that works
      without it.
- [ ] No `SKILL.md` passes the soft 300-line cap, and the context
      comparison stays inside its budgets.

## Expected Proof

- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- The recorded maintainer decision.

## Blocked By

None.

## Scope Exclusions

- Hard dependencies.
- Changing `software-design-principles` itself.
- Adapter changes.
