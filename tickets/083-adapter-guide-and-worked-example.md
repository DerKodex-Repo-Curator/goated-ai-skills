# Ticket 083: A Guide And Worked Example For Writing An Adapter

## Parent Spec

`docs/specs/2026-11-17-portable-enforcement-core.md` (R6, R7, R11; AC7)

## Type

AFK.

## Problem

The shared core can be called from any harness, but nothing shows how.
Someone wiring a custom API loop, or a harness the repo does not cover,
has to work out the mapping from the Claude Code adapter's code, and has
no way to check their adapter against the rules.

## What To Build

- **The guide.** A document under `adapters/` that explains how to write
  an adapter:
  - mapping the harness's tools to call kinds;
  - building the turn so far, and what to do when the harness cannot
    supply part of it;
  - calling the core, by import or by command, before a call runs and
    when the turn ends;
  - showing a hold to the agent so it can answer it;
  - the rules every adapter keeps: opt-in, no free bypass, fail open
    visibly, enforce nothing the contract does not state;
  - documenting what the adapter cannot enforce.
- **The runner.** A command that runs the conformance scenarios through
  an adapter: the author supplies a small translator from the scenario's
  events to their harness's shape, and the runner reports which scenarios
  pass.
- **The worked example.** A minimal tool loop, with no dependency on any
  harness or network, that calls the core before each tool call and at
  the end of a turn. It is an example to copy from, not a product. It
  runs in the repo's tests and passes the conformance scenarios.
- `adapters/README.md` links the guide, the runner and the example.

## Recommended First Reads

- The parent spec, R6, R7 and Constraints.
- The enforcement contract and event model from Ticket 079.
- The core as Ticket 081 left it, and the thin Claude Code adapter as an
  example of an adapter.
- `adapters/README.md`.

## Acceptance Criteria

- [x] The worked example runs in the repo's tests with no network and no
      harness installed.
- [x] It passes every conformance scenario through the runner.
- [x] The runner reports a failing scenario by name, with the expected and
      actual decision.
- [x] The guide covers each point listed above and names every command it
      tells the reader to run.
- [x] A reader can follow the guide using only files in this repo.

## Expected Proof

- Tests for the worked example and the runner.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- A fresh-agent read of the guide: a subagent given only the guide wires a
  second toy loop that passes the scenarios.

## Blocked By

- `tickets/081-shared-enforcement-core.md`

## Scope Exclusions

- Adapters for real harnesses (Tickets 084 and 085).
- An example that calls a model.
