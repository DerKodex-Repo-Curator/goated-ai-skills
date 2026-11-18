# Hook Friction Round 5 Delivery Order

Source spec: `docs/specs/2026-11-18-hook-friction-round-5.md`

Parallel waves, with the other rounds' open tickets:
[hook-friction-round-3-waves.md](hook-friction-round-3-waves.md)

Every ticket waits for the maintainer's decision on its options (H to K
in the spec). Each is written to the recommended option. None waits for
another round 5 ticket, so all four can run at once once decided.

1. `tickets/110-core-whole-shell-prints-orient.md`
   - Status: Decision needed (H; recommended H1).
   - Blocked by: decision H.
   - Overlaps: `shell.py` with 108 and 109 (their pull request reading,
     another part); `gates.py` with 111 (another function).
   - Enables: a session that oriented with `cat` not held for orientation.
2. `tickets/111-core-one-clearing-section-per-message.md`
   - Status: Decision needed (I; recommended I1).
   - Blocked by: decision I.
   - Overlaps: `gates.py` with 110; hold-text tests with 112.
   - Enables: several holds on one call saying once how to clear them.
3. `tickets/112-core-scripted-edit-names-unknown-kinds.md`
   - Status: Decision needed (J; recommended J1).
   - Blocked by: decision J.
   - Overlaps: hold-text tests with 111.
   - Enables: the `scripted-edit` hold no longer calling a docs file code.
4. `tickets/113-core-design-reads-sized-by-substance.md`
   - Status: Decision needed (K1 and K2; recommended K1.1 and K2.1).
   - Blocked by: decisions K1 and K2.
   - Overlaps: none in code with 110 to 112.
   - Enables: a short code edit with a comment, and new cases in an
     existing test, asking for no design read their size alone selected.

Only 110 touches `shell.py`, and not its pull request reading, which
Tickets 108 and 109 are changing.

## Ready Frontier

None until the maintainer decides H, I, J and K. Each ticket joins the
frontier when its decision is recorded.

## Coverage

- AC1 (whole shell prints orient) → 110
- AC2 (design reads sized by substance) → 113
- AC3 (one clearing section) → 111
- AC4 (`scripted-edit` wording) → 112
- AC5 (contract and scenarios) → every ticket
- AC6 (repo checks) → every ticket
