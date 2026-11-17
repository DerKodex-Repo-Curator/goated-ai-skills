# How Adapter Holds Are Delivered, And What They See

## Status

Decisions approved by the maintainer on 2026-11-17 in a grill-with-docs
session, and this text on the same day. R5 and R6 were amended at the
maintainer's request after Ticket 093 merged, for a false hold met in
use (Ticket 097). Ticket ready. Builds on
[the written-line holds spec](2026-11-17-adapter-written-line-holds.md),
[the skill placement spec](2026-11-17-skill-placement-gates.md) and
[ADR 0003](../adr/0003-opt-in-framework-enforcement-adapters.md). Its
companion is
[the low-signal holds spec](2026-11-17-adapter-low-signal-holds.md).

## Mode

Compact.

## Problem

The same agent reports, checked against the adapter on main at `3e3fcb9`,
show problems that are not about any one trigger:

- **One hold per retry.** Routing is judged first, then the action gates
  in a fixed order, and the first hold wins. A test edit was held for one
  reference, then on the retry for another, then for `repeated-failure`,
  and the agent resent a 220-line file three times. Two read-only
  subagent spawns in the planning session for this spec were held three
  times in a row, each resending the brief.
- **Repeated text.** Tickets 060 and 062 made the unseen-line advice
  appear once per turn. Other shared paragraphs still repeat in every
  hold and in every closeout item, and a repeated `Stop` hold prints the
  whole list again. A typical hold is 180 to 240 words.
- **Writes the adapter does not see.** An inline interpreter script
  (`python - <<'EOF'`, `python -c`, `node -e`) counts as neither a write
  nor a read. One agent made every edit to a code file that way, so forty
  new lines met no design hold, no reference hold and no closeout.
- **A subagent's report opens a turn.** A background subagent's report
  that Claude Code records as a prompt from another session starts a new
  turn. The turn's route line, skip lines, checks and change reads are
  dropped, and the `Stop` closeout never sees the changes made before
  the report. In the planning session it also ended the brief's route, so
  the router was asked for again.
- **Closeout after the report.** In a turn that changes code and does not
  commit, the closeout fires at `Stop`, after the final report, and the
  agent reports twice. Every item could have been met earlier had the
  agent known what would be asked.
- **A carrier for skip lines.** An edit call has no field for a skip
  line, so the line goes in another call. The holds do not name one that
  is certain to pass.

## Goals

- A call that would meet several holds is told all of them at once.
- A turn reads each shared paragraph once.
- A code file changed by an inline script is judged like any other edit.
- A report from the session's own subagent does not reset the turn.
- A turn learns its closeout items before its final report.

## Non-Goals

- Changing what any hold requires or what clears it. The companion spec
  changes triggers; this one changes delivery and coverage.
- Changing the format of a hold's first line
  (`goated-hold: <gate> | <kind>`).
- Seeing a write made by a script file (`node build.js`), a wrapped shell
  (`bash -c`), an archive tool or command substitution. These stay Known
  Limits.
- Making the design gates judge shell writes such as `sed -i`.
- Defending against an agent that works to defeat the adapter.
- Messages from sessions other than the session's own subagents, which
  open a turn as today.
- A new line field on edit calls. Claude Code gives them none.

## Requirements

- **R1, joint holds.** A call is judged against every routing and action
  gate, not only until the first hold. When more than one would hold it,
  the message carries each in the order they fire today: the first hold as
  today, then each further hold with its own
  `goated-hold: <gate> | <kind>` line and its text. A hold that can be
  judged only once another clears, such as the closeout at a commit the
  `commit` gate still holds, may follow on the retry. Each hold keeps its
  own kind and its own way to clear.
- **R2, each hold counted.** The skill-usage mod counts every hold in a
  joint message, with its own outcome, as if each had been shown alone.
- **R3, shared text once.** Within one message, a paragraph several holds
  or closeout items share appears once: the change-read explanation, the
  chained-command sentence, the skip-line sentence and the unseen-line
  advice. Within one turn, a second or later hold by the same gate carries
  a short form that names what is still unmet and how to clear it, the
  repeated `Stop` closeout included. When the turn marker cannot be
  claimed or read, the full text is used, as in Ticket 062.
- **R4, a named carrier.** A hold that a line can clear, on a call with
  no line field, names one carrier for the session's shell: a shell call
  whose description holds the line and whose command is `true` in Bash
  or `$null` in PowerShell, where `true` is not a command. Both are plain
  reads, and each passes every hold.
- **R5, inline scripts.** The adapter reads the code an interpreter is
  given inline (`python`, `node`, `perl`, `ruby`, `deno`, `bun` with `-c`
  or `-e` and the like, or a script on standard input from a heredoc) for
  calls that write, remove or rename a file. Such a script is a shell
  write:
  - its files are the path literals the write calls name, placed by the
    usual rules;
  - a path given as a name counts as a literal when the same script binds
    that name once, at its top level and before the call, to one string
    literal (`p = "notes.md"`, `const p = 'notes.md'`). Any other binding
    leaves the path unread: a name bound twice or changed, a binding
    inside a loop, branch or function, an f-string or other built string,
    a concatenation, input, an environment variable, a command's output,
    or a literal the shell may have expanded;
  - a write whose path cannot be read this way is an unnamed write. It is
    inside the project, unless the command's starting folder is known
    from a leading `cd` to a literal path and that folder is certainly
    outside: not in the project, in no git checkout and not under the
    user's `~/.claude` folder, the rule the routing holds use. Then the
    unnamed write is placed in that folder;
  - it meets the routing holds, the path gates and the closeout as any
    shell write does;
  - a script in which no such call is found is not a write, as today.
- **R6, scripted code edits.** An inline script that writes a code file
  inside the project is held by a new justified-skip gate,
  `scripted-edit`. The hold asks for the change to be made with a file
  edit tool, where the design and reference holds can judge it. A skip
  line naming `software-design-principles` with a reason, such as a
  mechanical rewrite across many files, clears it for the turn.
  `software-design-principles` states the rule in one sentence. An
  unnamed write counts as a code file inside the project only where R5
  places it there; a path R5 reads through a once-bound name is judged
  as the file it names.
- **R7, own subagent reports.** A prompt that is the report of a subagent
  this session started continues the current turn: the route line, skip
  lines, overrides, checks, change reads and the brief's route all stand,
  and the closeout sees the whole turn. A report that arrives after the
  turn ended with `Stop` continues that turn's route and lines too, but
  the turn's typed overrides stop applying at `Stop`: an override is the
  user's word for the turn they were watching, not for work a late report
  restarts. A prompt the adapter cannot tie to one of the session's own
  spawns opens a turn as today.
- **R8, early closeout note.** After the first finished code change a
  turn makes with a file edit tool, the adapter adds one short note, once
  per turn, naming the closeout items the turn will meet as far as it can
  tell then, and saying they can be met before the report. It is context
  for the agent and never blocks. The install snippet gains the hook that
  runs after a call, limited to the file edit tools so no other call
  starts a hook process; a code change by a shell command brings no note.
  A turn that already met a closeout hold gets no note.
- **R9, documentation.** The adapter README's What It Holds, Shell
  writes, Hold messages, Subagents, Install, Latency and Known Limits
  sections match the behaviour. Changed hold texts are regenerated for
  the skill-usage mod, and the mod's README says how a joint message is
  counted.

## Acceptance Criteria

- [ ] AC1: A test edit that would meet `design-reads`, `reference-reads`
      and `repeated-failure` is held once, by a message carrying three
      `goated-hold:` lines in today's order. Clearing all three lets the
      retry pass.
- [ ] AC2: A spawn that would meet `pipeline` and `spawn` is held once,
      with both.
- [ ] AC3: A joint message whose holds share the unseen-line advice or the
      change-read explanation carries each once.
- [ ] AC4: The mod counts three holds for the message in AC1, and records
      one as declined and two as followed when one is skipped and two are
      obeyed.
- [ ] AC5: A second `Stop` hold in a turn lists only the unmet items, in
      the short form. The first hold of the next turn is full again.
- [ ] AC6: A hold on an `Edit` call that a skip line can clear names the
      carrier for the session's shell, `true` in Bash or `$null` in
      PowerShell, and each passes before and after the router loads.
- [ ] AC7: `python - <<'EOF'` with `open("src/app.py", "w")` is held by
      `scripted-edit`; with a skip line it runs and the closeout then
      treats `src/app.py` as changed code. The same script writing
      `notes.txt` meets no `scripted-edit` hold and counts as a shell
      write. One writing a file in a temp folder outside the project meets
      no hold.
- [ ] AC8: `python -c "print(1)"` and a heredoc script that only reads
      files are not writes.
- [ ] AC9: An inline script whose write names its path through a variable
      it does not bind once, at top level, to one string literal counts
      as an unnamed write inside the project: `p = input()`, an
      environment variable, an f-string, a name bound twice, a binding
      inside a loop.
- [ ] AC10: After a background subagent's report arrives as a prompt, a
      write needs no new route line, an earlier skip line still counts,
      and the `Stop` closeout lists the code changed before the report. A
      message from an unrelated session opens a new turn. After a report
      that arrives once the turn ended with `Stop`, the turn's route line
      and skip lines still count and its typed override does not.
- [ ] AC11: In a session routed by its brief, an own-subagent report does
      not end the brief's route.
- [ ] AC12: A turn's first code change by a file edit tool brings one
      note naming its closeout items. A second change brings none, and no call or `Stop`
      is blocked by the note.
- [ ] AC13: Hold first lines are unchanged, and every hold today's tests
      expect alone is still given alone with the same text, apart from
      the short forms R3 adds.
- [ ] AC14: The adapter's measured latency stays within the README's
      stated budget with every gate judged.
- [ ] AC15: The repo checks in `AGENTS.md` pass on Python 3.11 and 3.14,
      and the mod's tests pass.
- [ ] AC16: A script that binds `p = "notes.md"` once at top level and
      writes `open(p, "w")` is judged as a write to `notes.md`: no
      `scripted-edit` hold. The same script with `p = "src/app.py"` is
      held by `scripted-edit`. `const p = 'notes.md'` and `let` behave
      the same in JavaScript.
- [ ] AC17: An unnamed write in a command that opens with a `cd` to a
      temp folder outside the project, any git checkout and `~/.claude`
      is placed there and meets no hold. After a `cd` into another git
      checkout, or with no leading `cd`, it is inside the project.

## Proof Surface

The adapter's hook entry points (`goated_hook.py` through
`tests/claude_code_adapter_support.py`), driven by transcript fixtures,
plus the mod's test suite. R7 is proved against a fixture cut from a real
recorded subagent report, with private content removed. A live check in
one real session confirms R1, R7 and R8.

## Constraints

- ADR 0003 has adapters enforce portable contracts. R6's rule is stated
  in `software-design-principles`. R1 to R5, R7 and R8 are adapter
  mechanics stated in its README; Ticket 079's enforcement contract
  restates them in harness-neutral words, and its event model must be
  able to carry several holds in one decision.
- Every change fails toward holding when the adapter cannot tell: a
  script it cannot read for certain is judged as today's Known Limits
  say, a write path it cannot read as a literal is inside the project
  unless the command's folder is certainly outside, a name it cannot
  show was bound once to one literal is not a literal, and a prompt it
  cannot tie to an own spawn opens a turn.
- Judging every gate must not change which calls pass. A call no gate
  holds today is not held, and a gate judged after an earlier hold must
  give the answer it would give alone.
- The scan for writes in inline code is lexical, like the rest of the
  shell reading. It reads each interpreter's common file-write calls from
  one table and is documented as such.
- The shared policy is at its word limit and the router has about six
  words of headroom. Nothing here adds to either.
- The adapter and the mod keep their shared tables and hold texts in
  step.
- This spec's tickets finish before Ticket 079.

## Open Questions

None.

## Risks

- R1 makes a hold message longer when several gates fire. R3 bounds it,
  and one long message replaces several retries that each resend the
  payload.
- R5 can miss a write an unusual call makes, and can read a write call
  inside a string as a write. The first is today's behaviour; the second
  fails toward holding and a skip line answers it.
- R5's reading of a once-bound name is lexical. Code that changes the
  name in a way the reading does not see, such as through `globals()` or
  `eval`, writes a file other than the one judged. That is an agent
  working to defeat the adapter, which is out of scope.
- R6 holds a legitimate bulk rewrite once, until its skip line.
- R7 depends on how Claude Code records a subagent's report. A new
  recording shape falls back to opening a turn, which is today's
  behaviour.
- R8 adds a sentence to every turn that changes code, and one more hook
  process per file edit call. A turn that changes code only by shell
  commands gets no note and still reports twice.

## Sources

- `adapters/claude-code/goated_adapter/hooks.py`: `_pre_tool_use`, `_stop`,
  `_deny`, the notices.
- `adapters/claude-code/goated_adapter/actions.py`: `check_action`,
  `_closeout_hold`, `CHANGE_READ`, the hold texts.
- `adapters/claude-code/goated_adapter/gates.py`: `check_routing`,
  `unseen_line_advice`, `advice_once`, `Hold`.
- `adapters/claude-code/goated_adapter/shell.py`: `analyze`,
  `_add_segment`, `INTERPRETERS`, `INLINE_CODE`.
- `adapters/claude-code/goated_adapter/transcript.py`: `_opener_kind`,
  `LINE_FIELDS`; `state.py`: the turn marker.
- `adapters/claude-code/skill-usage/hooks/` (`classify.ts`, `holds.ts`).
- `adapters/claude-code/README.md`: Hold messages, Shell writes,
  Subagents, Known Limits.
- Tickets 060, 062, 069 and 073.
