# Ticket 096: A Turn Learns Its Closeout Items Before Its Report

## Parent Spec

`docs/specs/2026-11-17-adapter-hold-delivery-and-coverage.md` (R8, R9;
AC12, AC13, AC14, AC15)

## Type

AFK.

## Problem

The closeout fires at a commit, or at the end of the turn. In a turn that
changes code and does not commit, it fires after the agent has written
its final report, so the agent meets the items and reports a second time.

Every item is judged from the turn's calls, so each can be met before the
report: a check run, a `doc-sync` load and a diff read, the red-flags
read. The agent only has to know what will be asked.

## What To Build

- **The note.** After the first finished code change of a turn, the
  adapter adds one short note, as context for the agent, naming the
  closeout items the turn will meet as far as it can tell then, and
  saying they can be met before the report. For example: Proof and Docs
  for a non-test code change; the Design red-flags item when
  `software-design-principles` counts as loaded and the edit is
  substantial; Verification on a `full` route.
- **Once per turn.** One note per turn and agent, claimed with the turn
  marker under a purpose key of its own. Ticket 095 gives the marker
  purpose keys; the note's key is separate from the advice's and from
  each gate's, so claiming one never fails or erases another. A turn that
  already met a closeout hold gets no note. A failed claim, or a marker
  that cannot be read, adds no note.
- **Never blocks.** The note holds no call and no `Stop`. If the adapter
  cannot tell an item yet, the note leaves it out; the closeout itself
  is unchanged and still decides.
- **The hook.** The note is delivered by a hook that runs after a call
  (`PostToolUse`). It reads the call that triggered it from the hook's
  own payload (`tool_name`, `tool_input`, `tool_response`), not from the
  transcript, which may not hold the call yet. The transcript and the
  state are read only for what the payload cannot say, such as whether
  a skill counts as loaded.
- **A matcher, for latency.** The install snippet registers the hook
  with a matcher limited to the write tools (`Edit`, `Write`,
  `MultiEdit`, `NotebookEdit`), so no other call starts a hook process.
  A code change made by a shell command therefore brings no note; say so
  in the README. The closeout still judges it.
- **Install.** The install snippet and the shell-form alternative gain
  the event, and the README's Install section says an existing install
  must add it to get the note; without it nothing else changes. The hook
  follows the adapter's failure rule.
- **No note in a subagent**, which has no closeout.
- Update the README's Install, What It Holds (the closeout), Session
  Start Notices or a section beside it, Latency and Known Limits.

## Recommended First Reads

- The parent spec: Problem, R8, Constraints, Risks.
- `adapters/claude-code/goated_adapter/hooks.py`: `run_hook`, how the
  existing notices are returned, `_pre_tool_use` and `_stop`.
- `adapters/claude-code/goated_adapter/actions.py`: `_closeout_hold`,
  `_code_items`, `_changes`, for what makes each item apply.
- `adapters/claude-code/goated_adapter/state.py`: `claim_turn` and
  `_drop_markers`, the turn marker as Ticket 095 leaves it.
- `adapters/claude-code/settings.snippet.json` and the README's Install
  and Latency sections.
- `tickets/073-notices-for-retrospective-and-onboarding.md`, for how a
  notice that never blocks was built.
- Claude Code's current hook documentation, for the event that runs after
  a tool call and how it adds context.

## Acceptance Criteria

- [ ] A turn's first finished edit of a non-test code file inside the
      project brings one note naming Proof and Docs.
- [ ] With `software-design-principles` loaded and a substantial edit,
      the note also names the Design red-flags item.
- [ ] A second code change in the turn brings no note. The first code
      change of the next turn brings one.
- [ ] An edit of a docs file, a held edit, a failed edit, an edit outside
      the project, and a code change by a shell command bring none.
- [ ] The note is right when the transcript does not yet hold the
      triggering call: it is judged from the hook's payload.
- [ ] In one turn that carries the full unseen-line advice, a short
      repeat of one gate's hold, and the first code change: the advice is
      full once, the repeat is short, and the note appears once. No claim
      fails or erases another.
- [ ] With the marker unwritable, no note is added and nothing is held.
- [ ] A turn whose items are all met before `Stop` ends with no closeout
      hold.
- [ ] No call or `Stop` is blocked by the note, and a failure in the new
      hook follows the failure rule.
- [ ] A subagent's edit brings no note.
- [ ] With the event missing from the settings, every other behaviour is
      as before.
- [ ] The adapter's measured latency stays within the README's budget,
      the new hook included.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, and the mod's
  tests.
- The README's latency measurement, rerun.
- A live check: one real session that changes code without committing,
  meets the named items and ends its turn with one report.

## Blocked By

- `tickets/095-adapter-joint-holds-in-one-message.md` (settles the
  closeout's texts, the turn marker's use and the hook dispatch this
  ticket adds to).

## Scope Exclusions

- Changing when the closeout fires or what it requires.
- A note for holds other than the closeout.
- Installing or migrating settings for the user.
