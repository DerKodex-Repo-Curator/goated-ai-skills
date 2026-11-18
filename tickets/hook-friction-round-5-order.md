# Hook Friction Round 5 Delivery Order

Source spec: `docs/specs/2026-11-18-hook-friction-round-5.md`

Parallel waves, with the other rounds' open tickets:
[hook-friction-round-3-waves.md](hook-friction-round-3-waves.md)

Every ticket waits for the maintainer's decision on its options (H to P
in the spec); decision Q (the carrier call) has no ticket. Each is written
to the recommended option. Listed in the combined ranking's order. 113 and
116 also wait for 114, which changes the same contract rows and closeout
items; the rest can run at once once decided.

1. `tickets/114-core-large-writes-land-and-read-after.md`
   - Status: Decision needed (L; recommended L1).
   - Blocked by: decision L.
   - Overlaps: `_closeout_items` and the read-gate rows with 113 and 116,
     which wait for it.
   - Enables: a large edit applied once, its reads asked at the closeout.
2. `tickets/110-core-whole-shell-prints-orient.md`
   - Status: Decision needed (H; recommended H1).
   - Blocked by: decision H.
   - Overlaps: `shell.py` with 108 and 109 (their pull request reading,
     another part); `gates.py` with 111 (another function).
   - Enables: a session that oriented with `cat` not held for orientation.
3. `tickets/116-core-proof-kept-while-nothing-material-changed.md`
   - Status: Decision needed (N and O; recommended N1 and O1).
   - Blocked by: decisions N and O; `114` (ordering, `_closeout_items`).
   - Overlaps: `_closeout_items` with 114.
   - Enables: no new Proof after a comment-only edit or while a
     background check runs.
4. `tickets/115-core-mocking-pattern-for-code-patches.md`
   - Status: Decision needed (M; recommended M1).
   - Blocked by: decision M.
   - Overlaps: `reference_reads.py` with 113 (another function).
   - Enables: no mocking reference for `fake` in data or
     `monkeypatch.setenv`.
5. `tickets/117-core-continue-meets-router-first-in-a-briefed-task.md`
   - Status: Decision needed (P; recommended P1).
   - Blocked by: decision P.
   - Overlaps: `gates.py` with 110 and 111 (other functions).
   - Enables: a typed `continue` in a briefed session with no router load.
6. `tickets/111-core-one-clearing-section-per-message.md`
   - Status: Decision needed (I; recommended I1).
   - Blocked by: decision I.
   - Overlaps: `gates.py` with 110; hold-text tests with 112.
   - Enables: several holds on one call saying once how to clear them.
7. `tickets/112-core-scripted-edit-names-unknown-kinds.md`
   - Status: Decision needed (J; recommended J1).
   - Blocked by: decision J.
   - Overlaps: hold-text tests with 111.
   - Enables: the `scripted-edit` hold no longer calling a docs file code.
8. `tickets/113-core-design-reads-sized-by-substance.md`
   - Status: Decision needed (K1 and K2; recommended K1.1 and K2.1).
   - Blocked by: decisions K1 and K2; `114` (ordering, the same contract
     rows).
   - Overlaps: `reference_reads.py` with 115.
   - Enables: a short code edit with a comment, and new cases in an
     existing test, asking for no design read their size alone selected.

Only 110 touches `shell.py`, and not its pull request reading, which
Tickets 108 and 109 are changing. No round 5 ticket touches that reading.

Decision Q, the `true` carrier call (item 12), has no ticket: the
recommended option keeps it.

## Ready Frontier

None until the maintainer decides H to P. Each ticket joins the
frontier when its decision is recorded; 113 and 116 once 114 has also
merged.

## Coverage

- AC1 (whole shell prints orient) → 110
- AC2 (design reads sized by substance) → 113
- AC3 (one clearing section) → 111
- AC4 (`scripted-edit` wording) → 112
- AC7 (large writes land) → 114
- AC8 (mocking pattern) → 115
- AC9 (Proof after comment-only edits) → 116
- AC10 (Proof while a check runs; waiting on the user) → 116
- AC11 (`continue` in a briefed task) → 117
- AC5 (contract and scenarios) → every ticket
- AC6 (repo checks) → every ticket
