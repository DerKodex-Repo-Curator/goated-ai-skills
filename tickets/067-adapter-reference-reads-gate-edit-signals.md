# Ticket 067: The Adapter Holds An Edit Until Its Declared Reference Is Read

## Parent Spec

`docs/specs/2026-11-17-registry-reference-reads.md` (R5, R6, R9; AC3, AC4,
AC5, AC6, AC7, AC8, AC9)

## Type

AFK.

## Problem

The registry now declares when each reference must be read (Ticket 066),
but the Claude Code adapter enforces only the references written into its
own code. `tdd` loaded 64 times in the skill-usage data, and its five
references were read once.

## What To Build

- **The gate.** A new justified-skip gate, `reference-reads`. Once a skill
  counts as loaded, a call that fires one of its enforced signals is held
  until the reference has been read with the Read tool since the last
  compaction. The hold names the file by its path under the skill, says
  what selected it, and offers the skip line. A skip line naming the skill
  clears that skill's references for the turn.
- **The registry.** The adapter reads the installed registry. When it
  cannot find or read it, the gate asks for nothing, and Known Limits says
  so.
- **Edit signals.** This ticket implements the kinds judged on one edit:
  added text matching a named pattern, and an edit of a kind of file. It
  enforces, from the registry:
  - `tdd` `mocking-and-seams.md` when a test edit adds a mock or patch;
  - `tdd` `test-design.md` at a test edit that adds five or more lines;
  - `diagnose` `condition-based-waiting.md` when an edit adds a sleep,
    retry or timeout.
  A reference of these kinds added to the registry later is enforced with
  no adapter change.
- **What stays.** References declared with the existing-rule kind keep
  their gates: `design`, `design-reads`, `spawn` and the closeout.
- **Reads kept.** The saved state keeps the references read, as it does
  for design references, and a compaction clears them.
- **The mod.** The skill-usage mod reads the new gate's first line and
  counts the hold and its outcome as it does for `design-reads`.
- Update the README (the gate table, a section on registry references,
  Hold messages, State, Known Limits) and regenerate
  `adapters/claude-code/skill-usage/tests/adapter-texts.ts`.

## Recommended First Reads

- The parent spec, R5, R6 and its Constraints.
- The registry entries and schema from Ticket 066.
- `adapters/claude-code/goated_adapter/design_reads.py` (`_Added`,
  `_signals`, `reference_read`, comment stripping).
- `adapters/claude-code/goated_adapter/actions.py` (`check_action`,
  `_design_hold`, the design-reads hold).
- `adapters/claude-code/goated_adapter/state.py` (`reference_reads`).
- `adapters/claude-code/README.md`: Design references, Hold messages.
- The mod's `hooks/classify.ts` and `hooks/holds.ts`.

## Acceptance Criteria

- [ ] With `tdd` loaded, a test edit that adds a mock is held by
      `reference-reads` until `mocking-and-seams.md` is read. A test edit
      with no mock is not held for it.
- [ ] With `tdd` not loaded, neither edit is held by the gate.
- [ ] A four-line test edit is not held for `test-design.md`; a five-line
      one is.
- [ ] With `diagnose` loaded, an edit adding a sleep is held until
      `condition-based-waiting.md` is read; the word in a comment does not
      count.
- [ ] After the read, a later matching edit passes until a compaction.
- [ ] A skip line naming the skill clears the hold for the turn only.
- [ ] A fixture registry entry of an existing kind is enforced with no
      adapter change.
- [ ] With no readable registry, the gate holds nothing.
- [ ] The `design`, `design-reads` and `spawn` holds are unchanged.
- [ ] The mod counts a `reference-reads` hold as read files, declined, or
      unanswered.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- `adapters/claude-code/skill-usage/tests/adapter-texts.ts` regenerated; the
  mod's tests pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- A live check: one real session with `tdd` loaded that adds a mock.

## Blocked By

- `tickets/066-registry-declares-every-reference.md` (the entries and
  schema).
- `tickets/065-adapter-loads-count-until-compaction.md` (when a skill
  counts as loaded).
- `tickets/063-adapter-design-reads-small-edits.md` (the design-reads
  signals this gate sits beside).

## Scope Exclusions

- Signals judged on the turn (Ticket 068).
- Citations for any reference.
- Moving the `software-design-principles` signals into the registry.
- Enforcement inside a subagent.
