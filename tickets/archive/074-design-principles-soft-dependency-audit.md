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

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `9b4ee70` (`8907b4b`).
- Exercised in later sessions; no separate live-check record.

Maintainer decision, 2026-11-17: six skills now name
`software-design-principles` as a soft dependency, each with the moment it
applies. Their existing fallbacks already cover a missing companion skill.

- `verification-before-completion`: a claim covers a changed module,
  interface, error-handling path, or configuration surface.
- `standards-and-spec-review`: the review judges design quality.
- `receiving-code-review`: classifying feedback about interfaces, naming,
  knowledge ownership, or error handling.
- `diagnose`: the proven fix changes a module, interface, or error path, or
  where the fix belongs is in question.
- `subagent-driven-development`: implementer and reviewer briefs for
  delegated design changes.
- `prototype`: absorption shapes the production interface. First proposed
  as excluded; the maintainer accepted adding it after the review.

Left out, with the maintainer's agreement:

- `code-security-review`: it judges trust boundaries, and
  `software-design-principles` already points to it.
- `write-a-spec`, `spec-to-tickets`, `grill-with-docs`: each defers module
  and interface strategy to `design-codebase-architecture`, which names it.
  They sit on the `product-idea-to-vertical-slice` comparison route, which
  has no word headroom. The maintainer allowed going over the budget where
  the value justifies it, and judged a direct pointer not worth that here.
- `architecture-design-map` (describes, not judges),
  `resolving-merge-conflicts` (keeps both sides' intent), and the docs,
  commit, PR, onboarding, research, prompt, productivity, and agent-workflow
  skills (no code design).
- Already named before this ticket: the router, `tdd`, `writing-plans`,
  `code-refinement`, `design-codebase-architecture`,
  `review-codebase-architecture`.

The registry, fixtures, and catalogs record no dependencies, so they are
unchanged.
