# Design Reference Reads Delivery Order

Source spec: `docs/specs/2026-11-16-design-reference-reads.md`

1. `tickets/archive/048-design-reference-moment-triggers.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: None
   - Enables: references named at their moment in the skill, the portable
     design-reads line and citations, and file-pointing citations in other
     skills.
2. `tickets/archive/049-reader-first-comment-profile.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: `tickets/archive/048-design-reference-moment-triggers.md`
   - Enables: an opt-in denser comment standard the skill names instead of
     contradicting.
3. `tickets/archive/050-skill-usage-reference-read-timing.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: `tickets/archive/047-adapter-overrides-from-other-agents.md`
   - Enables: reference reads measured by moment, and design-reads
     declarations counted.
4. `tickets/051-adapter-design-reference-reads.md`
   - Blocked by: `tickets/archive/046-adapter-pipeline-after-compaction.md`,
     `tickets/archive/048-design-reference-moment-triggers.md`,
     `tickets/archive/050-skill-usage-reference-read-timing.md`
   - Enables: required design references read before and during the edit,
     with a cooldown until compaction.
5. `tickets/052-adapter-design-citations-at-closeout.md`
   - Blocked by: `tickets/051-adapter-design-reference-reads.md`
   - Enables: a closeout that needs a cited id from each required reference.

Tickets 048 and 049 change only skill files, so they can run alongside the
adapter queue (047, then 042 to 046). Ticket 050 edits the mod after 047.
Tickets 051 and 052 edit the same adapter files and hold texts as 042 to 046,
so they run after 046 and before Ticket 035 in
`tickets/adapter-skill-activation-gates-order.md`.

## Ready Frontier

- `tickets/051-adapter-design-reference-reads.md`

Ticket 052 follows 051.

## Coverage

- AC1 → 048
- AC2 → 048
- AC3 → 048
- AC4 → 049
- AC5 → 051
- AC6 → 051
- AC7 → 052
- AC8 → 050 (timing, declarations), 051 (hold name)
- AC9 → the maintainer's next stretch of real use after 052
