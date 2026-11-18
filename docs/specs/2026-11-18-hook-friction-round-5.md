# Hook Friction Round 5

## Status

Decision Needed, 2026-11-18. R1 to R4 follow the lead's curation of the
round 5 feedback, items 1 to 4. Each has open options, H to K, with a
recommendation ([Decisions](#decisions)); the tickets are written to the
recommended options and change if the maintainer picks another. Builds on
[the round 4 spec](2026-11-18-hook-friction-round-4.md): every change is
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

## Goals

- A session that oriented by printing whole files with the shell is not
  held for orientation.
- A short code edit with a comment, and new cases added to an existing
  test table, ask for the design reads their substance needs, not their
  line count.
- One message of several holds says once how to clear them.
- The `scripted-edit` hold never says a file is code when it cannot tell.

## Non-Goals

- Kept, from the feedback (item 5): the red-flags read and its question,
  the early closeout notice, doc-sync at Stop, and the commit change read.
- Pointing a reference hold at a section (item 6): [deferred](#deferred).
- The second source's items 7 to 12 ([Not In This Round](#not-in-this-round)).
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
  text says that a whole print counts.
  - Touches: the file printers in `shell.py` (`FILE_PRINTERS`, beside the
    conflict reading), `gates._files_read`, and the orientation text in
    `gates`; the contract's Terms (Whole read), the `pipeline` row and
    Shell Reading. Not `shell.py`'s pull request reading.
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

## Proof Surface

The conformance scenarios, run against the core through both of its ways
in. The Claude Code adapter's tests show the same outcomes through its
hook, and its translation tests show R3's section.

## Constraints

- Work lands in `adapters/core/`, so each rule changes once.
- Tickets 108 and 109 are changing `shell.py`'s pull request reading now.
  Only R1 touches `shell.py`, in its file printers, a different part;
  resolve the shared file at merge time.
- Skill texts change only where a rule they state changes.

## Decisions

Each decision is open. The recommended option is first.

### H. What orients a session (R1)

1. **Recommended: a whole shell print counts, for orientation only**, as
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

1. **Recommended: one closing section per message**, as R3 states.
   Trade-off: an agent reading one hold alone must look to the message's
   end to learn where the line goes.
2. **Merge only identical sentences.** Each hold keeps a placement
   sentence; repeats with the same override drop. Trade-off: holds of
   different skills each keep one, so item 3's three holds stay three.
3. **No change.** Trade-off: the repeat stays; Ticket 095 already cut the
   full advice to once per turn.

### J. The `scripted-edit` words (R4)

1. **Recommended: wording only**, as R4 states. Cheap, and the steering
   stays. Trade-off: a markdown file named at run time is still held.
2. **Wording, and a visible extension decides the kind.** A run-time path
   whose literal tail ends in an extension (`f"{d}/notes.md"`,
   `p + ".md"`) is that kind of file, so a docs file passes. Trade-off:
   more script reading in `script_writes.py`, and the lead judged the
   steering right.

### K. What sizes a design read (R2)

K1 and K2 are separate choices.

- **K1, a comment on a short code edit.**
  1. **Recommended: code lines size the comment signal**, as R2 states.
     It matches Ticket 100's twenty-line comment-only rule. Trade-off: a
     comment of up to nineteen lines on a four-line change goes without
     `readability.md`.
  2. **Code lines size every design rule**: the `design` gate,
     `decoupling.md` and the Design item too. Trade-off: wider; a
     four-line fix with a long comment meets no design gate at all.
  3. **No change.** Trade-off: the reported hold stays.
- **K2, new cases in an existing test.**
  1. **Recommended: case-data lines do not count** toward the test-file
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

## Deferred

- **Item 6, pointing a reference hold at a section** (such as
  `coding.md#testing`). Not cheap: a reference counts as read only when
  read whole, so a section would need its own read rule (a ranged read
  covering the section, found through the index's section ids), a lasting
  record per section, and new hold text. It needs its own spec.

## Not In This Round

The curated note's second source (a product ticket in another project)
added items 7 to 12, and its combined ranking puts item 7, holds firing
after the content is written, first. This round's brief scoped items 1 to
4, so they are recorded here, not ticketed:

- item 7, announce the references an edit will need before it is written,
  or turn design reads into a closeout item (a design choice);
- item 8, mocking-reference false positives (`fake` in data,
  `monkeypatch.setenv`), to check against Ticket 100's narrowing;
- item 9, comment-only and docs-only changes after the last proof keeping
  that proof;
- item 10, closeout while waiting on the user or a background job;
- item 11, `router-first` on a continuing prompt;
- item 12, the `true` carrier call, kept in round 4, asked again.

Decision L, open: whether these go into a round 6 spec (recommended, with
item 7 first) or join this round.

## Open Questions

- H, I, J, K1 and K2 above.
- L: where items 7 to 12 go.

## Sources

- The lead's curated note, `.local/goated/hook-feedback-round5.md`
  (ignored; summarized above).
- `stack/enforcement-contract.md`: Terms, the `pipeline`, `design`,
  `design-reads` and `scripted-edit` rows, Hold Messages, Shell Reading,
  the design references table, Registry Reference Signals.
- `adapters/core/goated_core/` at `bf18b3b`: `gates.py` (`_files_read`,
  `shown_holds`, `ORIENTATION_READS`), `actions.py` (`_small_edit`,
  `_scripted_edit_hold`), `design_reads.py` (`_signals`, `comment_only`),
  `wording.py` (the advice slots), `shell.py` (`FILE_PRINTERS`).
- `stack/goated-stack.yaml`: `tdd`'s `test-design.md` signal.
- `tickets/hook-friction-round-3-waves.md`: the round 3 "kept" rows.
