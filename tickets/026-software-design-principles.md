# Ticket 026: Software Design Principles Skill

## Parent Spec

`docs/specs/2026-11-13-software-design-principles.md`

## Type

HITL — the maintainer judges the result after a period of real use and records
keep, revise, or revert.

## What To Build

Deliver the whole integration on `update/software-design-principles` as one
reviewable working-tree change: the `software-design-principles` skill and its
references, the rewritten readability paragraph in the shared policy, the five
gates in existing skills, the registry entry, one fixture, the section-id test,
the catalogue entries, and the human edition under `docs/reference/`. Leave the
branch validated. Do not commit, push, or install.

## Recommended First Reads

- `docs/specs/2026-11-13-software-design-principles.md` — requirements R1 to
  R5.
- `skills/README.md` — lean schema and body sections.
- `stack/AGENTS.md` — the shared policy and its word target.
- `tests/test_validator_compatibility.py` — count and word pins.

## Relevant Source Links

- `stack/goated-stack.yaml`
- `stack/fixtures/behavior-proof/`
- `scripts/validation/behavior_proof.py`
- `scripts/compare_v1_v2_context.py`

## Acceptance Criteria

- [ ] AC1 to AC7 of the parent spec hold on the working tree.
- [ ] Observations from real use are collected for the AC8 decision.

## Expected Proof

- Validator, unit-test, and context-comparison output.
- Before and after word counts for the shared policy and each edited
  `SKILL.md`.
- A list of every edit to an existing test assertion, each a numeric or count
  pin.

## Blocked By

- None

## Scope Exclusions

- An enforcement hook, a router gate, and registry schema changes.
- `standards-and-spec-review`, `verification-before-completion`, and
  `agent-instructions-integrator`.
- The maintainer's personal instruction files and the installed copy.
- Commits, pushes, and merging into `main`.
