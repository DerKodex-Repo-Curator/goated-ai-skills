# Ticket 068: Reference Reads Selected By What The Turn Did

## Parent Spec

`docs/specs/2026-11-17-registry-reference-reads.md` (R2, R5, R6; AC6, AC7)

## Type

AFK.

## Problem

Ticket 067 enforces references selected by a single edit. Some references
apply at a moment in the turn: after a check has failed twice, when
security-sensitive changes spread, or before a spec or ticket file is
written. In the skill-usage data the security checklist was never read in
13 loads, the `diagnose` references never in 6, and the ticket template
once in 10.

## What To Build

- The `reference-reads` gate implements the remaining signal kinds: another
  gate firing, a count of sensitive categories changed in the turn, and a
  write under a path.
- It enforces, from the registry, once the skill counts as loaded:
  - `diagnose` `root-cause-tracing.md` on a write held by, or made after,
    the repeated-failure gate's two failures of one check;
  - `code-security-review` `security-review-checklist.md` on a write to a
    sensitive path once the turn's sensitive changes span two or more
    categories, as the `security` gate names categories;
  - `write-a-spec` `spec-template.md` before a write under `docs/specs/`;
  - `spec-to-tickets` `ticket-slicing-templates.md` before a write under
    `tickets/`.
- A path signal judges the path inside the project, by the adapter's
  existing rule for where a file is.
- A reference of these kinds added to the registry later is enforced with
  no adapter change.
- Update the README's registry references section and regenerate
  `adapters/claude-code/skill-usage/tests/adapter-texts.ts` if a text
  changed.

## Recommended First Reads

- The parent spec, R2 and R6.
- The gate as Ticket 067 left it.
- `adapters/claude-code/goated_adapter/actions.py`
  (`_repeated_failure_hold`, the `security` gate's categories,
  `_Changes.sensitive`, `find_project`).
- `adapters/claude-code/README.md`: the `repeated-failure` and `security`
  rows.

## Acceptance Criteria

- [ ] With `diagnose` loaded, the first write after one check failed twice
      is held until `root-cause-tracing.md` is read. After one failure it
      is not.
- [ ] With `code-security-review` loaded, a sensitive write when the turn's
      changes span two categories is held until the checklist is read.
      With one category it is not.
- [ ] With `write-a-spec` loaded, a write under `docs/specs/` is held until
      the template is read. A write under `docs/` elsewhere is not.
- [ ] With `spec-to-tickets` loaded, a write under `tickets/` is held until
      the templates are read. A file outside the project named `tickets/x`
      is not held.
- [ ] Each hold clears on the read or on a skip line naming the skill.
- [ ] A fixture registry entry of each kind is enforced with no adapter
      change.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The mod's tests pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.

## Blocked By

- `tickets/067-adapter-reference-reads-gate-edit-signals.md` (the gate).

## Scope Exclusions

- New signal kinds beyond the schema's set.
- Changing the `repeated-failure` or `security` gates.
