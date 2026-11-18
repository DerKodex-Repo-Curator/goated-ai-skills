# Ticket 088: More Read-Only Commands Pass Before The Router Loads

## Parent Spec

`docs/specs/2026-11-17-adapter-low-signal-holds.md` (R5, R15; AC6, AC16,
AC17)

## Type

AFK.

## Problem

Before the router loads, `router-first` holds every shell command that is
not a plain read. The plain-read list is narrow, so common read-only
commands are held and the agent pays a round trip to look around:

- any command after a leading `cd`, such as `cd sub && ls`;
- `git branch`, `git rev-parse`, `git ls-files`, `git blame`,
  `git worktree list`;
- `pwd`, `echo`, `sort`, `uniq`, `diff`, `stat`;
- any pattern holding a backslash (`grep -n "def\s+x"`) or `//`, and
  `ls 2>/dev/null`.

A no-op call such as `true`, which agents use to carry a skip line, is
held too.

## What To Build

- These count as plain reads, alone or joined as plain reads already may
  be:
  - a command after a leading `cd` to a literal path;
  - git subcommands that only read: `branch` with no name to create,
    `rev-parse`, `ls-files`, `blame`, `worktree list`, and `remote` with
    no change;
  - `pwd`, `echo` with no redirect, `sort`, `uniq`, `cut`, `tr`, `diff`,
    `stat`, `file`, `which`, `true` and `:`;
  - a backslash or `//` inside a single-quoted argument, and a
    `2>/dev/null` redirect.
- **The test for each form.** A form is added only when it cannot write a
  file or run another program, with every option it accepts. Check each
  command's options for one that writes or executes (an output-file
  option, an editor, a pager override). Drop a form that fails, or admit
  it only without that option, and name each dropped form in the
  closeout.
- Everything else about plain reads stays: one refused segment refuses the
  whole command, and an unknown form is not a plain read.
- Update the README's Plain reads section and the `router-first` hold
  text, and regenerate the hold texts for the skill-usage mod.

## Recommended First Reads

- The parent spec: R5 and Constraints.
- `adapters/claude-code/goated_adapter/shell.py`: `READ_ONLY_COMMANDS`,
  the git read-only table, `NOT_PLAINLY_SPELLED_RE`, and the segment
  checks around them.
- `adapters/claude-code/README.md`: Plain reads, and the Known Limits item
  on what a plain read can still run.
- The existing plain-read tests under `tests/`.

## Acceptance Criteria

- [ ] Before the router loads, each kept form passes `router-first`:
      `cd sub && ls`, `git branch`, `git rev-parse HEAD`, `git ls-files`,
      `pwd`, `sort a.txt | uniq`, `grep -n 'def\s+x' a.py`,
      `ls 2>/dev/null`, `true`.
- [ ] A near miss for each is held: `git branch new-name`,
      `git remote add o url`, `echo x > f`, `cd sub && rm f`,
      `sort -o out.txt a.txt`, a backslash in a double-quoted argument,
      `ls 2> errors.txt`.
- [ ] A command joining a new form with a non-read is held whole.
- [ ] Every command that was a plain read before still is.
- [ ] The closeout lists each form of R5 that was dropped or narrowed, and
      why.

## Expected Proof

- Adapter tests for each kept form and each near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, and the mod's
  tests.

## Blocked By

None.

## Scope Exclusions

- Interpreter commands (`python`, `node`, `uv run`), which are never
  plain reads.
- `sed`, `awk` and `jq`, which can write or execute.
- Read-only subagents and which spawns pass routing.
- Inline scripts that write (Ticket 093).

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `e520ae6` (`ac9a203`, follow-up `a989642`).
- Exercised in later sessions; no separate live-check record.
