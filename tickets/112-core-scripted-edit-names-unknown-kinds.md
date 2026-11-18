# Ticket 112: Scripted-Edit Names Unknown Kinds

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-5.md` (R4; AC4, AC5, AC6)

## Type

AFK. Decision J, option 1 (the maintainer, 2026-11-18).

## What To Build

The `scripted-edit` hold stops calling a file code when it cannot tell
what kind of file it is. For a file an inline script names only at run
time, the hold says its kind cannot be told, so it is held as a code file
would be; its short form says the same. A script that writes a named code
file is still held with "the code file" and its name. When a command does
both, the text names each in its own words.

The gate's rule does not change: what it holds, what clears it, and its
steering to a file edit tool stay.

The text lives in the shared core at `adapters/core/goated_core/`:
`actions._scripted_edit_hold`. The contract's `scripted-edit` paragraph
changes only if it states the text; a test or conformance scenario that
checks the text changes with it.

**`shell.py`'s pull request reading:** not touched.

## Recommended First Reads

- The parent spec, R4 and decision J.
- `stack/enforcement-contract.md`, the `scripted-edit` row and its
  paragraph under Shell Reading.
- The core's `actions.py`, `_scripted_edit_hold`.

## Acceptance Criteria

- [ ] A script writing a file named only at run time is held with text
      that does not call the file code, in its full and short forms.
- [ ] A script writing a named `.py` file is still held with "the code
      file" and its name.
- [ ] A command doing both names each in its own words.
- [ ] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The core's `scripted-edit` tests, with the new text.
- The Claude Code adapter's tests and its regenerated hold texts.
- The repo checks in `AGENTS.md`.

## Blocked By

- None.

## Overlaps

- Hold-text tests with Ticket 111; land either first and rebase the
  other.

## Scope Exclusions

- Telling a run-time file's kind from its extension (option J2).
- Which writes the gate holds.
