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

## Recommended First Reads

- The parent spec, R3, R5 and Architecture.
- The ADR, contract and event model from Ticket 079.
- `adapters/claude-code/goated_adapter/gates.py` (the tool tables),
  `actions.py`, `transcript.py` (`Turn`, `Call`, `LINE_FIELDS`), `hooks.py`.
- `tests/claude_code_adapter_support.py`.

## Acceptance Criteria

- [ ] No rule module names a Claude Code tool, transcript field or hook
      field; a check enforces it.
- [ ] The adapter's existing tests pass with no change to expected
      outcomes or hold texts.
- [ ] Every conformance scenario still passes against the adapter.
- [ ] The adapter's measured latency stays within the README's stated
      budget.

## Expected Proof

- The existing adapter tests, unchanged in what they expect.
- The conformance scenarios.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- A live check: one real Claude Code session that meets a routing hold,
  an action hold and the closeout.

## Blocked By

- `tickets/079-enforcement-contract-and-event-model.md`

## Scope Exclusions

- Moving modules out of the adapter (Ticket 081).
- Any rule change.
- The JSON command.
