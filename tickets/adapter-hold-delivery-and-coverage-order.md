# Adapter Hold Delivery And Coverage Delivery Order

Source spec: `docs/specs/2026-11-17-adapter-hold-delivery-and-coverage.md`

Parallel waves across both round 3 order files, and against round 2's
remaining tickets:
[hook-friction-round-3-waves.md](hook-friction-round-3-waves.md)

1. `tickets/archive/093-adapter-inline-script-writes.md`
   - Status: Completed, merged and archived on 2026-11-18.
   - Blocked by: None
   - Enables: code changed by an inline script judged like any edit.
2. `tickets/archive/094-adapter-own-subagent-reports-continue-the-turn.md`
   - Status: Completed, merged and archived on 2026-11-18.
   - Blocked by: None
   - Enables: a turn that survives its own subagent's report.
3. `tickets/archive/097-adapter-script-write-paths-by-name-and-folder.md`
   - Status: Completed, merged and archived on 2026-11-18.
   - Blocked by: 093
   - Enables: no `scripted-edit` hold on a script that names its file in
     a variable, or that runs in a folder certainly outside the project.
4. `tickets/archive/095-adapter-joint-holds-in-one-message.md`
   - Status: Completed, merged and archived on 2026-11-18.
   - Blocked by: 093, 094, 097, and 086 to 092 in
     `tickets/adapter-low-signal-holds-order.md`
   - Enables: one retry for a call that meets several holds, and shorter
     hold texts.
5. `tickets/archive/096-adapter-early-closeout-note.md`
   - Status: Completed, merged and archived on 2026-11-18.
   - Blocked by: 095
   - Enables: closeout items met before the final report.

Ticket 095 holds joint holds, shared text once and the named carrier: all
three change how a hold message is assembled, and the mod's reading of
it.

Tickets 093 and 094 touch different modules: the shell reading and a new
gate, and the transcript's turn boundaries. Ticket 088, in the other
order file, also changes the shell reading, in different functions.
Ticket 095 restructures the dispatch every gate runs through and the way
a hold message is assembled, so it follows every other round 3 ticket
but 096: each changes a gate, a hold's text or, in 094, the turn
boundaries the turn marker resets on. Ticket 096 adds a hook and uses
the texts and the turn marker's purpose key that 095 settles.

Ticket 097 was added after Ticket 093 merged, for a false hold met in
use: a script that named its file in a variable. It amends the spec's R5
and R6. It changes how inline code is read and where an unnamed write is
placed, which no ticket of the other order file touches, so it runs
beside 090 and 092. It changes when `scripted-edit` fires in the dispatch
095 restructures, so 095 waits for it.

Ticket 079, in `tickets/portable-enforcement-core-order.md`, waits for
every ticket here; it reaches 097 through 095. Its event model must carry several holds in one
decision, which Ticket 095 defines.

## Ready Frontier

- None. Every ticket in this order is completed and archived.

## Coverage

- AC1 (joint holds on an edit) → 095
- AC2 (joint holds on a spawn) → 095
- AC3 (shared text once) → 095
- AC4 (the mod counts each) → 095
- AC5 (short repeats) → 095
- AC6 (named carrier) → 095
- AC7 (inline script writes held) → 093
- AC8 (read-only scripts pass) → 093
- AC9 (unnamed script writes) → 093, 097
- AC10 (own subagent reports) → 094
- AC11 (brief route survives a report) → 094
- AC12 (early closeout note) → 096
- AC13 (first lines and lone holds unchanged) → every ticket
- AC14 (latency) → 095, 096
- AC15 (repo checks) → every ticket
- AC16 (a once-bound path is its literal) → 097
- AC17 (an unnamed write in a known outside folder) → 097
