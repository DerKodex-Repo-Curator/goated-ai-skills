# Ticket 114: Large Writes Land And Read After

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-5.md` (R5; AC7, AC5, AC6)

## Type

HITL until decision L is recorded in the parent spec; AFK after. Written
to the recommended option, L1. If the maintainer picks L2 or L3, rewrite
the outcome before starting; L4 closes this ticket.

## What To Build

A large write is never composed twice because a read gate held it. The
read gates, `design`, `design-reads` and `reference-reads`, hold a file or
shell write only when it adds fewer than thirty lines, counted as each
gate counts them today. A write adding thirty or more, or one whose lines
cannot be counted, is applied and passes with a notice naming what it
needs: the skill load and each reference its signals select.

What a landed write still needs becomes a new closeout item, `Reads`. It
is met when the skill counts as loaded, each named reference is read
whole or a lasting skip covers it, and a change read of the file follows
the reads. It holds a commit and the turn's end as the other items do.
Its skip line names the skill whose references it asks for; a skip of it
lasts as a skip of the gate it stands for does (round 4's R4). A write
under thirty lines is held as today.

The rules live in the shared core at `adapters/core/goated_core/`: where
`actions.py` judges a write against `_design_hold` and
`_reference_reads_hold`, `_closeout_items`, and session state for what
landed writes still need. The contract changes with the code, as
`AGENTS.md` requires: the `design`, `design-reads` and `reference-reads`
rows, the Closeout Items table (a new stable label), Hold Messages if
they list labels; the event model only if it enumerates closeout labels;
and conformance scenarios under `stack/fixtures/enforcement/` (a test
fails when a closeout item lacks scenarios).

**`shell.py`'s pull request reading:** not touched.

## Recommended First Reads

- The parent spec, R5 and decision L.
- `stack/enforcement-contract.md`: the three gate rows, Holds, Closeout
  Items, and how lasting skips work.
- The core's `actions.py` (`_design_hold`, `_reference_reads_hold`,
  `_design_need`, `_closeout_items`) and `state.py` (`lasting_skips`).
- `tests/test_enforcement_contract.py`, for what a new closeout item needs.
- `tickets/archive/101-core-read-skips-last-the-task.md`, lasting skips.

## Acceptance Criteria

- [ ] With `software-design-principles` loaded, a 40-line edit whose
      signals select an unread reference is applied, with a notice naming
      the reference.
- [ ] The turn's end and a commit then meet the `Reads` item until the
      reference is read whole and a change read of the file follows; a
      skip line naming the skill clears it.
- [ ] The same holds for a large write meeting `design` (skill not
      loaded) and `reference-reads` (a registry signal).
- [ ] A 29-line edit is held as today.
- [ ] The contract states the rule and the new item, and conformance
      scenarios cover the hold, the landed write, each way the item
      clears, and the near miss.
- [ ] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The core's gate and closeout tests; the Claude Code adapter's tests
  through its hook.
- The repo checks in `AGENTS.md`.

## Blocked By

- Decision L in the parent spec.

## Overlaps

- Ticket 113 changes the same contract rows; it waits for this one.
- Ticket 116 changes `_closeout_items`; it waits for this one.
- Ticket 111 changes how holds share a message, not which hold fires.

## Scope Exclusions

- Announcing references before a write (option L2).
- Strict gates (`pipeline`, `commit`, `security`), which still hold.
- `scripted-edit`, whose script is short and steered to a file edit tool.
