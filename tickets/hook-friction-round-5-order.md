# Hook Friction Round 5 Delivery Order

Source spec: `docs/specs/2026-11-18-hook-friction-round-5.md`

Parallel waves, with the other rounds' open tickets:
[hook-friction-round-3-waves.md](hook-friction-round-3-waves.md)

The maintainer chose the first option of every decision on 2026-11-18;
decision Q (the carrier call) has no ticket. Review the same day reopened
O (restated) and narrowed L1, which awaits the maintainer's confirmation.
Listed in the combined ranking's order.

1. `tickets/114-core-large-writes-land-and-read-after.md`
   - Status: Waiting for the maintainer to confirm L1 as narrowed.
   - Blocked by: that confirmation.
   - Overlaps: `_closeout_items` and the read-gate rows with 113 and 116,
     which wait for it.
   - Enables: a large edit applied once, its reads asked at the closeout.
2. `tickets/110-core-whole-shell-prints-orient.md`
   - Status: Waiting for 108 and 109. Decision H1.
   - Blocked by: `108` and `109` on branch `tickets/shell-pr-follow-ups`
     (ordering: adjacent lines in `shell._add_segment`).
   - Overlaps: `gates.py` with 111 and 117 (other functions).
   - Enables: a session that oriented with `cat` not held for orientation.
3. `tickets/116-core-proof-kept-while-nothing-material-changed.md`
   - Status: Waiting for decision O (restated) and 114. Decision N1.
   - Blocked by: decision O; `114` (ordering, `_closeout_items`).
   - Overlaps: `_closeout_items` with 114; under O2, the event model
     version with 114.
   - Enables: no new Proof after a comment-only edit, and no background
     launch passing for a proof.
4. `tickets/115-core-mocking-pattern-for-code-patches.md`
   - Status: Ready. Decision M1.
   - Blocked by: None.
   - Overlaps: `reference_reads.py` with 113 (another function).
   - Enables: no mocking reference for `fake` in data or
     `monkeypatch.setenv`.
5. `tickets/117-core-continue-meets-router-first-in-a-briefed-task.md`
   - Status: Ready. Decision P1.
   - Blocked by: None.
   - Overlaps: `gates.py` with 110 and 111 (other functions).
   - Enables: a typed `continue` in a briefed session with no router load.
6. `tickets/111-core-one-clearing-section-per-message.md`
   - Status: Ready. Decision I1.
   - Blocked by: None.
   - Overlaps: `gates.py` with 110; hold-text tests with 112.
   - Enables: several holds on one call saying once how to clear them.
7. `tickets/112-core-scripted-edit-names-unknown-kinds.md`
   - Status: Ready. Decision J1.
   - Blocked by: None.
   - Overlaps: hold-text tests with 111.
   - Enables: the `scripted-edit` hold no longer calling a docs file code.
8. `tickets/113-core-design-reads-sized-by-substance.md`
   - Status: Waiting for 114. Decisions K1.1 and K2.1.
   - Blocked by: `114` (ordering, the same contract rows).
   - Overlaps: `reference_reads.py` with 115.
   - Enables: a short code edit with a comment, and new cases in an
     existing test, asking for no design read their size alone selected.

Only 110 touches `shell.py`, and not its pull request reading, which
Tickets 108 and 109 are changing. No round 5 ticket touches that reading.

Decision Q, the `true` carrier call (item 12), has no ticket: the
maintainer chose to keep it.

## Merge Order

Branch `tickets/shell-pr-follow-ups` (Tickets 108 and 109, waves 16 and
17) merges before this branch. Both add wave rows after 085's; keep 108's
and 109's rows first, then round 5's (waves 18 and 19).

## Ready Frontier

- `tickets/115-core-mocking-pattern-for-code-patches.md`
- `tickets/117-core-continue-meets-router-first-in-a-briefed-task.md`
- `tickets/111-core-one-clearing-section-per-message.md`
- `tickets/112-core-scripted-edit-names-unknown-kinds.md`

114 joins when the maintainer confirms the narrowed L1; 110 once 108 and
109 merge; 113 once 114 merges; 116 once O is decided and 114 merges.

## Coverage

- AC1 (whole shell prints orient) → 110
- AC2 (design reads sized by substance) → 113
- AC3 (one clearing section) → 111
- AC4 (`scripted-edit` wording) → 112
- AC7 (large writes land) → 114
- AC8 (mocking pattern) → 115
- AC9 (Proof after comment-only edits) → 116
- AC10 (background checks and waiting) → 116
- AC11 (`continue` in a briefed task) → 117
- AC5 (contract and scenarios) → every ticket
- AC6 (repo checks) → every ticket
