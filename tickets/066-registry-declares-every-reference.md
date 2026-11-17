# Ticket 066: The Registry Declares Every Skill Reference

## Parent Spec

`docs/specs/2026-11-17-registry-reference-reads.md` (R1, R2, R3, R4, R7, R8;
AC1, AC2)

## Type

HITL. The maintainer reviews the classification of every reference,
enforced or advisory, before it lands.

## Problem

Skills say when to read each reference file, but nothing records those
moments in a form a framework adapter can enforce or a check can verify.
The skill-usage data shows that references no hold asks for are almost
never read. A new skill's references can go uncovered with no warning.

## What To Build

- **Schema.** Each skill's registry entry lists its reference files. Each
  file has either a signal, which makes the read enforced, or the word
  advisory with a short reason. A signal is one of a closed set of kinds
  the schema names:
  - an edit whose added text matches a named pattern;
  - an edit of a kind of file;
  - a write under a path;
  - another gate firing;
  - a count of sensitive categories changed in the turn;
  - a spawn with a brief;
  - an existing adapter rule named by its gate.
- **Entries.** Every file under every skill's `references/` is declared.
  - The first enforced set is the spec's R6.
  - References enforced today (`software-design-principles`, `handoff`,
    `subagent-driven-development`) are declared with the existing-rule
    kind and change no behaviour.
  - Every other reference is classified from its "read when" sentence:
    enforced where a kind fits, advisory with the reason where none does.
    Present the full list to the maintainer before finishing.
- **Validation.** `scripts/validate_skills.py` fails when a reference file
  is undeclared, a declared file is missing, a kind is unknown, an advisory
  entry has no reason, or a skill's `SKILL.md` links a reference the
  registry lacks. A fixture under `stack/fixtures/` covers the entries.
- **Standard.** `AGENTS.md` and `skills/README.md` say that adding,
  renaming or removing a reference file updates the registry in the same
  change.

## Recommended First Reads

- The parent spec, R1 to R4, R6 to R8.
- `stack/goated-stack.yaml` and `stack/schemas/`.
- `scripts/validate_skills.py` and its tests.
- `skills/README.md` (frontmatter schema and required sections).
- Each skill's References section, for its "read when" sentences.
- `adapters/claude-code/README.md`: Design references, for the signals
  enforced today.

## Acceptance Criteria

- [ ] Every file under every skill's `references/` is in the registry with
      a signal or an advisory reason.
- [ ] The validator fails for an undeclared reference file, an entry for a
      missing file, an unknown kind, and an advisory entry with no reason;
      a test covers each.
- [ ] The validator fails when a `SKILL.md` links a reference the registry
      lacks.
- [ ] The spec's first enforced set is declared as enforced.
- [ ] The maintainer's decision on the classification is recorded in this
      ticket's closeout.
- [ ] `AGENTS.md` and `skills/README.md` state the standard.
- [ ] No installed skill needs the registry at runtime.

## Expected Proof

- Validator tests for each failure, each with a passing near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, including the
  context comparison.

## Blocked By

None.

## Scope Exclusions

- Any adapter change.
- Rewording a skill's "read when" sentences, except to fix one that names a
  missing file.
- New reference files.
