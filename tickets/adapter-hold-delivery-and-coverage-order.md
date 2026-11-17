# Adapter Hold Delivery And Coverage Delivery Order

Source spec: `docs/specs/2026-11-17-adapter-hold-delivery-and-coverage.md`

Parallel waves across both round 3 order files, and against round 2's
remaining tickets:
[hook-friction-round-3-waves.md](hook-friction-round-3-waves.md)

1. `tickets/093-adapter-inline-script-writes.md`
   - Blocked by: None
   - Enables: code changed by an inline script judged like any edit.
2. `tickets/094-adapter-own-subagent-reports-continue-the-turn.md`
   - Blocked by: None
   - Enables: a turn that survives its own subagent's report.
3. `tickets/095-adapter-joint-holds-in-one-message.md`
   - Blocked by: 093, and 086, 087, 088, 089 and 091 in
     `tickets/adapter-low-signal-holds-order.md`
   - Enables: one retry for a call that meets several holds, and shorter
     hold texts.
4. `tickets/096-adapter-early-closeout-note.md`
   - Blocked by: 095
   - Enables: closeout items met before the final report.

Ticket 095 holds joint holds, shared text once and the named carrier: all
three change how a hold message is assembled, and the mod's reading of
it.

Tickets 093 and 094 touch different modules: the shell reading and a new
gate, and the transcript's turn boundaries. Ticket 088, in the other
order file, also changes the shell reading, in different functions.
Ticket 095 restructures the dispatch every gate runs through, so it
follows each ticket that changes or adds a gate. Ticket 096 adds a hook
and uses the texts and turn marker 095 settles.

Ticket 079, in `tickets/portable-enforcement-core-order.md`, waits for
every ticket here. Its event model must carry several holds in one
decision, which Ticket 095 defines.

## Ready Frontier

- `tickets/093-adapter-inline-script-writes.md`
- `tickets/094-adapter-own-subagent-reports-continue-the-turn.md`

Ticket 095 follows 086, 087, 088, 089, 091 and 093. Ticket 096 follows
095.

## Coverage

- AC1 (joint holds on an edit) → 095
- AC2 (joint holds on a spawn) → 095
- AC3 (shared text once) → 095
- AC4 (the mod counts each) → 095
- AC5 (short repeats) → 095
- AC6 (named carrier) → 095
- AC7 (inline script writes held) → 093
- AC8 (read-only scripts pass) → 093
- AC9 (unnamed script writes) → 093
- AC10 (own subagent reports) → 094
- AC11 (brief route survives a report) → 094
- AC12 (early closeout note) → 096
- AC13 (first lines and lone holds unchanged) → every ticket
- AC14 (latency) → 095, 096
- AC15 (repo checks) → every ticket
