# Ticket 104: Script Receivers And A Posix `nul`

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-4.md` (addendum R8, R9; AC10,
AC11, AC7, AC8)

## Type

AFK. The maintainer decided E and F on 2026-11-18: option 1 of each, in
the parent spec's addendum.

## What To Build

Both halves change what the core counts as a shell command writing a
file, in the same contract section and scenario file. They share a ticket
because each is small and they meet the same gates (`scripted-edit`,
`route-line`, `pipeline`).

- **JavaScript receivers (R8, decision E).** `.open`, `.rename`, `.rm`,
  `.unlink`, `.rmdir`, `.truncate`, `.cp` and `.copyFile` in inline
  `node`, `deno` or `bun` code count as writes only on `fs`,
  `fs.promises`, `fsPromises`, `Deno`, or a name the script binds to a
  `require` or `import` of `fs`, `node:fs`, `fs/promises` or
  `node:fs/promises`, a destructured name included. A receiver the core
  cannot name (`a[b].rm(`) counts, as today. So
  `window.open(url, 'width=200')` and `db.rm(id)` write nothing. Today the
  `js` table in `script_writes.py` matches `.<name>(` on any receiver and
  judges `.open` by its second argument alone.
- **`nul` in a posix shell (R9, decision F).** Null devices are per
  shell. A `posix` command's redirect into `nul` (any case) writes a file
  named `nul`, as bash does, and is held as a write; a hold it meets names
  `/dev/null` as the posix null device. `nul` stays a null device in a
  `powershell` command. Today `shell.NULL_TARGETS` holds `nul` for both
  shells. Plain Reads already treats `nul` in bash as a real file and does
  not change.

Trade-offs the maintainer accepted: a file-system object passed into a
script function as a parameter goes unseen (E); an agent typing the
Windows `> nul` habit in bash meets one more held call, though the file it
leaves is real and on Windows hard to delete (F).

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

- [x] `node -e "window.open(u,'width=200')"` and `node -e "db.rm(id)"`
      meet no `scripted-edit` hold.
- [x] `fs.rmSync(p)`, `fs.promises.rm(p)`, `fs.open(p,'w')`, a call on a
      name bound to `require('node:fs')`, and a destructured
      `const { rm } = require('fs'); rm(p)` are still writes.
- [x] A posix `echo x > nul` is a write that meets the write gates, and
      its hold text names `/dev/null`; the same in a `powershell` command
      is not a write.
- [x] The contract states each rule, and conformance scenarios cover each
      hold and near miss above.
- [x] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The core's script-writes and shell-reading tests, with the new cases.
- The repo checks in `AGENTS.md`.

## Blocked By

- `tickets/archive/081-shared-enforcement-core.md` (merged)

## Overlaps

- No code shared with 099 or 100. The hold text naming `/dev/null` may
  live in `gates.py` (`route-line`, `pipeline`), the file Ticket 102 edits
  (`check_routing`): land after 102, or keep the change to the text.
- Shares `shell.py` with Ticket 103 (another function).

## Scope Exclusions

- Python, Perl and Ruby receivers.
- `$null` in a posix command and `/dev/null` in a powershell command.
- Plain Reads, which already holds any redirect into a null device.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `c6ced98` (`1d711d1`, follow-up `b3ae338`).
- Maintainer decisions: E1 and F1 (option 1 of decisions E and F).
- Exercised in later sessions; no separate live-check record.
