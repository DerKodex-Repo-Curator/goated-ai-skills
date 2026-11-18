# Portable Enforcement Core Delivery Order

Source spec: `docs/specs/2026-11-17-portable-enforcement-core.md`

Parallel waves across the round 2 and round 3 order files:
[hook-friction-round-3-waves.md](hook-friction-round-3-waves.md), which
replaces waves 5 to 10 of
[hook-friction-round-2-waves.md](hook-friction-round-2-waves.md)

1. `tickets/archive/079-enforcement-contract-and-event-model.md`
   - Status: Completed, merged and archived on 2026-11-18.
   - Blocked by: 065, 068, 069, 070, 072, 073, 077, and 086 to 096
   - Enables: a harness-neutral statement of the rules, and scenarios any
     adapter can be checked against.
2. `tickets/098-adapter-contract-gaps.md`
   - Blocked by: 079
   - Enables: an adapter as strict as the contract it enforces, before its
     code moves.
3. `tickets/080-adapter-rules-read-the-event-model.md`
   - Blocked by: 079, 098
   - Enables: rules that no longer know which harness they run in.
4. `tickets/081-shared-enforcement-core.md`
   - Blocked by: 080
   - Enables: one core, callable by import or by a JSON command.
5. `tickets/082-neutral-usage-log-and-report.md`
   - Blocked by: 081, `tickets/archive/078-skill-usage-reference-counts.md`
   - Enables: the same measurement in every harness.
6. `tickets/083-adapter-guide-and-worked-example.md`
   - Blocked by: 081
   - Enables: adapters written by anyone, checked by the scenarios.
7. `tickets/084-pi-agent-adapter.md`
   - Blocked by: 083, 082
   - Enables: the enforced workflow in Pi Agent.
8. `tickets/085-opencode-adapter.md`
   - Blocked by: 084
   - Enables: the enforced workflow in OpenCode.

The extraction is two tickets. Ticket 080 is the prefactoring: it makes
the rules read the event model while they still live in the Claude Code
adapter, proved by the existing tests. Ticket 081 is then a mechanical
move plus the two ways in. Together they would not fit one session, and
080 alone leaves a working adapter.

Ticket 079 waits for the last adapter tickets of the three preceding
specs, in `tickets/adapter-written-line-holds-order.md`,
`tickets/registry-reference-reads-order.md` and
`tickets/skill-placement-gates-order.md`: they settle the rules the
contract states and change the files the extraction moves. Tickets 077 and
078 are in `tickets/skill-usage-data-detail-order.md`; 077 may change the
override parsing the extraction then moves.

Ticket 079 also waits for Tickets 086 to 096, hook-friction round 3, in
`tickets/adapter-low-signal-holds-order.md` and
`tickets/adapter-hold-delivery-and-coverage-order.md`. They change gates
and how holds are delivered, so the contract is written once, after them.
The waves from here on are in
[hook-friction-round-3-waves.md](hook-friction-round-3-waves.md).

Ticket 098 was added by Ticket 079's review. Where the adapter was looser
than the contract, the maintainer decided on 2026-11-18 that the contract
states today's behaviour and marks each gap, and that 098 fixes the code
before 080 starts moving it.

Ticket 085 follows 084 so the second real adapter can reuse what the
first learned; they could run in parallel if the maintainer prefers, at
the cost of some duplicated translation code.

## Ready Frontier

Ticket 079 is completed and archived, and 098, 080, 081, 082 and 083 are
merged. Ticket 084 is ready.

## Coverage

- AC1 (the ADR) → 079
- AC2 (the contract covers every gate) → 079, 098 (its gaps)
- AC3 (the core knows no harness) → 081
- AC4 (Claude Code behaviour unchanged) → 080, 081
- AC5 (command and import agree) → 081
- AC6 (conformance scenarios) → 079
- AC7 (the worked example) → 083
- AC8 (the same log from any harness) → 082
- AC9 (the mod reads the log) → 082
- AC10 (Pi Agent adapter) → 084
- AC11 (OpenCode adapter) → 085
- AC12 (repo checks) → every ticket
