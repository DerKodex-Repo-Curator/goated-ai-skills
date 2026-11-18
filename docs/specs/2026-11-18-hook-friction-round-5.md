# Hook Friction Round 5

## Status

Decision Needed, for O and the narrowed L1, 2026-11-18. R1 to R4
follow the lead's curation of the round 5 feedback, items 1 to 4. R5 to
R8 cover the second source's items 7 to 11, added to this spec by the
lead on 2026-11-18; item 12 is a decision with no ticket. The maintainer
chose the recommended option of every decision on 2026-11-18: H1, I1, J1,
K1.1, K2.1, L1, M1, N1, O1, P1 and Q1 ([Decisions](#decisions)). A review
the same day found O1 rested on a wrong reading of today's behaviour, so
O is open again, restated; and it narrowed L1, which the maintainer is to
confirm. Tickets 114 and 116 are written to the recommended options and
change if another is chosen. Builds on [the round 4 spec](2026-11-18-hook-friction-round-4.md): every change is
made once, in the shared core at `adapters/core/goated_core/`, and stated
in [the enforcement contract](../../stack/enforcement-contract.md).

## Mode

Compact.

## Problem

Ticket 108's agent made a 5-line production change with 28 lines of tests,
two scenarios and a contract edit. It estimates that half or more of its
tokens, and about seven extra round trips, went to holds. No hold caught a
correctness issue; the red-flags question did.

Each item was checked against main at `bf18b3b`.

- **Orientation after real orientation** (feedback items 1 and 13). The
  agent read the ticket, the spec, `shell.py`, the tests, the contract and
  the fixtures with `cat`, `sed` and `grep`, and the `pipeline` gate still
  held it. Orientation counts the skill's load or whole reads of three
  distinct files (the `pipeline` row), and a whole read is a `file_read`
  with `whole` true (Terms). A shell print never counts
  (`gates._files_read` uses `Call.whole_read_path`, which is for file
  reads only). The agent's claim that the brief's route line "wasn't seen"
  is wrong: the line was seen, and it is what requires orientation. The
  session that wrote this spec met the same hold after orienting with
  `cat`, `sed` and `grep`.
- **Design reads sized by every added line** (item 2). An edit adding
  three code lines and a two-line comment adds five lines, so it is not
  small (`actions._small_edit`), and its comment selects `readability.md`
  (`design_reads._signals`). Ticket 100 covers comment-only edits, not code
  plus a comment. Separately, 24 added lines of cases in an existing
  parametrized test pass the registry's `min_added_lines: 20` for test
  files, which selects `coding.md` and `tdd`'s `test-design.md` by one rule.
  Round 3 kept "How many references one edit asks for"; that was about how
  many references a typical change needs, not what sizes a trigger.
- **Clearing advice repeated per hold** (item 3). Ticket 095 joined holds
  into one message, and `gates.shown_holds` gives the full placement
  advice once per turn. Every other hold a line can clear still carries a
  short sentence of its own on where the line goes and which override the
  user can type, so three holds repeat it three times.
- **`scripted-edit` calls a markdown file code** (item 4). A script that
  builds its file's name at run time is held with "a file it names only at
  run time, which counts as code" (`actions._scripted_edit_hold`). The file
  was markdown. Steering the agent to a file edit tool was right; the words
  are not.

A second source, a product ticket in another project, found a modest gain
in quality at an estimated 15 to 20% extra time and tokens. What helped:
the "name one input that would break this" question, the concurrency
reference, the diff read before each commit, `code-security-review`, and
`test-design.md`. Its friction:

- **Holds fire after the content is written** (item 7, the largest cost).
  The `design`, `design-reads` and `reference-reads` gates judge a write
  by its text, so they hold it once it is composed, and the whole edit is
  sent again: a 300-line file twice, plus four other files. A held call is
  not run, and no harness keeps its content.
- **Mocking-reference false positives** (item 8). Checked against main:
  the `mock-or-patch` pattern (`reference_reads.PATTERNS`) still matches
  the word `fake` in code, so a line of invented TOML in a test, such as
  `[providers.fake]` or `name = fake`, selects the mocking reference;
  `provider = "fake"` no longer does (Ticket 100). `monkeypatch` is a word
  match, so `monkeypatch.setenv(...)` and a bare `monkeypatch` parameter
  select it too.
- **Proof after a docstring-only change** (item 9). The `Proof` item is
  needed for "a change not already proved", and any code change counts,
  comment-only ones included. A docs file is not code, so a docs-only
  change already keeps its proof. The Design item skips comment-only edits
  under twenty lines; Proof has no such rule.
- **Closeout while waiting** (item 10). The closeout held three times
  while the agent waited on a user's walk-through or a full check. Ticket
  102 named the case of waiting on another session in the Proof text.
  Checked against main: a check started in the background already meets
  Proof, at a commit and at the turn's end. `actions._checks` reads only
  the command's text, never the shell call's `background` field, so the
  launch counts as a passing check, and a later failure never makes
  Unfinished needed. The contract's "not in the background" means only a
  check put in the background inside one command (`pytest &`), so the
  contract and the code disagree about a harness background run. The
  event model has no entry for a background shell command finishing
  (`agent_finished` is for agents); in Claude Code its result arrives as a
  task notification that continues the turn.
- **Router-first on a continued prompt** (item 11). Checked against the
  contract: `router-first` is met by a router load, or "until a person's
  prompt opens a turn" by a brief with a route line. So in a briefed
  session that never loaded the router, the first typed prompt holds every
  write and command until the router loads, though the agent then writes
  only `goated-route: continue`.
- **The `true` carrier call** (item 12). A line asked for by a call that
  has no field for it still needs a shell `true` call. Round 4 kept it;
  both sources raised it again.

## Goals

- A session that oriented by printing whole files with the shell is not
  held for orientation.
- A short code edit with a comment, and new cases added to an existing
  test table, ask for the design reads their substance needs, not their
  line count.
- One message of several holds says once how to clear them.
- The `scripted-edit` hold never says a file is code when it cannot tell.
- A large edit is not composed twice because a read gate held it.
- The mocking reference is asked for a mock or patch of code, not for
  `fake` in data or a patched environment variable.
- A comment-only edit, and a check still running, do not cost a new Proof.
- A briefed session's typed prompt that continues the task needs only its
  route line.

## Non-Goals

- Kept, from the feedback (item 5): the red-flags read and its question,
  the early closeout notice, doc-sync at Stop, and the commit change read.
- Pointing a reference hold at a section (item 6): [deferred](#deferred).
- The carrier call (item 12), unless decision Q says otherwise.
- Which references a read must cover, how long a read or skip lasts, and
  hold first lines (`goated-hold: <gate> | <kind>`).
- Any harness-specific rule: an adapter only translates.

## Requirements

- **R1, shell prints orient** (item 1; decision H). A finished, successful
  shell command whose plain file printer prints a file whole counts as a
  whole read of that file for orientation, the `pipeline` gate's three
  distinct files. A print is whole when:
  - the printer is `cat`, or PowerShell's `Get-Content`, `gc` or `type`
    without `-TotalCount`, `-Head`, `-First`, `-Tail` or `-Last`;
  - its output is not piped into another command.

  `head`, `tail`, `sed`, `grep` and other commands print part of a file and
  never count. Every other rule that asks for a whole read (references, red
  flags, templates) keeps asking for a file read. The orientation hold's
  text says that a whole print counts. A printed path is resolved from the
  command's folder to the form a file read records, so one file printed
  and read under two spellings counts once.
  - The contract names this a new term, **whole print**, used in the
    `pipeline` row only; "Whole read" keeps its meaning.
  - Touches: the file printers in `shell.py` (`FILE_PRINTERS`, beside the
    conflict reading), `gates._files_read`, and the orientation text in
    `gates`; the contract's Terms (a new Whole print), the `pipeline` row
    and Shell Reading. Not `shell.py`'s pull request reading, though its
    printer branch in `_add_segment` sits beside 108's `FORGE_DIFFS`
    change, so Ticket 110 lands after 108 and 109.
- **R2, design reads sized by substance** (item 2; decision K).
  - **K1:** an edit that adds fewer than five code lines (comments,
    docstrings and blank lines left out, as `comment_only` reads them) and
    fewer than twenty comment lines selects no `readability.md` for its
    comment. Every other signal, the `design` gate and the Design item
    keep today's size rule. A file whose comment syntax the core does not
    know has no code lines it can count, so it is judged as today.
  - **K2:** in an edit to a test file that the edit does not create, an
    added line that only holds case data does not count toward the
    registry's `min_added_lines` for test files. A case-data line holds,
    once comments are left out, only string and number literals, `True`,
    `False`, `None`, `true`, `false`, `null`, `nil`, brackets, commas,
    colons, `=` between a keyword and a literal, and a case wrapper
    (`pytest.param(`, `param(`). A new test file selects as today.
  - Touches: `design_reads._signals` and the small-edit sizing it is
    given; the counting of `edit-of-file-kind` signals (`design_reads` and
    `reference_reads`); the contract's design references table (the
    `readability.md` and `coding.md` rows), the `edit-of-file-kind` row of
    Registry Reference Signals, and `skills/README.md` if it states the
    signal's counting.
- **R3, one clearing section per message** (item 3; decision I). When a
  message carries two or more holds that a line can clear, each hold keeps
  its own line to write (its skip or route line) and drops its placement
  sentence. The message ends with one section that says where a line goes
  (the full advice when the turn has not had it, else one sentence) and
  lists each hold's typed override once. A message with one such hold is
  unchanged. Every skill, reference and line each hold names stays.
  - Touches: `gates.shown_holds` and the advice slots in `wording.py`; the
    Claude Code adapter's slot translation (`translation.py`) if a new
    slot is needed; the contract's Hold Messages ("When a decision carries
    several holds").
- **R4, `scripted-edit` wording** (item 4; decision J). The hold names a
  file named only at run time as one whose kind cannot be told, held as
  code would be, not as a code file. Its short form says the same.
  - Touches: `actions._scripted_edit_hold`; the contract's `scripted-edit`
    paragraph only if it states the text.
- **R5, large writes land and read after** (item 7; decision L, as
  narrowed at review). `design-reads` and `reference-reads` hold a write
  only when it adds fewer than thirty lines, counted as each gate counts
  them today. A write whose lines cannot be counted (a shell write showing
  no text, such as a heredoc holding `$(...)` or a program's output)
  counts as under thirty and is held, so Tickets 093 and 097's coverage
  of shell writes stays. A write of thirty or more is applied and passes
  with a notice naming the references it needs. A new closeout item,
  `Reads`, is then needed: it is met when each named reference is read
  whole or a lasting skip covers it, and a change read of the file
  follows. It holds a commit and the turn's end, as the other items do.
  Its skip line names the skill whose references it asks for, and a skip
  of it lasts as round 4's R4 states for the gate it stands for.
  - The `design` gate is unchanged: the skill still loads before the
    first substantial edit (its workflow step 2), and the reads `design`
    asks for alongside the load stay a hold.
  - `software-design-principles`'s step 4 ("Read now") and
    `skills/README.md`'s description of registry reference signals change
    to say that, for a large edit already written, the reads may follow
    it, before the closeout, and the edit is revised after them. This is
    a text change the rule needs; it runs the context comparison.
  - The notice is a new kind, `reads_owed`, since none of today's fits:
    `closeout_note` is once per turn after the first write, and
    `skip_carried` names a skip. So the event model moves to version 4,
    and the contract's Notices section lists it.
  - Touches: where `actions.py` judges a write against `design-reads`
    and `reference-reads`, and `_closeout_items`; session state for what
    a landed write still needs; the event model's notice enum and
    version; the contract's two gate rows, Closeout Items and Notices; the
    two skill texts.
- **R6, mocks of code** (item 8; decision M). In the `mock-or-patch`
  pattern:
  - `monkeypatch` selects only as `monkeypatch.setattr(`,
    `monkeypatch.delattr(` or `monkeypatch.context(` (whose `m.setattr(`
    patches code); `setenv`, `delenv`, `setitem`, `delitem`, `chdir`,
    `syspath_prepend` and the bare name select nothing;
  - a line the edit shows inside a multi-line string (a Python
    triple-quoted string that is not a docstring, a JavaScript template
    literal) is inside a string, so `fake` in invented TOML there
    (`[providers.fake]`, `fake = true`) selects nothing.

  Where the edit does not show where a multi-line string opens, the line
  is read as today. The registry's pattern description stays true.
  - Touches: `reference_reads.PATTERNS` and `_without_strings` (or the
    reading of added lines it is given); the registry's
    `reference_patterns` entry in `stack/goated-stack.yaml`; the
    contract's `reference-reads` row and Registry Reference Signals.
- **R7, Proof kept while nothing material changed** (items 9 and 10;
  decisions N and O).
  - **N:** a
    [comment-only edit](../../stack/enforcement-contract.md#comment-only-edits) (as `comment_only` reads it, of any
    size) after the last check is already proved: it does not make Proof
    needed. A file whose comment syntax the core does not know is never
    comment-only, as today. The Docs item still fires after a
    docstring-only edit of a non-test code file, by intent: a docstring
    is documentation, and the durable docs may repeat it.
  - **O (open again; see [decision O](#o-background-checks-and-waiting-r7)):**
    a check started in the background meets Proof only as the decision
    states, and the contract and the code agree on it. Whatever O
    decides, the Proof text names waiting on the user: the skip line
    naming `verification-before-completion`, with what is awaited as the
    reason, clears it, as for waiting on another session.
  - Touches: the Proof and Unfinished items in `_closeout_items` and
    `actions._checks`; the contract's Closeout Items (Proof row and the
    paragraph after the table) and Shell Reading's "not in the
    background"; for O2 also the event model, the Claude Code adapter's
    transcript reading and session state (see decision O).
- **R8, a continued prompt in a briefed session** (item 11; decision P).
  In a session whose brief's route line set its task, a turn opened by a
  person's prompt whose route line is `goated-route: continue` meets
  `router-first` without a router load. A route line that starts a new
  task, or a turn with no route line yet, still needs the router; plain
  reads pass as today. This is its own state, not a return of
  `brief_routed`: that flag also switches on briefed-session orientation
  in `pipeline`, which a typed `continue` must not bring back.
  - Touches: `gates.check_routing` (the `router-first` check and its
    `brief-route` clear); the contract's `router-first` row and "Prompts,
    Turns, And Tasks".

Every change to a rule updates `stack/enforcement-contract.md` and a
conformance scenario under `stack/fixtures/enforcement/` in the same
change, as `AGENTS.md` requires.

## Acceptance Criteria

- [ ] **AC1.** R1: in a session routed by its brief on a `standard`
      route, with the orientation skill installed and not loaded, three
      finished `cat` commands of three distinct files (or one `cat a b c`)
      clear orientation; `head`, `sed -n`, `grep`, and `cat a | head`
      do not; `Get-Content x` counts and `Get-Content x -TotalCount 5`
      does not. A shell print of a design reference still does not clear
      `design-reads`. A scenario covers the hold and each near-miss kind.
- [ ] **AC2.** R2, K1: in a Python file, an edit adding three code lines
      and a two-line comment selects no `readability.md`; one adding five
      code lines and a comment does. K2: 24 added case-data lines in an
      existing test file select no `coding.md` or `test-design.md`; 24
      lines of a new test function do, and so does a new test file. A
      scenario covers a hold and the near miss of each.
- [ ] **AC3.** R3: a call meeting three holds that lines can clear shows
      one clearing section, with each skip line once in its hold and each
      override once in the section; a call meeting one is unchanged.
- [ ] **AC4.** R4: a script writing a run-time-named file is held with
      text that does not call the file code; a script writing a named
      `.py` file still says "the code file".
- [ ] **AC5.** The contract states every changed rule, and
      `tests/test_enforcement_contract.py` and the scenario runner pass.
- [ ] **AC6.** The repo checks in `AGENTS.md` pass.
- [ ] **AC7.** R5: with `software-design-principles` loaded, a 40-line
      edit whose signals select an unread reference is applied with a
      `reads_owed` notice, and the turn's end and a commit then meet a
      `Reads` item until the reference is read whole and a change read
      follows; a 29-line edit, and a shell write whose text it does not
      show, are held as today; the first substantial edit with the skill
      not loaded still meets `design`. A scenario covers each and the
      item's skip line.
- [ ] **AC8.** R6: in a test file with `tdd` loaded, `monkeypatch.setenv(`
      and a bare `monkeypatch` parameter select no mocking reference;
      `monkeypatch.setattr(` and `monkeypatch.context(` do. A
      `[providers.fake]` line inside a
      triple-quoted string the edit shows selects nothing; the same line
      as code still does.
- [ ] **AC9.** R7 N: after a passing check, a docstring-only edit of any
      size meets no Proof item; an edit changing one code line does.
- [ ] **AC10.** R7 O: a background check's launch meets Proof exactly as
      decision O states, at a commit and at the turn's end, and the
      contract says the same; the Proof text names waiting on the user.
- [ ] **AC11.** R8: in a briefed session that never loaded the router, a
      person's prompt followed by `goated-route: continue` meets no
      `router-first` hold, and brings back neither briefed-session
      orientation nor any `pipeline` hold; one followed by a new route
      line is held.

## Proof Surface

The conformance scenarios, run against the core through both of its ways
in. The Claude Code adapter's tests show the same outcomes through its
hook, and its translation tests show R3's section.

## Constraints

- Work lands in `adapters/core/`, so each rule changes once.
- Tickets 108 and 109, on branch `tickets/shell-pr-follow-ups`, are
  changing `shell.py`'s pull request reading now. Only R1 touches
  `shell.py`, in its file printers, beside 108's change; Ticket 110 lands
  after 108 and 109. No requirement changes the pull request reading.
- Skill texts change only where a rule they state changes. R5 is such a
  rule: it changes `software-design-principles`'s step 4.

## Decisions

The maintainer chose the first option of each decision on 2026-11-18
(K1 later that day). The restated O is open, its recommended option
first; L1 as narrowed at review awaits the maintainer's confirmation. The other options are kept as the record of what was
weighed.

### H. What orients a session (R1)

1. **Chosen: a whole shell print counts, for orientation only**, as
   R1 states. Orientation asks for a look at the project, and `cat` is how
   agents look. Trade-off: the harness may cut a long output, so a "whole"
   print may not have been seen whole; orientation tolerates that,
   references do not, so they keep asking for a file read.
2. **A whole shell print counts as a whole read everywhere**: orientation,
   design and registry references, red flags and templates. Trade-off:
   reverses the contract's "A shell command printing one does not count"
   for references whose whole text matters, with the cut-output risk.
3. **Any read of three distinct files orients**, partial reads included
   (`sed -n`, `grep` of a file, a ranged file read). Trade-off: three
   greps orient a session; reverses "partial reads never count" for
   orientation, which Tickets 092 and 098 settled.

Also weighed: counting reads of the files the brief names. The brief's
paths are free text the core would have to find and match; option 1
already counts them when they are printed whole.

### I. Clearing several holds (R3)

1. **Chosen: one closing section per message**, as R3 states.
   Trade-off: an agent reading one hold alone must look to the message's
   end to learn where the line goes.
2. **Merge only identical sentences.** Each hold keeps a placement
   sentence; repeats with the same override drop. Trade-off: holds of
   different skills each keep one, so item 3's three holds stay three.
3. **No change.** Trade-off: the repeat stays; Ticket 095 already cut the
   full advice to once per turn.

### J. The `scripted-edit` words (R4)

1. **Chosen: wording only**, as R4 states. Cheap, and the steering
   stays. Trade-off: a markdown file named at run time is still held.
2. **Wording, and a visible extension decides the kind.** A run-time path
   whose literal tail ends in an extension (`f"{d}/notes.md"`,
   `p + ".md"`) is that kind of file, so a docs file passes. Trade-off:
   more script reading in `script_writes.py`, and the lead judged the
   steering right.

### K. What sizes a design read (R2)

K1 and K2 are separate choices.

- **K1, a comment on a short code edit.**
  1. **Chosen: code lines size the comment signal**, as R2 states.
     It matches Ticket 100's twenty-line comment-only rule. Trade-off: a
     comment of up to nineteen lines on a four-line change goes without
     `readability.md`.
  2. **Code lines size every design rule**: the `design` gate,
     `decoupling.md` and the Design item too. Trade-off: wider; a
     four-line fix with a long comment meets no design gate at all.
  3. **No change.** Trade-off: the reported hold stays.
- **K2, new cases in an existing test.**
  1. **Chosen: case-data lines do not count** toward the test-file
     threshold, as R2 states. The test's design was judged when it was
     written; new rows extend it. Trade-off: one rule decides both
     `coding.md` and `test-design.md`, so choosing the new cases no longer
     asks for `test-design.md`, which the second source found useful; and
     a new heuristic reads each line.
  2. **A higher threshold for edits of existing test files** (say forty
     lines). Trade-off: blunt; a forty-line new test in an existing file
     goes unasked.
  3. **No change.** Trade-off: the reported hold stays; choosing cases is
     test design, so the read is arguably right.

  Review (2026-11-18) judged K2.1 weak, since the second source credited
  `test-design.md`, and asked whether K2.2 or K2.3 should be recommended.
  The maintainer's K2.1 stands until the maintainer says otherwise.

### L. Holds after the content is written (R5)

The read gates judge a write by its text, so they can only hold it once
it is composed. The options differ in when the agent learns what it needs.

1. **Chosen, then narrowed at review (2026-11-18; the maintainer to
   confirm): large writes land past `design-reads` and
   `reference-reads`, and their reads move to the closeout**, as R5
   states. Re-sent content costs in proportion to its size, so a short
   edit keeps the hold (cheap to send again) and a long one keeps its
   content. Review narrowed the option the maintainer chose in two ways:
   - `design` keeps holding, since moving the skill's load past the code
     goes against its workflow steps 2 and 4; the load is once per task
     and usually comes before any large edit;
   - a write whose lines cannot be counted is held, since letting it land
     would let a shell write showing no text skip both read gates,
     undoing Tickets 093 and 097.

   Trade-off: for a large write the reads review the design instead of
   shaping it; the change read after them is where the agent revises, and
   the skill's step 4 and the registry signals' description must say so.
   A new closeout label (`Reads`), a new notice kind (`reads_owed`, event
   model version 4), and session state for what landed writes still
   need.
2. **Announce the references before the write.** After a read of a file,
   a notice names the references an edit of it would need by its path
   alone (a configuration file, a test file, the third code file, a new
   file). Trade-off: the signals read from the added text (a new public
   definition, error handling, concurrency, a comment) cannot be known
   before it is written, so the costly holds remain; and a notice on every
   read adds tokens of its own.
3. **Every read-gate write lands; all reads move to the closeout.**
   Trade-off: simplest, but the design reads never come before code, which
   is what the skill asks for; the closeout grows for every edit.
4. **No change.** Trade-off: the top cost stays.

Options 1 and 2 can combine; 1 alone removes the reported cost.

### M. The mocking pattern (R6)

1. **Chosen: `monkeypatch` only as a patch of code, and multi-line
   strings are strings**, as R6 states. Trade-off: `monkeypatch.setitem`
   on a module's dict patches code and goes unasked; reading where a
   multi-line string opens needs the edit's context.
2. **Drop `fake` and `monkeypatch` from the pattern.** Trade-off: a
   hand-written fake is a seam choice the reference covers; it would go
   unasked.
3. **No change.** Trade-off: a read once per context window costs little,
   which is why the pattern matches word starts.

### N. Proof after a comment-only edit (R7)

1. **Chosen: a comment-only edit of any size keeps the proof**, as
   R7 states. Comments do not run. Trade-off: a docstring a tool reads
   (doctests, a docstring-driven CLI or schema) can break a check; the
   agent must judge that case itself.
2. **Only under twenty lines**, as the Design item. Trade-off: the
   reported case (a docstring fix) may still pass the cap; the size does
   not track the doctest risk.
3. **No change.** Trade-off: the rerun stays.

### O. Background checks and waiting (R7)

Open again, 2026-11-18. The maintainer chose the first option of an
earlier version of O, which assumed a background check never met Proof.
Review found the reverse ([Problem](#problem)): its launch meets Proof
today, at a commit and at the turn's end, and its result is never read.
So O is restated around two questions: (a) whether a background check
still running meets Proof at a commit, and (b) how its later result is
judged. In every option the waiting-on-the-user half stays as chosen:
text only, the Proof text naming the skip line for it.

1. **Recommended: a background launch is not a check.** (a) It meets
   Proof neither at a commit nor at the turn's end; (b) its result is
   not read. `actions._checks` skips a call whose `background` is true,
   and the contract's "not in the background" covers a harness
   background run as well as `pytest &`. The Proof text says that a
   session waiting on a background check writes the skip line naming
   `verification-before-completion` with what it waits for, or runs the
   check in the foreground. No event model change. Trade-off: a wait over
   several turns writes the skip line each turn, so item 10's cost stays
   for background checks; but no launch passes for a proof.
2. **A running check defers Proof, and its result is judged when it
   arrives.** (a) Not at a commit, which needs a finished check; at the
   turn's end it meets Proof with a new `check_pending` notice. (b) A new
   entry kind for a background shell command finishing, with its exit
   status; the Claude Code adapter reads it from the task notification
   that continues the turn. A pass proves the change; a failure makes
   Unfinished needed in the turn it arrives, even one with no code
   change, through cross-turn state of pending checks. The event model
   moves to version 4 (with L's `reads_owed`, one bump). Trade-off: the
   most work (schema, adapter transcript reading, state), and a check
   whose result never arrives is never judged.
3. **Keep today's behaviour and state it.** The launch counts; the
   contract says so. Trade-off: a failing background check never
   surfaces, so Proof proves nothing for it.

### P. Router-first on a continued prompt (R8)

1. **Chosen: a `continue` route line meets `router-first` in a
   briefed session's task**, as R8 states. The router would only say
   `continue`. Trade-off: the agent judges the prompt continues the task
   without the router's classification.
2. **The brief's exemption lasts until the next compaction**, whatever
   the prompts. Trade-off: a typed prompt that starts new work runs
   without the router.
3. **No change.** Trade-off: one router load per briefed session that a
   person types into.

### Q. The `true` carrier call (item 12; no ticket)

Claude Code records a message only after the hook's check, and may store
a message that makes a tool call as a summary without the line, so a line
in reply text cannot be trusted and a call's field must carry it.

1. **Chosen: keep it; no ticket.** R3's one clearing section
   shortens the advice around it, and R5 removes the holds most often
   cleared this way. Trade-off: one extra call per held call without a
   field for its line.
2. **Read the held call's own message once recorded.** A retry after
   writing the line in reply text passes when the stored text keeps it,
   and the carrier is advised only when it does not. Trade-off: an
   adapter rule over a harness detail the contract calls unreliable; when
   it fails the agent pays a second retry.
3. **The typed override only.** Trade-off: the person must type it; an
   agent cannot clear its own reasoned skip.

## Deferred

- **Item 6, pointing a reference hold at a section** (such as
  `coding.md#testing`). Not cheap: a reference counts as read only when
  read whole, so a section would need its own read rule (a ranged read
  covering the section, found through the index's section ids), a lasting
  record per section, and new hold text. It needs its own spec.

Item 13 (orientation by partial reads) repeats item 1 and is covered by
decision H.

## Open Questions

- O (the maintainer): whether a background check's launch meets Proof,
  restated after review.
- L1 (the maintainer): confirm it as narrowed at review (`design` keeps
  holding; a write whose lines cannot be counted is held).
- K2 (the maintainer, optional): review asked whether K2.1 should stand.

The combined ranking orders the work: L (item 7), H (item 1), N and O
(items 9 and 10), M (item 8), P (item 11), I and J (items 3 and 4), K
(item 2). Q (item 12) has no ticket.

## Sources

- The lead's curated note, `.local/goated/hook-feedback-round5.md`
  (ignored; summarized above).
- `stack/enforcement-contract.md`: Terms, the `pipeline`, `design`,
  `design-reads` and `scripted-edit` rows, Hold Messages, Shell Reading,
  the design references table, Registry Reference Signals.
- `adapters/core/goated_core/` at `bf18b3b`: `gates.py` (`_files_read`,
  `shown_holds`, `ORIENTATION_READS`), `actions.py` (`_small_edit`,
  `_scripted_edit_hold`), `design_reads.py` (`_signals`, `comment_only`),
  `wording.py` (the advice slots), `shell.py` (`FILE_PRINTERS`),
  `reference_reads.py` (`PATTERNS`, checked by running
  `Pattern.token` on the reported lines).
- The contract's Closeout Items and the `router-first` row, for items 9
  to 11.
- `stack/goated-stack.yaml`: `tdd`'s `test-design.md` signal.
- `tickets/hook-friction-round-3-waves.md`: the round 3 "kept" rows.
