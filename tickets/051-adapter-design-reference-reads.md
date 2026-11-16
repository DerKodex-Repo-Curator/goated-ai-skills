# Ticket 051: Adapter Holds Edits Until Their Design References Are Read

## Parent Spec

`docs/specs/2026-11-16-design-reference-reads.md` (R5; AC5, AC6, and AC8's
hold part)

## Type

AFK.

## Problem

The `design` hold clears on a skill load alone, and nothing makes the agent
read any reference before or while it writes. Real use shows agents do not
read the eight theme references unless forced, and that a read alone does not
mean the instructions are followed.

## What To Build

- **Required set.** For a code change, the required references are those named
  in the turn's `goated-design-reads:` line (portable contract from Ticket 048)
  plus those the adapter detects by the signals in the spec's R5 table. Keep
  the signal rules in one place, documented in the README.
- **Pre-edit.** The `design` hold also needs a design-reads line in the turn
  and a read of every required reference. A `none: <reason>` line with no
  detected references clears it.
- **Mid-turn.** A new `design-reads` gate, `justified-skip`, holds a later code
  edit whose signals require a reference not yet read. The hold text names the
  file and the signal that selected it.
- **Cooldown.** A reference read counts until the next compaction, using the
  compaction handling from Ticket 046; after it, the reference is required
  again.
- Skip lines and overrides clear these holds as they clear `design`. Files
  outside the project are treated as in the `design` gate.
- Teach the skill-usage mod the `design-reads` gate name and its outcomes.
- Update the README's gate tables and hold texts.

## Recommended First Reads

- The parent spec, R5 and Risks.
- `adapters/claude-code/README.md`: What It Holds, change reads.
- `adapters/claude-code/goated_adapter/actions.py` (`_design_hold`, `_Proof`,
  `added_lines`, `TEST_PATH_RE`) and the compaction handling Ticket 046 left.
- The `software-design-principles` `SKILL.md` as Ticket 048 left it.
- `tests/test_claude_code_adapter_actions.py`.

## Acceptance Criteria

- [ ] A first substantial edit with no design-reads line is held; with the line
      but an unread required reference, it is held naming that file; with both,
      it passes.
- [ ] Each R5 signal selects its reference, and a near miss does not.
- [ ] A later edit tripping a signal for an unread reference is held by
      `design-reads`; one tripping none, or only references already read, is
      not.
- [ ] A reference read before a compaction is required again after it, and not
      before it.
- [ ] A skip line or an override clears both holds; files outside the project
      are not held.
- [ ] The mod names `design-reads` holds and records their outcomes.

## Expected Proof

- Adapter tests for each criterion and its near miss; mod tests for the gate
  name.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- A live check in one real session: the holds fire and clear as the README
  says.

## Blocked By

- `tickets/046-adapter-pipeline-after-compaction.md` (same files; compaction
  handling)
- `tickets/048-design-reference-moment-triggers.md` (the portable contract)
- `tickets/050-skill-usage-reference-read-timing.md` (same mod files)

## Scope Exclusions

- Closeout citations (Ticket 052).
- Changing the closeout's `red-flags.md` read or change read.
- Signals beyond the spec's table.
