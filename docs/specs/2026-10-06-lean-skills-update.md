# Lean Skills Update

## Status

Approved for an experimental branch (`update/lean-skills`). Not yet accepted
for `main`; acceptance follows a period of real use.

## Mode

Compact.

## Problem

A second comparison against `mattpocock/skills`, pinned at commit
`6fd947921b935b7e1e69293a200400f0fdd5c15f`, found that upstream has moved toward
fewer and shorter skills while GOATED's 37 `SKILL.md` files carried about
50,700 words and 340 `- Do not` guardrail lines, many of them repeated
boilerplate. The authoring lenses added by Ticket 015 (no-op guidance, positive
steering, observable completion) had been applied to the skill creator but not
to the existing catalogue. The product-idea route sat at 10.2% against the 10%
context-reduction floor, leaving no room for additions.

The comparison also found a small number of upstream ideas GOATED lacked.

## Goals

- Shorten every skill's hot path without changing its workflow, gates, or
  output contract.
- Add the two capabilities with no GOATED equivalent: a pull-request
  description and a session retrospective.
- Apply the small refinements the comparison verified as real gaps.
- Leave the branch installable so the changes can be judged in real use.

## Non-Goals

- No change to `stack/AGENTS.md`, the registry schema, or the router gate table.
- No `domain-modeling` skill, issue triage, remote tracker publishing, guided
  learning, hooks, or installer tooling.
- No rewrite of skills toward upstream's structure; this is an edit pass.
- No commits, pushes, or acceptance into `main` as part of this work.

## Requirements

### R1: Catalogue pruning

Every `SKILL.md` is pruned at moderate depth: source-repository and generic
privacy boilerplate removed, prohibitions rewritten as positive targets except
where they guard destructive, security, privacy, production, external, Git
lifecycle, or authorization boundaries, soft-dependency lists trimmed to real
routes, and Delegation sections shortened. Frontmatter, required headings,
links, workflow order, gates, approval rules, and output-contract fields are
preserved.

### R2: New skills

- `pr-description` (engineering): text-only pull-request body grounded in the
  inspected diff and fresh verification evidence. It follows an existing
  project template, otherwise Summary, Evidence, and Merge Risk. It never
  opens, edits, or publishes a pull request.
- `retrospective` (agent-workflows): proposal-only review of a session that
  turns agent mistakes and friction into proposed changes to the project's
  checks, standards, instruction files, and tooling. It edits nothing itself.

Both are reached by description. Neither adds a router gate.

### R3: Refinements to existing skills

- `diagnose`: observable exit test for the feedback loop, raising the
  reproduction rate of intermittent symptoms, one tag for temporary
  instrumentation, showing ranked hypotheses without blocking, recording the
  confirmed cause with the fix.
- `tdd`: tautological assertions as an anti-pattern.
- `write-a-spec`: optional proof surface.
- `spec-to-tickets`: one-session sizing test, prefactoring as the named
  foundation ticket, first reads treated as orientation.
- `handoff`: a check that a handoff is the right tool.
- `review-codebase-architecture`: scoping by recent change, and checking and
  offering to record rejections.
- `framework-agnostic-skill-creator`: an environment-as-source evaluation lens.
- `grill-me` and `grill-with-docs`: frontier rounds in rapid and deep-dive
  modes, and a stakeholder-questionnaire reference.
- `grill-with-docs`: writing one settled term or ADR-worthy decision at the
  moment it settles, when current consent covers the write.
- `setup-scribe`: a guided-manual-procedure reference.
- `resolving-merge-conflicts`: its inspiration link pinned to the last upstream
  commit that contained the skill.

### R4: Recorded decisions this spec reopens or defers

- Scoping an architecture review by recent change reopens one item of the
  "optional architecture hotspot and review ergonomics" track that
  `tickets/selective-upstream-skill-adoption-order.md` lists as deferred. The
  rest of that track stays deferred.
- The `grill-with-docs` inline write is the "refine current skills" remedy that
  Ticket 023 is meant to evaluate. Ticket 023 stays open. Use of this branch is
  evidence for that ticket, not its decision.

## Acceptance Criteria

- [ ] AC1: All 37 existing skills are pruned under R1, and every sentence
      pinned by `tests/test_v2_refinement_contracts.py` is unchanged.
- [ ] AC2: `pr-description` and `retrospective` are implemented, registered,
      covered by fixtures, self-contained, and listed in the public catalogue.
- [ ] AC3: Each R3 refinement is present in the named skill or reference.
- [ ] AC4: The validator, the unit tests, and the V1/V2 context comparison
      pass, with every route at or above the 10% floor.
- [ ] AC5: Test edits are limited to numeric, count, and path pins; no
      assertion about skill wording is changed.
- [ ] AC6: After a period of real use, the maintainer records keep, revise, or
      revert for the pruning pass, each new skill, and the grill changes.

## Constraints

- Individually installed skills keep a standalone fallback.
- New `SKILL.md` files stay under the 1,500-word decomposition threshold.
- Adapted ideas are written in GOATED's own wording. Upstream `pr` credits
  Humanlayer's `show-me` skill as its source; that source's licence was not
  reviewed, so none of its wording is reused.

## Open Questions

- Does the pruned catalogue behave as well as the original in real use? Owner:
  GOATED maintainer, after the trial period. There is no live evaluation
  harness, so this cannot be answered by the repository's checks.

## Sources

- `AGENTS.md` and `skills/README.md` — maintainer contract and lean schema.
- `docs/specs/2026-07-26-selective-upstream-skill-adoption.md` — earlier
  adoption, its non-goals, and requirement R7.
- `tickets/023-evaluate-active-domain-modeling.md` — the open evaluation gate.
- `skills/agent-workflows/framework-agnostic-skill-creator/references/skill-evaluation.md`
  — the authoring lenses applied by R1.
- `https://github.com/mattpocock/skills` at
  `6fd947921b935b7e1e69293a200400f0fdd5c15f` — upstream comparison point.
