# Adapter Low-Signal Holds Delivery Order

Source spec: `docs/specs/2026-11-17-adapter-low-signal-holds.md`

Parallel waves across both round 3 order files, and against round 2's
remaining tickets:
[hook-friction-round-3-waves.md](hook-friction-round-3-waves.md)

1. `tickets/086-adapter-repeated-failure-red-runs.md`
   - Blocked by: None
   - Enables: TDD red runs and shrinking failures with no hold.
2. `tickets/087-adapter-routing-orientation-by-reads-and-outside-writes.md`
   - Blocked by: None
   - Enables: briefed sessions oriented by their reads, and scratch writes
     with no routing hold.
3. `tickets/088-adapter-wider-plain-reads.md`
   - Blocked by: None
   - Enables: looking around before the router loads, and a carrier call
     that always passes.
4. `tickets/089-adapter-design-holds-without-written-text.md`
   - Blocked by: None
   - Enables: design holds that ask only for a load and reads.
5. `tickets/091-adapter-review-size-and-installs.md`
   - Blocked by: None
   - Enables: no Review item in a delegated session, branch size by code,
     and installs judged by place.
6. `tickets/090-adapter-test-edit-reference-thresholds.md`
   - Blocked by: 089
   - Enables: test references asked only when a test is designed.
7. `tickets/092-adapter-whole-reads-and-read-order.md`
   - Blocked by: 089, 091, and
     `tickets/078-skill-usage-reference-counts.md`
   - Enables: whole reads of required files, and one diff read per item.

Tickets were combined where splitting bought no parallel work, separate
proof or approval:

- 086 holds both changes to how `repeated-failure` counts and shows a
  check.
- 087 holds both changes to the routing check.
- 089 holds the design-reads line, the citations and the red-flags
  reread: three changes to the design gate and the closeout's Design
  items, which share one skill and one piece of state.
- 091 holds three closeout triggers. The install rule is small and rides
  with the Review changes.
- 092 holds two rules about what counts as a read.

Tickets 086, 087, 088, 089 and 091 touch different functions. Their
overlaps are the adapter README and the regenerated `adapter-texts.ts`,
resolved at merge time by regenerating, as in earlier waves. Ticket 090
changes the design signals and the Design references section that 089
changes first. Ticket 092 changes the reads the design gate counts (089)
and the Review item and `pr-review` hold (091).

Ticket 079, in `tickets/portable-enforcement-core-order.md`, writes the
enforcement contract from the adapter's rules. It waits for every ticket
here, so the contract states these rules as they then stand.

## Ready Frontier

- `tickets/086-adapter-repeated-failure-red-runs.md`
- `tickets/087-adapter-routing-orientation-by-reads-and-outside-writes.md`
- `tickets/088-adapter-wider-plain-reads.md`
- `tickets/089-adapter-design-holds-without-written-text.md`
- `tickets/091-adapter-review-size-and-installs.md`

Ticket 090 follows 089. Ticket 092 follows 089, 091 and round 2's 078.

## Coverage

- AC1 (red runs) → 086
- AC2 (shrinking runs) → 086
- AC3 (the check as shown) → 086
- AC4 (orientation by reads) → 087
- AC5 (writes outside the project) → 087
- AC6 (plain reads) → 088
- AC7 (no design-reads line) → 089
- AC8 (no citations) → 089
- AC9 (red-flags reread) → 089
- AC10 (test edits) → 090
- AC11 (review in a briefed session) → 091
- AC12 (branch size) → 091
- AC13 (read order) → 092
- AC14 (whole reads) → 092
- AC15 (installs) → 091
- AC16 (kept holds unchanged) → every ticket
- AC17 (repo checks and budgets) → every ticket
- R15 (documentation) → every ticket; the Known Limits correction on
  shell writes → 090
