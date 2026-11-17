# Ticket 085: An OpenCode Adapter

## Parent Spec

`docs/specs/2026-11-17-portable-enforcement-core.md` (R10; AC11)

## Type

HITL. The maintainer decides whether to build after the research step,
and runs the live session.

## Problem

The maintainer wants the same enforced workflow in OpenCode as in Claude
Code. Nothing connects OpenCode to the shared core, and what its plugin
hooks allow is not yet known to this repo.

## What To Build

- **Research first.** From OpenCode's current public documentation and the
  version the maintainer will use, establish:
  - whether a plugin can stop a tool call before it runs and return text
    to the agent;
  - what it can see of the turn: prompts, earlier calls and results, reply
    text, and whether a compaction happened;
  - whether it can act when a turn ends;
  - how skills are loaded there, and so what counts as proof of a load;
  - how a plugin is installed.
  Report the findings and what can and cannot be enforced to the
  maintainer, with sources, and wait for the go-ahead.
- **The adapter.** Under `adapters/`, following the guide of Ticket 083: a
  translation from OpenCode's events to the event model, a call to the
  core's command, and the hold shown to the agent. Opt-in install steps
  and a README that lists what is enforced and what is not.
- **Proof.** The adapter passes the conformance scenarios its plugin hooks
  allow, through the runner, and the README names the scenarios it cannot
  pass and why.
- Reuse what Ticket 084 learned: where the two adapters share translation
  code in the same language, give it one home.

## Recommended First Reads

- The parent spec, R10, Constraints and Risks.
- The adapter guide and worked example from Ticket 083.
- The Pi Agent adapter and its closeout from Ticket 084.
- The enforcement contract and event model from Ticket 079.
- OpenCode's current documentation on plugins.

## Acceptance Criteria

- [ ] The research findings, with sources and the version, and the
      maintainer's decision are recorded in this ticket's closeout.
- [ ] The adapter passes every conformance scenario its plugin hooks
      allow, and the README lists the rest with the reason.
- [ ] A live OpenCode session shows one hold and its clearing, and the
      neutral log records both.
- [ ] Removing the adapter leaves OpenCode and the skills working as
      before.
- [ ] The adapter enforces nothing the contract does not state.

## Expected Proof

- The conformance runner's report.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, plus any tests
  in the adapter's own language.
- The maintainer's live session.

## Blocked By

- `tickets/084-pi-agent-adapter.md` (what it learns about a second
  harness, and any shared translation code).

## Scope Exclusions

- Changing OpenCode.
- A measurement pane for OpenCode beyond the report command.
- Rules specific to OpenCode.
