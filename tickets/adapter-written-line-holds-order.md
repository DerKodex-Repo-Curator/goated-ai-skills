# Adapter Written-Line Holds Delivery Order

Source spec: `docs/specs/2026-11-17-adapter-written-line-holds.md`

Parallel waves across all five order files:
[hook-friction-round-2-waves.md](hook-friction-round-2-waves.md)

1. `tickets/061-adapter-design-closeout-citations-and-question.md`
   - Blocked by: None
   - Enables: citations that clear at commit, a concrete question at the
     red flags, and a documented restore limit.
2. `tickets/062-adapter-unseen-line-advice-once-across-parallel-holds.md`
   - Blocked by: None
   - Enables: one full advice per turn, parallel holds included.
3. `tickets/063-adapter-design-reads-small-edits.md`
   - Blocked by: None
   - Enables: small fixes with no reference chosen by file kind.
4. `tickets/064-adapter-session-cards-pass-routing.md`
   - Blocked by: None
   - Enables: proposal and offer cards with no routing round trip.
5. `tickets/065-adapter-loads-count-until-compaction.md`
   - Blocked by: 061, 062 and 064
   - Enables: no reloads of skills or templates still in context.

Tickets were combined where splitting bought no parallel work, separate
proof or approval. Ticket 061 holds three changes to the closeout's Design
and Proof items and their texts, one of them a README note. Ticket 065
holds loads and template reads, which share one rule and one piece of
state.

Tickets 061 to 064 touch different functions. Their overlaps are the
adapter README and the regenerated `adapter-texts.ts`, which can be
resolved at merge time by regenerating, as in earlier waves. Ticket 065
changes what the turn's proof reads and the closeout's Design items (061),
the session state and the `pipeline` hold's text (062), and the routing
check (064), so it runs after all three. It shares no function with 063.

## Ready Frontier

- `tickets/061-adapter-design-closeout-citations-and-question.md`
- `tickets/062-adapter-unseen-line-advice-once-across-parallel-holds.md`
- `tickets/063-adapter-design-reads-small-edits.md`
- `tickets/064-adapter-session-cards-pass-routing.md`

Ticket 065 follows 061, 062 and 064.

## Coverage

- AC1 (citations from call fields) → 061
- AC2 (citations item text) → 061
- AC3 (advice once across parallel holds) → 062
- AC4 (loads until compaction) → 065
- AC5 (lines and overrides stay per turn) → 065
- AC6 (Design items in later turns) → 065
- AC7 (template reads until compaction) → 065
- AC8 (small edits) → 063
- AC9 (the question) → 061
- AC10 (cards) → 064
- AC11 (restore limit) → 061
- AC12 (kept holds unchanged) → every ticket
- AC13 (repo checks) → every ticket
