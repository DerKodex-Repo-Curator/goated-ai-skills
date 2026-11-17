# Ticket 043: Adapter Holds Skip Files Outside The Project

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (Trial Result; AC11)

## Type

AFK.

## Problem

In the Ticket 033 trial, 9 of 23 design holds were on scratch scripts in a
session scratchpad, outside the project, and 5 of 16 skip lines existed only
to clear holds like that. The closeout already ignores absolute paths outside
the project, but it treats every relative path as inside, so
`cd ~/.claude/hooks && mv a.ps1 b.ps1` counted as a project code change and
held the turn end.

## What To Build

- The `design` and `security` gates apply only to files inside the project
  folder, with the same rule the closeout uses (`_in_project` in
  `actions.py`).
- Shell write targets are resolved against a `cd` (or `Set-Location`,
  `pushd`) earlier in the same command, so a relative target after a `cd`
  to an absolute folder outside the project is outside. A `cd` the analysis
  cannot resolve, such as one to a variable, leaves the target as today.
- Update the README's What It Holds and Shell writes sections.

## Recommended First Reads

- `adapters/claude-code/README.md`: What It Holds, Shell writes.
- `adapters/claude-code/goated_adapter/actions.py` (`_design_hold`,
  `_security_hold`, `_changed_paths`, `_in_project`) and
  `goated_adapter/shell.py`.
- `tests/test_claude_code_adapter_actions.py`.

## Acceptance Criteria

- [ ] A large `Write` of a `.py` file outside the project is not held by the
      design gate; the same write inside is.
- [ ] A write to a security-sensitive path outside the project is not held;
      inside, it is.
- [ ] `cd /outside && mv a.py b.py` does not count as a project code change
      at closeout; `cd sub && mv a.py b.py` inside the project does.
- [ ] Unresolvable `cd` targets keep today's behaviour.

## Expected Proof

- Adapter tests for each criterion and its near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.

## Blocked By

- `tickets/archive/042-adapter-fresh-session-routing.md` (same files)

## Scope Exclusions

- Modelling a full shell: only a `cd` in the same command is followed.

## Closeout

Completed, merged and archived on 2026-11-17.

- Merged as `b8c4ece` after four rounds (`672c74c`, `a00d92f`, `98af08b`,
  `2521fb0`). Each review found ways to make a project file look outside, so
  the final rule is: a file counts as outside the project only when the
  adapter is certain; when in doubt it is inside. The project's folders are
  `CLAUDE_PROJECT_DIR`, the working folder, and the git checkout above
  either. Only a plain `cd` or `Set-Location` with one path, at the start or
  in an `&&` chain, is followed; links and junctions are resolved; Git Bash
  drive paths are read only when certain, and other rooted paths, device and
  network paths count as inside.
- The maintainer's main session reran all five review probes (about 90 cases)
  on the final commit: every escape was held, and a `%TEMP%` scratch file,
  `cd ~/.claude/hooks && mv`, and `cd /abs/outside && mv` still passed.
- Every check passed: the validator, the unit tests on Python 3.14 and 3.11,
  the V1/V2 context comparison, and the mod's tests.
- Known limits, in the README, all fail toward holding: `CDPATH`, Git Bash
  mounts such as `/tmp`, and unread path forms.
