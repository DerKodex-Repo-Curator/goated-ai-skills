# Ticket 119: Routing And Orientation For Continued Work

## Parent Spec

`docs/specs/2026-11-19-hook-friction-round-6.md` (R2, R3, R10, R13; AC3,
AC4, AC11, AC13's context pointer, AC14)

## Type

AFK. Decisions T1, U1, W1 and Y1 (the maintainer, 2026-11-19). T1 reverses
round 4's R5 and U1 reverses round 5's H3. Phase 4 ends in a written
finding for the maintainer; it changes no rule.

## What To Build

The holds at the start of a prompt stop firing on work that is already
routed and already oriented. One agent can do this in four phases; each
phase lands green.

- **Phase 1, a typed follow-up continues the task (R2).** When the
  session's current task has a route, a typed prompt with no route line
  runs as `goated-route: continue`: `router-first` and `route-line` do not
  hold in that turn.
  - A notice on that prompt says once that new work needs a new route
    line.
  - A route line the agent writes still wins.
  - The task's route survives a compaction for this rule. The route's
    required skills are still asked for again after one, by `pipeline`, as
    today.
  - A session with no task and no brief keeps today's rule.
  - A message from another session keeps Ticket 102's rule.
- **Phase 2, distinct files orient (R3).** Reads from five distinct
  project files orient a session, whole or ranged.
  - The file tool counts, with or without a range.
  - A finished, successful shell printer of a named file counts, one file
    for each command part: `cat`, `head`, `tail`, `sed -n`, and
    PowerShell's `Get-Content` and its aliases. Confirm against the core's
    shell reading which of these it can already tie to a named file, and
    add only what is missing.
  - A search that prints matching lines (`grep`, `rg`, `Select-String`)
    never counts.
  - Three whole reads and the orientation skill still count.
- **Phase 3, the project's own documents (R13).** When the project has a
  context file, a context matrix or a standards profile, the orientation
  hold and the turn's first code-change notice name the ones that exist,
  and name none when none exists. The core stays pure: the adapter reports
  which exist, as it already checks them for its onboarding notice.
- **Phase 4, the carrier probe (R10).** Establish, in a real Claude Code
  session with a cheap model, in what order the harness judges the calls
  of one message, and whether session state written while judging one call
  is visible when the next is judged. Record the finding and the commands
  used under `docs/reference/`, with a recommendation on whether a route or skip
  line seen on one call could count for the later calls of its message.
  Do not change the carrier rule.

The rules live in the shared core at `adapters/core/goated_core/`. The
contract's Gates, Notices, Prompts Turns And Tasks, and Shell Reading
sections, and conformance scenarios under `stack/fixtures/enforcement/`,
change with the code. A new notice kind, or a new request field for
phase 3, bumps the event model's version.

## Recommended First Reads

- The parent spec: R2, R3, R10, R13 and decisions T, U, W and Y.
- `stack/enforcement-contract.md`: Lines, Gates (the `router-first`,
  `route-line` and `pipeline` rows), Notices, Prompts Turns And Tasks, and
  Shell Reading's paragraphs on whole prints.
- `tickets/archive/102-core-session-messages-continue-the-task.md`,
  `tickets/archive/110-core-whole-shell-prints-orient.md` and
  `tickets/archive/117-core-continue-meets-router-first-in-a-briefed-task.md`.
- The core's `gates.py` and `state.py`, and the Claude Code adapter's
  onboarding notice.
- `docs/adr/0004-portable-enforcement-core.md`, for what session
  facts the core keeps.

## Acceptance Criteria

- [x] In a session with a routed task, a typed prompt followed by an edit
      meets no `router-first` or `route-line` hold, and the prompt carries
      the notice once.
- [x] The same prompt in a session with no task and no brief is held as
      today.
- [x] After a compaction, a typed prompt followed by an edit is held by
      `pipeline` for the route's skills, not by `route-line`.
- [x] A route line the agent writes in that turn replaces the inferred
      one.
- [x] Five ranged reads of five files orient, by the file tool and by
      `sed -n`; four do not; five searches do not; three whole reads
      still do.
- [x] The orientation hold and the first code-change notice name an
      existing context file, and name none when none exists.
- [x] A written finding answers phase 4's two questions with the commands
      used.
- [x] The contract states each rule, and conformance scenarios cover each
      hold, each way it clears, and a near miss.
- [x] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The core's gate tests; the Claude Code adapter's tests through its hook.
- For phase 4, the recorded session output.
- The repo checks in `AGENTS.md`.

## Blocked By

- None.

## Scope Exclusions

- Any change to where a route or skip line may be written.
- A `pipeline` rule by file kind or change size.
- Counting the files a brief names without a read of them.
- The words of the routing holds beyond the new notice: Ticket 121 owns
  hold text, including the malformed route line's reason.
