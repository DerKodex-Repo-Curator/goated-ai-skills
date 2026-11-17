# Registry Reference Reads Delivery Order

Source spec: `docs/specs/2026-11-17-registry-reference-reads.md`

Parallel waves across all five order files:
[hook-friction-round-2-waves.md](hook-friction-round-2-waves.md)

1. `tickets/066-registry-declares-every-reference.md`
   - Blocked by: None
   - Enables: a complete, checked record of when each reference is read.
2. `tickets/067-adapter-reference-reads-gate-edit-signals.md`
   - Blocked by: 066, `tickets/065-adapter-loads-count-until-compaction.md`,
     `tickets/063-adapter-design-reads-small-edits.md`
   - Enables: enforced reads for references selected by one edit.
3. `tickets/068-adapter-reference-reads-turn-signals.md`
   - Blocked by: 067
   - Enables: enforced reads for references selected by what the turn did.

The registry work is one ticket because the schema, the entries and the
validator are unusable apart. The adapter work is two because the gate with
edit signals can be proved and used alone, and the turn signals read
different parts of the adapter.

Tickets 063 and 065 belong to `tickets/adapter-written-line-holds-order.md`.

## Ready Frontier

- `tickets/066-registry-declares-every-reference.md`

Ticket 067 follows 066, 065 and 063. Ticket 068 follows 067.

## Coverage

- AC1 (every reference declared) → 066
- AC2 (validator failures) → 066
- AC3 (held only when loaded) → 067
- AC4 (read counts until compaction) → 067
- AC5 (skip line) → 067
- AC6 (the first enforced set) → 067, 068
- AC7 (no adapter change for a new reference) → 067, 068
- AC8 (existing gates unchanged) → 067
- AC9 (the mod counts the gate) → 067
- AC10 (repo checks) → every ticket
