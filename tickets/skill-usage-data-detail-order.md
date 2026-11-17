# Skill-Usage Data Detail Delivery Order

Source spec: `docs/specs/2026-11-17-skill-usage-data-detail.md`

Parallel waves across the round 2 order files:
[hook-friction-round-2-waves.md](hook-friction-round-2-waves.md). For
Ticket 078 and later, with round 3's two order files:
[hook-friction-round-3-waves.md](hook-friction-round-3-waves.md)

1. `tickets/075-skill-usage-hold-detail.md`
   - Blocked by: None
   - Enables: closeout items, skip reasons and kinds of unanswered hold in
     the data.
2. `tickets/076-skill-usage-routes-sessions-projects-versions.md`
   - Blocked by: 075
   - Enables: the router's choices, side sessions, and data split by
     project and version.
3. `tickets/077-undocumented-override-phrases.md`
   - Blocked by: None
   - Enables: override data that can be trusted.
4. `tickets/078-skill-usage-reference-counts.md`
   - Blocked by: `tickets/068-adapter-reference-reads-turn-signals.md`, 076
   - Enables: numbers to tune reference signals.

Tickets 075 and 076 both change the stored shape and the summary code, so
they run in order. Ticket 077 is a diagnosis whose fix may lie in the
adapter, so it stands alone. Ticket 068 belongs to
`tickets/registry-reference-reads-order.md`.

Adapter tickets in other order files regenerate `adapter-texts.ts`, which
the mod's tests read; that overlap is resolved at merge time by
regenerating.

## Ready Frontier

- `tickets/075-skill-usage-hold-detail.md`
- `tickets/077-undocumented-override-phrases.md`

Ticket 076 follows 075. Ticket 078 follows 076 and 068.

## Coverage

- AC1 (closeout items) → 075
- AC2 (skip reasons) → 075
- AC3 (unanswered holds) → 075
- AC4 (routes) → 076
- AC5 (side sessions) → 076
- AC6 (projects) → 076
- AC7 (versions) → 076
- AC8 (override phrases) → 077
- AC9 (reference counts) → 078
- AC10 (tests and repo checks) → every ticket
