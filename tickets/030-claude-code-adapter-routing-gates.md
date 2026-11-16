# Ticket 030: Claude Code Adapter, Routing Gates

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (R2 detection, R5
router-first, route line and pipeline gates, R6, R7 baseline, R8, R9, R10)

## Type

AFK. Resolve the spec's open questions on adapter location and on where the
rule table lives with `design-codebase-architecture` at the start, and record
the answers in the spec.

## What To Build

The first working slice of the opt-in Claude Code adapter: Python standard
library hooks that:

- hold the first write or command until the router has loaded;
- require a route line on the first write after each new user prompt;
- hold writes until the route's `requires:` skills have loaded for the current
  task;
- record user-typed overrides such as "skip routing" from the user-prompt hook;
- detect at session start when the shared policy is not loaded, and say so
  once;
- fail open with a visible warning when the transcript or input cannot be read.

Proof of use is a successful Skill load in the current task, read from the
current turn of the transcript. Inside subagents these routing gates do not
apply. The slice includes the transcript reader, per-session state, the settings
snippet, and install, disable and remove docs.

## Recommended First Reads

- `docs/adr/0003-opt-in-framework-enforcement-adapters.md` — the five adapter
  rules.
- The spec's Requirements, Architecture, and Risks sections.
- The route-line and skip-line grammar and fixtures from Ticket 029.
- `AGENTS.md` — the "Where Work Lives" section must be updated if a new
  top-level folder is added.
- Claude Code hook documentation for hook input fields, `transcript_path`,
  decision output, and subagent identification.

## Acceptance Criteria

- [x] Unit tests drive the hooks with recorded hook inputs and transcript
      fixtures, and prove each of these:
  - [x] router-first holds and clears;
  - [x] a missing route line holds, and `continue` passes;
  - [x] `requires:` skills hold until loaded;
  - [x] `direct` exempts the task;
  - [x] an unchanged retry never passes;
  - [x] a load from an earlier task does not satisfy a new one;
  - [x] a user-typed override stands the matching hold down, and the same text
        written by the agent does not;
  - [x] routing gates are skipped in subagents;
  - [x] unreadable input fails open with a warning.
- [x] The tests run in CI on Python 3.11 and 3.14 with standard-library code
      only.
- [x] The validator ignores the adapter folder, or validates it on purpose, and
      no skill depends on the adapter.
- [x] Install, disable, and remove docs exist.
- [x] Hook latency is measured on Windows and reported.

## Expected Proof

- Unit-test and validator output.
- A latency measurement.

## Blocked By

- `tickets/archive/029-router-skill-map-and-route-line.md`

## Scope Exclusions

- Commit, PR, spawn, design, security, and closeout gates (Ticket 031).
- The skill-usage mod (Ticket 032).
- Changing the maintainer's personal hooks or settings (Ticket 033).
