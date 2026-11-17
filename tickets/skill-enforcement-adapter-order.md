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
3. `tickets/archive/030-claude-code-adapter-routing-gates.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: `tickets/archive/029-router-skill-map-and-route-line.md`
   - Enables: router-first, route-line, and pipeline enforcement, and the
     adapter base for 031 and 032.
4. `tickets/archive/031-claude-code-adapter-action-and-closeout-gates.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: `tickets/archive/030-claude-code-adapter-routing-gates.md`
   - Enables: action and closeout enforcement, and the stable hold format for
     034.
5. `tickets/archive/032-skill-usage-mod-in-repo.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: `tickets/archive/030-claude-code-adapter-routing-gates.md`
   - Enables: the mod in the repo, measuring routing holds, route lines,
     skips, overrides, references, and subagents; the base for 034.
6. `tickets/archive/034-skill-usage-mod-action-holds.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: `tickets/archive/031-claude-code-adapter-action-and-closeout-gates.md`,
     `tickets/archive/032-skill-usage-mod-in-repo.md`
   - Enables: measurement of every hold for the trial.
7. `tickets/archive/033-adapter-real-use-trial.md`
   - Status: Completed, merged and archived on 2026-11-16 (decision: revise).
   - Blocked by: `tickets/archive/028-discoverable-skill-descriptions.md`,
     `tickets/archive/034-skill-usage-mod-action-holds.md`
   - Enables: the maintainer's keep, revise, or revert decision.
8. `tickets/archive/039-skill-usage-hold-settlement-module.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: `tickets/archive/033-adapter-real-use-trial.md` (its legacy removal)
   - Enables: hold-outcome fixes in one module instead of inside `summarize`.
9. `tickets/archive/040-skill-usage-all-time-picture-badges.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: none. It changes only what the pane draws, not what the mod
     counts, so it landed during the 033 trial.
   - Enables: an All time picture without per-case badges, and Session badges
     whose colours each mean one thing.
10. `tickets/archive/041-adapter-review-holds-read-the-change.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: `tickets/archive/033-adapter-real-use-trial.md` (its keep decision)
   - Enables: review holds that clear only after the agent reads the change,
     not on a skill load alone; ticket 038 builds on it.
11. `tickets/archive/047-adapter-overrides-from-other-agents.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: `tickets/archive/041-adapter-review-holds-read-the-change.md`
   - Enables: overrides recorded and announced only for a prompt a person
     typed, never for a message from another agent or session.
12. `tickets/archive/042-adapter-fresh-session-routing.md`
   - Status: Completed, merged and archived on 2026-11-16.
   - Blocked by: `tickets/archive/047-adapter-overrides-from-other-agents.md`
   - Enables: `continue` in a session with no task, and loads earlier in the
     turn counting for the task it starts.
13. `tickets/archive/043-adapter-out-of-project-holds.md`
   - Status: Completed, merged and archived on 2026-11-17.
   - Blocked by: `tickets/archive/042-adapter-fresh-session-routing.md`
   - Enables: no design, security, or closeout holds for files outside the
     project.
14. `tickets/044-adapter-closeout-same-command-check.md`
   - Blocked by: `tickets/archive/043-adapter-out-of-project-holds.md`
   - Enables: a check in the same command as the write proving it.
15. `tickets/archive/045-route-and-skip-lines-before-the-call.md`
   - Status: Completed, merged and archived on 2026-11-17.
   - Blocked by: None
   - Enables: route and skip lines the adapter can see on the first try.
16. `tickets/archive/046-adapter-pipeline-after-compaction.md`
   - Status: Completed, merged and archived on 2026-11-17.
   - Blocked by: None
   - Enables: the last route line winning after a compaction, and the
     compaction handling Ticket 051 builds on.
17. `tickets/053-adapter-route-and-skip-lines-from-tool-input.md`
   - Blocked by: `tickets/archive/045-route-and-skip-lines-before-the-call.md`,
     `tickets/archive/046-adapter-pipeline-after-compaction.md`
   - Enables: route and skip lines the adapter always sees, from tool input,
     after 045 found that a message's text can be saved without them.

Tickets 041–046 are the trial's revise fixes (spec, Trial Result), and 047
fixes an R8 gap found in real use after the trial. 041, 047 and 042 ran one
after another. On 2026-11-16 the maintainer chose to run the rest in
parallel where only file overlap linked them: 044 still follows 043, since
both rework the shell analysis, while 045 and 046 depend on neither and on
each other only through shared README and hold-text lines, resolved at merge
time. Tickets 035–038 in `tickets/adapter-skill-activation-gates-order.md`
also run in parallel now. The trial's revise decision counts as the keep
decision those tickets are blocked on.

Tickets 028 and 029 ran in parallel and were merged on 2026-11-15. Ticket 032
was split on 2026-11-16 so it can run alongside 031: 031 works in
`adapters/claude-code/goated_adapter/` and 032 in the mod's own folder, so
their write scopes do not overlap. Ticket 034 needs both.

Ticket 051 from `tickets/design-reference-reads-order.md` follows 046
because its cooldown uses 046's compaction handling, and 052 follows 051.
Ticket 050 there edited the mod after 047.

## Ready Frontier

- `tickets/044-adapter-closeout-same-command-check.md`
- `tickets/053-adapter-route-and-skip-lines-from-tool-input.md` (HITL: the
  maintainer chooses where the line goes in a tool call)

Both edit adapter files; they can run in parallel and resolve overlaps at
merge time.

## Coverage

- AC1 → 028
- AC2 → 029 (docs), 030 (detection)
- AC3 → 029
- AC4 → 030 (routing gates, overrides, subagents, fail-open), 031 (action and
  closeout gates, content checks, shell writes), 047 (overrides only from a
  typed prompt)
- AC5 → 030, 031
- AC6 → 028, 029, 030
- AC7 → 032 (routing holds, lines, skips, overrides, references, subagents),
  034 (action and closeout holds, live check)
- AC8 → 030 (adapter), 032 (mod)
- AC9 → 033
- AC10 → 041
- AC11 → 042, 043, 044, 045, 046, 053
