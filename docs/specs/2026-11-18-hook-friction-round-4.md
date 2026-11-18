# Hook Friction Round 4

## Status

Ticket Ready, 2026-11-18. R1 to R3 follow the lead's curation of the
round 3 feedback. R4 to R6 state the maintainer's decisions of 2026-11-18
on C, D1 and D2, each the recommended option
([Decisions](#decisions)). Builds on
[the portable enforcement core spec](2026-11-17-portable-enforcement-core.md):
every change here is made once, in the shared core that
[Ticket 081](../../tickets/081-shared-enforcement-core.md) creates at
`adapters/core/`, and stated in
[the enforcement contract](../../stack/enforcement-contract.md).

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

## Sources

- `stack/enforcement-contract.md` — Terms, Holds, the `design`,
  `design-reads`, `reference-reads` and `route-line` rows, the `Proof` and
  `Design` closeout rows, and "Prompts, Turns, And Tasks".
- `adapters/claude-code/goated_adapter/design_reads.py`,
  `reference_reads.py`, `actions.py`, `gates.py`, `transcript.py` — the
  behaviour each problem item describes, at `2a0e691`.
- `stack/schemas/enforcement-event-model.schema.json` — prompt `author`.
- `stack/goated-stack.yaml` — the `mock-or-patch` pattern.
