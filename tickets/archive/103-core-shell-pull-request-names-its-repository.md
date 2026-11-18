# Ticket 103: A Shell Pull Request Names Its Repository

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-4.md` (addendum R7; AC9, AC7,
AC8)

## Type

AFK.

## What To Build

A shell `gh pr create` or `gh pr new`, or `glab mr create` or
`glab mr new`, that names a repository with `--repo` or `-R` is measured
the way a `pull_request` call naming that `repository` is: only when it
matches the checkout's `origin` URL, and not at all when it names another
repository or the folder has no `origin`. A host prefix
(`github.com/owner/repo`, `gitlab.example.com/group/sub/repo`) or a full
URL names the same repository as its path. A command with no such option
is measured as today.

Today the shell reading skips the option and its value (`shell.py`, the
`FORGE_DIFFS` branch, `_skip_options(args, {"-R", "--repo"})`), and the
shell path in `actions.py` measures `opens_pr` with
`changed_lines(cwd, pr_base, pr_head)` and no repository, while the
`pull_request` path passes `call.repository`. The rule lives in the shared
core at `adapters/core/goated_core/`.

The contract and a conformance scenario change with the code, as
`AGENTS.md` requires:

- `stack/enforcement-contract.md`, Commits And Pull Requests: the bullet
  that today says a shell `--repo`/`-R` is "measured in the working
  folder's checkout as if it named none";
- `stack/fixtures/enforcement/handing-on.yaml` (or the file holding the
  pull request holds): a shell pull request aimed at another repository
  that is not measured, beside one naming the checkout's own repository
  that is.

## Recommended First Reads

- The parent spec's addendum, R7.
- `stack/enforcement-contract.md`, Commits And Pull Requests.
- The core's shell reading of `gh` and `glab`, and the pull request holds
  and `changed_lines` with its repository match in `actions.py`.
- `stack/fixtures/enforcement/README.md`, for the scenario format.

## Acceptance Criteria

- [x] `gh pr create --repo other/x` and `glab mr create -R other/x` from a
      checkout whose `origin` is not `other/x` are not measured.
- [x] `gh pr create -R <owner>/<repo>` naming the checkout's own `origin`
      is measured as a command without the option is.
- [x] A host-prefixed or URL form names the same repository as its
      `owner/repo` path.
- [x] `--base`, `--head` and their glab forms are still read with the
      option present.
- [x] The contract states the rule, and a conformance scenario covers the
      measured case and the other-repository near miss.
- [x] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- Core or adapter tests of the shell reading with each option spelling.
- The repo checks in `AGENTS.md`.

## Blocked By

- `tickets/archive/081-shared-enforcement-core.md` (merged)

## Overlaps

- No code shared with 099, 100 or 102. Shares `shell.py` with Ticket 104
  (another function) and `actions.py` with 102 and 105 (other
  functions).

## Scope Exclusions

- The `GH_REPO`-style environment variables, and a repository chosen by
  `gh repo set-default`.
- Which holds a pull request meets, and how a branch is measured.

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `ebf782e` (`e56c3f0`, follow-up `43aa4e2`).
- Exercised in later sessions; no separate live-check record.
