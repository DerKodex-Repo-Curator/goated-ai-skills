# Ticket 025: Lean Skills Update

## Parent Spec

`docs/specs/2026-10-06-lean-skills-update.md`

## Type

HITL — the maintainer judges the result after a period of real use and records
keep, revise, or revert.

## What To Build

Deliver the whole lean-skills batch on `update/lean-skills` as one reviewable
working-tree change: the moderate pruning pass over all 37 skills, the
`pr-description` and `retrospective` skills, and the listed refinements to
existing skills. Leave the branch validated and installable. Do not commit or
merge.

## Recommended First Reads

- `docs/specs/2026-10-06-lean-skills-update.md` — requirements R1 to R4.
- `skills/README.md` — lean schema and body sections.
- `skills/agent-workflows/framework-agnostic-skill-creator/references/skill-evaluation.md`
  — the lenses the pruning pass applies.
- `tests/test_v2_refinement_contracts.py` — wording that must not change.

## Relevant Source Links

- `stack/goated-stack.yaml`
- `stack/fixtures/output-communication/`
- `scripts/validation/behavior_proof.py`
- `tests/test_validator_compatibility.py`

## Acceptance Criteria

- [ ] AC1 to AC5 of the parent spec hold on the working tree.
- [ ] The branch is installed into the maintainer's agent framework from a
      backed-up snapshot, with both new skills discoverable.
- [ ] Observations from real use are collected for the AC6 decision and for
      Ticket 023.

## Expected Proof

- Validator, unit-test, and context-comparison output.
- Before and after totals for `SKILL.md` words and `- Do not` lines.
- A list of every test edit, each a numeric, count, or path pin.

## Blocked By

- None

## Scope Exclusions

- `stack/AGENTS.md`, the registry schema, and the router gate table.
- A `domain-modeling` skill, and closing Ticket 023 or 024.
- Commits, pushes, and merging into `main`.
