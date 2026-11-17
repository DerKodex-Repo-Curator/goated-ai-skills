# Ticket 055: Router-First Lets Read-Only Commands Through

## Parent Spec

`docs/specs/2026-11-17-adapter-hook-friction.md` (R5, R14; AC5)

## Type

AFK.

## Problem

Before the router loads, `router-first` holds every Bash and PowerShell call,
though its own text says "Reads stay free". Read, Grep and Glob already pass,
but `cat`, `grep` or `git diff` run through a shell are held, so an agent
can't look around before it routes.

## What To Build

- `router-first` passes a shell command made only of plainly read-only
  commands:
  - `cat`, `head`, `tail`, `ls`, `grep`, `rg` and `wc`;
  - `find` with no `-exec`, `-execdir` or `-delete`;
  - `git status`, `diff`, `log` and `show`;
  - PowerShell's read equivalents (`Get-Content`, `Get-ChildItem`,
    `Select-String`).

  Pipes between such commands are fine.
- A redirect, a write, a command substitution, or any other command in the
  call keeps the hold. When the shell analysis can't tell, the call is held.
- If the hold's "Reads stay free" sentence needs to say which commands pass,
  update it.
- In the README's Known Limits, name `python - <<'EOF'` and other
  interpreters fed a script on stdin as writes the adapter doesn't see.

## Recommended First Reads

- The parent spec, R5.
- `adapters/claude-code/goated_adapter/gates.py` (`check_routing`).
- `adapters/claude-code/goated_adapter/shell.py` (`analyze`, and how a
  command line is split into simple commands).
- `adapters/claude-code/README.md`: What It Holds (router-first) and Known
  Limits (shell analysis).

## Acceptance Criteria

- [ ] Before the router loads, `cat a.py`, `git diff`,
      `grep -n x a.py | head` and `Get-Content a.py` pass.
- [ ] `cat a > b`, `find . -delete`, `find . -exec rm {} +`, `pytest`,
      `git push` and ``cat $(make-it)`` are held.
- [ ] Once the router loads, routing behaves as before.
- [ ] Known Limits names stdin-fed interpreters.

## Expected Proof

- Adapter tests for each case, each with a near miss.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14.

## Blocked By

- None.

## Scope Exclusions

- Exempting commands from `route-line` or `pipeline`, which already pass
  commands that write nothing.
- Treating stdin-fed interpreters as writes.
