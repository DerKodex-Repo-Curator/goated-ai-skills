# Ticket 080: The Claude Code Adapter's Rules Read The Event Model

## Parent Spec

`docs/specs/2026-11-17-portable-enforcement-core.md` (R3, R5; AC4)

## Type

AFK.

## Problem

The adapter's rule modules judge calls by Claude Code's tool names, such
as `Edit`, `Bash` and `Skill`, and read a turn shaped by Claude Code's
transcript. Before the rules can move into a shared core, they must stop
knowing which harness they run in. Doing that inside the adapter first
keeps the move itself mechanical.

## What To Build

- A translation layer in the Claude Code adapter turns hook input and the
  transcript into the event model of Ticket 079: call kinds in place of
  tool names, and a turn in the model's terms.
- The rule modules (routing gates, action gates, the closeout, design
  reads, reference reads, content checks, overrides) read only the event
  model. Claude Code's tool names, transcript fields and hook fields
  appear only in the translation layer, the transcript reader and the
  hook entry point.
- Behaviour does not change: the same calls are held with the same texts.
- Hold texts that name a Claude Code tool keep their wording through a
  table the translation layer supplies, so the rules hold no harness
  wording.
- **The scenario runner's missing steps.** Ticket 079's runner
  (`tests/claude_code_scenarios.py`) raises on steps it cannot record
  faithfully. With the translation layer in place, add them, each with a
  conformance scenario: a skill a person invokes by typing `/<skill>`
  (`skill_invoked`), a background agent finishing (`agent_finished`), a
  report from this session's own subagent that continues the turn, and,
  in a subagent scenario (`setup.agent: subagent`, which Ticket 098 added
  to pin its subagent commit rule), the steps the runner still refuses: a
  turn end, a compaction, and a session start.

## Recommended First Reads

- The parent spec, R3, R5 and Architecture.
- The ADR, contract and event model from Ticket 079.
- `adapters/claude-code/goated_adapter/gates.py` (the tool tables),
  `actions.py`, `transcript.py` (`Turn`, `Call`, `LINE_FIELDS`), `hooks.py`.
- `tests/claude_code_adapter_support.py`.

## Acceptance Criteria

- [x] No rule module names a Claude Code tool, transcript field or hook
      field; a check enforces it.
- [x] The adapter's existing tests pass with no change to expected
      outcomes or hold texts.
- [x] Every conformance scenario still passes against the adapter.
- [x] The adapter's measured latency stays within the README's stated
      budget.

## Expected Proof

- The existing adapter tests, unchanged in what they expect.
- The conformance scenarios.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- A live check: one real Claude Code session that meets a routing hold,
  an action hold and the closeout.

## Blocked By

- `tickets/archive/079-enforcement-contract-and-event-model.md`
- `tickets/archive/098-adapter-contract-gaps.md`

## Scope Exclusions

- Moving modules out of the adapter (Ticket 081).
- Any rule change.
- The JSON command.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `eacea8f` (`0314f2d`, `eb1df81`, `d580b66`, follow-up
  `08540db`).
- Maintainer decision: option A, with the event model bumped to version 2.
- Exercised in later sessions; no separate live-check record.
