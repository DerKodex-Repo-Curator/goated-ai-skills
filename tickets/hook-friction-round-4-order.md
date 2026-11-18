# Hook Friction Round 4 Delivery Order

Source spec: `docs/specs/2026-11-18-hook-friction-round-4.md`

Parallel waves, with round 2's remaining tickets:
[hook-friction-round-3-waves.md](hook-friction-round-3-waves.md)

1. `tickets/archive/099-core-fixture-data-is-test-data.md`
   - Status: Completed, merged and archived on 2026-11-18.
   - Blocked by: `tickets/archive/081-shared-enforcement-core.md`
   - Enables: fixture edits with no configuration reference.
2. `tickets/archive/100-core-narrower-reference-triggers.md`
   - Status: Completed, merged and archived on 2026-11-18.
   - Blocked by: `tickets/archive/081-shared-enforcement-core.md`
   - Enables: the mocking reference for mocks in code, and short
     comment-only edits with no design reads.
3. `tickets/archive/102-core-session-messages-continue-the-task.md`
   - Status: Completed, merged and archived on 2026-11-18.
   - Decisions: D1 option 2 and D2 option 1 (the maintainer, 2026-11-18).
   - Blocked by: `tickets/archive/081-shared-enforcement-core.md`
   - Enables: a peer's message continuing the work without a held write.
4. `tickets/archive/101-core-read-skips-last-the-task.md`
   - Status: Completed, merged and archived on 2026-11-18.
   - Decision: C option 2 (the maintainer, 2026-11-18).
   - Blocked by: `tickets/archive/081-shared-enforcement-core.md`, 099, 100
   - Enables: a reasoned skip of a read written once per task.

Every ticket waits for Ticket 081, so each rule changes once, in
`adapters/core/`. Ticket 101 also waits for 099 and 100: they narrow the
triggers of the same two gates and edit the same contract rows, and with
them landed the remaining need for lasting skips can be judged again.

## Rule Gaps Left By Ticket 081

The spec's addendum (R7 to R12), written 2026-11-18. Tickets 103, 104,
105 and 107 run in wave 14 and 106 in wave 15, after 101, in
[hook-friction-round-3-waves.md](hook-friction-round-3-waves.md). The
overlaps below were with 099, 100 and 102, which have merged.

- `tickets/archive/103-core-shell-pull-request-names-its-repository.md`
  - Status: Completed, merged and archived on 2026-11-18.
  - Blocked by: `tickets/archive/081-shared-enforcement-core.md`
  - Overlaps: none with 099, 100, 102.
  - Enables: a shell pull request aimed at another repository measured
    as the tool call is.
- `tickets/archive/104-core-script-receivers-and-posix-nul.md`
  - Status: Completed, merged and archived on 2026-11-18.
  - Decisions: E and F option 1 (the maintainer, 2026-11-18).
  - Blocked by: `tickets/archive/081-shared-enforcement-core.md`
  - Overlaps: 102, if the `/dev/null` hold text lives in `gates.py`.
  - Enables: `window.open` and `db.rm` in a script not held as writes;
    a posix `> nul` seen as the file it makes.
- `tickets/archive/105-core-conflicts-opened-by-shell-reads-and-ended-by-commits.md`
  - Status: Completed, merged and archived on 2026-11-18.
  - Decision: G option 1 (the maintainer, 2026-11-18).
  - Blocked by: `tickets/archive/081-shared-enforcement-core.md`
  - Overlaps: none with 099, 100, 102 in code; shares `writes.yaml`.
  - Enables: a `commit` call ending a conflict; markers shown by `cat`
    or `git diff` opening one.
- `tickets/archive/106-core-definition-starts-read-their-keyword.md`
  - Status: Completed, merged and archived on 2026-11-18.
  - Blocked by: `tickets/archive/081-shared-enforcement-core.md`
  - Blocked by (ordering): `tickets/archive/101-core-read-skips-last-the-task.md`
  - Overlaps: 099 and 100 (`design_reads.py`, the `design-reads` row and
    the design references table), now merged; and 101, the same gate.
  - Enables: `pub use` and YAML keys no longer asking for `process.md`.
- `tickets/archive/107-core-a-reviewer-starts-work.md`
  - Status: Completed, merged and archived on 2026-11-18.
  - Blocked by: `tickets/archive/081-shared-enforcement-core.md`
  - Overlaps: 102 (`actions.py`, another function; `closeout.yaml`).
  - Enables: a proposed spawn never counting as a reviewer.

## Follow-Ups From Ticket 103's Review

The spec's R13 and R14, written 2026-11-18. They change the same lines of
the `FORGE_DIFFS` branch in `shell.py`, so they run one after the other.

- `tickets/archive/108-core-pull-request-options-between-noun-and-verb.md`
  - Status: Completed, merged and archived on 2026-11-18.
  - Blocked by: `tickets/archive/103-core-shell-pull-request-names-its-repository.md`
  - Enables: `gh pr -R x create` read as a pull request.
- `tickets/archive/109-core-one-pull-request-per-simple-command.md`
  - Status: Completed, merged and archived on 2026-11-18.
  - Blocked by (ordering): 108
  - Enables: each pull request in a chained command measured with its
    own options.

## Ready Frontier

Tickets 081 and 099 to 107 are merged and archived (waves 14 and 15,
2026-11-18), and so are 108 and 109 (waves 16 and 17). Round 4 is complete.

## Coverage

- AC1 (fixture data) → 099
- AC2 (mocking pattern) → 100
- AC3 (short comment-only edits) → 100
- AC4 (lasting skips) → 101
- AC5 (another session's message) → 102
- AC6 (waiting on another session) → 102
- AC9 (shell pull request's repository) → 103
- AC10 (JavaScript receivers) → 104
- AC11 (posix `nul`) → 104
- AC12 (conflicts opened and ended) → 105
- AC13 (definition starts) → 106
- AC14 (a reviewer starts work) → 107
- AC15 (options between noun and verb) → 108
- AC16 (one pull request per simple command) → 109
- AC7 (contract and scenarios) → every ticket
- AC8 (repo checks) → every ticket
