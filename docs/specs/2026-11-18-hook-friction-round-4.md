# Hook Friction Round 4

## Status

Ticket Ready, 2026-11-18. R1 to R3 follow the lead's curation of the
round 3 feedback. R4 to R6 state the maintainer's decisions of 2026-11-18
on C, D1 and D2, each the recommended option
([Decisions](#decisions)). Builds on
[the portable enforcement core spec](2026-11-17-portable-enforcement-core.md):
every change here is made once, in the shared core that
[Ticket 081](../../tickets/archive/081-shared-enforcement-core.md) creates at
`adapters/core/`, and stated in
[the enforcement contract](../../stack/enforcement-contract.md).

R7 to R12 are an addendum of 2026-11-18
([Addendum](#addendum-rule-gaps-left-by-ticket-081)): rule gaps Ticket 081
found and documented in the contract instead of fixing. The maintainer
decided E, F and G on 2026-11-18, each option 1, the recommended one; all
of R7 to R12 are ticket ready.

## Mode

Compact.

## Problem

The agents that implemented Tickets 079, 095, 096 and 098 reported which
holds fired and which were worth it. They kept round 3's verdict: the
red-flags question, proof after the last change, the commit change read,
the early closeout note, joint holds and the design references for a new
public function all earned their place. The holds improved discipline, not
correctness: none caught the logic bugs that review found in 098.

Each friction item was checked against main at `2a0e691`. Function names
are as they are there, in `adapters/claude-code/goated_adapter/`; after
Ticket 081 they live in `adapters/core/`, perhaps under new module names.

- **Fixture data read as configuration.** `design-reads` applies to "a
  configuration file that is neither a lock file nor test data"
  (`design_reads.applies`). Test data means a path `is_test_path` matches,
  which knows `tests/`, `test/`, `__tests__/` and a top-level `spec/`, but
  not `fixtures/`. So a YAML file under `stack/fixtures/` is configuration,
  and every edit of five or more lines selects `decoupling.md`
  (`design_reads._signals`, "edits a configuration file"). One agent
  skipped it four times; another met a hold on a YAML comment.
- **Mocking reference on bare words.** The registry's `mock-or-patch`
  pattern (`reference_reads.PATTERNS`) matches any word starting with
  `patch`, `mock`, `stub`, `spy` or `fake`, and any word ending in `Mock`,
  inside strings too, by design. Test data that names `patch` or holds the
  string `"MagicMock"` asks for `tdd/references/mocking-and-seams.md`.
- **Comment-only edits asking for design reads.** An edit adding a comment
  or docstring of five or more lines selects `readability.md` (199 lines),
  and the same edit is substantial for the `design` gate. The closeout's
  Design item already lets a comment-only edit go without a second
  red-flags read (`_closeout_items`, `comment_only`), but a turn whose only
  code change was a docstring rewrap still owes the item.
- **Skip lines last one turn.** A skip line counts only in its turn
  (contract, Holds: "Route and skip lines ... count only in their turn"),
  and it names a skill, not a file. The same skip for the same kind of file
  is written again each turn.
- **Messages from other sessions.** A prompt with `author: session`
  (another session's message, such as a lead's) opens a turn, so the
  `route-line` gate holds its first write until the agent writes
  `goated-route: continue`. A report from the session's own subagent
  continues the turn instead (Ticket 094). One agent lost three parallel
  edits to the first such hold.
- **Proof while waiting.** At the turn's end the closeout asks for Proof
  from a session that reports it is waiting on another session. A skip
  line naming `verification-before-completion` already clears it; the hold
  text does not say that this case is what it is for.
- **The `true` carrier call.** A line that must ride with a call that has
  no field for it still needs a shell `true` call. The hold's advice works
  each time. Kept; no change.

## Goals

- Fixture data never asks for the configuration reference.
- The mocking reference is asked for a mock or patch in code, not a word
  in data.
- A short comment-only edit asks for no design reads and no Design item.
- A deliberate skip of a read is not retyped for the same kind of file
  each turn (decision C).
- A message from another session that continues the work does not cost a
  held write (decision D1).
- A session waiting on another session can end its turn honestly without
  a token check (decision D2).

## Non-Goals

- Changing what the kept holds require: the red-flags read and question,
  Proof after the last change, change reads, joint holds, the early
  closeout note, and the references a new code file or public definition
  selects.
- The `true` carrier call (feedback item 8).
- Overrides from anything but a person's prompt. No change here lets a
  message from another session carry an override.
- `security` and the closeout's `Setup` item for files under `fixtures/`:
  a fixture `.env` or `settings.json` keeps today's handling.
- The registry's other pattern and its other references.
- Holds inside a subagent, which stay as they are.
- Any harness-specific change: the Claude Code adapter only translates.

## Requirements

- **R1, fixture data is test data** (feedback item 1). A file under a
  folder named `fixtures` or `__fixtures__`, at any depth inside the
  project, is test data. A configuration file that is test data is not
  judged by `design` or `design-reads`, as a configuration file under
  `tests/` is not today. A code file under such a folder stays a code
  file; whether it is a test file keeps today's rule.
  - Touches: `design_reads.applies` and `_is_config`; the contract's Terms
    (Code file, Test file) and the `design-reads` row.
- **R2, mocks and patches in code** (item 4). The `mock-or-patch` pattern
  matches:
  - `patch` only as a call or decorator: `patch(`, `@patch`, `mock.patch`,
    or `patch.<name>(` such as `patch.object(`; `monkeypatch` stays a word
    match;
  - the other words (`mock`, `stub`, `spy`, `fake`, a name ending in
    `Mock`, `jest.fn`, `vi.fn`, `sinon`) as today, except inside a quoted
    string on the added line.

  A match inside a quoted string selects nothing. Where a line's strings
  cannot be read with certainty, it selects, as today. The registry's
  pattern description stays true of the narrower match.
  - Touches: `reference_reads.PATTERNS`, its comment, and the registry's
    `reference_patterns` entry in `stack/goated-stack.yaml`; the contract's
    `reference-reads` row and Detection Detail.
- **R3, short comment-only edits** (items 5, 7). An edit that is
  comment-only (`design_reads.comment_only`, unchanged) and adds fewer
  than 20 lines:
  - is not substantial for the `design` gate;
  - selects no reference by its comment (`readability.md`);
  - is not a code change the closeout's Design item counts: it neither
    makes the item needed nor needs a change read after it.

  A comment-only edit of 20 or more lines is judged as today. A file whose
  comment syntax the core does not know is never comment-only, as today.
  - Touches: `design_reads._signals`, `actions._design_need`,
    `actions._designing` and the Design item in `_closeout_items`; the
    contract's `design` and `design-reads` rows and the `Design` closeout
    row.
- **R4, how long a skip lasts** (item 2). Decision C, option 2 (the
  maintainer's): a skip line that clears a `design-reads` or `reference-reads` hold lasts, for
  the references that hold named and the same kind of file (test,
  configuration, other code), until the task ends or the next compaction,
  as the reads those gates ask for already last. Every other skip keeps
  lasting one turn. A later hold the lasting skip covers passes with a
  notice naming the skip.
  - Touches: the contract's Holds section ("count only in their turn")
    and the two gate rows; the core's skip lookup (`_Proof.skips`) and
    session state, which would keep the task's lasting skips.
- **R5, another session's message** (item 3). Decision D1, option 2 (the
  maintainer's): in a session with a task, a prompt with `author: session` opens a turn
  whose route is `continue` until a route line in the turn says
  otherwise. The `route-line` gate does not hold that turn. The turn is
  still new: it carries no override, and its skip lines, checks and
  change reads start empty. A person's prompt is unchanged.
  - Touches: the contract's "Prompts, Turns, And Tasks" and the
    `route-line` row; the core's route-line check (`gates.check_routing`,
    `_task_route_in`). The event model needs no change: `author: session`
    already marks these prompts.
- **R6, a session waiting on another** (item 6). Decision D2,
  option 1 (the maintainer's): no rule change. The Proof item's text says
  that a session waiting on another session's result may write
  `goated-skip: verification-before-completion: <what it waits for>`.
  - Touches: the Proof item's text in `_closeout_items`, and the
    contract's Hold Messages only if it states that text.

Every change to a rule updates `stack/enforcement-contract.md` and a
conformance scenario under `stack/fixtures/enforcement/` in the same
change, as `AGENTS.md` requires.

## Acceptance Criteria

- [ ] **AC1.** A five-line edit of `stack/fixtures/x.yaml` or
      `a/fixtures/b.json`, with `software-design-principles` loaded, meets
      no `design-reads` hold; the same edit of `config/app.yaml` still
      asks for `decoupling.md`. A conformance scenario covers both.
- [ ] **AC2.** In a test file, with `tdd` loaded, an added line holding
      `"patch"` or `"MagicMock"` only inside a string, or the bare word
      `patch`, asks for no mocking reference; `@patch("x")`, `mock.patch(`,
      `patch.object(` and `m = MagicMock()` each do. A conformance
      scenario covers a hold and a near miss.
- [ ] **AC3.** A comment-only edit of a Python file adding 19 lines meets
      no `design` or `design-reads` hold and, as the turn's only code
      change, no Design item; one adding 20 lines is judged as today. A
      conformance scenario covers the near miss.
- [ ] **AC4.** R4, with a scenario in which a lasting skip
      covers a later turn and one in which it does not (another
      reference, another kind of file, or a new task).
- [ ] **AC5.** R5, with a scenario for a session-authored
      prompt in a task and one for a person's prompt, which is still held.
- [ ] **AC6.** R6: a test shows the Proof text
      names the waiting case.
- [ ] **AC7.** The contract states every changed rule, and
      `tests/test_enforcement_contract.py` and the scenario runner pass.
- [ ] **AC8.** The repo checks in `AGENTS.md` pass.

## Proof Surface

The conformance scenarios, run against the core through both of 081's
ways in. The Claude Code adapter's tests show the same outcomes through
its hook.

## Constraints

- All work lands after Ticket 081, in `adapters/core/`, so each rule
  changes once.
- Hold first lines (`goated-hold: <gate> | <kind>`) do not change.
- Skill texts change only where a rule they state changes.

## Decisions

The maintainer decided C, D1 and D2 on 2026-11-18, each the recommended
option: C2, D1.2 and D2.1. The options are kept as the record of what was
weighed.

### C. How long a skip line lasts (R4)

1. **Keep one-turn skips.** No ticket. R1 removes the case that caused
   the repeats. Trade-off: rarer repeats stay.
2. **Chosen: read-gate skips last the task, per reference and file
   kind**, as R4 states. A read those gates ask for already counts until
   the compaction, so a reasoned skip of the same read lasting as long is
   symmetrical. Trade-off: a later edit that does need the reference goes
   unasked until the task changes or the context compacts, and the skip's
   reason was written for one file, not every file of its kind.

   The notice a covered hold passes with is a new kind, `skip_carried`,
   so the event model moved to version 3 (the maintainer's choice,
   2026-11-18, made while Ticket 101 was in progress). The other choices
   were to reuse `warning` or `session_notice`, whose meanings do not fit.
   Tickets 084 and 085 had not started, so they target version 3.
3. **Every skip line lasts the task.** Trade-off: one skip of
   `software-design-principles` would stand down `design`, `design-reads`,
   `scripted-edit` and the Design item for the whole task; the closeout
   would lose its per-turn check.

### D1. Another session's message (R5)

1. **Keep the hold; sharpen its text** for a session-authored prompt, so
   the agent writes `goated-route: continue` before parallel edits.
   Trade-off: one held call per message remains.
2. **Chosen: a session-authored prompt opens a turn whose route is
   `continue`**, as R5 states. Trade-off: a peer message that starts new
   work runs under the old route unless the agent writes a fresh one; the
   router's "at the start of each new task" is no longer checked for
   prompts nobody typed. No override rides in and per-turn proof resets,
   so the widening is limited to the route.
3. **A session-authored prompt continues the turn**, as a report from the
   session's own subagent does. Trade-off: the turn's lines, skips, proof
   and a person's earlier overrides would cover work a non-person asked
   for; the widest option.

### D2. A session waiting on another (R6)

1. **Chosen: text only.** The existing skip line already fits; the
   Proof text names the case. Trade-off: the agent still writes one line.
2. **A status line defers Proof.** A reply line such as `Status:
   NEEDS_CONTEXT` or `BLOCKED` at the turn's end defers the Proof and
   Unfinished items (never at a commit). Trade-off: a new line grammar in
   the shared policy and the marker fixtures, and a way to end a turn
   without proof that gives no reason.
3. **Defer the whole closeout** while the reply says it is waiting.
   Trade-off: Docs, Design and Review drop with it.

## Open Questions

None.

## Addendum: Rule Gaps Left By Ticket 081

Ticket 081's review found places where the core's code was looser than, or
different from, the contract. Where fixing one would change a rule, 081
corrected the contract to describe the code and left the rule as it was.
Each gap below was checked against main at `c7fc561`, in
`adapters/core/goated_core/`. The goals, non-goals and constraints above
still apply: hold first lines do not change, and every rule change updates
the contract and a conformance scenario in the same change.

One reported gap is not real: `git pull --abort` is not a git command
(git 2.55 answers `unknown option 'abort'`, exit 129), so it can end
nothing. A pull's conflict ends with `git merge --abort` or
`git rebase --abort`, which already end it. The contract's mention of
`git pull --abort` can go when R10 changes that paragraph.

### Requirements

- **R7, a shell pull request's repository.** A shell `gh pr create` or
  `gh pr new`, or `glab mr create` or `glab mr new`, with `--repo` or `-R`
  is measured as a `pull_request` call naming that repository is: only
  when it matches the checkout's `origin`, and not at all otherwise. A
  host prefix (`github.com/owner/repo`) or a full URL names the same
  repository as `owner/repo`.
  - Today: `shell.py` skips the option and its value; `actions.py`
    measures `opens_pr` with `changed_lines(cwd, base, head)` and no
    repository.
  - Contract: Commits And Pull Requests (the `repository` bullet).
- **R8, JavaScript writes need a file-system receiver** (decision E,
  option 1). `.open`, `.rename`, `.rm`, `.unlink`, `.rmdir`, `.truncate`,
  `.cp` and `.copyFile` count as writes only on `fs`, `fs.promises`,
  `fsPromises`, `Deno`, or a name the script binds to a `require` or
  `import` of `fs`, `node:fs`, `fs/promises` or `node:fs/promises`, a
  destructured name included. A receiver the core cannot name (`a[b].rm(`)
  counts, as today. So `window.open(url, 'width=200')` and `db.rm(id)`
  write nothing.
  - Today: `script_writes.py`'s `js` table matches `.<name>(` on any
    receiver, and judges `.open` by its second argument alone.
  - Contract: Shell Reading, the script writes table and the paragraph
    after it.
- **R9, `nul` in a posix shell** (decision F, option 1). Null devices are
  per shell. A `posix` command's redirect into `nul` (any case) writes a
  file named `nul`, as bash does, and is held as a write; the hold text
  names `/dev/null` as the posix null device. `nul` stays a null device in
  a `powershell` command.
  - Today: `shell.NULL_TARGETS` holds `nul` for both shells.
  - Contract: Shell Reading (the `NULL_TARGETS` bullet).
- **R10, conflicts opened and ended.**
  - A finished `commit` call ends an open conflict, as a finished shell
    `git commit` does.
  - Decision G, option 1: per file, as a file read. A plain-read command
    (`cat`, `head`, `tail`, `type`, `Get-Content`) whose finished output
    has a marker at a line start opens the conflict for writes to the
    files it names; a `git diff` opens it for each path whose
    combined-diff section shows a marker after the diff prefix
    (`++<<<<<<<`, `+<<<<<<<`).
  - Today: `actions._open_conflict` reads markers from `file_read` calls
    only, and ends a conflict on shell commands only.
  - Contract: Conflicts.
- **R11, definition starts.** A public top-level definition is counted in
  a code file only, never in a configuration file. `async` starts one only
  before `def`, `function` or `fn`; `pub` only before a definition keyword
  (`fn`, `struct`, `enum`, `trait`, `type`, `const`, `static`, `mod`,
  `union`, `impl`, `async fn`, `unsafe fn`, `extern`), so `pub use x`
  re-exports and defines nothing.
  - Today: `design_reads.DEFINITION_START_RE` decides by the first word
    alone, in code and configuration files.
  - Contract: the `process.md` row of the design references table, and the
    rows that say "the same as `process.md`".
- **R12, a reviewer must start work.** A reviewer agent is a finished
  spawn that starts work now (`starts_now`) and is not `separate`. A spawn
  that only proposes work reviewed nothing.
  - Today: `actions._reviewer_returned` tests `not call.separate` only.
  - Contract: Reviewer Agents.

### Acceptance Criteria

- [ ] **AC9.** R7: `gh pr create --repo other/x` from a checkout whose
      `origin` is not `other/x` is not measured; `-R` naming the
      checkout's own repository is measured as today. A scenario covers
      both.
- [ ] **AC10.** R8: `node -e "window.open(u,'width=200')"` and
      `node -e "db.rm(id)"` meet no `scripted-edit` hold;
      `fs.rmSync(p)`, `fs.promises.rm(p)` and `fs.open(p,'w')` still do.
- [ ] **AC11.** R9: a posix `echo x > nul` is a write that meets the
      write gates; the same in a `powershell` command is not. Scenarios
      cover both.
- [ ] **AC12.** R10: after a conflicted merge, a finished `commit` call
      ends the conflict; a `cat` of a marked file opens it for a write to
      that file and not to another, and a scenario covers the hold and
      the near miss.
- [ ] **AC13.** R11: an added `pub use x;` or `async_helper = 1` line, or
      a YAML `class: foo` key, selects no `process.md`; `pub fn run()`,
      `async def run()` and `async function run()` still do.
- [ ] **AC14.** R12: a proposed (`starts_now` false), not separate spawn
      with a reviewer brief meets no Review item and opens no
      `review-intake` hold.
- [ ] AC7 and AC8 apply to each.

### Addendum Decisions

The maintainer decided E, F and G on 2026-11-18, each option 1, the
recommended one. The options are kept as the record of what was weighed.

#### E. Which receivers write (R8)

1. **Chosen: known file-system receivers.** The calls count on `fs`,
   `fs.promises`, `fsPromises`, `Deno`, or a name the script binds to a
   `require` or `import` of `fs`, `node:fs`, `fs/promises` or
   `node:fs/promises`, a destructured name included. A receiver the core
   cannot name (`a[b].rm(`) counts, as today. Trade-off: a file-system
   object passed in as a parameter goes unseen.
2. **Known non-file receivers write nothing**: `window`, `document`,
   `location`, `db`, and a growing list. Trade-off: an open-ended list;
   each new false hold is a new entry.
3. **Fix `.open` only**: `.open` counts on a file-system receiver or with
   a flag-shaped literal; the other names keep any receiver. Trade-off:
   `.rm` and `.cp` on other objects stay held.

#### F. `nul` in a posix shell (R9)

1. **Chosen: null devices per shell.** A posix `> nul` writes a file
   named `nul` and is held as a write; the hold text names `/dev/null` for
   a posix command. Trade-off: one more held call where an agent types the
   Windows habit, though the file it leaves is real (and on Windows hard
   to delete).
2. **Keep `nul` a null device in both shells.** No ticket for R9.
   Trade-off: the stray file goes unseen, and the contract keeps saying
   so.

#### G. Markers a shell command shows (R10)

1. **Chosen: per file, as a file read.** A plain-read command (`cat`,
   `head`, `tail`, `type`, `Get-Content`) whose output has a marker at a
   line start opens the conflict for the files it names; `git diff`
   output opens it for each path whose combined-diff section shows a
   marker after the diff prefix (`++<<<<<<<`, `+<<<<<<<`), which today's
   line-start pattern does not match. Trade-off: more reading of output; a
   command naming several files opens all of them.
2. **Any shell output with a marker opens it for any write**, as a git
   conflict result does. Trade-off: simpler, but a `cat` of a doc that
   quotes a marker holds every write for the rest of the turn.
3. **No change** for the shell-read half. Trade-off: an agent that
   inspects with `cat` and then edits is not held.

## Sources

- `stack/enforcement-contract.md` — Terms, Holds, the `design`,
  `design-reads`, `reference-reads` and `route-line` rows, the `Proof` and
  `Design` closeout rows, and "Prompts, Turns, And Tasks".
- `adapters/claude-code/goated_adapter/design_reads.py`,
  `reference_reads.py`, `actions.py`, `gates.py`, `transcript.py` — the
  behaviour each problem item describes, at `2a0e691`.
- `stack/schemas/enforcement-event-model.schema.json` — prompt `author`.
- `stack/goated-stack.yaml` — the `mock-or-patch` pattern.
- Addendum: `adapters/core/goated_core/actions.py`, `shell.py`,
  `script_writes.py` and `design_reads.py` at `c7fc561`; the contract's
  Conflicts, Commits And Pull Requests, Reviewer Agents and Shell Reading
  sections and the design references table.
