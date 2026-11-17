# Skill Placement Gates Delivery Order

Source spec: `docs/specs/2026-11-17-skill-placement-gates.md`

Parallel waves across all five order files:
[hook-friction-round-2-waves.md](hook-friction-round-2-waves.md)

1. `tickets/069-adapter-closeout-review-and-verification.md`
   - Blocked by: `tickets/065-adapter-loads-count-until-compaction.md`
   - Enables: review and verification before a large or risky commit.
2. `tickets/070-adapter-review-intake-hold.md`
   - Blocked by: 069,
     `tickets/067-adapter-reference-reads-gate-edit-signals.md`
   - Enables: review findings handled through `receiving-code-review`.
3. `tickets/071-spawn-briefs-name-skills.md`
   - Blocked by: None
   - Enables: subagents and side sessions told which skills to read.
4. `tickets/072-orientation-and-plans-in-routes.md`
   - Blocked by: `tickets/065-adapter-loads-count-until-compaction.md`, 071
   - Enables: oriented side sessions and planned ticket work.
5. `tickets/073-notices-for-retrospective-and-onboarding.md`
   - Blocked by: 072
   - Enables: prompts toward retrospective and onboarding skills.
6. `tickets/074-design-principles-soft-dependency-audit.md`
   - Blocked by: None
   - Enables: design guidance reachable from every skill that judges
     design.

Tickets were combined where splitting bought no parallel work, separate
proof or approval: the two closeout items (069), the two router changes
with their `pipeline` rule (072), and the two notices (073).

Ticket 065 belongs to `tickets/adapter-written-line-holds-order.md`. It
changes when a skill counts as loaded and the functions 069 and 072 build
on, and it follows 071, which changes the `spawn` gate first. Ticket 070
follows 069, which records which template a spawn's brief matched, and
067, in `tickets/registry-reference-reads-order.md`, because both add a
gate to the action check, the README's gate table and the mod's
first-line reading. Ticket 070 states its trigger in
`receiving-code-review`'s own text, so it does not touch the router.
Ticket 072 follows 071 because both edit the spawn-brief template, and 073
follows 072 because both edit the router; each file has a word budget.
Other overlaps are the adapter README and the regenerated
`adapter-texts.ts`, resolved at merge time by regenerating.

## Ready Frontier

- `tickets/071-spawn-briefs-name-skills.md`
- `tickets/074-design-principles-soft-dependency-audit.md`

Ticket 069 follows 065. Ticket 070 follows 069 and 067. Ticket 072 follows
065 and 071. Ticket 073 follows 072.

## Coverage

- AC1 (review at commit) → 069
- AC2 (review intake) → 070
- AC3 (verification triggers) → 069
- AC4 (orientation in briefed sessions) → 072
- AC5 (plans for ticket work) → 072
- AC6 (retrospective notice) → 073
- AC7 (skills line in a brief) → 071
- AC8 (design principles audit) → 074
- AC9 (onboarding notice) → 073
- AC10 (kept holds, repo checks, budgets) → every ticket
