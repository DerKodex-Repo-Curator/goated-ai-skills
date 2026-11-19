# Ticket 110: Whole Shell Prints Orient

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-5.md` (R1; AC1, AC5, AC6)

## Type

AFK. Decision H, option 1 (the maintainer, 2026-11-18).

## What To Build

A session routed by its brief orients by whole shell prints as it does by
whole file reads. A finished, successful shell command whose plain file
printer prints a file whole counts as a whole read of that file toward the
`pipeline` gate's three distinct files. A print is whole when the printer
is `cat`, or PowerShell's `Get-Content`, `gc` or `type` without
`-TotalCount`, `-Head`, `-First`, `-Tail` or `-Last`, and its output is
not piped into another command. `cat a b c` prints three files. The
contract names this a new term, **whole print**, used in the `pipeline`
row only; "Whole read" keeps its meaning. A printed path is resolved from
the command's folder to the form a file read records, so one file printed
once and read once under another spelling counts as one.

`head`, `tail`, `sed`, `grep` and every other command never count. Every
other rule that asks for a whole read (design and registry references,
red flags, spawn templates) keeps asking for a file read: this widens
orientation only. The orientation hold's text says a whole print counts.

The rule lives in the shared core at `adapters/core/goated_core/`: the file
printer reading in `shell.py` (`FILE_PRINTERS`, which the conflict rule
already uses to name the files a printer shows), and where orientation
counts files (`gates._files_read`, `ORIENTATION_READS`, the orientation
hold text). The contract and a conformance scenario change with the code,
as `AGENTS.md` requires: the contract's Terms (a new Whole print), the
`pipeline` row and Shell Reading; a scenario under
`stack/fixtures/enforcement/`.

**`shell.py`'s pull request reading:** not touched. The printer branch
of `_add_segment` sits in the lines next to Ticket 108's `FORGE_DIFFS`
change; 108 and 109 have merged, so read that code as it is now.

## Recommended First Reads

- The parent spec, R1 and decision H.
- `stack/enforcement-contract.md`: Terms (Whole read, beside which Whole
  print goes), the `pipeline` row,
  Conflicts (how a printer names files) and Shell Reading.
- The core's `gates.py` (`_files_read`, `_brief_orientation`, the
  orientation hold) and `shell.py` (`FILE_PRINTERS` and the function that
  names a printer's files).
- `tickets/archive/105-core-conflicts-opened-by-shell-reads-and-ended-by-commits.md`,
  which made printers name their files.

## Acceptance Criteria

- [x] Three finished `cat` commands of three distinct files, or one
      `cat a b c`, clear orientation in a briefed `standard` session with
      the orientation skill installed and not loaded.
- [x] `head a`, `sed -n 1,50p a`, `grep x a`, `cat a | head`, and
      `Get-Content a -TotalCount 5` do not count; `Get-Content a` does.
- [x] A failed command, or one still running, does not count.
- [x] A shell print of a design reference still does not clear
      `design-reads`.
- [x] Two spellings of one path count as one file, as for file reads,
      and `cat src/a.py` run from the project root and a file read of the
      same file's absolute path count once.
- [x] The orientation hold's text says a whole shell print counts.
- [x] The contract states the rule, and a conformance scenario covers the
      hold and each near-miss kind.
- [x] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The core's gate and shell tests, with the new cases.
- The Claude Code adapter's tests through its hook.
- The repo checks in `AGENTS.md`.

## Blocked By

- `tickets/archive/108-core-pull-request-options-between-noun-and-verb.md`
  and `tickets/archive/109-core-one-pull-request-per-simple-command.md`
  (merged; ordering: adjacent lines in `shell._add_segment`).

## Overlaps

- `shell.py` with Tickets 108 and 109 (pull request reading, another
  part of the file).
- `gates.py` with Ticket 111 (`shown_holds`, another function).

## Scope Exclusions

- Counting reads of the files a brief names.
- Partial reads toward orientation.
- Shell prints for any rule but orientation.

## Closeout

Completed, merged and archived on 2026-11-19.

- Merged as `759b518` (`62087b0`, follow-up `cc109ff`).
- Maintainer decision H1. Lead decisions at review: a print counts only when its exit status is the command's own (in the trailing `&&` chain), common PowerShell value parameters and range prefixes are read as options, and words holding `$`, `~` or a glob count as no file.
- Exercised in later sessions; no separate live-check record.
