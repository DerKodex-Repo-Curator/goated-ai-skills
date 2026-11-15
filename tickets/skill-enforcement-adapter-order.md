# Skill Enforcement Adapter Delivery Order

Source spec: `docs/specs/2026-11-15-skill-enforcement-adapter.md`
Decision record: `docs/adr/0003-opt-in-framework-enforcement-adapters.md`

1. `tickets/archive/028-discoverable-skill-descriptions.md`
   - Status: Completed and archived on 2026-11-15.
   - Blocked by: None
   - Enables: skills found from their descriptions in any framework; the
     trial in 033.
2. `tickets/archive/029-router-skill-map-and-route-line.md`
   - Status: Completed and archived on 2026-11-15.
   - Blocked by: None
   - Enables: the portable route and skip contracts the adapter enforces.
3. `tickets/030-claude-code-adapter-routing-gates.md`
   - Blocked by: `tickets/archive/029-router-skill-map-and-route-line.md`
   - Enables: router-first, route-line, and pipeline enforcement, and the
     adapter base for 031.
4. `tickets/031-claude-code-adapter-action-and-closeout-gates.md`
   - Blocked by: `tickets/030-claude-code-adapter-routing-gates.md`
   - Enables: action and closeout enforcement, and the stable hold format for
     032.
5. `tickets/032-skill-usage-mod-in-repo.md`
   - Blocked by: `tickets/031-claude-code-adapter-action-and-closeout-gates.md`
   - Enables: measurement for the trial.
6. `tickets/033-adapter-real-use-trial.md`
   - Blocked by: `tickets/archive/028-discoverable-skill-descriptions.md`,
     `tickets/032-skill-usage-mod-in-repo.md`
   - Enables: the maintainer's keep, revise, or revert decision.

Tickets 028 and 029 ran in parallel and were merged on 2026-11-15.

## Ready Frontier

- `tickets/030-claude-code-adapter-routing-gates.md`

## Coverage

- AC1 → 028
- AC2 → 029 (docs), 030 (detection)
- AC3 → 029
- AC4 → 030 (routing gates, overrides, subagents, fail-open), 031 (action and
  closeout gates, content checks)
- AC5 → 030, 031
- AC6 → 028, 029, 030
- AC7 → 032
- AC8 → 030 (adapter), 032 (mod)
- AC9 → 033
