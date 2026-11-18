# Ticket 109: One Pull Request Per Simple Command

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-4.md` (follow-up R14; AC16,
AC7, AC8)

## Type

AFK.

## What To Build

Each `gh pr create|new` or `glab mr create|new` in a chained shell command
is read with its own options. A later one never takes an earlier one's
`--repo`, `--base` or `--head`. Each pull request the command opens is
measured on its own, as a `pull_request` call with those fields would be,
and the `pr-review` gate holds when any of them measures 400 or more
lines. The hold names the pull request it measured.

Today `shell.ShellCommand` keeps one `opens_pr`, `pr_base`, `pr_head` and
`pr_repository`, each filled by whichever simple command last named it
(`named.get("base") or result.pr_base`), and `actions.py` measures once
with them. So in `gh pr create -R other/x && gh pr create`, the second
pull request is taken as aimed at `other/x` and is not measured. The rule
lives in the shared core at `adapters/core/goated_core/`: the
`FORGE_DIFFS` branch of `shell.py`, the `ShellCommand` fields, and the
shell path in `actions.py` that adds `_pr_review_hold`.

The contract and a conformance scenario change with the code, as
`AGENTS.md` requires:

- `stack/enforcement-contract.md`, Commits And Pull Requests and Branch
  Size: that each pull request in a command is read and measured on its
  own;
- `stack/fixtures/enforcement/handing-on.yaml` (or the file holding the
  pull request holds): a chain whose first pull request is aimed at
  another repository and whose second, large one is held.

## Recommended First Reads

- The parent spec's follow-up section, R14.
- `adapters/core/goated_core/shell.py`: `ShellCommand`, the
  `FORGE_DIFFS` branch, `_pr_options`.
- `adapters/core/goated_core/actions.py`: the shell path that adds
  `_pr_hold` and `_pr_review_hold`, and `changed_lines`.
- `tickets/108-core-pull-request-options-between-noun-and-verb.md`, which
  lands first in the same lines.

## Acceptance Criteria

- [ ] In `gh pr create -R other/x && gh pr create`, the second pull
      request is measured in the checkout.
- [ ] In `gh pr create -B small && gh pr create -B main`, each is measured
      against its own base, and the hold holds when either is 400 or more
      lines.
- [ ] A command with one pull request is measured exactly as today.
- [ ] Branch size still runs at most once per pull request, and only when
      the call would otherwise be held by `pr-review`.
- [ ] The contract states the rule, and a conformance scenario covers a
      hold and a near miss.
- [ ] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The core's shell-reading and pull request tests, with chained commands.
- The conformance scenarios through the core.
- The repo checks in `AGENTS.md`.

## Blocked By

- `tickets/108-core-pull-request-options-between-noun-and-verb.md`
  (ordering: the same lines of the `FORGE_DIFFS` branch)

## Scope Exclusions

- The two-second limit on all of branch size's git calls stays one limit
  for the whole call.
- The `pull-request` gate (`pr-description`) stays one hold per call.
