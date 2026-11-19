# Hook Friction Round 6 Delivery Order

Source spec: `docs/specs/2026-11-19-hook-friction-round-6.md`

The maintainer chose every decision on 2026-11-19 and asked for as few
tickets as the work allows: closely related changes share a ticket and are
phased inside it, for one agent each.

1. `tickets/archive/118-core-design-reads-never-refuse-an-edit.md`
   - Status: Completed, merged and archived on 2026-11-19. Decision S1.
   - Blocked by: None.
   - Overlaps: the closeout Reads item with 120 (other items).
   - Enables: no edit refused, and no batch half-applied, for a design
     read.
2. `tickets/archive/119-core-routing-and-orientation-for-continued-work.md`
   - Status: Completed, merged and archived on 2026-11-19. Decisions T1, U1, W1 and Y1.
   - Blocked by: None.
   - Overlaps: none with 118 or 120 beyond the contract's Gates table.
   - Enables: a typed follow-up with no route line, orientation by
     distinct files, the project's own documents named, and the carrier
     probe's finding.
3. `tickets/archive/120-core-commit-time-holds-in-one-pass.md`
   - Status: Completed, merged and archived on 2026-11-19. Decisions V1, V2, X1, X2 and X3, and the Design
     item's count bug.
   - Blocked by: None.
   - Overlaps: the closeout items with 118 (the Reads item only).
   - Enables: one message per held commit, and commit and closeout asks
     that fire where they can find something.
4. `tickets/121-hold-text-small-fixes-and-log-detail.md`
   - Status: Ready. Decisions Z, Y2 and Y4.
   - Blocked by: `118`, `119` and `120` (ordering: hold and notice text).
   - Enables: holds that open with their clearing action, temp paths
     outside the project, log detail, and the spawn brief's two lines.

Decision Y3, a visual and interface design reference, has no ticket: it
gets its own spec.

## Waves

- Wave 20: 118, 119 and 120 in parallel.
- Wave 21: 121.

## Ready Frontier

Wave 20 (118, 119 and 120) is merged and archived (2026-11-19).

- `tickets/121-hold-text-small-fixes-and-log-detail.md`

## Coverage

- AC1, AC2 (design reads never refuse an edit) → 118
- AC3 (a typed follow-up continues) → 119
- AC4 (distinct files orient) → 119
- AC5 (one commit-time message) → 120
- AC6 (non-code changes keep the change read) → 120
- AC7 (small follow-ups counted by what they add) → 120
- AC8 (Docs accepts a doc change) → 120
- AC9 (a conflict's commit asks for less) → 120
- AC10 (test files are not security-sensitive) → 120
- AC11 (the carrier probe) → 119
- AC12 (hold text) → 121
- AC13 (temp paths, context pointer, spawn brief lines, log detail) →
  121, and 119 for the context pointer
- AC14 (contract and scenarios) → every ticket
