# Ticket 065: A Skill Load Counts Until The Next Compaction

## Parent Spec

`docs/specs/2026-11-17-adapter-written-line-holds.md` (R3, R4, R9; AC4, AC5,
AC6, AC7)

## Type

AFK.

## Problem

A skill load counts only in its own turn, for the action gates and the
closeout, or in its own task, for a route's `requires:` skills. In a
session of several turns an agent reloads skills whose text is still in its
context, at about 10,000 to 15,000 tokens a session. Design references
already count until the next compaction, which is the point where text
really leaves the context.

## What To Build

- **Loads.** A successful skill load counts from its call until the next
  compaction or `/clear`, in this turn or a later one, for every hold that
  asks for a load: `pipeline`, `commit`, `pull-request`, `pr-review`,
  `spawn`, `design`, `design-reads`, `security`, `conflict-resolution`,
  `repeated-failure`, and the closeout's items. A skill the user invoked by
  typing `/<skill>` counts the same way.
- **Template reads.** The reads the `spawn` gate asks for (`handoff`'s
  `references/spawn-brief.md`, and the implementer or reviewer prompt of
  `subagent-driven-development`) count the same way. The brief's content
  check still runs on every spawn.
- **State.** The saved state keeps the loaded skill names and template
  reads, as it keeps design references read. A resumed session keeps them.
  A compaction's or `/clear`'s `SessionStart` clears them. Missing or reset
  state counts as not loaded.
- **What stays per turn.** Route, skip and design-reads lines, and typed
  overrides. Checks tied to a change: change reads, the red-flags read
  after the last change, and Proof.
- **Design closeout.** The Design red-flags and citations items apply in a
  turn that loaded `software-design-principles`, as today, or that made an
  edit the `design` gate triggers on while the skill counts as loaded. A
  later turn of small edits meets no Design item.
- **Security closeout.** The Security item applies when the skill counts as
  loaded and the turn changed a security-sensitive file.
- **Subagents.** Unchanged: inside a subagent only its current turn counts.
- **Texts.** Hold texts stop saying a load in an earlier turn does not
  count. Update the README (What It Holds, the gate table, Design
  references, Hold messages, State, Known Limits) and the mod's README
  where it says a hold asks for a load in the current turn. Regenerate
  `adapters/claude-code/skill-usage/tests/adapter-texts.ts`.

## Recommended First Reads

- The parent spec, R3 and R4.
- `adapters/claude-code/goated_adapter/state.py` (`SessionState`,
  `reference_reads`, and how a compaction clears state).
- `adapters/claude-code/goated_adapter/gates.py` (`fold_turns`,
  `_task_started_in`, `check_routing`).
- `adapters/claude-code/goated_adapter/actions.py` (`_Proof`, `check_action`,
  `_spawn_hold`, `_design_hold`, `check_closeout`, `_code_items`).
- `adapters/claude-code/goated_adapter/hooks.py` (where state is loaded,
  saved and reset).
- `adapters/claude-code/README.md`: the "Loads that count for a task",
  "Action and closeout proof is per turn", "Compaction" and "Proof of use"
  bullets.
- The mod's README and `hooks/holds.ts`, for how a held skill's outcome is
  judged.

## Acceptance Criteria

- [ ] A skill loaded in one turn meets `pipeline`, `commit`, `design` and
      the Docs item in a later turn with no new load.
- [ ] After a compaction, and after `/clear`, each asks for the load again.
- [ ] With the state file missing, each asks for the load again.
- [ ] A skip line or typed override from an earlier turn clears nothing in
      a later one.
- [ ] A change read made in an earlier turn does not answer a change made
      in a later one.
- [ ] In a later turn, a four-line code edit with the design skill still
      counted as loaded raises no Design closeout item; a twenty-line
      non-test edit does.
- [ ] A spawn in a later turn passes with the template read in an earlier
      turn, and is still held when its brief fails the content check.
- [ ] Inside a subagent, a load from an earlier turn of that subagent does
      not count.
- [ ] The mod shows a hold only when the adapter made one, and its tests
      pass against the regenerated texts.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- `adapters/claude-code/skill-usage/tests/adapter-texts.ts` regenerated; the
  mod's tests pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.
- A live check: one real session with two code-changing turns and a commit
  in the second, with no reload.

## Blocked By

- `tickets/061-adapter-design-closeout-citations-and-question.md` (the
  closeout's Design items and what the turn's proof reads).
- `tickets/062-adapter-unseen-line-advice-once-across-parallel-holds.md`
  (the session state, and the `pipeline` hold's text).
- `tickets/064-adapter-session-cards-pass-routing.md` (the routing check).
- `tickets/071-spawn-briefs-name-skills.md` (the `spawn` gate, whose
  content check it changes).

## Scope Exclusions

- Loads inside a subagent.
- A time or turn limit on how long a load counts.
- Counting lines or overrides across turns.
