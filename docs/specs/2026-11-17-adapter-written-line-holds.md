# Adapter Holds That Check Written Text

## Status

Decisions approved by the maintainer on 2026-11-17 in a grill-with-docs
session. Ticket ready. Builds on
[the hook friction spec](2026-11-17-adapter-hook-friction.md),
[the design reference reads spec](2026-11-16-design-reference-reads.md) and
[ADR 0003](../adr/0003-opt-in-framework-enforcement-adapters.md).

## Mode

Compact.

## Problem

The two agents that implemented Tickets 059 and 060 reported how the Claude
Code adapter's holds worked for them. They agreed on one pattern:

- A hold that asks for an action, such as loading a skill or reading the
  change, was cheap and kept them on the workflow.
- A hold that checks whether something was written, such as a line or a
  citation, caused most of the friction, because the adapter often cannot
  see what was written.

Each claim was checked against the adapter on main at `ca7e8b6`. These are
the confirmed sources of friction:

- **Citations at commit.** The closeout's Design citations item reads
  citations only from reply text. Before a commit, every message of the turn
  also makes a tool call, and Claude Code can store such a message's text as
  a summary. The Ticket 060 session's transcript shows it: the message that
  cited the references is stored as "Before committing, I've cited the design
  docs…", with no `file#id` in it. The agent then put the citations in the
  commit call's `description`, which the adapter does not read for
  citations, and the hold does not say so. It cleared the hold with a skip
  line. The hold also says "in your report", though at commit the report is
  not written yet.
- **Parallel holds.** Ticket 060 reads "the advice was already given" from
  the turn's earlier held results. Calls held in parallel have no result
  yet, so four parallel edits carried four copies of the full advice.
- **Reloads.** A skill load counts only in its own turn, for action and
  closeout holds, or its own task, for a route's `requires:` skills. Agents
  reload skills whose text is still in context, at about 10,000 to 15,000
  tokens a session. Design references already count until the next
  compaction.
- **Design-reads triggers.** Any edit of a test file selects `coding.md`,
  whatever its size, so a one-line fix of an escaped `\n` in a test was held
  for a reference read and later needed a citation.
- **Red flags.** The Design red-flags item is met by reading a file and the
  diff. Nothing in it prompts a concrete finding. An adversarial reviewer,
  not a hold, caught Ticket 059's high-severity bug.
- **Proposal cards.** A `start_session` call that only shows a proposal or
  offer card runs nothing until the user starts it, but it is held as a
  spawn by `router-first`, `route-line` and `pipeline`.
- **Restores.** Proof asks for a rerun after `git checkout -- <file>`
  restored files whose content was unchanged. The adapter reads commands,
  not file contents, so it cannot tell.

## Goals

- A citation the agent writes where the adapter can read it clears the
  Design citations item on the next attempt, and the hold says where that
  is.
- A turn carries the full unseen-line advice at most once, parallel holds
  included.
- A skill or template whose text is still in context is not asked for again.
- A small edit is not held for a reference chosen only by the kind of file.
- The red-flags step asks for one concrete finding without adding a check.
- A card that runs nothing meets no routing hold.

## Non-Goals

- Changing what the kept holds require. Both agents valued TDD's
  watch-it-fail rule, change reads, route lines in a brief (Ticket 056), and
  lines read from call fields (Ticket 053).
- Checking any new written text. No hold added here reads an answer the
  agent wrote.
- Judging the quality of a citation (Ticket 052's exclusion).
- Telling whether a restore left a file's content unchanged.
- Changing hold first lines (`goated-hold: <gate> | <kind>`).
- Skill loads inside a subagent, which still count only in the subagent's
  current turn.
- The wider question of which skills and references no hold reaches. A
  second spec covers it.

## Requirements

- **R1, citations from call fields.** The Design citations item counts a
  citation in the call fields that carry route and skip lines
  (`LINE_FIELDS`: the `description` of a shell or agent call and the `args`
  of a Skill call), in any call of the turn, the held commit call included.
  Reply text still counts. The item's text names those fields, and at commit
  it no longer says "in your report".
- **R2, advice once per turn.** At most one hold in a turn carries the full
  unseen-line advice, including holds on calls made in parallel. The first
  hold claims a per-turn marker atomically; every other hold in that turn
  carries the one-sentence form. This replaces Ticket 060's read from held
  results. When the marker cannot be claimed or read, the hold carries the
  full advice.
- **R3, loads until compaction.** A successful skill load counts from its
  call until the next compaction or `/clear`, in this turn or a later one,
  for every hold that asks for a load: a route's `requires:` skills
  (`pipeline`), the action gates, and the closeout items. The saved state
  keeps the loaded names, as it keeps design references read. A resumed
  session keeps them, and missing state counts as not loaded.
  - Lines stay per turn: route, skip and design-reads lines, and typed
    overrides.
  - Checks tied to a change stay as they are: change reads, the red-flags
    read after the last change, and Proof.
  - The closeout's Design items apply in a turn that loaded
    `software-design-principles`, as today, or that made an edit the
    `design` gate triggers on while the skill counts as loaded. A turn of
    small edits in a later turn still meets no Design item.
- **R4, template reads until compaction.** The reads the `spawn` gate asks
  for (`handoff`'s `references/spawn-brief.md`, and the implementer or
  reviewer prompt of `subagent-driven-development`) count until the next
  compaction, like the loads. The brief's content check still runs on every
  spawn.
- **R5, small edits.** An edit that adds fewer than five lines, the `design`
  gate's own threshold, selects no reference for the kind of file or text it
  touches: a test file (`coding.md`), a configuration file or the third code
  file (`decoupling.md`), or an added comment (`readability.md`). Signals
  read from the added code still apply at any size: a new file or public
  definition, error handling, and concurrency. A design-reads line still
  requires what it names.
- **R6, a question at the red flags.** `red-flags.md` ends with one
  question: name one input that would break this change, and say what
  happens. The closeout's Design red-flags item repeats it. The adapter
  checks no answer.
- **R7, cards.** A `start_session` call whose `initiation` is `offer` or
  `own_initiative`, and that has no `proposal_id`, the field that starts a
  saved proposal, passes `router-first`, `route-line` and `pipeline`. An
  `own_initiative` card always carries a brief, so it still meets `spawn`,
  since that brief runs when the user starts the card; an `offer` card
  carries none. Any other `initiation`, or none, is held as today.
- **R8, restores.** Known Limits says that a restore command counts as a
  change whatever it restores, so Proof asks for a check after it, and that
  a rerun or a skip line answers it.
- **R9, documentation.** The adapter README's What It Holds, Design
  references, Hold messages and Known Limits sections match the behaviour.
  Changed hold texts are regenerated for the skill-usage mod, the mod's
  README matches what a hold now asks for, and the mod still counts every
  hold it showed before.

## Acceptance Criteria

- [ ] AC1: A commit held for an uncited reference passes when retried with
      a `file#id` citation of that reference in its `description`. A
      citation in an earlier call's `description` or a Skill call's `args`
      counts too. A citation in a command, an edit's text or an MCP tool's
      `description` does not.
- [ ] AC2: The citations item names the call fields, and its commit-time
      text does not say "in your report".
- [ ] AC3: Of four calls held in parallel in one turn, exactly one carries
      the full advice. The first such hold of the next turn carries it
      again. With the marker unwritable, each hold carries the full text.
- [ ] AC4: A skill loaded in one turn meets `pipeline`, `commit`, `design`
      and the Docs item in a later turn with no new load. After a
      compaction each asks for the load again.
- [ ] AC5: A skip line or typed override from an earlier turn clears nothing
      in a later one.
- [ ] AC6: In a later turn, a four-line code edit with the design skill
      still counted as loaded raises no Design closeout item. A twenty-line
      non-test edit does.
- [ ] AC7: A spawn in a later turn passes with the template read in an
      earlier turn, and is still held when its brief fails the content
      check.
- [ ] AC8: A one-line edit of a test file requires no reference. A
      twenty-line test edit requires `coding.md`. A one-line edit adding
      `except` still requires `errors.md`.
- [ ] AC9: `red-flags.md` and the Design red-flags item carry the question,
      and no hold depends on an answer.
- [ ] AC10: Before the router loads, an `own_initiative` card with a brief
      passes `router-first`, `route-line` and `pipeline` and is held by
      `spawn`. An `offer` card with no brief passes every hold. A
      `user_asked` start, and a start of a saved proposal, are held as
      today.
- [ ] AC11: Known Limits names the restore case.
- [ ] AC12: The kept holds behave as before. Existing tests pass unchanged
      except where a test asserted friction this spec removes, and each such
      change is named in its ticket's closeout.
- [ ] AC13: The repo checks in `AGENTS.md` pass on Python 3.11 and 3.14. The
      mod's tests pass, and hold first lines are unchanged.

## Proof Surface

The adapter's hook entry points (`goated_hook.py` through
`tests/claude_code_adapter_support.py`), driven by transcript fixtures, plus
the mod's test suite for regenerated hold texts and the repo's skill
validators for `red-flags.md`. A live check in one real session confirms R1
and R3.

## Constraints

- ADR 0003 has adapters enforce portable contracts, not define them. The
  small-edit rule (R5) and the question (R6) are stated in
  `software-design-principles`. The rules on how long a load or a template
  read counts (R3, R4), where a citation may be written (R1), the advice
  (R2) and cards (R7) are adapter mechanics stated in its README; Ticket
  079's enforcement contract
  ([portable enforcement spec](2026-11-17-portable-enforcement-core.md))
  restates them in harness-neutral words.
- Every change fails toward holding when the adapter cannot tell. Missing
  state means not loaded, an unknown `initiation` is a spawn, and an edit
  whose size cannot be read is not small.
- The adapter and the mod keep their shared tables in step (`LINE_FIELDS`,
  hold texts).
- `red-flags.md` gains no new section id unless the skill's Section Index
  gains it too, and the skill stays inside its context budget
  (`scripts/compare_v1_v2_context.py`).
- Tickets edit overlapping adapter files, so the order file sequences them
  by function overlap.

## Open Questions

None.

## Risks

- R3 lets a skill loaded many turns ago answer a hold, when the agent may no
  longer follow it closely. This is mitigated because a compaction, the
  point where the text really leaves context, still clears every load, and
  because the checks tied to a change are unchanged.
- R5 lets a small edit of a test or configuration file pass with no
  reference. This is mitigated because signals read from the added code
  still apply at any size.
- R6 can be ignored, since nothing checks it. That is the chosen trade:
  the agents' reports say a checked answer would cost more than it finds.
- R7 lets a card through routing with a brief no route covered. This is
  mitigated because the `spawn` gate still checks that brief.

## Sources

- `adapters/claude-code/goated_adapter/actions.py`: `_uncited_references`,
  `_code_items`, `_Proof`, `check_action`, `SPAWN_BRIEF_FIELDS` (R1, R3, R4,
  R6).
- `adapters/claude-code/goated_adapter/gates.py`: `unseen_line_advice`,
  `check_routing`, `fold_turns` (R2, R3, R7).
- `adapters/claude-code/goated_adapter/design_reads.py`: `_signals` (R5).
- `adapters/claude-code/goated_adapter/transcript.py`: `LINE_FIELDS`,
  `call_line_text` (R1).
- `adapters/claude-code/goated_adapter/state.py`: `SessionState` (R2, R3,
  R4).
- `adapters/claude-code/README.md`: What It Holds, Design references, Hold
  messages, Known Limits.
- `skills/engineering/software-design-principles/references/red-flags.md`
  (R6).
- Tickets 052, 053, 056, 059 and 060.
