# Hook Friction Round 6

## Status

Ticket Ready, 2026-11-19, sliced into Tickets 118 to 121
([order](../../tickets/hook-friction-round-6-order.md)); the maintainer has
yet to read the whole text. The maintainer chose an option for every
decision on 2026-11-19 ([Decisions](#decisions)); four of them reverse or reopen choices kept in
rounds 3 to 5, and each says which. No question is open. Builds on
[the round 5 spec](2026-11-18-hook-friction-round-5.md):
every rule change is made once, in the shared core at
`adapters/core/goated_core/`, and stated in
[the enforcement contract](../../stack/enforcement-contract.md).

## Mode

Compact.

## Problem

Seven ticket sessions and their orchestrator, working in another project
with the adapter installed, each reported on the holds in one shared
format. Their average ratings, from 1 (poor) to 5 (excellent):

| Dimension | Average |
| --- | --- |
| Efficiency | 2.1 |
| Distraction (5 means never) | 2.1 |
| Clarity of hold messages | 3.0 |
| Effectiveness | 3.1 |
| Fit of the skills loaded | 3.1 |
| Effect on output quality | 3.4 |

Their shared verdict: the commit-time checks earned their cost and improved
the work; the start-of-prompt and per-edit holds cost the most and gave the
least.

The usage log for the same period (about 28 hours, 50 sessions, two
projects) agrees:

| Measure | Value |
| --- | --- |
| Holds | 570 |
| Holds per session, median | 10 |
| Holds per typed prompt | 4.7 |
| Holds by `design-reads`, `design` and `reference-reads` | 178 |
| `design-reads` holds followed by another in the same turn | 62% |
| Route lines that were `goated-route: continue` | 146 of 217 |
| `closeout` outcomes that were a skip line | 39 of 75 |
| `security` holds answered with a skip line | 11 of 12 |
| Overrides typed by a user | 0 |

Agents obey nearly every hold in the end (7 of 385 outcomes went
unanswered), so the cost is retries and skip lines, not abandoned work.

Each complaint was checked against main at `32a7156` by reading the code;
no probe was run.

- **Edits refused for design reads.** An edit under 30 lines that selects a
  design reference is refused until the reference is read whole; a larger
  write lands and owes the read (Ticket 114). All seven sessions reported
  the refusals as the largest cost, arriving after the design was already
  chosen.
- **A parallel batch lands in part.** The core judges each call alone and
  cannot see the other calls of the same message. When one edit of a batch
  is refused and its siblings land, the file is left half-changed. Four
  sessions hit this, and one lost a cycle to a test failure it caused.
- **Routing holds on typed follow-ups.** Every typed prompt that writes
  needs a route line of its own, though two thirds of route lines only say
  `continue`. Five sessions reported it, each time while the owner waited.
  Round 4 (R5) and round 5 (P) kept this.
- **Orientation after real orientation.** Only three whole-file reads, or
  the orientation skill, orient a session. Five sessions were held after 10
  to 40 ranged reads. Round 5 (H3) kept "partial reads never count".
- **Commit holds arrive in turn.** The commit-message load, the change
  read and the closeout are judged one after another, so one commit can
  take three held attempts (Ticket 095 chose this). The commit change read
  also resets on any project-file change, a Markdown closing note included.
- **A small follow-up fix re-arms the Design item.** Later changes adding
  fewer than five lines should need only a new change read, but the count
  includes the edit's unchanged context lines, so a two-line fix sent with
  three lines of context re-arms the red-flags read. This is a bug.
- **The Docs item ignores docs already changed.** It needs a `doc-sync`
  load whatever the turn did. It was asked 67 times and is the item agents
  skip most.
- **Merge commits get the whole closeout.** A commit that ends a conflict
  is judged like any other; the orchestrator wrote a skip line on about
  eight of them.
- **The security hold matches a file name.** `tests/test_session_*.py`
  matches the auth pattern for a one-line edit of a test list. Test files
  are not exempt and the change itself is not read.
- **The carrier call.** A route or skip line for a call with no field for
  it (a file edit) still rides in a shell `true` call made in an earlier
  message. All eight reports raised it. Round 5 (Q1) kept it.
- **Hold text.** The messages are exact but long, and the one action that
  clears a hold sits mid-paragraph. A malformed route line is quoted
  without saying what is wrong with it. A held read-only command does not
  say which part made it count as a write.
- **Run-time temp paths.** A script that writes a file it names at run
  time is held by `scripted-edit` even when the path is built from the
  system temp folder.
- **Nothing points at the project's own documents.** No hold or notice
  names a project's context file, context matrix or standards, where three
  sessions found the facts that decided their work.
- **The spawn brief omits checks and shared files.** The orchestrator's two
  real mistakes came from briefs: one wave ran the whole suite on every
  branch, the next ran checks too narrow to catch a break between two
  tickets.
- **The log cannot confirm a per-file complaint.** It records no notices
  and nothing about what kind of file a hold was about.

## Goals

- No edit is refused, and no batch half-applied, because of a design
  reference read.
- A typed prompt that continues a routed task needs no route line.
- A session that read from enough distinct files is not held for
  orientation.
- One commit attempt shows everything that commit still needs.
- A comment, a doc edit or a two-line fix does not cost a second diff read
  or a second red-flags read.
- The Docs, Security and merge-commit asks fire where they can find
  something.
- Every hold opens with the action that clears it.
- A hold or notice names the project's own context documents when they
  exist.
- The next round can be judged from the log.

## Non-Goals

- Kept, from the feedback: the red-flags read and its question, a separate
  change read before a commit, doc-sync and verification at closeout, and
  the commit-message contract.
- A diff chained before the commit in the same command still does not
  count as a change read.
- How long a load or a reference read counts: both still end at a
  compaction.
- Which references a trigger selects, and reading a section instead of a
  whole file: [deferred](#deferred).
- The `pipeline` gate does not look at file kind or change size. A route
  that asks for too much is corrected with a new route line.
- A skip line for the closeout Design item still lasts one turn
  (decision X4).
- A visual and interface design reference: it gets its own spec
  ([deferred](#deferred)).
- Any harness-specific rule: an adapter only translates.

## Requirements

- **R1, design reads never refuse an edit** (decision S). An edit that
  selects a design or registry reference lands at any size, and the
  reference is owed.
  - Owed references are collected by the closeout Reads item, at a commit
    and at the end of the turn, as today for large writes. The item stays
    a justified skip (decision S).
  - One notice per turn lists the owed references. A later edit adds to
    the list only the references it newly selects.
  - A reference read whole since the last compaction is not owed again.
  - The `design` gate (load `software-design-principles` before code) is
    unchanged.
- **R2, a typed follow-up continues the task** (decision T). When the
  session's current task has a route, a typed prompt with no route line
  runs as `goated-route: continue`.
  - `router-first` and `route-line` do not hold in that turn.
  - A notice on that prompt says once that new work needs a new route
    line.
  - A route line the agent writes still wins, and the route's required
    skills still apply through `pipeline`.
  - The task's route survives a compaction for this rule. The route's
    required skills are still asked for again after one, as today.
  - A session with no task and no brief keeps today's rule.
- **R3, distinct files orient** (decision U). Reads from five distinct
  project files orient a session, whole or ranged.
  - The file tool counts, with or without a range.
  - A finished, successful shell printer of a named file counts, one file
    for each command part: `cat`, `head`, `tail`, `sed -n`, and
    PowerShell's `Get-Content` and its aliases.
  - A search that prints matching lines, such as `grep`, `rg` or
    `Select-String`, never counts.
  - Three whole reads and the orientation skill still count.
- **R4, one commit-time message** (decision V1). A held commit reports, in
  one message, every unmet ask the commit has: the `commit-message` load,
  the message contract, the change read, and each closeout item.
- **R5, non-code changes keep the commit change read** (decision V2). A
  comment-only edit, or a change to a file that is not code, made after a
  change read does not reset the `commit` gate's change read. Closeout
  items keep their own rules.
- **R6, small follow-ups are counted by what they add** (bug fix). The
  "fewer than five lines" rule for the Design item counts only lines the
  edit adds that its removed text did not hold.
- **R7, the Docs item accepts a doc change** (decision X1). Docs is met
  without a `doc-sync` load when the turn changed a documentation file
  after its last code change and a change read follows that doc change.
- **R8, a conflict's commit asks for less** (decision X2). A commit that
  ends a conflict, in a session with `resolving-merge-conflicts` loaded,
  asks for the change read and Proof, and for the items about what the
  resolution itself did: Reads, Unfinished and Setup. Docs, Design,
  Security, Review and Verification are not asked at that commit (the
  maintainer, 2026-11-19, at Ticket 120's review). Without the load, the
  commit gets the full closeout.
- **R9, test files are not security-sensitive** (decision X3). A test path
  does not match the security path patterns.
- **R10, the carrier probe** (decision W). An investigation establishes
  whether a line the core sees on one call can count for later calls of
  the same message. Its result decides whether a rule follows; this spec
  commits to the investigation only.
- **R11, hold text** (decision Z).
  - Each hold, and each closeout item, opens with its clearing action;
    conditions and caveats follow.
  - A malformed route line is quoted with the reason, such as "nothing may
    follow the line".
  - A read-only-looking command held as a write names the part that made
    it one.
  - A hold on a file edit says that other calls of the same message may
    have landed, and to read the file before sending the edit again.
  - Hold text says a route or skip line may ride on a shell call earlier
    in the same message when the held call is a write (the maintainer,
    2026-11-19, from the carrier probe's
    finding that one message's writes are judged in order).
- **R12, temp paths are outside** (decision Z). A script write whose path
  is built from the system temp folder counts as outside the project.
- **R13, project context pointer** (decision Y1). When the project has a
  context file, a context matrix or a standards profile, the orientation
  hold and the turn's first code-change notice name the ones that exist.
- **R14, spawn brief lines** (decision Y2). The spawn-brief template gains
  a Checks line (what the agent runs, what the starter runs after merging)
  and a Shared-with line (other agents that may change the same files).
  Neither is a required heading.
- **R15, log detail** (decision Y4). The usage log records each notice by
  kind, and for each hold the class of file it was about, never a path.

## Acceptance Criteria

- **AC1** (R1). A 3-line edit adding a public function lands with a notice
  naming its references and no hold; a commit in that turn is held by the
  Reads item until they are read. A second edit selecting the same
  references adds no notice text.
- **AC2** (R1). Four edits sent in one message, each selecting a
  reference, all land.
- **AC3** (R2). In a session with a routed task, a typed prompt followed by
  an edit lands with no route line, and the prompt carries the notice. The
  same prompt in a session with no task is held as today. After a
  compaction, a typed prompt followed by an edit is held by `pipeline` for
  the route's skills, not by `route-line`.
- **AC4** (R3). Five ranged reads of five files orient, by the file tool
  or by `sed -n`; four do not; five searches do not.
- **AC5** (R4). A commit with no `commit-message` load, no change read and
  an unmet Proof item returns one message naming all three.
- **AC6** (R5). After a change read, a Markdown edit and a comment-only
  edit leave the commit unheld; a one-line code edit holds it.
- **AC7** (R6). After a red-flags read, a 2-line replacement sent with 3
  unchanged context lines needs only a change read.
- **AC8** (R7). A turn that changes code, then a doc, then reads the
  change meets Docs with no load. With the doc changed before the code, it
  does not.
- **AC9** (R8). With `resolving-merge-conflicts` loaded, a commit ending
  a conflict asks for no Docs, Design, Security, Review or Verification
  item. The same commit
  without the load, and the next ordinary commit, ask for the full
  closeout.
- **AC10** (R9). An edit to `tests/test_session_x.py` meets no security
  hold; an edit to `src/session.py` does.
- **AC11** (R10). A written finding states, with the commands used, in
  what order the harness judges the calls of one message and whether
  session state written during one is visible to the next.
- **AC12** (R11). Each hold text in the adapter's text fixture opens with
  an imperative action; the malformed-line and held-command texts carry
  their reason.
- **AC13** (R12 to R15). A script writing under the temp folder is not
  held; the orientation hold names an existing context file and names none
  when none exists; the template carries both lines and the `spawn` gate
  still passes a brief without them; a log written by a held edit carries
  a file class and a notice entry.
- **AC14.** Every changed gate has conformance scenarios for holding, each
  way it clears, and a near miss, and the contract states the new rule.

## Proof Surface

The conformance scenarios under `stack/fixtures/enforcement/`, run through
the example translator, and the core's unit tests. Hold texts are proved
through the adapter's generated text fixture. The usage-log change is
proved through its schema.

## Constraints

- A rule change, its contract text and a conformance scenario land in one
  change, as the maintainer contract requires.
- A new notice kind or a changed result shape bumps the event model's
  whole-number version; a new log field bumps the usage-log schema.
- The core stays pure: no harness detail enters it.
- R14 changes an installed skill file, so installed copies need syncing
  after it merges.
- The log never records a path, prompt text or file content.

## Decisions

All chosen by the maintainer on 2026-11-19.

### S. Edits that need a design reference (R1)

- **Chosen: S1, always land and owe.** Reverses round 5's narrowed L1
  ("design keeps holding"). Trade-off: reading always follows the code.
- S2, keep refusing small edits and ask for fewer references: batches
  could still half-apply.
- S3, also announce references at plan time: keyword triggers cannot be
  known before the code exists.

### T. A typed prompt in a routed task (R2)

- **Chosen: T1, infer `continue` with a notice.** Reverses round 4's R5
  and extends round 5's P1. Trade-off: new work typed mid-session runs
  under the old route if the agent ignores the notice.
- T2, infer silently; T3, keep today's rule.

### U. What orients a session (R3)

- **Chosen: U1, five distinct files by any read.** Reverses round 5's H3.
  Trade-off: five small ranged reads orient a session.
- U2, a briefed session needs no orientation; U3, whole reads only.

### V. Commit-time holds (R4, R5)

- **Chosen: V1 and V2, one message, and non-code changes keep the change
  read.** V1 reverses Ticket 095's "may arrive on the retry" for the
  commit. Trade-off of V2: a commit can include doc text the agent did not
  read again.
- A chained diff counting as the read: rejected. The agent could not act
  on the diff before the commit landed.

### W. The carrier call (R10)

- **Chosen: W1, probe first.** Round 5's Q1 stands until the probe
  reports.
- W2, keep the carrier with no probe; W3, a dedicated tool for lines.

### X. Closeout relaxations (R7 to R9)

- **Chosen: X1** (Docs accepts a doc change), **X2** (a conflict's commit
  asks for less) **and X3** (test files are not security-sensitive).
  Trade-offs: a token doc edit meets Docs; a resolution that changes
  behaviour skips those reviews; changes to auth tests go unreviewed.
- **Not chosen: X4**, a Design skip that lasts the task. It would silence
  the red-flags question for later, larger changes, and R6 ends the loop
  behind the complaint.

### Y. Additions (R13 to R15)

- **Chosen: Y1** (project context pointer), **Y2** (spawn brief lines)
  **and Y4** (log detail).
- **Y3, a visual design reference: its own spec.**

### Z. Small fixes (R11, R12)

- **Chosen: all of them.**

## Deferred

- **A visual and interface design reference.** Most findings from the
  owner's page reviews were visual (contrast, alignment, wrapping), and no
  reference covers them. New skill content needs its own spec and ticket.
- **Section reads and fewer references per trigger.** A small new public
  definition still selects three references. R1 moves their cost to the
  closeout; if the Reads item becomes the next most skipped ask, revisit
  with the section ids the reference index already has.
- **Holding or passing a batch as a whole.** It needs the harness to tell
  the core which calls share a message. R1 removes the main cause, and R10
  may remove another.
- **A project-declared proof step and project-declared reference
  signals.** Both need a project-side registry and a view on trusting
  project configuration.
- **Reading a background check's result when it arrives** (round 5's O2).
- **A compaction between an edit and the turn's end.** It starts a new
  turn, so the closeout asks for nothing the earlier part of the turn
  owed, owed reads included. This predates round 6; R1 makes it matter
  more often (found at Ticket 118's review).
- **The conformance runner as a check.** A foreground run of
  `scripts/run_conformance.py` did not meet the Proof item at a commit
  (seen by the lead while merging wave 20). Whether a project can name
  its own check commands belongs with the project-declared proof step
  above.

## Open Questions

None. The maintainer answered the draft's four questions on 2026-11-19:
the route survives a compaction (R2), a conflict's commit needs the skill
loaded (R8), the Reads item stays a justified skip (R1), and shell
printers of a named file count as ranged reads (R3).

## Sources

- Eight session reports from another project, 2026-11-19, and the lead's
  check of each complaint against main at `32a7156`; kept outside the
  repository.
- The usage log's report for 2026-11-18 to 2026-11-19, from
  `adapters/core/goated_usage_report.py`.
- [The round 4 spec](2026-11-18-hook-friction-round-4.md) and
  [the round 5 spec](2026-11-18-hook-friction-round-5.md), for the
  decisions this round reopens.
- [The enforcement contract](../../stack/enforcement-contract.md).
