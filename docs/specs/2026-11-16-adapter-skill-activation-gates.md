# Adapter Gates For Valuable Skills That Go Unused

## Status

Approved in direction by the maintainer on 2026-11-16, in the grill that
closed the skill-usage mod's quality check. The four gates below were each
chosen. Thresholds and the open questions are provisional until the ticket
that delivers each gate settles them. Builds on
[the skill enforcement spec](2026-11-15-skill-enforcement-adapter.md) and
[ADR 0003](../adr/0003-opt-in-framework-enforcement-adapters.md).

## Mode

Compact.

## Problem

The skill-usage mod's data from the maintainer's first 20 real sessions,
recorded under the earlier hand-written hooks, shows which skills load:
`commit-message`, the router, `software-design-principles`, `tdd`, and
`handoff` load often, almost always after a hook or a route. Several skills
whose moment is easy to recognise from the outside never loaded:

- `resolving-merge-conflicts`: 0 loads; the old merge-conflict nudge was
  ignored both times it fired.
- `diagnose`: 1 load in 20 sessions.
- `setup-scribe`: 0 loads.
- `standards-and-spec-review`: 1 load.

The adapter (Tickets 030 and 031) has no gate for any of these moments, so an
agent that does not think of the skill never meets it.

Many other skills also went unused (research, retrieval, plans, prototypes,
wayfinder, retrospectives, docs, onboarding). They get no gate here: their
moment depends on judgement that no tool call or transcript shows reliably,
and a gate on a guess would hold good work.

## Goals

- Each of the four skills loads, or is declined with a reason, at the moment
  it applies, in sessions where the adapter is installed.
- The new holds stay rare: they fire on a precise trigger, and a justified
  skip always clears them.

## Non-Goals

- Gates for skills whose moment cannot be recognised from tool calls and
  their results.
- Changing the hold format, `goated-hold: <gate> | <kind>`, or any existing
  gate's behaviour.
- Strict holds. Every gate here is `justified-skip`.

## Requirements

### G1: Merge conflicts → `resolving-merge-conflicts`

- A new action gate, `merge-conflict`, holds a write to a file while a
  conflict is open in the turn: an `Edit` whose `old_string` holds conflict
  markers (`<<<<<<<`, `=======`, `>>>>>>>` at line starts), or any write after
  a `git merge`, `rebase`, `cherry-pick`, `revert`, `pull`, or
  `stash pop|apply` whose result in the turn reports a conflict.
- It clears when `resolving-merge-conflicts` loads in the turn, or on a skip
  line naming it.

### G2: Repeated failure → `diagnose`

- A new action gate, `diagnose`, holds the next write after the same check
  command (as the closeout gate recognises checks) has failed twice in the
  turn.
- It clears when `diagnose` loads in the turn, or on a skip line naming it.
- Provisional threshold: two failures of the same command.

### G3: Setup changes → `setup-scribe`

- A new closeout item, **Setup**, applies when the turn installed or added a
  dependency or tool (`npm`/`pnpm`/`yarn add` or `install <package>`,
  `pip install <package>`, `uv add`, `cargo add`, `go get`, `winget`/`choco`/
  `brew`/`apt install`), or wrote an environment or settings file (`.env*`,
  a `settings*.json` under `.claude/` or `.vscode/`, and the like).
- It is met when `setup-scribe` loads in the turn, or by a skip line naming
  it.

### G4: Large pull requests → `standards-and-spec-review`

- The `pull-request` gate gains a second item. When the change the pull
  request opens is large, it also needs `standards-and-spec-review` loaded in
  the turn, or a skip line naming it. The existing `pr-description`
  requirement stays strict. The new item is justified-skip.
- Provisional threshold: 400 or more changed lines against the base branch.

### Shared

- Each new hold uses the documented first line and backticks only the skill
  it asks for, so the skill-usage mod reads it with no grammar change. The mod
  gains a display name for each new gate.
- User overrides (`skip <skill>`) stand each new requirement down, as they
  do for the existing gates.
- The adapter README's gate tables and the generated
  `tests/adapter-texts.ts` cover each new hold.

## Acceptance Criteria

- [ ] G1–G4 each fire on their trigger and stay silent on a near miss, as
      shown by adapter tests in Claude Code's recorded transcript shape.
- [ ] Each new hold is cleared by its skill's load, by a skip line, and by a
      typed `skip <skill>` override.
- [ ] The skill-usage mod names each new gate and records its outcome.
- [ ] After the maintainer's next stretch of real use, the mod's data shows
      each new hold's follow and decline rate, and no hold fired on work it
      was not meant for. If one did, its trigger is narrowed or the gate is
      removed.

## Proof Surface

The adapter's hook entry point driven with recorded-shape transcripts
(`tests/test_claude_code_adapter_actions.py`), and the skill-usage mod's
All time tab after real use.

## Constraints

- The adapter's action gates are pure functions of the current turn as the
  transcript shows it, with no state (adapter README, State). G1 and G2 fit
  that. G4 needs the size of the change, which the transcript does not hold.
- Hook latency: each `PreToolUse` call is measured (adapter README,
  Latency). A gate that runs a command must stay within that budget.
- Ticket 033's trial decision (keep, revise, or revert the adapter) comes
  first. These gates build on a kept adapter.

## Open Questions

- G1: should the adapter also read repository state on disk, such as
  `.git/MERGE_HEAD`, to catch a conflict opened in an earlier turn? That
  would break the turn-only purity. Decide in G1's ticket.
- G2: does "the same command" mean the same command text, or the same check
  tool? Decide in G2's ticket from real transcripts.
- G3: does a bare `npm install` that restores a lockfile count as a setup
  change? Provisionally no: only commands that name a package.
- G4: how does the adapter learn the change's size? Running
  `git diff --shortstat <base>...HEAD` at pull-request time adds latency once
  per pull request; counting the turn's own writes misses earlier turns.
  Decide in G4's ticket.
