# Ticket 098: Close The Adapter's Gaps Against The Enforcement Contract

## Parent Spec

`docs/specs/2026-11-17-portable-enforcement-core.md` (R2, R5; AC2, AC4)

## Type

AFK.

## Problem

Ticket 079's review compared the enforcement contract with the Claude Code
adapter's code and found three places where the adapter is looser than the
rule it enforces. The maintainer decided on 2026-11-18 that the contract
and its scenarios state today's behaviour and mark each gap, and that the
code is fixed before Ticket 080 starts moving it:

- **(a) Orientation counts partial reads.** In a session routed by its
  brief, `pipeline`'s orientation is met by reads of three distinct files.
  Every other read a hold asks for counts only when whole (Ticket 092), but
  `_files_read` in `goated_adapter/gates.py` counts any finished read, so
  three reads of 20 lines each meet it.
- **(b) The design gates never judge a shell write.** `design` and
  `design-reads` judge only file edit tools (`check_action` in
  `goated_adapter/actions.py`). A heredoc or redirect that writes six lines
  of non-test code meets neither, while `security`, `review-intake`,
  `conflict-resolution`, `reference-reads` and `repeated-failure` judge the
  same command.
- **(c) A subagent's commit meets no closeout.** The closeout runs at a
  commit only for the main agent (`_subagent_pre_tool_use` in
  `goated_adapter/hooks.py`), so a subagent commits unproved work without
  the Proof or Docs items the main agent would meet.

## What To Build

- **(a)** Orientation counts only whole reads, as every other read a hold
  asks for does. Partial reads never add up to a whole one.
- **(b)** `design` and `design-reads` judge a shell write to a code or
  configuration file inside the project. Its added text is unknown, so it
  counts as five or more added lines, as the closeout already counts it,
  and selects the references its path selects (a configuration file, the
  third code file). Decide with the tests whether a write whose files
  cannot be named meets `design`; the closeout counts it as non-test code.
- **(c)** A subagent's commit, once the `commit` gate passes it, meets the
  closeout judged from the subagent's own turn: its changes, checks, loads,
  reads and skip lines. No override applies, as for every subagent hold.
- For each gap: remove the gap note from `stack/enforcement-contract.md`,
  and turn the conformance scenario that pins today's behaviour into one
  that pins the fixed rule. Update the adapter README where it states the
  old behaviour (its Subagents section says a subagent's commit meets no
  closeout).

## Recommended First Reads

- `stack/enforcement-contract.md`: the `pipeline`, `design` and
  `design-reads` rows and the Subagents section, each with its gap note.
- `stack/fixtures/enforcement/` and `tests/claude_code_scenarios.py`.
- `adapters/claude-code/goated_adapter/gates.py` (`_files_read`),
  `actions.py` (`check_action`), `hooks.py` (`_subagent_pre_tool_use`).
- Ticket 079's closeout, for the review that found these.

## Acceptance Criteria

- [ ] Three partial reads no longer meet a briefed session's orientation;
      three whole reads still do.
- [ ] A shell write of non-test code inside the project meets `design`,
      and a shell write to a configuration file meets `design-reads` once
      `software-design-principles` counts as loaded.
- [ ] A subagent's commit meets the closeout from its own turn, and a
      subagent that proved and documented its change commits freely.
- [ ] The contract carries no gap note, and a conformance scenario pins
      each fixed rule.
- [ ] The adapter's other tests pass with no change to their expected
      outcomes.

## Expected Proof

- Adapter tests for each gap, red before the fix.
- The conformance scenarios and the contract check.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.

## Blocked By

- `tickets/079-enforcement-contract-and-event-model.md`

## Scope Exclusions

- Any other rule change.
- Moving rule code (Tickets 080 and 081).
