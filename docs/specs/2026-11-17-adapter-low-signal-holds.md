# Adapter Holds On Low-Signal Triggers

## Status

Decisions approved by the maintainer on 2026-11-17 in a grill-with-docs
session, and this text on the same day. Ticket ready. Builds on
[the written-line holds spec](2026-11-17-adapter-written-line-holds.md),
[the registry reference reads spec](2026-11-17-registry-reference-reads.md),
[the skill placement spec](2026-11-17-skill-placement-gates.md) and
[ADR 0003](../adr/0003-opt-in-framework-enforcement-adapters.md). Its
companion is
[the hold delivery spec](2026-11-17-adapter-hold-delivery-and-coverage.md).

## Mode

Compact.

## Problem

The three agents that implemented Tickets 068, 070 and 073 reported how the
Claude Code adapter's holds worked for them, and earlier reports left open
items. Each claim was checked against the adapter on main at `3e3fcb9`.

The agents kept the same verdict as the round before:

- A hold that asks for an action (load a skill, read a reference, reread
  the change) earned its place. So did the closeout's diff reread, the
  red-flags question, Proof reruns, and the skills line in a brief.
- Friction came from holds that fire on a trigger that says little about
  the work, and from the two holds that still check written text.

These are the confirmed low-signal triggers:

- **Red runs.** `repeated-failure` counts every failed run of one check and
  holds the next write after two. In TDD the first run is meant to fail, so
  "red, write the code, still red" holds the fix. It never asks whether a
  test was just written or whether failures are going down. Its hold shows
  the first 80 characters of the command, which is mostly a leading
  `cd "<path>"`.
- **Orientation.** A session started from a brief must load
  `session-start-progressive-disclosure` before its first write on a
  `standard` or `full` route. All three agents had already read the ticket,
  the spec and the code.
- **Writes outside the project.** `router-first`, `route-line` and
  `pipeline` hold a write wherever its file is, so a copy into a temp
  scratch folder was held. The other gates already ignore such a file.
- **Read-only commands.** Before the router loads, `router-first` holds
  common read-only commands: any command after a leading `cd`, `git branch`,
  `git rev-parse`, `pwd`, `sort`, and any pattern holding a backslash.
- **Design lines and citations.** The `design` gate asks for a
  `goated-design-reads:` line, and the closeout asks for a `file#id`
  citation of each required reference. The signals already select the
  references; the citation is checked for presence only. An edit call has
  no field to carry either, so the agent makes an empty shell call to carry
  them.
- **Red-flags reread.** A two-line fix after the red-flags read asks for
  the read again.
- **Test edits.** Any test edit of five or more lines asks for `coding.md`
  once `software-design-principles` is loaded, and for `test-design.md`
  once `tdd` is loaded.
- **Review in a delegated session.** The closeout's Review item fires at
  400 changed lines on the branch, counting tests, fixtures and docs, in a
  ticket session whose starting session reviews the branch anyway.
- **Read order.** Review, Security and `pr-review` count a change read only
  after the skill load, so a diff read just before the load is read again.
- **Partial reads.** A `Read` with `limit: 20` of a required reference
  counts as reading it.
- **Installs elsewhere.** A package install in a scratch folder asks for
  `setup-scribe`.

## Goals

- An intended red run, and a run that shows progress, do not bring a hold.
- A briefed session that has read its sources is not asked to load the
  orientation skill.
- A write or install that is certainly outside the project meets no hold
  meant for project work.
- A read-only command is not held before the router loads.
- No design hold checks written text.
- A test edit asks for a test reference only when a test is being designed.
- A delegated session is not asked for a review its starter performs.
- A required reference is read whole, once.

## Non-Goals

- Changing what the kept holds require: the closeout's diff reread, the
  red-flags read and its question, Proof, the skills line in a brief
  (Ticket 071 stays as shipped: the line is required, and
  `goated-skills: none: <reason>` is its justified skip), route lines, and
  the load and read holds generally.
- Telling a known failing test from a new failure by test name.
- Changing how many references a new code file or public definition
  selects. The maintainer kept three.
- Judging whether a reference was applied.
- Changing hold first lines (`goated-hold: <gate> | <kind>`).
- Holds inside a subagent, which stay as they are.
- How holds are reported together, script writes, turn boundaries and
  closeout timing. The companion spec covers them.

## Requirements

- **R1, red and shrinking runs.** For `repeated-failure`, a failed run of a
  check is not counted, and does not reset the count, when either holds:
  - it is the first run of that check after a finished write to a test file
    in the turn;
  - its runner reports fewer failures than the previous run of that check
    in the turn. Failures are the failed and errored tests the runner's
    summary counts. When either run's count cannot be read, the run counts.

  Everything else stays: two counted failures in a row hold the next write,
  a pass resets the count, and `diagnose` clears the hold.
- **R2, the check as shown.** "The same check" ignores a leading `cd` to a
  folder, joined by `&&` or `;`, and the hold shows the check's own command,
  not the `cd`.
- **R3, orientation by reads.** In a session routed by its brief, on a
  `standard` or `full` route, the orientation requirement is met by loading
  `session-start-progressive-disclosure`, as today, or by three finished
  `Read` calls of distinct files, anywhere, since the session started or
  the last compaction. The hold names both ways.
- **R4, writes outside the project.** A write passes `router-first`,
  `route-line` and `pipeline` when every file it writes is certainly
  outside the project, and is also inside no git checkout and not under
  the user's `~/.claude` folder. "Certainly outside" is the rule the other
  gates use: when in doubt, a file is inside. The two further conditions
  keep routing on a write to another repository or worktree, and on a
  write to installed skills, rules and settings; a temp scratch folder
  meets all three. Spawns and commands that are not writes are held as
  today.
- **R5, plain reads.** These also count as plain reads, alone or joined as
  plain reads already may be:
  - a command after a leading `cd` to a literal path;
  - git subcommands that only read: `branch` with no name to create,
    `rev-parse`, `ls-files`, `blame`, `worktree list`, `remote` with no
    change;
  - `pwd`, `echo` with no redirect, `sort`, `uniq`, `cut`, `tr`, `diff`,
    `stat`, `file`, `which`, `true` and `:`;
  - a backslash or `//` inside a single-quoted argument, and a
    `2>/dev/null` redirect.

  A form is added only when it cannot write a file or run another program.
  The ticket may drop a form that fails that test and must say so.
- **R6, no design-reads line.** The `design` gate asks for the
  `software-design-principles` load and the references the edit's signals
  select, and for no line. The `goated-design-reads:` line leaves the
  skill, the marker grammar and its fixtures, the adapter and the
  skill-usage mod. A line an agent still writes is ignored. A reference no
  signal selects (`differences.md`) is declared advisory in the registry.
- **R7, no design citations.** The closeout has no Design citations item,
  and `software-design-principles` no longer asks for citations. Section
  ids and the Section Index stay as navigation. The adapter keeps no record
  of which references each edit required.
- **R8, red-flags reread.** After a red-flags read in the turn, later code
  changes that add fewer than five lines in total, comment-only changes
  aside, do not ask for the read again. The change read after the last
  change is still required.
- **R9, test edits.** A test-file edit selects `coding.md` (design skill
  loaded) and `test-design.md` (`tdd` loaded) only when it creates the test
  file or adds twenty or more lines, counted the same way for both. The
  registry's signal for `test-design.md` states the rule, and the adapter
  reads it from there; `software-design-principles` and `tdd` state it in
  their "read when" text. `mocking-and-seams.md` keeps its pattern signal.
- **R10, review in a briefed session.** A session whose first prompt was a
  brief meets no Review item, for the whole session, typed prompts and
  compactions included. The spawn-brief template already says the starting
  session inspects the report and the changed paths; it gains one sentence
  saying that this is the review. Verification is unchanged.
- **R11, branch size.** "Large" counts changed lines in code files outside
  test paths only, for the Review item, the Verification item's size
  trigger and the `pr-review` gate. Docs, fixtures, configuration and
  tests add nothing. The skill that owns the 400-line rule states it.
- **R12, read order.** For Review, Security and `pr-review`, a change read
  after the last change counts whether it came before or after the skill
  load, as it does for commit, pull request and Docs.
- **R13, whole reads.** A `Read` with `limit` or `offset` does not count
  for a required design or registry reference, a spawn template or
  `red-flags.md`. The hold says to read the whole file. Change reads are
  unaffected.
- **R14, installs.** A package install run in a folder certainly outside
  the project does not count for the Setup item, unless it is a global or
  machine install (`npm` or `pnpm` with `-g`, `yarn global add`,
  `uv tool install`, `pipx install`, `cargo install`, `go install`,
  `gem install`, `brew`, `apt`, `apt-get`, `winget`, `choco`, `scoop`),
  which counts wherever it runs.
- **R15, documentation.** The adapter README's What It Holds, Design
  references, Registry references, Plain reads, Large branches, Hold
  messages and Known Limits sections match the behaviour. Known Limits
  also stops saying that `reference-reads` ignores shell writes, which the
  code does judge. Changed hold texts are regenerated for the skill-usage
  mod, the mod's README matches, and the mod still counts every hold it
  showed before except the removed design-reads and citation asks.

## Acceptance Criteria

- [ ] AC1: Test edit, failed run, code edit, failed run, code edit: the
      second code edit is not held. A third failed run with the same
      failure count then holds the next write.
- [ ] AC2: Runs reporting 5, 3 and 1 failures hold nothing. Runs reporting
      3, 3 hold the next write, and so do two failed runs whose counts
      cannot be read.
- [ ] AC3: `cd "<long path>" && pytest -q` failing twice shows `pytest -q`
      in the hold, and counts as the same check as `pytest -q` run from
      that folder.
- [ ] AC4: A briefed session on a `full` route that made three `Read`
      calls of distinct files writes with no orientation hold. With two
      reads it is held, and the hold names both ways to clear it.
- [ ] AC5: Before the router loads, a `cp` into a temp folder outside the
      project is not held, a `cp` into the project is, and a write whose
      folder cannot be read is. A write into another git checkout, or
      under the user's `~/.claude` folder, is held.
- [ ] AC6: Each form R5 keeps passes `router-first` before the router
      loads, and a near miss for each is held: `git branch new-name`,
      `echo x > f`, `cd sub && rm f`.
- [ ] AC7: A substantial first edit with the design skill loaded and its
      selected references read passes with no line in the turn. A written
      `goated-design-reads:` line changes nothing.
- [ ] AC8: A closeout after design edits lists no citations item, and the
      skill's text asks for none. The marker fixtures and validators pass
      without the design-reads grammar.
- [ ] AC9: After the red-flags read and a change read, a two-line code fix
      asks only for a change read. A six-line fix asks for the red-flags
      read again.
- [ ] AC10: A ten-line edit of an existing test file requires no
      reference. A `Write` creating a test file, and a twenty-line edit,
      each require `coding.md` and `test-design.md` when their skills count
      as loaded.
- [ ] AC11: A briefed session with 600 changed code lines meets no Review
      item, also after a typed prompt. The same branch in a session started
      by a typed prompt does.
- [ ] AC12: A branch of 300 changed code lines and 500 changed test,
      fixture and doc lines is not large for Review, Verification or
      `pr-review`.
- [ ] AC13: A diff read after the last change and before the
      `standards-and-spec-review` load meets the Review item.
- [ ] AC14: A `Read` with `limit: 20` of a required reference leaves the
      hold in place; a whole read clears it.
- [ ] AC15: `pip install requests` in a temp folder raises no Setup item;
      `uv tool install ruff` there does; `pip install requests` in the
      project does.
- [ ] AC16: The kept holds behave as before. Existing tests pass unchanged
      except where a test asserted friction this spec removes, and each
      such change is named in its ticket's closeout.
- [ ] AC17: The repo checks in `AGENTS.md` pass on Python 3.11 and 3.14,
      the router and the shared policy stay inside their word budgets, the
      mod's tests pass, and hold first lines are unchanged.

## Proof Surface

The adapter's hook entry points (`goated_hook.py` through
`tests/claude_code_adapter_support.py`), driven by transcript fixtures;
the registry, marker and skill validators; the routing and context-budget
checks; and the mod's test suite for regenerated hold texts.

## Constraints

- ADR 0003 has adapters enforce portable contracts, not define them. Each
  rule has an owner outside the adapter:
  - R1: `tdd` (the first run after writing a test is expected to fail)
    and `diagnose` (when repeated failure calls for it);
  - R3 and R10: `handoff`'s spawn-brief template and
    `session-start-progressive-disclosure`;
  - R6 to R9: `software-design-principles`, and for R9 also `tdd` and the
    registry;
  - R11: the skill that states the review size rule;
  - R14: `setup-scribe`.

  R2, R4, R5, R12 and R13 are adapter mechanics stated in its README;
  Ticket 079's enforcement contract restates them in harness-neutral
  words.
- The router has about six words of headroom and the shared policy none.
  No requirement here adds a rule to either; a ticket that must touch the
  router replaces words.
- Every change fails toward holding when the adapter cannot tell: a
  failure count it cannot read counts, a file it cannot place is inside,
  a command form it does not know is not a plain read, and a read whose
  range it cannot read is partial.
- The adapter and the mod keep their shared tables and hold texts in step.
- Tickets edit overlapping adapter files, so the order file sequences them
  by function overlap.
- This spec's tickets finish before Ticket 079, which writes the
  enforcement contract from the rules as they then stand.

## Open Questions

None.

## Risks

- R1 lets a loop that edits a test before every run go uncounted. This is
  mitigated because only the first run after each test write is excused,
  and the next failure counts.
- R3 lets three unrelated reads stand for orientation. That is the chosen
  trade: the skill's own work is targeted reading, and a session that
  writes before reading anything is still held.
- R4 lets unrouted work write outside the project. Left at "outside the
  project" alone, that would include another repository, a sibling
  worktree and the user's installed skills and settings, where a write
  is real work or changes how every session behaves. R4 therefore keeps
  routing on any file inside a git checkout or under `~/.claude`. What
  still passes is a write to a folder that is none of these, such as a
  temp scratch folder; a project kept outside any git checkout and
  outside the session's folders is not protected.
- R6 and R7 remove the only check that an agent connected a reference to
  its change. The agents' reports say the reads and the red-flags question
  carried the value.
- R10 trusts the starting session to review. A brief sent with no review
  planned leaves a large branch unreviewed; the starter's own closeout
  still raises Verification when a subagent changed code.
- R11 lets a branch that is large only in tests or configuration pass
  with no review. Security-sensitive files still bring Verification.

## Sources

- `adapters/claude-code/goated_adapter/actions.py`: `_repeated_check`,
  `_check_key`, `_design_hold`, `_code_items`, `_designing`,
  `_uncited_references`, `_review_item`, `_verification_item`,
  `changed_lines`, `_change_read_hold`, `_setup_changes`, `_Proof`.
- `adapters/claude-code/goated_adapter/gates.py`: `check_routing`,
  `_brief_orientation`, `writes_like_an_edit`, `fold_turns`.
- `adapters/claude-code/goated_adapter/shell.py`: `READ_ONLY_COMMANDS`,
  `NOT_PLAINLY_SPELLED_RE`, `_installs_package`.
- `adapters/claude-code/goated_adapter/design_reads.py`: `_signals`,
  `required`, `reads_in`; `reference_reads.py`: `reads_in`;
  `contracts.py`: `templates_read`.
- `stack/goated-stack.yaml` (the `tdd` reference signals),
  `stack/fixtures/markers/`, `scripts/validation/markers.py`.
- `skills/engineering/software-design-principles/SKILL.md`, the `tdd`,
  `handoff`, `session-start-progressive-disclosure`, `setup-scribe` and
  `standards-and-spec-review` skills.
- `adapters/claude-code/README.md`.
- Tickets 061, 063, 067 to 072.
