# GOATED Enforcement Contract

This file states, in words that name no harness, every rule a GOATED
enforcement adapter enforces. Under
[ADR 0003](../docs/adr/0003-opt-in-framework-enforcement-adapters.md) an
adapter enforces portable contracts and never defines them; under
[ADR 0004](../docs/adr/0004-portable-enforcement-core.md) the rules live in
one shared core behind the
[event model](schemas/enforcement-event-model.schema.json), and this file is
what that core enforces.

Each gate enforces a rule that a skill, the shared policy, or the registry
owns. This file cites that owner and does not restate its procedure. What
this file owns is how a rule is judged from events: what is held, what
clears it, and how a hold is shown.

A rule change updates this file and a conformance scenario under
[`fixtures/enforcement/`](fixtures/enforcement/README.md) in the same change.
A test fails when a gate an adapter can return is missing from the
[Gates](#gates) table.

## Contents

- [Terms](#terms)
- [Lines](#lines)
- [Holds](#holds)
- [Gates](#gates)
- [Closeout Items](#closeout-items)
- [Hold Messages](#hold-messages)
- [Overrides](#overrides)
- [Prompts, Turns, And Tasks](#prompts-turns-and-tasks)
- [Subagents](#subagents)
- [Notices](#notices)
- [Failing Open](#failing-open)
- [What An Adapter May Leave Out](#what-an-adapter-may-leave-out)
- [Known Gaps](#known-gaps)
- [Detection Detail](#detection-detail)

## Terms

The event model's names are used throughout: call kinds, turns, entries,
prompts and their authors, and the project.

- **Write**: a `file_write` call, or a `shell_command` that writes files.
  **Spawn**: a `spawn` call that starts work now (`starts_now`), or that
  carries a brief a person may start later. **Command**: any
  `shell_command`. Every other call is never held.
- **Code file**: a file with a programming-language extension. Docs and
  configuration are not code. **Test file**: a code file under a `tests`,
  `test`, or `__tests__` folder at any depth inside the project, or a
  top-level `spec` folder, or named `test_*`, `*_test.*`, `*_spec.*`,
  `*.test.*`, or `*.spec.*`. A file whose place in the project is unknown is
  not a test file.
- **Inside the project**: under any of `project.folders` or the nearest
  checkout above one. A file is outside only when that is certain; in doubt,
  it is inside. A **scratch file** is outside the project, inside no
  checkout, outside `project.agent_folders`, and not a folder holding the
  project.
- **Change**: a write to a file inside the project, or by a subagent this
  turn spawned. A shell write whose files cannot be named counts as a change
  to non-test code.
- **Check**: a test runner, linter, type checker, or build command, or a
  script whose name says test, check, lint, verify, validate, or build. Inline
  interpreter code is not a check.
- **Counts as loaded**: a finished, successful `skill_load` of the skill, or
  a `skill_invoked` entry, since the last compaction. A load counts by its
  bare name, or under a namespace the user configured. Naming a skill in text
  is not a load.
- **Whole read**: a finished, successful `file_read` with `whole` true. A
  read asked for by a hold counts until the next compaction; partial reads
  never add up to a whole one.
- **Change read**: a finished call after the last change a step covers that
  puts the change in front of the agent: a command that prints the diff's
  content, or a read of a file the turn changed. A listing of names or
  counts does not count, nor does a read chained in the held command or made
  in parallel with the held call.

## Lines

The route line, the skip line and the skills line are defined by their
owners: the route line by the `using-goated-ai-skills` router's output
contract, the skip line by the shared policy (`stack/AGENTS.md`), and the
skills line by `handoff`'s `references/spawn-brief.md`. Their grammar is
[`fixtures/markers/README.md`](fixtures/markers/README.md).

Where a line counts:

- in a `reply_text` entry, or in a call's `line_text`, which an adapter fills
  when its harness may not keep reply text whole. A line in a call counts
  from that call on, so it covers the call itself. No other field counts:
  file text, edit text, and commands never carry a line;
- in the session's first prompt, when it starts the session
  (`starts_session`): its last route line is the first turn's route, until a
  prompt a person wrote opens a turn;
- only in its own turn, and only for the agent that wrote it;
- outside fenced blocks, as a whole line. The last route line wins.

No line is ever read from a prompt, so a line quoted in a prompt counts for
nothing, and no override is ever read from a call or a reply.

## Holds

There are two kinds of hold:

- **strict**: clears only on proof of use or a person's override;
- **justified-skip**: also clears on a skip line naming its skill with a
  reason of three or more words, in the current turn.

Every hold follows these rules:

- **No free retry.** A hold is decided from the events, so repeating a held
  call unchanged gives the same answer until the proof, line, or override
  appears. A held call is recorded as held, and never counts as a change, a
  check, or a read.
- **Every hold at once.** A call is judged by every gate, and one decision
  carries every hold it meets, in firing order: the routing gates
  (`router-first` and `route-line` together, then `pipeline`), then the
  action gates for the call's kind:
  - a file write: `conflict-resolution`, `security`, `review-intake`,
    `design` or `design-reads`, `reference-reads`, `repeated-failure`;
  - a shell command: `conflict-resolution`, `commit` (with the closeout in
    its place once `commit` passes), `pull-request`, `pr-review`,
    `security`, `review-intake`, `scripted-edit`, `reference-reads`,
    `repeated-failure`;
  - a `commit` call: `commit`, then the closeout in its place; a
    `pull_request` call: `pull-request`, `pr-review`; a spawn: `spawn`.

  `pipeline` is judged once the router counts as loaded and the turn has a
  route line, and the closeout at a commit once the `commit` gate passes
  the commit; each may follow on the retry. The [Gates](#gates) table lists
  gates by subject, not in this order.
- **Loads count until the next compaction**, in this turn or a later one, as
  do the reads a hold asks for. Route and skip lines, overrides, change
  reads, the red-flags read after the last change, and proof by a check
  count only in their turn.
- **A skip line never clears a strict hold.** To drop a skill a route
  requires, write a corrected route line without it.
- **Scratch writes.** `router-first`, `route-line`, and `pipeline` let a
  write through when every file it writes is a scratch file. A shell command
  passes only when every part of it is a plain read, a folder change, or a
  command that only writes, copies, moves, or removes the files it names.

## Gates

Clear ways: `proof` is the gate's own proof of use, in the Clears column;
`skip-line` is a skip line naming the gate's skill; `override` is a person's
override (see [Overrides](#overrides)); `route-line` is a route line in the
turn, or a corrected one that drops the requirement; `brief-route` is a
route line in the brief that started the session.

| Gate | Kind | Holds | Clears | Clear ways | Enforces |
| --- | --- | --- | --- | --- | --- |
| `router-first` | strict | A write, spawn, or command while the router does not count as loaded; a command made only of plain reads passes | The router counts as loaded; or, until a person's prompt opens a turn, the session's first prompt is a brief with a route line | `proof`, `brief-route`, `override` | The router's "use at the start of each new task before the first edit or command" |
| `route-line` | strict | The first write or spawn after each prompt until the turn has a valid route line; also `goated-route: continue` when no task is known | A valid route line in the turn | `route-line`, `override` | The router's output contract |
| `pipeline` | strict | A write or spawn while a `requires:` skill of the task does not count as loaded; in a session routed by its brief on a `standard` or `full` route, also while orientation is unmet and the orientation skill is installed. A spawn of a read-only agent passes | Each listed skill counts as loaded; orientation by its skill's load or finished reads of three distinct files, partial reads included (gap (a): every other read a hold asks for must be whole; [Ticket 098](../tickets/098-adapter-contract-gaps.md) fixes it) | `proof`, `route-line`, `override` | The router's route line ("must load before the first write") and the shared policy's corrected route line |
| `commit` | strict | A commit, by a git command (not a dry run) or a `commit` call | `commit-message` counts as loaded, an inline message passes the content check, and a change read follows the last change to any project file | `proof`, `override` | `commit-message` ("use before any Git commit") |
| `pull-request` | strict | Opening a pull or merge request, by a `gh` or `glab` command or a `pull_request` call | `pr-description` counts as loaded, and a change read follows the last change to any project file | `proof`, `override` | `pr-description` |
| `pr-review` | justified-skip | Opening a pull or merge request that changes 400 or more lines of non-test code against its base. It is judged together with `pull-request`, so both may hold the same call | `standards-and-spec-review` counts as loaded, and a change read follows the last change | `proof`, `skip-line`, `override` | `standards-and-spec-review`'s rule to review a branch of 400 or more changed lines in code outside test paths (`skills/engineering/standards-and-spec-review/SKILL.md`) |
| `spawn` | strict | A spawn with a brief, except of a read-only agent | `handoff` counts as loaded and its `references/spawn-brief.md` is read whole, or `subagent-driven-development` counts as loaded and its implementer or reviewer prompt is read whole; and the brief passes the content check | `proof`, `override` | `handoff` and `subagent-driven-development` |
| `design` | justified-skip | The turn's first file write adding five or more lines to a non-test code file inside the project, or any such file write while the skill does not count as loaded. A shell write is never judged (gap (b): [Ticket 098](../tickets/098-adapter-contract-gaps.md) adds it) | `software-design-principles` counts as loaded, and every reference the edit's signals select is read whole | `proof`, `skip-line`, `override` | `software-design-principles`, workflow steps 2 and 4 |
| `design-reads` | justified-skip | A later file write to a code or configuration file inside the project, once `software-design-principles` counts as loaded, whose signals select a reference not read whole since the last compaction. A shell write is never judged (gap (b): [Ticket 098](../tickets/098-adapter-contract-gaps.md) adds it) | Each selected reference is read whole | `proof`, `skip-line`, `override` | `software-design-principles`'s Read now lists |
| `reference-reads` | justified-skip | A write inside the project (or anywhere, for a `gate-fires` signal) that fires a signal the installed registry declares for a reference of a skill that counts as loaded | Each named reference is read whole | `proof`, `skip-line`, `override` | The registry's `references` signals (`stack/goated-stack.yaml`, `skills/README.md`) |
| `review-intake` | justified-skip | A write to a code file inside the project once a reviewer agent has reported in the turn: an agent started now by a spawn whose brief followed `subagent-driven-development`'s reviewer template, whose result arrived or, started in the background, whose completion did. Any other brief, and a held or failed spawn, trigger nothing | `receiving-code-review` counts as loaded | `proof`, `skip-line`, `override` | `receiving-code-review` |
| `security` | justified-skip | A write to a security-sensitive path inside the project: dependency manifests and lockfiles, env and key files, files named for secrets, credentials, or tokens, auth, session, and permission code, migrations and schemas, CI, container, and deployment files | `code-security-review` counts as loaded | `proof`, `skip-line`, `override` | `code-security-review` |
| `scripted-edit` | justified-skip | A shell command whose inline script writes a code file inside the project, or a file it names only at run time. It follows `security` and `review-intake` for the same file | A skip line naming `software-design-principles`; loading the skill does not clear it | `skip-line`, `override` | `software-design-principles`: change code with the file edit tools |
| `conflict-resolution` | justified-skip | A write while a merge conflict is open in the turn: an edit whose removed text has a conflict marker at a line start, a write to a file a read showed with one, or any write after a merge, rebase, cherry-pick, revert, or pull reported a conflict, until it finishes or is aborted | `resolving-merge-conflicts` counts as loaded | `proof`, `skip-line`, `override` | `resolving-merge-conflicts` |
| `repeated-failure` | justified-skip | A write once the same check has failed twice in a row in the turn. A run that only fails to load a missing module, the first run after a test file was written, and a run with fewer failures than the one before neither add nor reset | `diagnose` counts as loaded | `proof`, `skip-line`, `override` | `diagnose` ("a check that keeps failing") |
| `closeout` | justified-skip | A commit the `commit` gate passes, or the turn's end, in a turn that changed code or a security-sensitive file or setup, while a [closeout item](#closeout-items) is unmet | Every item is met or skipped | `proof`, `skip-line`, `override` | The shared policy's closeout and the skills each item names |

## Closeout Items

Each item is judged against the turn's last code change. Code a subagent
changed counts at its spawn; if it ran a check after its own last change,
that change is already proved.

| Label | Needed when | Met by | Skip line names |
| --- | --- | --- | --- |
| `Proof` | A change not already proved | A check after the last code change, in a later call or later in the same shell command, joined by sequencing operators, not in the background | `verification-before-completion` |
| `Unfinished` | The last check after the change failed | `handoff` counts as loaded | `handoff` |
| `Docs` | A non-test code file changed | `doc-sync` counts as loaded, and a change read follows the last code change | `doc-sync` |
| `Design` | `software-design-principles` loaded in the turn, or counts as loaded and the turn made an edit the `design` gate triggers on | `software-design-principles/references/red-flags.md` read whole after the last code change that is not comment-only, then a change read; later changes adding fewer than five lines in total need only the change read. The item repeats the question `red-flags.md` ends with; no answer is checked | `software-design-principles` |
| `Review` | The turn changed code, the session was not started from a brief with a route line, and the branch's work is large: 400 or more changed lines of non-test code against its base | A reviewer agent that finished after the last code change; or `standards-and-spec-review` counts as loaded and a change read follows the last code change | `standards-and-spec-review` |
| `Verification` | The turn changed code or a security-sensitive file, and the route is `full`, a spawned agent changed code, a security-sensitive file changed, or the branch's work is large | `verification-before-completion` counts as loaded | `verification-before-completion` |
| `Security` | `code-security-review` counts as loaded and a security-sensitive file changed | A change read after the last sensitive change | `code-security-review` |
| `Setup` | The turn installed or added a named package or tool, or wrote an env or settings file inside the project | `setup-scribe` counts as loaded, before or after the change | `setup-scribe` |

The Setup item is not judged against code changes. A bare install that only
restores what a manifest records, or installs a local path, does not count.

## Hold Messages

A hold's text is shown after its hold line:

```text
goated-hold: <gate> | <kind>
<what the agent must do, in plain words>
```

- The hold line matches
  `^goated-hold: ([a-z]+(?:-[a-z]+)*) \| (strict|justified-skip)$`, alone on
  its line. Measurement tools parse it, so it never changes.
- When a decision carries several holds, one message carries them all in
  firing order: the first as it would be alone, then, after a blank line,
  each further hold with its own hold line and text.
- The text is guidance and may change between releases. It backticks each
  skill it asks for by its bare name, and no other bare word; a file is
  quoted by its path. In the `spawn` hold the two skills are alternatives;
  everywhere else each named skill is a separate requirement.
- The closeout lists each unmet item on its own line, starting
  `- <Label>: `, with the labels of the [Closeout Items](#closeout-items)
  table. The labels are stable.
- A hold asks for a load only when the skill does not count as loaded. A
  hold that asks only for a change read once its skill has loaded names the
  skill without backticks, or only in its skip line.
- A hold that repeats an ask the turn already showed in full is short: it
  opens `Still unmet:` and keeps every skill, reference, and skip line the
  full text names.
- The core returns the rule text. The adapter adds what only its harness can
  say: where a line can be put so the harness keeps it, and which call can
  carry it.

## Overrides

Overrides come only from a prompt a person wrote (`author: person`), apply
only to the turn that prompt opened, and stop at that turn's end
(`turn_ended`). Matching ignores case and the prompt's `pasted` text. A
phrase negated just before it, such as "don't skip routing", is not an
override.

| Phrase | Effect for the turn |
| --- | --- |
| `skip routing`, `skip the router` | Stands down `router-first`, `route-line`, and `pipeline` |
| `skip <skill>`, `skip the <skill> skill` | Stands down every requirement for that skill, in `pipeline`, an action gate, or a closeout item. `skip using-goated-ai-skills` also stands down `router-first`. `<skill>` must be an installed skill, or a registry skill when none can be found |
| `commit message: <text>`, `commit with the message "<text>"`, or a fenced block right after such a phrase | Stands down the `commit` hold for a commit whose inline message has the same subject line |

A recorded override brings an `override_recorded` notice.

## Prompts, Turns, And Tasks

- A prompt with `author: person` opens a turn and may carry overrides. A
  prompt from another session opens a turn with no override. A prompt the
  harness wrote, or a report from an agent this session spawned, continues
  the current turn as an entry: the turn's lines, overrides, checks, and
  change reads stand.
- A compaction opens a turn of its own and clears loads and reads. The route
  carries over, so `goated-route: continue` keeps the task.
- **A task** starts at a route line that is not `continue` and runs through
  later `continue` turns. In a session with no task yet, a turn whose only
  route lines are `continue` starts a task that requires no skills.
  `goated-route: direct` exempts the task from `pipeline`.
- A session whose first prompt is a brief with a route line is **briefed**
  for good: it meets no Review item.

## Subagents

For a subagent (`session.agent.role` of `subagent`):

- the routing gates do not apply, since the parent's brief carries the route;
- every other gate applies, `reference-reads` and `review-intake` aside,
  judged from the subagent's own turn: only its own loads and reads count;
- no override applies;
- the closeout does not run when it stops, and a subagent's commit meets no
  closeout (gap (c): the main agent's commit meets one;
  [Ticket 098](../tickets/098-adapter-contract-gaps.md) adds it for a
  subagent). Its changes count toward the closeout of the parent turn that
  spawned it.

## Notices

A notice never holds.

- `fail_open`: the core could not judge and allowed the event (see
  [Failing Open](#failing-open)).
- `warning`: it judged, but something it reads was missing, such as a
  subagent's turn or the registry.
- `override_recorded`: a person's override for the turn.
- `closeout_note`: after the main agent's first finished file write of a
  turn that changes code inside the project, the closeout items the turn
  will meet, each short, judged as if the turn ended there. Once per turn;
  none in a turn the closeout already held.
- `session_notice`: at a session start, when the shared policy or the router
  is missing, or project agent files the onboarding skills write are
  missing; and at the next person's prompt after a session's third declined
  or unanswered hold, once per session, naming `retrospective`.

## Failing Open

The core never blocks because of its own failure. It allows the event, with
a `fail_open` notice that says why, when:

- the request cannot be read, or its `event_model` is not a version it knows;
- the turns it needs cannot be read, or do not show the prompt the event
  belongs to;
- it hits an internal error;
- its state, where it keeps any, is unsafe to trust.

State that cannot be read is reset, and a reset can only re-hold, never pass.
A finished-call event has no action to let through, so its failure adds
nothing.

## What An Adapter May Leave Out

An adapter enforces less than this contract only where its harness lacks a
hook, documents each gap, and never enforces a rule this file does not
state:

- a harness that cannot hold a call before it runs cannot enforce the call
  gates;
- a harness that cannot hold a turn's end delivers the closeout as a request
  to continue, and documents it;
- a harness that cannot tell who wrote a prompt marks it `unknown`, and no
  override counts from it;
- a harness with no subagents sends none.

## Known Gaps

Where today's adapter is looser than the rule it enforces, this contract
states today's behaviour and marks the gap, and conformance scenarios with
`case: gap` pin it. [Ticket 098](../tickets/098-adapter-contract-gaps.md)
closes each before the rule code moves:

- **(a)** A briefed session's orientation counts partial reads.
- **(b)** `design` and `design-reads` never judge a shell write.
- **(c)** A subagent's commit meets no closeout.

## Detection Detail

The rules above name what is detected. The exact tables (code extensions,
check commands, security path words, package managers, shell parsing,
comment syntax, content checks, branch size) are the reference
implementation's, documented in the Claude Code adapter's README sections
[Shell writes](../adapters/claude-code/README.md#shell-writes),
[Plain reads](../adapters/claude-code/README.md#plain-reads),
[Large pull requests](../adapters/claude-code/README.md#large-pull-requests),
[Design references](../adapters/claude-code/README.md#design-references),
[Registry references](../adapters/claude-code/README.md#registry-references),
[Change reads](../adapters/claude-code/README.md#change-reads), and
[Content checks](../adapters/claude-code/README.md#content-checks). They move
here with the rule code when the shared core is extracted (Ticket 081).
