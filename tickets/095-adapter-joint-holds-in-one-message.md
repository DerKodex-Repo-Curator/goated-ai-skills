# Ticket 095: Every Hold A Call Would Meet Arrives In One Message

## Parent Spec

`docs/specs/2026-11-17-adapter-hold-delivery-and-coverage.md` (R1, R2, R3,
R4, R9; AC1 to AC6, AC13, AC14, AC15)

## Type

AFK.

## Problem

The adapter judges routing first, then the action gates in a fixed
order, and stops at the first hold. A call that would meet three holds is
held three times, and the agent resends its payload each time: a 220-line
file was sent three times, and a subagent brief three times.

The text repeats as well. Tickets 060 and 062 made the unseen-line advice
appear once per turn, but other shared paragraphs still appear in every
hold and every closeout item, and a repeated `Stop` hold prints the whole
list again. A typical hold is 180 to 240 words.

A hold that a skip line can clear, on an edit call, tells the agent to
put the line in another call but names none that is certain to pass.

## What To Build

- **Judge every gate.** A call is judged against every routing and action
  gate, not only until the first hold. A gate judged after an earlier
  hold gives the answer it would give alone. A call no gate holds today
  is not held.
- **One message.** When more than one gate would hold the call, the
  message carries each in the order they fire today: the first hold as
  today, then each further hold with its own
  `goated-hold: <gate> | <kind>` line and its text. Each hold keeps its
  kind and its own way to clear. The hook's decision still names the
  first hold.
- **What may still follow.** A hold that can be judged only once another
  clears may arrive on the retry, such as the closeout at a commit the
  `commit` gate still holds. Name each such pair in the README.
- **The mod counts each.** The skill-usage mod reads every `goated-hold:`
  line in a message and records each hold with its own outcome, as if it
  had been shown alone.
- **Shared text once per message.** A paragraph several holds or closeout
  items share appears once in a message: the change-read explanation, the
  chained-command sentence, the skip-line sentence and the unseen-line
  advice.
- **Short repeats per turn.** A second or later hold by the same gate in
  a turn carries a short form naming what is still unmet and how to clear
  it; the repeated `Stop` closeout lists only its unmet items that way.
  Use the turn marker of Ticket 062. When it cannot be claimed or read,
  the full text is used.
- **A named carrier.** A hold that a line can clear, on a call with no
  line field, names one carrier: a shell call whose command is `true` and
  whose description holds the line. Confirm that call passes every hold,
  before and after the router loads (Ticket 088 makes `true` a plain
  read).
- Update the README's Hold messages, What It Holds ("No free retry") and
  Latency sections, the mod's README, and regenerate the hold texts.

## Recommended First Reads

- The parent spec: Problem, R1 to R4, Constraints.
- `adapters/claude-code/goated_adapter/hooks.py`: `_pre_tool_use`,
  `_stop`, `_deny`, and where `advice_once` is applied.
- `adapters/claude-code/goated_adapter/actions.py`: `check_action`,
  `_closeout_hold`, `CHANGE_READ` and the other shared texts.
- `adapters/claude-code/goated_adapter/gates.py`: `check_routing`, `Hold`,
  `unseen_line_advice`, `advice_once`; `state.py`: the turn marker.
- `adapters/claude-code/skill-usage/hooks/holds.ts` and `classify.ts`,
  and `tests/adapter-texts.ts`, for how the mod reads a hold.
- `adapters/claude-code/README.md`: Hold messages, Latency.
- Tickets 060 and 062.

## Acceptance Criteria

- [ ] A test edit that would meet `design-reads`, `reference-reads` and
      `repeated-failure` is held once, by a message carrying three
      `goated-hold:` lines in today's order. Clearing all three lets the
      retry pass.
- [ ] A spawn that would meet `pipeline` and `spawn` is held once, with
      both.
- [ ] A call that meets one gate gets the message it gets today.
- [ ] A joint message whose holds share the unseen-line advice or the
      change-read explanation carries each once.
- [ ] The mod counts three holds for the first message above, and records
      one as declined and two as followed when one is skipped and two are
      obeyed.
- [ ] A second `Stop` hold in a turn lists only the unmet items, in the
      short form. The first hold of the next turn is full again. With the
      marker unwritable, each hold is full.
- [ ] A hold on an `Edit` call that a skip line can clear names the
      `true` carrier, and that call passes before and after the router
      loads.
- [ ] Hold first lines are unchanged.
- [ ] The adapter's measured latency stays within the README's budget
      with every gate judged.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The mod's tests, with the regenerated texts.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- The README's latency measurement, rerun.
- A live check: one real session that meets a joint hold and clears it
  in one retry.

## Blocked By

- `tickets/086-adapter-repeated-failure-red-runs.md`
- `tickets/087-adapter-routing-orientation-by-reads-and-outside-writes.md`
- `tickets/088-adapter-wider-plain-reads.md`
- `tickets/089-adapter-design-holds-without-written-text.md`
- `tickets/091-adapter-review-size-and-installs.md`
- `tickets/093-adapter-inline-script-writes.md`

Each changes a gate, or adds one, in the dispatch this ticket
restructures. Ticket 088 makes `true` a plain read, which the carrier
criterion needs.

## Scope Exclusions

- What any gate requires or what clears it.
- A combined first line naming several gates.
- A line field on edit calls.
- The early closeout note (Ticket 096).
