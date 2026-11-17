# Ticket 055: Routing Lets Reads Through

## Parent Spec

`docs/specs/2026-11-17-adapter-hook-friction.md` (R5, R13, R14; AC5, AC15)

## Type

AFK.

## Problem

`router-first` says "Reads stay free", but two kinds of read are held:

- **Shell reads.** Before the router loads, `router-first` holds every Bash
  and PowerShell call. Read, Grep and Glob already pass, but `cat`, `grep` or
  `git diff` run through a shell are held, so an agent can't look around
  before it routes.
- **Read-only subagents.** A spawn counts as a write, so starting a read-only
  research subagent meets the same holds as starting an implementer. While
  the planning session that wrote the parent spec was checking claims, an
  `Explore` spawn was held three times:
  - by `route-line`;
  - by `pipeline`, for skills of a later phase (`write-a-spec`,
    `spec-to-tickets`);
  - by `spawn`, which asked for the handoff brief template for a short
    search brief.

  Doing the reads inline was cheaper than meeting the holds, which defeats
  the point of delegating bounded reads.

Both are the same rule, applied in the same routing function.

## What To Build

- **Shell reads.** `router-first` passes a shell command made only of plainly
  read-only commands:
  - `cat`, `head`, `tail`, `ls`, `grep`, `rg` and `wc`;
  - `find` with no `-exec`, `-execdir` or `-delete`;
  - `git status`, `diff`, `log` and `show`;
  - PowerShell's read equivalents (`Get-Content`, `Get-ChildItem`,
    `Select-String`).

  Pipes between such commands are fine. A redirect, a write, a command
  substitution, or any other command in the call keeps the hold. When the
  shell analysis can't tell, the call is held.
- **Read-only subagents.** A spawn of a read-only subagent type passes
  `pipeline` and `spawn`; after review only `claude-code-guide` qualifies,
  since `Explore` and `Plan` have shell tools. It still needs
  a route line, as any first spawn does. Any other subagent type, including
  `general-purpose` and a missing type, is unchanged, and so are side
  sessions.
- Keep the read-only commands and subagent types in named tables, each with a
  comment on why.
- If the hold's "Reads stay free" sentence needs to say what passes, update
  it.
- Update the README's router-first, spawn and pipeline text.
- In the README's Known Limits, name `python - <<'EOF'` and other
  interpreters fed a script on stdin as writes the adapter doesn't see.

## Recommended First Reads

- The parent spec, R5 and R13.
- `adapters/claude-code/goated_adapter/gates.py` (`check_routing`,
  `writes_like_an_edit`, `HELD_LIKE_WRITES`).
- `adapters/claude-code/goated_adapter/shell.py` (`analyze`, and how a
  command line is split into simple commands).
- `adapters/claude-code/goated_adapter/actions.py` (`_spawn_hold`,
  `SPAWN_BRIEF_FIELDS`).
- `adapters/claude-code/README.md`: What It Holds (router-first, spawn,
  pipeline) and Known Limits (shell analysis).

## Acceptance Criteria

- [ ] Before the router loads, `cat a.py`, `git diff`,
      `grep -n x a.py | head` and `Get-Content a.py` pass.
- [ ] `cat a > b`, `find . -delete`, `find . -exec rm {} +`, `pytest`,
      `git push` and ``cat $(make-it)`` are held.
- [ ] Once the router loads, routing behaves as before.
- [ ] A `claude-code-guide` spawn with required skills not loaded and no
      handoff template passes `pipeline` and `spawn`.
- [ ] An `Explore` or `general-purpose` spawn with the same brief is still
      held.
- [ ] A `claude-code-guide` spawn with no route line in the turn is held by
      `route-line`.
- [ ] Known Limits names stdin-fed interpreters.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.

## Blocked By

- None.

## Scope Exclusions

- Exempting commands or read-only subagents from `route-line`.
- Side sessions.
- Treating stdin-fed interpreters as writes.

## Closeout

Completed, merged and archived on 2026-11-17.

- Merged in `b98e85b` (`e8631d7`, `d2bcd8c`, review fixes `57e17bf`,
  `7d67838`, `6950a7a`, `0deb68c`), with the integration fix `4f5cc75` that
  judges a plain read by the calling shell tool.
- Three review rounds probed real Git Bash and PowerShell 5.1. A plain read
  now allows only printable ASCII, a bare command word, no `$`, backslash,
  `<<<`, `[[`, `<#`, output redirect, UNC path, or program-running option;
  every bypass found was held by the final round, and common reads still
  pass.
- Only `claude-code-guide` counts as a read-only subagent: `Explore` and
  `Plan` have shell tools and no routing applies inside a subagent. The spec
  (R13, AC15) and this ticket were amended to match.
- Every check passed on the integrated branch fast-forwarded into main (`4f5cc75`): the validator, 606 unit tests on Python 3.14 and 3.11, the V1/V2 context comparison, `claude plugin test` (165 pass), and the TypeScript check with only the 5 known errors in `tests/register.test.tsx`.
- Known limit, in the README: repository git config (`diff.external`,
  textconv, `core.fsmonitor`) can run programs under a passing git read.
