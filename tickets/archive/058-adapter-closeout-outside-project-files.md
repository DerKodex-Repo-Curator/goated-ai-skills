# Ticket 058: Closeout Ignores Setup And Scratch Files Outside The Project

## Parent Spec

`docs/specs/2026-11-17-adapter-hook-friction.md` (R9, R10; AC10, AC11)

## Type

HITL: if the scratch-file closeout has a cause other than the Git Bash
`/tmp` path, the maintainer decides the fix before code changes.

## Problem

Two closeouts fired on files outside the project:

- **Setup.** The closeout Setup item fired on a `settings.json` in a scratch
  live-check folder. The Setup item matches every write target with no
  inside-the-project check, while code changes already exclude files that
  are certainly outside.
- **Proof and Docs.** In the maintainer's main session, a `Stop` closeout
  asked for proof and doc-sync after edits only to scratch files outside the
  repo. This was not reproduced. The likely cause is the documented limit
  that a Git Bash path such as `/tmp/x.py` counts as inside the project.

## What To Build

- The Setup item counts only setup files inside the project. A package
  install counts wherever it runs.
- Reproduce the scratch-file closeout with a test. If the cause is a Git
  Bash `/tmp/...` path, read `/tmp` as the operating system's temp folder,
  so those writes count as outside. Other mounts stay as documented.
- If the cause is something else, stop and report it to the maintainer with
  the reproduction.
- Update Known Limits for the `/tmp` reading.

## Recommended First Reads

- The parent spec, R9 and R10.
- `adapters/claude-code/goated_adapter/actions.py` (`_setup_changes`,
  `_changed_paths`, `_in_project`, `_readings`).
- `adapters/claude-code/README.md`: Known Limits (paths inside the project).

## Acceptance Criteria

- [ ] A `settings.json` written outside the project raises no Setup item;
      one inside still does.
- [ ] A package install outside the project still raises the Setup item.
- [ ] The scratch-file closeout is reproduced by a test, and the fix passes
      it, or the cause is reported.
- [ ] A Git Bash write to `/tmp/x.py` raises no Proof or Docs item, while
      `/c/<project>/x.py` still does.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.

## Blocked By

- None.

## Scope Exclusions

- Reading other Git Bash mounts or `CDPATH`.

## Closeout

Completed, merged and archived on 2026-11-17.

- Merged as `744ca13` (`f3b2f43`, review fixes `c1031dd`, `9c31ac8`,
  `105bd64`, `ff91c6b`). The maintainer approved fixing the cause the session
  found instead of stopping, since it explained the closeout.
- The Setup item counts only setup files inside the project; a package
  install counts wherever it runs. Git Bash `/tmp` is read as the temp
  folder, and a `cd` through `..` counts as inside.
- The scratch-file closeout came mainly from .NET write text read as an
  unnamed write. In Bash, .NET text is now data unless the command runs
  PowerShell (`pwsh`, `powershell`, `iex`, a `.ps1`); in the PowerShell tool
  any .NET write text still counts. Scratch Writes and
  `git checkout --theirs` edits now count as outside.
- Every check passed on the integrated branch fast-forwarded into main (`4f5cc75`): the validator, 606 unit tests on Python 3.14 and 3.11, the V1/V2 context comparison, `claude plugin test` (165 pass), and the TypeScript check with only the 5 known errors in `tests/register.test.tsx`.
- Known limits, in the README: a script or text file written in one call and
  run in a later one.
