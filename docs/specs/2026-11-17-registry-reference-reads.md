# Reference Reads Declared In The Registry

## Status

Approved by the maintainer on 2026-11-17 in a
grill-with-docs session. Ticket ready.
Builds on
[the design reference reads spec](2026-11-16-design-reference-reads.md),
[the written-line holds spec](2026-11-17-adapter-written-line-holds.md) and
[ADR 0003](../adr/0003-opt-in-framework-enforcement-adapters.md).

## Mode

Compact.

## Problem

Skills keep detail in reference files and say when to read each one. The
skill-usage mod's data, 84 sessions from 15 to 17 November 2026, shows that
agents read a reference when a hold asks for it and almost never otherwise:

| Reference | Reads | A hold asks for it |
| --- | --- | --- |
| `software-design-principles` `red-flags.md` | 97 | yes |
| `handoff` `spawn-brief.md` | 47 | yes |
| other `software-design-principles` references | 59 | yes |
| `subagent-driven-development` prompts | 11 | yes |
| `tdd`, five references, 64 loads | 1 | no |
| `spec-to-tickets` template, 10 loads | 1 | no |
| `write-a-spec` template, 7 loads | 4 | no |
| `code-security-review` checklist, 13 loads | 0 | no |
| `diagnose`, four references, 6 loads | 0 | no |

The rules that are enforced live in the Claude Code adapter's code, so each
new reference needs an adapter change, another framework's adapter cannot
reuse them, and nothing tells a maintainer that a new skill's references are
not covered.

## Goals

- Every reference file of every skill is declared in the registry, with
  when it must be read or why it is advisory.
- The adapter enforces what the registry declares, with no adapter change
  for a new reference that uses an existing kind of signal.
- A skill added or changed without declaring its references fails the
  repo's checks.
- Enforcement applies only once the skill is loaded, so it adds no hold to
  work that does not use the skill.

## Non-Goals

- Deciding whether a skill loads. Routing and the action gates own that.
- Checking that a reference was applied. No citation is asked for outside
  `software-design-principles`.
- Changing how `software-design-principles` references are selected or
  cited.
- A line the agent writes to declare which references apply.
- Enforcement inside a subagent, or by adapters for other frameworks.

## Requirements

- **R1, registry entries.** Each skill's entry in `stack/goated-stack.yaml`
  lists every file under its `references/` folder. Each file has either a
  signal, which makes the read enforced, or the word advisory with a short
  reason. The registry schema defines the shape.
- **R2, signal kinds.** A signal is one of a small closed set of kinds the
  schema names, each observable from a tool call or the turn so far. The
  first set covers:
  - an edit whose added text matches a named pattern (a mock or patch; a
    sleep, retry or timeout);
  - an edit of a kind of file (a test file);
  - a write under a path (`docs/specs/`, `tickets/`);
  - another gate firing (repeated failure);
  - a count of sensitive categories changed in the turn;
  - a spawn with a brief;
  - an existing adapter rule named by its gate (`design-reads`, the
    closeout's red flags), for references that are enforced today.
  A new kind needs a schema change and an adapter change; a new reference
  of an existing kind needs neither.
- **R3, validation.** `scripts/validate_skills.py` fails when a reference
  file is undeclared, a declared file does not exist, a signal's kind is
  unknown, or an advisory entry has no reason. A fixture under
  `stack/fixtures/` covers the entries.
- **R4, the project standard.** `AGENTS.md` and `skills/README.md` say that
  adding, renaming or removing a reference file updates the registry in the
  same change.
- **R5, enforcement.** In the Claude Code adapter, once a skill counts as
  loaded, a call that fires one of its enforced signals is held until the
  reference has been read with the Read tool since the last compaction. The
  hold is a new justified-skip gate, `reference-reads`, that names the
  file, what selected it, and the skip line. A skip line naming the skill
  clears the skill's references for the turn. References already enforced
  by `design`, `design-reads`, `spawn` and the closeout keep their gates
  and behaviour.
- **R6, first enforced set.** These are enforced from the first version:
  - `tdd`: `mocking-and-seams.md` when a test edit adds a mock or patch;
    `test-design.md` at the first test edit that adds five or more lines.
  - `diagnose`: `root-cause-tracing.md` when the repeated-failure gate
    fires; `condition-based-waiting.md` when an edit adds a sleep, retry or
    timeout.
  - `code-security-review`: `security-review-checklist.md` when the turn's
    sensitive changes span two or more categories.
  - `write-a-spec`: `spec-template.md` before a write under `docs/specs/`.
  - `spec-to-tickets`: `ticket-slicing-templates.md` before a write under
    `tickets/`.
- **R7, the rest.** Every other reference is classified with the
  maintainer: enforced, where one of the signal kinds fits its "read
  when" sentence, or advisory with the reason no signal fits.
- **R8, one owner.** Each skill's `SKILL.md` keeps its "read when"
  sentences; the registry entry is the enforceable form. A check compares
  the two lists of files in both directions, so a reference the skill
  links but the registry lacks, and one the registry declares but the
  skill never links, both fail.
- **R9, documentation.** The adapter README gains the gate, its table row
  and its hold text; the skill-usage mod reads the new gate's first line
  and counts it like `design-reads`.

## Acceptance Criteria

- [ ] AC1: Every file under every skill's `references/` is in the registry
      with a signal or an advisory reason, and the validator passes.
- [ ] AC2: Adding a reference file without a registry entry, or an entry
      for a missing file, fails the validator.
- [ ] AC3: With `tdd` loaded, a test edit that adds a mock is held by
      `reference-reads` until `mocking-and-seams.md` is read. With `tdd`
      not loaded, the same edit is not held by it.
- [ ] AC4: After the read, a later matching edit passes until a compaction.
- [ ] AC5: A skip line naming the skill clears the hold for the turn.
- [ ] AC6: Each reference in R6 is held at its signal and not at a near
      miss.
- [ ] AC7: A reference of an existing kind added to the registry is
      enforced with no adapter change.
- [ ] AC8: `software-design-principles`, `handoff` and
      `subagent-driven-development` references behave as before.
- [ ] AC9: The mod counts a `reference-reads` hold and its outcome.
- [ ] AC10: The repo checks in `AGENTS.md` pass on Python 3.11 and 3.14,
      and the context comparison stays inside its budgets.

## Proof Surface

The validator and its fixtures for R1 to R4 and R8. The adapter's hook
entry points, driven by transcript fixtures, for R5 and R6. The mod's test
suite for R9. A live check in one real session with `tdd` loaded.

## Constraints

- Every new rule (a signal, a trigger, a threshold, an item's wording of
  what is required) is stated in the registry, the shared policy or a skill.
  The adapter maps Claude Code's events to those rules and adds none of its
  own, as ADR 0003 requires, so another harness's adapter can enforce the
  same rules ([portable enforcement spec](2026-11-17-portable-enforcement-core.md)).
- Fail toward holding only where the registry is readable. If the adapter
  cannot find or read the registry, it asks for nothing new and says so in
  Known Limits, as the Design citations item does.
- The adapter reads the installed registry, not the source repo.
- Installed skills must not depend on the registry at runtime; a skill
  installed alone works as today.
- Ticket 065 of the written-line holds spec defines when a skill counts as
  loaded, and Ticket 063 changes the design-reads signals; this work
  follows both.

## Open Questions

None.

## Risks

- More holds per session. This is mitigated because a hold fires only for a
  loaded skill, once per reference per context window, and a skip line
  clears it.
- A pattern signal can misfire, as `try` in a string does for `errors.md`.
  This is mitigated by near-miss tests and by the mod's per-reference
  counts (see [the mod data spec](2026-11-17-skill-usage-data-detail.md)).
- The classification in R7 can mark too much advisory. The maintainer
  reviews the list.

## Sources

- `stack/goated-stack.yaml`, `stack/schemas/`, `scripts/validate_skills.py`.
- `adapters/claude-code/goated_adapter/design_reads.py` and `actions.py`
  (the enforced reads today).
- `adapters/claude-code/README.md`: Design references, Hold messages.
- The skill-usage mod's stored summaries, 15 to 17 November 2026.
