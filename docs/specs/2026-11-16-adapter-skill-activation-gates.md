# Adapter Gates For Valuable Skills That Go Unused

## Status

Approved in direction by the maintainer on 2026-11-16, in the grill that
closed the skill-usage mod's quality check. The four gates below were each
chosen. Thresholds and the open questions are provisional until the ticket
that delivers each gate settles them. Revised the same day after an
independent review: distinct gate names, G4 as a gate of its own, and the
portable text each gate enforces (ADR 0003, rule 2). Builds on
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
- Changing the hold format, `goated-hold: <gate> | <kind>`, or what any
  existing gate holds and how it clears. G3 adds an item to the closeout gate,
  which keeps its first line and kind; G4 is a gate of its own beside
  `pull-request`, which stays as it is.
- Strict holds. Every gate here is `justified-skip`.

## Requirements

### G1: Merge conflicts → `resolving-merge-conflicts`

- A new action gate, `conflict-resolution`, holds a write to a file while a
  conflict is open in the turn: an `Edit` whose `old_string` holds conflict
  markers (`<<<<<<<`, `=======`, `>>>>>>>` at line starts), or any write after
  a `git merge`, `rebase`, `cherry-pick`, `revert`, or `pull` whose result in
  the turn reports a conflict.
- It clears when `resolving-merge-conflicts` loads in the turn, or on a skip
  line naming it.
- Grounded in the skill's description: "Use when an in-progress Git merge,
  rebase, cherry-pick, or revert has conflicts". A `pull` is a merge or a
  rebase. A conflicting `git stash pop` or `apply` is not in the description,
  so the gate leaves it alone.

### G2: Repeated failure → `diagnose`

- A new action gate, `repeated-failure`, holds the next write after the same
  check command (as the closeout gate recognises checks) has failed twice in
  the turn.
- It clears when `diagnose` loads in the turn, or on a skip line naming it.
- Provisional threshold: two failures of the same command.
- Grounded in the skill's description ("Use when investigating ... failing
  behavior, flaky tests, build failures ... before proposing or implementing
  fixes") and the router's gate table ("`diagnose` for failures"). The text
  applies from the first failure; two failures is a narrower stand-in that
  holds less than the text asks, to keep the hold rare. It adds no rule.

### G3: Setup changes → `setup-scribe`

- A new closeout item, **Setup**, applies when the turn installed or added a
  dependency or tool (`npm`/`pnpm`/`yarn add` or `install <package>`,
  `pip install <package>`, `uv add`, `cargo add`, `go get`, `winget`/`choco`/
  `brew`/`apt install`), or wrote an environment or settings file (`.env*`,
  a `settings*.json` under `.claude/` or `.vscode/`, and the like).
- It is met when `setup-scribe` loads in the turn, or by a skip line naming
  it.
- Grounded in the skill's description ("Use after installing project
  dependencies or tools, changing environment variables, application or
  machine settings") and the shared policy ("Select `setup-scribe` only when
  project setup knowledge is missing, changed, stale, or automation-ready").

### G4: Large pull requests → `standards-and-spec-review`

- A new action gate, `pr-review`, holds the same pull-request commands the
  `pull-request` gate holds, once that gate has passed, when the change the
  pull request opens is large. It clears when `standards-and-spec-review`
  loads in the turn, or on a skip line naming it. The `pull-request` gate and
  its strict `pr-description` requirement stay as they are: one hold has one
  kind, so the justified-skip review is a hold of its own.
- Provisional threshold: 400 or more changed lines against the base branch.
- Grounded in the skill's description ("Use when a change is large or risky
  enough to review before it lands") and the shared policy ("Load
  standards/spec review when diff size, risk, acceptance, scope, or convention
  uncertainty warrants it"). Neither gives a number. Ticket 038 either puts
  the threshold into that portable text first, or records it in the adapter
  README as a documented mechanical stand-in for "large", as the design
  gate's five added lines are.

### Shared

- Each new hold uses the documented first line and backticks only the skill
  it asks for, so the skill-usage mod reads it with no grammar change. The mod
  gains a display name for each new gate.
- Each new gate name differs from every gate key of the earlier hand-written
  hooks the mod still reads (`merge-conflict` and `diagnose` among them), so
  All time keeps their counts apart from the new gates' follow and decline
  rates.
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
