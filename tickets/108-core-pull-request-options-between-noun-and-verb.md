# Ticket 108: Pull Request Options Between The Noun And The Verb

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-4.md` (follow-up R13; AC15,
AC7, AC8)

## Type

AFK.

## What To Build

A shell `gh pr <options> create` or `gh pr <options> new`, or the `glab mr`
forms, opens a pull or merge request exactly as the same command with the
options after the verb does. That includes `-R`/`--repo` in every form
Ticket 103 reads (`-R x`, `-Rx`, `-R=x`, `--repo x`, `--repo=x`), so the
pull request is measured only in the repository it names, and `--base`,
`--head` and their short forms count wherever they sit.

Today the `FORGE_DIFFS` branch of `shell.py` runs
`_skip_options(args, {"-R", "--repo"})` before the noun only, then
expects the verb right after the noun, so `gh pr -R x create` opens
nothing and meets no pull request hold (`pull-request`, `pr-review`). The
rule lives in the shared core at `adapters/core/goated_core/`.

The contract and a conformance scenario change with the code, as
`AGENTS.md` requires:

- `stack/enforcement-contract.md`, Commits And Pull Requests and Branch
  Size: where a shell pull request is recognized, and the "before or
  after the subcommand" wording of the `--repo` bullet;
- `stack/fixtures/enforcement/handing-on.yaml` (or the file holding the
  pull request holds): `gh pr -R <own repo> create` held by `pr-review`
  beside `gh pr -R other/x create` that is not measured.

## Recommended First Reads

- The parent spec's follow-up section, R13.
- `adapters/core/goated_core/shell.py`: the `FORGE_DIFFS` branch,
  `_skip_options`, `_pr_options`, `PR_VALUE_OPTIONS`.
- `tickets/archive/103-core-shell-pull-request-names-its-repository.md`.

## Acceptance Criteria

- [ ] `gh pr -R <own repo> create` and `glab mr --repo <own repo> create`
      open a pull request that is measured; `gh pr -R other/x create` is
      not measured.
- [ ] `gh pr --repo=x create`, `gh pr -Rx new` and an option with no value
      between noun and verb (such as `gh pr --draft create`, if `gh`
      accepts it there) are read the same way.
- [ ] `echo gh pr create` and `gh pr list` still open nothing.
- [ ] The contract states the rule, and a conformance scenario covers a
      hold and a near miss.
- [ ] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The core's shell-reading tests, with the new forms.
- The conformance scenarios through the core.
- The repo checks in `AGENTS.md`.

## Blocked By

- `tickets/archive/103-core-shell-pull-request-names-its-repository.md`
  (merged)

## Overlaps

- **Ticket 109** changes the same lines of the `FORGE_DIFFS` branch and
  waits for this ticket.

## Scope Exclusions

- Reading several pull requests in one chained command (Ticket 109).
- The `GH_REPO`-style environment variables and `gh repo set-default`.
- Which `gh` or `glab` options take a value beyond those `_pr_options`
  and `_skip_options` already know.
