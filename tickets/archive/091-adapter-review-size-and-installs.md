# Ticket 091: Review In Briefed Sessions, Branch Size By Code, Installs By Place

## Parent Spec

`docs/specs/2026-11-17-adapter-low-signal-holds.md` (R10, R11, R14, R15;
AC11, AC12, AC15, AC16, AC17)

## Type

AFK.

## Problem

Three closeout triggers fire where the work does not call for them:

- **Review in a delegated session.** The closeout's Review item asks for a
  reviewer subagent or a `standards-and-spec-review` load once the branch
  is large. In a session started from a brief, the session that started
  it reviews the branch, so the agent writes a skip line.
- **Branch size.** "Large" is 400 changed lines against the branch's
  base, counting every file git does not ignore: tests, fixtures, docs
  and configuration. A branch with 150 lines of code and 300 of tests is
  large. The same measure feeds the Verification item and `pr-review`.
- **Installs elsewhere.** A package install counts for the Setup item
  wherever it runs, so `pip install` in a scratch folder asks for
  `setup-scribe`.

## What To Build

- **Review in a briefed session.** A session whose first prompt was a
  brief meets no Review item, for the whole session: typed prompts and
  compactions do not bring it back. This is a fact about the session, not
  about the brief's route, which a typed prompt ends. Missing state means
  not briefed, so the item applies.
- **Rule owner.** `handoff`'s spawn-brief template says, in its After
  Sending step, that inspecting the report and the changed paths is the
  starting session's review of the work. One sentence.
- **Branch size.** "Large" counts changed lines in code files outside
  test paths only: committed, staged, unstaged and untracked, as today,
  but only files the adapter calls code and not test files. Use it for
  the Review item, the Verification item's size trigger and `pr-review`.
  The skill that states the 400-line rule says what is counted.
- **Installs.** A package install run in a folder certainly outside the
  project does not count for the Setup item, unless it is a global or
  machine install: `npm` or `pnpm` with `-g`, `yarn global add`,
  `uv tool install`, `pipx install`, `cargo install`, `go install`,
  `gem install`, `brew`, `apt`, `apt-get`, `winget`, `choco`, `scoop`.
  An install whose folder cannot be read counts. `setup-scribe` says
  which installs it records, if it does not already.
- Update the README's closeout table, Large pull requests, Large branches,
  the Setup text and Known Limits (the untracked-file limit changes), and
  regenerate the hold texts for the skill-usage mod.

## Recommended First Reads

- The parent spec: Problem, R10, R11, R14, Risks.
- `adapters/claude-code/goated_adapter/actions.py`: `_review_item`,
  `_verification_item`, `changed_lines`, the `pr-review` hold,
  `_setup_changes`, `is_code`, and the test-path rule it shares with
  `design_reads.py`.
- `adapters/claude-code/goated_adapter/shell.py`: `_installs_package`,
  `PACKAGE_MANAGERS`, and how a segment's folder is tracked.
- `adapters/claude-code/goated_adapter/transcript.py` (how a brief is
  recognised) and `state.py` (`SessionState`).
- `adapters/claude-code/README.md`: the closeout table, Large pull
  requests, Large branches, the Setup paragraphs.
- `skills/agent-workflows/handoff/references/spawn-brief.md`, and the
  `standards-and-spec-review` and `setup-scribe` skills.
- `tickets/archive/069-adapter-closeout-review-and-verification.md`.

## Acceptance Criteria

- [ ] A briefed session with 600 changed code lines meets no Review item,
      also in a turn opened by a typed prompt and after a compaction.
- [ ] The same branch in a session started by a typed prompt meets it.
- [ ] A briefed session on a `full` route still meets Verification.
- [ ] A branch of 300 changed code lines and 500 changed test, fixture
      and doc lines is not large for Review, Verification or `pr-review`.
      One of 400 changed non-test code lines is.
- [ ] An untracked non-code folder no longer makes a branch large.
- [ ] `pip install requests` in a temp folder raises no Setup item.
      `uv tool install ruff` there does. `pip install requests` in the
      project does, and so does one after a `cd` the adapter cannot
      follow.
- [ ] Existing tests pass unchanged except where one asserted the old
      size count or install rule; each such change is named in the
      closeout.

## Expected Proof

- Adapter tests for each criterion, each with a near miss.
- The skill validators and the context comparison.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, and the mod's
  tests.

## Blocked By

None.

## Scope Exclusions

- The 400-line threshold itself.
- Verification's other triggers.
- Recognising a brief in any shape but the one the adapter reads today.
- Env and settings files, which already count only inside the project.
- The order of change reads and loads (Ticket 092).

## Closeout

Completed, merged and archived on 2026-11-18.

- Merged as `10040f5` (`7ae6cf6`, review fixes `e74347f`).
- Exercised in later sessions; no separate live-check record.
