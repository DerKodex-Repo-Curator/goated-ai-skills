# Ticket 111: One Clearing Section Per Message

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-5.md` (R3; AC3, AC5, AC6)

## Type

AFK. Decision I, option 1 (the maintainer, 2026-11-18).

## What To Build

When one message carries two or more holds that a route or skip line can
clear, the message says once how to clear them:

- each hold keeps its own text and the line it asks for (its skip or
  route line), and every skill, reference and line it names;
- each hold drops its own placement sentence (the full or short
  unseen-line advice);
- the message ends with one clearing section: where a line goes (the full
  advice when the turn has not had it yet, else one sentence) and each
  hold's typed override, listed once;
- the carrier slot, when the call has no field for a line, stays last.

A message with one such hold is unchanged. Hold first lines
(`goated-hold: <gate> | <kind>`) and their firing order do not change.

The rule lives in the shared core at `adapters/core/goated_core/`:
`gates.shown_holds` and the advice slots in `wording.py`. If the section
needs a new slot, the Claude Code adapter's `translation.py` fills it, and
its generated texts are regenerated. The contract's Hold Messages ("When a
decision carries several holds") and a conformance scenario change with
the code, as `AGENTS.md` requires.

**`shell.py`'s pull request reading:** not touched.

## Recommended First Reads

- The parent spec, R3 and decision I.
- `stack/enforcement-contract.md`, Hold Messages.
- The core's `gates.py` (`shown_holds`, `_full_advice`, `_SHARED_TEXTS`,
  `_once`) and `wording.py` (`unseen_line_advice`, `short_advice`, the
  slot names).
- The Claude Code adapter's `translation.py` (how it fills the advice
  slots).
- `tickets/archive/095-adapter-joint-holds-in-one-message.md`, which joined
  holds into one message.

## Acceptance Criteria

- [ ] A call meeting three holds that lines can clear (for example
      `design-reads`, `reference-reads` and `scripted-edit`) shows each
      hold's skip line once, in its hold, and one clearing section after
      the last hold that names each override once.
- [ ] The section carries the full placement advice on the turn's first
      such message and one sentence on later ones.
- [ ] A call meeting one such hold shows today's text.
- [ ] A strict hold that no line clears is unchanged.
- [ ] The contract states the message shape, and a conformance scenario
      covers a joint message and a single hold.
- [ ] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The core's message tests and the Claude Code adapter's translation tests.
- The repo checks in `AGENTS.md`.

## Blocked By

- None.

## Overlaps

- `gates.py` with Ticket 110 (orientation, another function).
- Hold-text tests and fixtures with Ticket 112, whose `scripted-edit`
  hold carries the advice slot; land either first and rebase the other.

## Scope Exclusions

- Changing what any hold asks for.
- The carrier call itself (feedback item 12).
- Closeout item texts.
