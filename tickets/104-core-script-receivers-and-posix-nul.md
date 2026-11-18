# Ticket 104: Script Receivers And A Posix `nul`

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-4.md` (addendum R8, R9; AC10,
AC11, AC7, AC8)

## Type

HITL: decisions E and F in the parent spec's addendum must be made before
work starts. Recommended: E option 1 and F option 1. If F is option 2,
the R9 half drops and the ticket is AFK once E is decided.

## What To Build

Both halves change what the core counts as a shell command writing a
file, in the same contract section and scenario file. They share a ticket
because each is small and they meet the same gates (`scripted-edit`,
`route-line`, `pipeline`).

- **JavaScript receivers (R8, decision E).** `.open`, `.rename`, `.rm`,
  `.unlink`, `.rmdir`, `.truncate`, `.cp` and `.copyFile` in inline
  `node`, `deno` or `bun` code count as writes only on the receivers
  decision E names. Under option 1: `fs`, `fs.promises`, `fsPromises`,
  `Deno`, or a name the script binds to a `require` or `import` of `fs`,
  `node:fs`, `fs/promises` or `node:fs/promises`, a destructured name
  included; a receiver the core cannot name counts, as today. So
  `window.open(url, 'width=200')` and `db.rm(id)` write nothing. Today the
  `js` table in `script_writes.py` matches `.<name>(` on any receiver and
  judges `.open` by its second argument alone.
- **`nul` in a posix shell (R9, decision F).** Under option 1, a `posix`
  command's redirect into `nul` (any case) writes a file named `nul`, as
  bash does, and a hold it meets names `/dev/null` as the posix null
  device; `nul` stays a null device in a `powershell` command. Today
  `shell.NULL_TARGETS` holds `nul` for both shells. Plain Reads already
  treats `nul` in bash as a real file and does not change.

The rules live in the shared core at `adapters/core/goated_core/`
(`script_writes.py`, `shell.py`). The contract and conformance scenarios
change with the code, as `AGENTS.md` requires:

- `stack/enforcement-contract.md`, Shell Reading: the `NULL_TARGETS`
  bullet (and its sentence contrasting Plain Reads), the script writes
  table's JavaScript row, and the paragraph after the table that states
  the any-receiver rule;
- `stack/fixtures/enforcement/writes.yaml`: a `window.open` and a `db.rm`
  near miss beside an `fs` write that is held; a posix `> nul` beside a
  powershell `> nul`.

## Recommended First Reads

- The parent spec's addendum: R8, R9, decisions E and F.
- `stack/enforcement-contract.md`, Shell Reading and Plain Reads.
- The core's `script_writes.py` (the `js` table, and how a name bound once
  to a literal is followed today) and `shell.py` (`NULL_TARGETS` and where
  it is read).
- `stack/fixtures/enforcement/README.md`, for the scenario format.

## Acceptance Criteria

- [ ] `node -e "window.open(u,'width=200')"` and `node -e "db.rm(id)"`
      meet no `scripted-edit` hold.
- [ ] `fs.rmSync(p)`, `fs.promises.rm(p)`, `fs.open(p,'w')` and a call on
      a name bound to `require('node:fs')` are still writes.
- [ ] Under F option 1: a posix `echo x > nul` is a write that meets the
      write gates, and the same in a `powershell` command is not.
- [ ] The contract states each rule as decided, and conformance scenarios
      cover each hold and near miss above.
- [ ] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The core's script-writes and shell-reading tests, with the new cases.
- The repo checks in `AGENTS.md`.

## Blocked By

- `tickets/081-shared-enforcement-core.md` (merged)
- Maintainer decisions E and F.

## Overlaps

- No code shared with 099 or 100. If F option 1 changes a hold text that
  `gates.py` owns (`route-line`, `pipeline`), that is the file Ticket 102
  edits (`check_routing`): land after 102, or keep the change to the text.
- Shares `shell.py` with Ticket 103 (another function).

## Scope Exclusions

- Python, Perl and Ruby receivers.
- `$null` in a posix command and `/dev/null` in a powershell command.
- Plain Reads, which already holds any redirect into a null device.
