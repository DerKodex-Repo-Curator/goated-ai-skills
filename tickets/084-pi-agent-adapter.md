# Ticket 084: A Pi Agent Adapter

## Parent Spec

`docs/specs/2026-11-17-portable-enforcement-core.md` (R9; AC10)

## Type

HITL. The maintainer decides whether to build after the research step,
and runs the live session on their own machine, where Pi Agent is
installed.

## Problem

The maintainer has Pi Agent installed and wants the same enforced
workflow there as in Claude Code. Nothing connects Pi Agent to the shared
core, and what its extension points allow is not yet known to this repo.

## What To Build

- **Research first.** From Pi Agent's current public documentation and the
  version installed on the maintainer's machine, establish:
  - whether an extension can stop a tool call before it runs and return
    text to the agent;
  - what it can see of the turn: prompts, earlier calls and results, reply
    text, and whether a compaction happened;
  - whether it can act when a turn ends;
  - how skills are loaded there, and so what counts as proof of a load;
  - how an extension is installed.
  Report the findings and what can and cannot be enforced to the
  maintainer, with sources, and wait for the go-ahead.
- **The adapter.** Under `adapters/`, following the guide of Ticket 083: a
  translation from Pi Agent's events to the event model, a call to the
  core's command, and the hold shown to the agent. Opt-in install steps
  and a README that lists what is enforced and what is not.
- **Proof.** The adapter passes the conformance scenarios its extension
  points allow, through the runner, and the README names the scenarios it
  cannot pass and why.

## Recommended First Reads

- The parent spec, R9, Constraints and Risks.
- The adapter guide and worked example from Ticket 083.
- The enforcement contract and event model from Ticket 079.
- `docs/adr/0003-opt-in-framework-enforcement-adapters.md`.
- Pi Agent's current documentation on extensions.

## Acceptance Criteria

- [ ] The research findings, with sources and the installed version, and
      the maintainer's decision are recorded in this ticket's closeout.
- [ ] The adapter passes every conformance scenario its extension points
      allow, and the README lists the rest with the reason.
- [ ] A live Pi Agent session shows one hold and its clearing, and the
      neutral log records both.
- [ ] Removing the adapter leaves Pi Agent and the skills working as
      before.
- [ ] The adapter enforces nothing the contract does not state.

## Expected Proof

- The conformance runner's report.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, plus any tests
  in the adapter's own language.
- The maintainer's live session.

## Blocked By

- `tickets/archive/083-adapter-guide-and-worked-example.md`
- `tickets/archive/082-neutral-usage-log-and-report.md` (the live check reads the
  log).

## Scope Exclusions

- Changing Pi Agent.
- A measurement pane for Pi Agent beyond the report command.
- Rules specific to Pi Agent.
