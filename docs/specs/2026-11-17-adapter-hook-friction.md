# Adapter Hook Friction From Real Sessions

## Status

Approved by the maintainer on 2026-11-17 in a grill-with-docs session. Ticket
ready. Builds on
[the skill enforcement spec](2026-11-15-skill-enforcement-adapter.md),
[the activation gates spec](2026-11-16-adapter-skill-activation-gates.md),
[the design reference reads spec](2026-11-16-design-reference-reads.md) and
[ADR 0003](../adr/0003-opt-in-framework-enforcement-adapters.md).

## Mode

Compact.

## Problem

Three agents that implemented Tickets 044, 051 and 053 reported how the
Claude Code adapter's holds worked for them. The planning session found two
more cases. Each claim was checked against the adapter on main at `0358832`.
These are the confirmed sources of friction:

- **Timing.** The closeout hold runs only from the `Stop` hook, after the
  agent has written its final report. All three agents hit this. The report
  is split, and its tail can fall outside the 400 characters a parent session
  sees.
- **Re-reads.** A change read made just before loading `commit-message` or
  `doc-sync` does not count, even with no change since. An edit that touches
  only comments or docstrings resets the red-flags read.
- **TDD.** The repeated-failure gate counts a planned red run that failed on
  a missing module, so it holds the implementation write that follows.
- **Ceremony.** `router-first` holds read-only shell commands such as `cat`,
  though its own text says reads stay free. A side session briefed by
  another session still pays the router round trip. The `design` gate fires
  on a test file, the usual first edit in TDD. The 95-word "line may not be
  seen" advice is repeated in every hold that can be cleared by a line. A
  read-only research subagent (`Explore`) is held by `pipeline`, for skills
  of a later phase, and by `spawn`, for the handoff brief template.
- **Bugs.**
  - The closeout Setup item counts a settings file outside the project.
  - A typed `skip commit-message` is recorded but never clears the commit
    hold's load step, though the README's override table says it does.
  - Text inside a `<pasted_content>` block can yield an override.
  - The closeout asked for proof and docs after edits only to scratch files.
    This was not reproduced; the likely cause is the documented Git Bash
    `/tmp` path limit.

Two claims were not confirmed:

- Harness nudges such as "The user hasn't heard from you" are recorded as
  `attachment` entries, which never open a turn.
- `python - <<'EOF'` writing with no hold is already covered in general by
  Known Limits.

Design citations are already Ticket 052.

## Goals

- Closeout work happens before the final report in turns that commit.
- No hold asks again for proof the agent already gave.
- TDD's planned red runs and test-first edits meet no hold meant for other
  work.
- Hold texts stay clear but stop repeating long advice.
- The fixed bugs are covered by tests with near misses.

## Non-Goals

- Changing what the kept holds require: the commit diff-read hold, the
  red-flags read followed by a change read, `tdd` routing, and the clarity of
  the hold texts. Agents named these as the adapter's real value.
- Changing hold first lines (`goated-hold: <gate> | <mode>`).
- Overrides from anything but a prompt a person typed (Ticket 047).
- Treating an interpreter fed a script on stdin as a write.
- Judging the quality of a design citation (Ticket 052's exclusion).

## Requirements

- **R1, closeout at commit.** A commit or commit-tool call whose own commit
  hold is met is held while the turn has unmet closeout items. The hold uses
  the closeout's first line and item texts, and each item accepts its usual
  skip line. The `Stop` closeout stays as a backstop. An item met before the
  commit stays met, since a commit changes no file. Turns that never commit
  meet the closeout only at `Stop`, as today.
- **R2, change reads in any order.** For the commit, pull request and Docs
  checks, a change read counts when it follows the turn's last project
  change, whether it came before or after the skill load. The Design item
  keeps its order: red flags, then the change read.
- **R3, comment-only edits.** An edit whose added and removed text is only
  comments and docstrings does not move the last change that the Design
  item's red-flags read must follow. Proof and Docs are unchanged. The
  comment rules are the ones `design_reads.py` already uses; an edit the
  rules cannot read counts as a change.
- **R4, import and collection errors.** A failing run whose output shows an
  import or collection error does not count toward the repeated-failure
  gate. Examples are pytest's `ERROR collecting` or `ImportError while
  importing test module`, `ModuleNotFoundError`, unittest's
  `Failed to import test module`, and jest's `Cannot find module`. Such a run
  neither adds to nor resets the count.
- **R5, read-only commands.** `router-first` passes a shell command made only
  of plainly read-only commands. These are `cat`, `head`, `tail`, `ls`,
  `grep`, `rg`, `wc`, `find` with no `-exec`, `-execdir` or `-delete`, and
  `git status`, `diff`, `log` or `show`, with PowerShell's read equivalents.
  A redirect, a write, or any other command in it keeps the hold.
- **R6, a route from the brief.** When a session's first prompt is a brief
  from the session that started it, a valid route line on its own line in
  that brief is the turn's route and meets `router-first`. The route's
  required skills still load in the new session. The handoff skill's
  spawn-brief template says where the parent puts that line. A brief carries
  no override.
- **R7, test edits and design.** A test file does not trigger the `design`
  gate, so the turn's first substantial non-test code edit does. Once the
  skill is loaded, test files still meet `design-reads`.
- **R8, advice once per turn.** The full unseen-line advice appears in the
  first hold of a turn that carries it. Later holds in that turn carry one
  sentence pointing to the call fields. Whether the full text was shown is
  read from the turn's earlier held results, not new state.
- **R9, Setup in the project.** The closeout Setup item counts only setup
  files inside the project, as code changes already do. A package install
  counts wherever it runs.
- **R10, scratch files.** Reproduce the closeout that followed scratch-only
  edits. If the cause is a Git Bash `/tmp/...` path, read `/tmp` as the
  operating system's temp folder, so those writes count as outside. Other
  mounts stay as documented. If the cause is something else, report it to
  the maintainer before changing anything.
- **R11, pasted text.** Override phrases inside a
  `<pasted_content …>…</pasted_content>` block are ignored. A phrase typed
  outside the block still counts.
- **R12, a typed commit skip.** A typed `skip commit-message` stands down the
  whole commit hold, its load step included, as the README's override table
  says.
- **R13, read-only subagents.** A spawn of a read-only subagent type passes
  `pipeline` and `spawn`. Only `claude-code-guide` qualifies: `Explore` and
  `Plan` have shell tools, and no routing applies inside a subagent, so
  their shell writes would run unrouted (settled in Ticket 055's review).
  Other subagent types and side sessions are unchanged.
- **R14, documentation.** The adapter README's What It Holds, Hold messages,
  User Overrides and Known Limits sections match the behaviour. Known Limits
  names `python - <<'EOF'` and other interpreters fed a script on stdin. Any
  changed hold text is regenerated for the skill-usage mod, and the mod still
  counts every hold it showed before.

## Acceptance Criteria

- [ ] AC1: A commit made while a closeout item is unmet is held with the
      closeout's first line, listing that item. Meeting or skipping it lets
      the commit through, and the `Stop` that follows passes.
- [ ] AC2: A diff read, then a `commit-message` load, with no change between
      them, passes the commit's change-read step. The same order passes the
      Docs item. A change after the read still requires a new read.
- [ ] AC3: After the red flags and change reads, a comment-only edit does not
      reopen the Design item; an edit that also changes code does.
- [ ] AC4: Two failing runs of one check, the first an import error and the
      second a real failure, do not hold the next write. Two real failures
      still do.
- [ ] AC5: Before the router loads, `cat a.py`, `git diff` and `grep -n x a.py`
      pass `router-first`. `cat a > b`, `find . -delete` and `pytest` are
      held.
- [ ] AC6: A side session whose brief carries a route line passes
      `router-first` and `route-line` on its first write. It is still held by
      `pipeline` until the brief's required skills load. A brief with no line
      is held as today.
- [ ] AC7: An `attachment` entry, such as `silent_turn_reminder`, never opens
      a turn. A regression test pins this.
- [ ] AC8: A 20-line test-file edit as the first edit of a turn is not held
      by `design`. A later 20-line non-test edit is.
- [ ] AC9: The second hold in a turn that would repeat the unseen-line
      advice carries the one-sentence form. The first hold of the next turn
      carries the full text again.
- [ ] AC10: A `settings.json` written outside the project raises no Setup
      item. One inside the project still does.
- [ ] AC11: The scratch-file closeout is reproduced by a test, and the fix
      passes it, or the cause is reported to the maintainer.
- [ ] AC12: A `skip commit-message` inside a `<pasted_content>` block records
      no override. The same phrase typed after the block does.
- [ ] AC13: A typed `skip commit-message` lets a commit through with no
      `commit-message` load.
- [ ] AC14: Ticket 052 notes that its citation item joins the commit-time
      list from R1.
- [ ] AC15: A `claude-code-guide` spawn passes `pipeline` and `spawn` while
      an `Explore` or `general-purpose` spawn with the same brief is still
      held.
- [ ] AC16: The kept holds behave as before. Existing tests pass unchanged
      except where a test asserted friction this spec removes, and each such
      change is named in its ticket's closeout.
- [ ] AC17: The repo checks in `AGENTS.md` pass on Python 3.11 and 3.14. The
      mod's tests pass, and hold first lines are unchanged.

## Proof Surface

The adapter's hook entry points (`goated_hook.py` through
`tests/claude_code_adapter_support.py`), driven by transcript fixtures, plus
the mod's test suite for regenerated hold texts. A live check in one real
session confirms R1 and R8.

## Constraints

- Every change fails toward holding when the adapter cannot tell. An
  unreadable edit counts as code, and an unknown command is not read-only.
- The adapter and the mod keep their shared tables in step (`LINE_FIELDS`,
  hold texts).
- The shared policy and the router keep their word budgets. Ticket 053's
  notes record the policy at exactly 1,200 words and the product-idea route
  at its limit. The spawn-brief line from R6 must fit the context comparison.
- Tickets edit overlapping adapter files, so the order file sequences them
  by file overlap.

## Open Questions

None.

## Risks

- R1 adds a hold at commit time, which an agent may meet before it has run
  its checks. This is mitigated because the items are the same ones `Stop`
  asks for, so no new work is asked, only earlier.
- R5's allow list could pass a command that writes through a form the lexer
  misses. This is mitigated because only listed commands with no redirect
  pass, and anything unknown is held.

## Sources

- `adapters/claude-code/goated_adapter/actions.py`: `_commit_hold`,
  `_change_read_hold`, `_code_items`, `_setup_changes`, `_design_hold`,
  `_repeated_failure_hold`, `_spawn_hold` (claims 1 to 4, 7, 9, 13b, 15).
- `adapters/claude-code/goated_adapter/gates.py`: `check_routing`,
  `unseen_line_advice` (claims 5, 8, 15).
- `adapters/claude-code/goated_adapter/transcript.py`: `_opener_kind`,
  `_build_turn` (claims 6, 12).
- `adapters/claude-code/goated_adapter/overrides.py`: `parse_overrides`
  (claim 13a).
- `adapters/claude-code/README.md`: User Overrides and Known Limits (claims
  10, 11, 13b).
- `tickets/archive/052-adapter-design-citations-at-closeout.md` (claim 14).
