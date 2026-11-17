# A Portable Enforcement Core For Any Agent Harness

## Status

Decisions approved by the maintainer on 2026-11-17 in a grill-with-docs
session. Ticket ready. Builds on
[ADR 0003](../adr/0003-opt-in-framework-enforcement-adapters.md),
[the skill enforcement spec](2026-11-15-skill-enforcement-adapter.md) and
the three specs of 2026-11-17 that precede it:
[written-line holds](2026-11-17-adapter-written-line-holds.md),
[registry reference reads](2026-11-17-registry-reference-reads.md) and
[skill placement](2026-11-17-skill-placement-gates.md).

## Mode

Full.

## Problem

GOATED's skills are framework-agnostic, but enforcement exists only for
Claude Code. The maintainer also runs Claude through the API in other
harnesses, orchestrates other agents, and has Pi Agent and OpenCode
available. Those sessions get the skills with no holds, and the data shows
that without holds most skills and references go unused.

The Claude Code adapter is closer to portable than its location suggests:

- Its rule modules (routing gates, action gates, the closeout, design
  reads, shell reading, the line grammar, content checks, overrides) depend
  on Claude Code in two ways only: a `Turn` built from Claude Code's
  transcript, and Claude Code's tool names, such as `Edit`, `Bash` and
  `Skill`.
- The Claude Code specifics are the transcript reader, the hook entry
  point, session state on disk, and those name tables.

But nothing lets another harness use the rules:

- Many rules are stated only in the adapter's code and README, though ADR
  0003 says adapters enforce portable contracts and never define them.
- There is no harness-neutral description of a turn, a call or a decision.
- The adapter's tests are written against Claude Code's transcript shape,
  so they cannot check another adapter.
- Measurement is a Claude desktop mod that reads Claude Code's events.

## Goals

- One implementation of the rules serves every harness.
- A new harness needs only a thin adapter that translates its events, in
  any language.
- An adapter can be proved correct by fixtures that do not mention any
  harness.
- Measurement works the same in every harness.
- Claude Code users see no change in behaviour.

## Non-Goals

- New rules. This spec moves and exposes the rules the earlier specs
  define.
- Automatic framework detection, installers, or generated plugin
  manifests, which ADR 0002 excludes.
- Running or orchestrating agents. The core judges calls; the harness runs
  them.
- Adapters beyond Pi Agent and OpenCode.
- A hosted or networked service. Everything runs on the user's machine.
- Making skills depend on the core. Skills work with no enforcement, as
  ADR 0003 requires.

## Users

- **The maintainer**, using several harnesses and wanting the same
  workflow in each.
- **A user of one other harness**, installing an adapter for it.
- **An adapter author**, wiring a harness the repo does not cover,
  including a custom API loop.

## Requirements

- **R1, the decision record.** An ADR records the choice of one shared
  core with thin adapters over per-harness reimplementation, the event
  model, and the two ways to call the core. It states how this stays
  inside ADR 0002's exclusions.
- **R2, the enforcement contract.** One document under `stack/` states
  every enforced rule in harness-neutral words: each gate, what it holds,
  what clears it, the closeout items, the hold line's format, the line
  grammar and where lines may be written, and the fail-open rules. Rules
  owned by a skill, the shared policy or the registry are cited, not
  copied. The Claude Code README keeps only what is specific to Claude
  Code and links to the contract.
- **R3, the event model.** A versioned, harness-neutral model describes
  what the core needs to judge a call:
  - the pending call: its kind (file write, shell command, skill load,
    file read, spawn, commit, pull request, session end), its target or
    command, added and removed text for a write, and the fields that may
    carry lines;
  - the turn so far: prompts with who wrote them, finished calls with
    their results, reply text, loads, and whether a compaction happened;
  - the project: its folders and the working folder.
  An adapter maps its harness's tool names to call kinds; the core knows
  no harness's tool names.
- **R4, the core.** The rules move into a package at `adapters/core/` that
  depends on the event model alone. It keeps its own session state. It is
  called in two ways:
  - imported from Python;
  - as a command that reads one JSON request and writes one JSON decision:
    allow, or a hold with its gate, kind and text, plus any notices.
  Both give the same decision for the same events.
- **R5, the Claude Code adapter becomes thin.** It translates Claude Code's
  transcript and hook input into the event model and the decision back
  into hook output. Its behaviour, hold texts and tests' outcomes do not
  change.
- **R6, conformance fixtures.** Scenario files hold a sequence of events
  and the expected decision at each step, in the event model's terms. The
  repo's tests run them against the core. An adapter author runs the same
  files through their adapter with a runner the repo provides.
- **R7, the adapter guide.** A guide under `adapters/` explains how to
  write an adapter: mapping tools to call kinds, building the turn,
  calling the core, showing a hold, the no-free-bypass and fail-open
  rules, and passing the conformance fixtures. It includes a minimal
  worked example of a tool loop that calls the core before each tool call.
- **R8, the neutral log.** The core appends each hold, its outcome, each
  skill load with its cause, each route and skip line, and each reference
  read to a local log in a documented, versioned format. A report command
  prints a summary. The skill-usage mod reads the log when it exists and
  keeps its current reading otherwise.
- **R9, a Pi Agent adapter.** An adapter for Pi Agent, built on the
  extension points its current version provides. Research confirms those
  first; where Pi Agent cannot hold a call before it runs, the ticket
  reports what can and cannot be enforced before building.
- **R10, an OpenCode adapter.** The same for OpenCode, on its current
  plugin hooks, with the same research step.
- **R11, documentation and standards.** `adapters/README.md` lists the
  adapters and the core. `AGENTS.md`'s "Where Work Lives" says `adapters/`
  holds one subfolder per framework plus `core/`, the shared rules every
  adapter calls, and that a rule change updates the contract and a
  conformance fixture in the same change.

## Architecture

- **Seam.** The event model is the one seam. Above it sit adapters, which
  know a harness. Below it sits the core, which knows the rules. Neither
  reaches across.
- **State.** The core owns session state, keyed by a session id the
  adapter supplies. An adapter that can supply the whole turn each time
  may run the core statelessly for that turn; loads and reads that count
  until compaction still live in the core's state.
- **Languages.** The core stays in Python, as the adapter is today. The
  command form lets a TypeScript plugin, or any other harness, call it
  with no Python of its own.
- **Order.** The extraction is a behaviour-preserving refactor. It runs
  after the tickets of the three preceding specs, which change the same
  files, and is proved by the existing adapter tests passing unchanged.

## Acceptance Criteria

- [ ] AC1: The ADR is accepted and indexed.
- [ ] AC2: Every gate and closeout item in the Claude Code README's tables
      appears in the enforcement contract, and a check fails when a gate
      the core can return is missing from it.
- [ ] AC3: The core's package imports nothing from the Claude Code adapter
      and names no Claude Code tool.
- [ ] AC4: The Claude Code adapter's existing tests pass with no change to
      expected outcomes or hold texts.
- [ ] AC5: The command and the Python call return the same decision for
      every conformance scenario.
- [ ] AC6: Conformance scenarios cover each gate holding, each way it
      clears, and a near miss, and name no harness.
- [ ] AC7: The guide's worked example runs in the repo's tests and passes
      the conformance scenarios.
- [ ] AC8: A hold in a Claude Code session and the same hold from the
      worked example produce the same log entries, and the report command
      summarises both.
- [ ] AC9: The skill-usage mod shows the same counts from the log as from
      its current reading for a recorded session.
- [ ] AC10: The Pi Agent adapter passes the conformance scenarios its
      extension points allow, and a live session shows a hold and its
      clearing. What cannot be enforced there is documented.
- [ ] AC11: The same for the OpenCode adapter.
- [ ] AC12: The repo checks in `AGENTS.md` pass on Python 3.11 and 3.14.

## Proof Surface

The conformance scenarios are the main surface: the core, the Claude Code
adapter, the worked example and each new adapter are proved against them.
The existing Claude Code adapter tests prove the refactor changed nothing.
Live sessions prove the Pi Agent and OpenCode adapters.

## Constraints

- ADR 0003's rules hold for every adapter: opt-in only, enforce portable
  contracts, no free bypass, fail open visibly, tested in this repo.
- The core never blocks when it cannot read its input: it allows the call
  and says so.
- An adapter may enforce less than the core offers when its harness lacks
  a hook, but it must document the gap and never enforce a rule the
  contract does not state.
- The event model and the log format are versioned, and a request or log
  of an unknown version is refused with a clear message, not guessed at.
- No private data leaves the machine; the log holds what the skill-usage
  mod stores today and nothing more.
- Research into Pi Agent and OpenCode uses their current public
  documentation and the versions installed on the maintainer's machine.

## Rollout

1. The ADR, the contract and the event model, with conformance scenarios
   run against the current rules through a temporary bridge.
2. The core extracted, and the Claude Code adapter made thin.
3. The log, the report command and the mod's reader.
4. The guide and the worked example.
5. The Pi Agent adapter, then the OpenCode adapter, each after its
   research step and the maintainer's go-ahead.

## Open Questions

None that block the first four steps. What Pi Agent and OpenCode can hold
before a call runs is settled by each adapter's research step, with the
maintainer deciding whether to proceed.

## Risks

- The refactor could change behaviour. This is mitigated by running it
  after the queued tickets, in two steps, with the existing tests as the
  check.
- The event model could bake in Claude Code's shape. This is mitigated by
  designing it against three harnesses and proving it with the worked
  example before the two real adapters.
- A harness may offer no way to deny a call. The adapter then documents
  what it can do, such as a notice, and the maintainer decides whether it
  is worth shipping.
- Starting a Python process for each call costs time in harnesses with
  many calls. The Claude Code adapter already does this within its latency
  budget; the guide tells Python harnesses to import the core.

## Sources

- `docs/adr/0002-v2-integrated-stack-foundation.md` and
  `docs/adr/0003-opt-in-framework-enforcement-adapters.md`.
- `adapters/claude-code/goated_adapter/` (module docstrings and imports),
  `adapters/claude-code/goated_hook.py`, `adapters/claude-code/README.md`.
- `adapters/claude-code/skill-usage/README.md`.
- `stack/fixtures/markers/README.md`.
