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
  When the marker cannot be claimed or read, the full text is used.
- **The turn marker gains a purpose.** Ticket 062's marker cannot be
  reused as written: `state.claim_turn` keeps one marker per owner and
  turn, and `_drop_markers` deletes the owner's other markers, so a second
  kind of claim in a turn would fail or erase the first. The marker gains
  a purpose key, such as the advice or a gate's name. A claim is exclusive
  per owner, turn and purpose. Markers are dropped only across turns,
  never across purposes within a turn. Ticket 096 adds a purpose of its
  own on top of this.
- **A named carrier per shell.** A hold that a line can clear, on a call
  with no line field, names one carrier for the shell the session has: a
  shell call whose description holds the line and whose command is `true`
  in Bash or `$null` in PowerShell (`true` is not a command there). Both
  are plain reads and pass every hold, before and after the router loads.
  Ticket 088 makes `true` a plain read; add `$null` as one here.
- Update the README's Hold messages, What It Holds ("No free retry") and
  Latency sections, the mod's README, and regenerate the hold texts.

## Recommended First Reads

- The parent spec: Problem, R1 to R4, Constraints.
- `adapters/claude-code/goated_adapter/hooks.py`: `_pre_tool_use`,
  `_stop`, `_deny`, and where `advice_once` is applied.
- `adapters/claude-code/goated_adapter/actions.py`: `check_action`,
  `_closeout_hold`, `CHANGE_READ` and the other shared texts.
- `adapters/claude-code/goated_adapter/gates.py`: `check_routing`, `Hold`,
  `unseen_line_advice`, `advice_once`; `state.py`: `claim_turn` and
  `_drop_markers`, the turn marker.
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
- [ ] In one turn, a hold carrying the full unseen-line advice, then two
      holds by one gate, then two by another: the advice is full once,
      and each gate's second hold is short. Neither claim erases the
      other, and the next turn starts with every form full again.
- [ ] A hold on an `Edit` call that a skip line can clear names the
      carrier: `true` in a session whose shell tool is Bash, `$null` in
      one whose shell tool is PowerShell. A Bash call of `true` and a
      PowerShell call of `$null` each pass before and after the router
      loads, and carry the line.
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
- `tickets/090-adapter-test-edit-reference-thresholds.md`
- `tickets/091-adapter-review-size-and-installs.md`
- `tickets/092-adapter-whole-reads-and-read-order.md`
- `tickets/093-adapter-inline-script-writes.md`
- `tickets/094-adapter-own-subagent-reports-continue-the-turn.md`
- `tickets/097-adapter-script-write-paths-by-name-and-folder.md`

Each changes a gate, a hold's text or the turn's boundaries, or adds a
gate, in the dispatch and message assembly this ticket restructures.
Ticket 088 makes `true` a plain read, which the carrier criterion needs.
Ticket 094 changes which prompts open a turn, which decides when the
turn marker resets.

## Scope Exclusions

- What any gate requires or what clears it.
- A combined first line naming several gates.
- A line field on edit calls.
- The early closeout note (Ticket 096).
