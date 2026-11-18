# Ticket 093: Inline Script Writes Are Seen, And Scripted Code Edits Are Held

## Parent Spec

`docs/specs/2026-11-17-adapter-hold-delivery-and-coverage.md` (R5, R6, R9;
AC7, AC8, AC9, AC13, AC15)

## Type

AFK.

## Problem

A write made by code an interpreter is given inline counts as neither a
write nor a read:

```text
python - <<'EOF'
open("src/app.py", "w").write(text)
EOF
```

The same is true of `python -c`, `node -e` and the like. Such a call
meets only `router-first`. One agent of the last wave made every edit to
a code file this way, so forty new lines met no design hold, no reference
hold and no closeout. The adapter README lists the form under Known
Limits.

Treating every inline script as a write would hold the many read-only
one-liners agents run.

## What To Build

- **Read inline code for writes.** When a shell command gives an
  interpreter its code inline, the adapter reads that code for calls that
  write, remove or rename a file. Cover `python`, `node`, `perl`, `ruby`,
  `deno` and `bun`, each also through `uv run` or `npx` as checks are
  read today, with the code given by an inline-code option or on standard
  input from a heredoc. Keep each interpreter's write calls in one table.
- **Such a script is a shell write.**
  - Its files are the path literals its write calls name, placed by the
    usual rules for a shell write's target.
  - A write call whose path is not a literal is an unnamed write, inside
    the project, as `git apply` is today.
  - It meets the routing holds, the path gates (`security`,
    `review-intake`, `reference-reads`, `conflict-resolution`,
    `repeated-failure`) and the closeout as any shell write does.
  - A script in which no write call is found is not a write, as today.
- **A new gate, `scripted-edit`, kind justified-skip.** It holds an
  inline script that writes a code file inside the project, test files
  included. The hold asks for the change to be made with a file edit
  tool, where the design and reference holds can judge it. A skip line
  naming `software-design-principles`, with a reason, clears it for the
  turn; so does the typed override for that skill. Once cleared, the
  script runs and its files count as changed.
- **Rule owner.** `software-design-principles` says, in one sentence,
  that a code file is changed with the file edit tools, and by a script
  only for a mechanical rewrite across many files. Inside its context
  budget.
- **README.** Add the gate's row to What It Holds, extend Shell writes
  with the inline-code rule and its table, and narrow the Known Limits
  item to what is still unseen. Add the gate to the skill-usage mod's
  tables and regenerate the hold texts.

## Recommended First Reads

- The parent spec: Problem, R5, R6, Constraints, Risks.
- `adapters/claude-code/goated_adapter/shell.py`: `analyze`,
  `_add_segment`, `INTERPRETERS`, `INLINE_CODE`, how a heredoc is read,
  and how an unnamed write is reported.
- `adapters/claude-code/goated_adapter/actions.py`: `check_action`'s
  shell branch, `_in_project`, `is_code`, `UNNAMED_FILES`, and one
  justified-skip gate end to end, such as `security`.
- `adapters/claude-code/README.md`: Shell writes, and the Known Limits
  item that opens "Shell analysis is lexical".
- `adapters/claude-code/skill-usage/hooks/` for the gate tables the mod
  keeps.
- `skills/engineering/software-design-principles/SKILL.md`.

## Acceptance Criteria

- [ ] `python - <<'EOF'` with `open("src/app.py", "w")` is held by
      `scripted-edit`. With a skip line naming
      `software-design-principles` it runs, and the closeout then treats
      `src/app.py` as changed code.
- [ ] `python -c` and `node -e` forms of the same write are held the same
      way.
- [ ] The same script writing `notes.txt` meets no `scripted-edit` hold
      and counts as a shell write. One writing only a file in a temp
      folder outside the project meets no hold.
- [ ] `python -c "print(1)"`, and a heredoc script that opens files only
      to read them, are not writes.
- [ ] A script whose write call takes its path from a variable counts as
      an unnamed write inside the project. An unnamed write counts as
      code, as it does for the closeout, so `scripted-edit` holds it.
- [ ] A script writing a security-sensitive path inside the project meets
      the `security` gate.
- [ ] A check run through an interpreter (`python -m pytest`) is still a
      check and not a write.
- [ ] The gate's hold opens `goated-hold: scripted-edit | justified-skip`,
      and the mod counts it.
- [ ] Existing tests pass unchanged except where one asserted that an
      inline script is not a write; each such change is named in the
      closeout.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The skill validators and the context comparison.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, and the mod's
  tests.

## Blocked By

None.

## Scope Exclusions

- A script file run by name (`node build.js`, `python tools/gen.py`), a
  wrapped shell (`bash -c`), archive tools and command substitution,
  which stay Known Limits.
- Making the design gates judge shell writes such as `sed -i`.
- Reading how many lines a script adds.
- Defending against an agent that hides a write on purpose.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `ec490de` (`e1263d0`, review fixes `9f0c772`).
- Exercised in later sessions; no separate live-check record.
