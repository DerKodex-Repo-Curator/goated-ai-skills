# Ticket 099: Fixture Data Is Test Data

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-4.md` (R1; AC1, AC7, AC8)

## Type

AFK.

## What To Build

A configuration file under a `fixtures` or `__fixtures__` folder, at any
depth inside the project, is test data. The `design` and `design-reads`
gates do not judge it, as they already do not judge a configuration file
under `tests/`. So an edit of a fixture YAML or JSON file no longer asks
for `software-design-principles/references/decoupling.md`.

A code file under such a folder stays a code file, and whether it is a
test file keeps today's rule. `security` and the closeout's `Setup` item
keep today's handling of files under `fixtures/`.

The rule lives in the shared core at `adapters/core/` after Ticket 081:
today's `design_reads.applies` and `_is_config`, which may have moved or
been renamed. The contract and a conformance scenario change with the
code, as `AGENTS.md` requires:

- `stack/enforcement-contract.md`: the Terms (what test data is) and the
  `design-reads` row ("a later file write to a code or configuration
  file");
- `stack/fixtures/enforcement/writes.yaml` (or the file that holds the
  design-reads scenarios): a fixture edit that passes, beside a
  configuration edit that is still held.

## Recommended First Reads

- The parent spec, R1 and its Problem item.
- `stack/enforcement-contract.md`, Terms and the `design-reads` row.
- The core's design-reads module (today's `design_reads.py`).
- `stack/fixtures/enforcement/README.md`, for the scenario format.

## Acceptance Criteria

- [ ] With `software-design-principles` loaded, a five-line edit of
      `stack/fixtures/x.yaml` and one of `a/__fixtures__/b.json` meet no
      `design-reads` hold.
- [ ] The same edit of `config/app.yaml` still asks for `decoupling.md`.
- [ ] A Python file under `fixtures/` is still judged as code.
- [ ] The contract states the rule, and a conformance scenario covers the
      hold, its near miss and the fixture pass.
- [ ] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The Claude Code adapter's design-hold tests, with a fixture case added.
- The repo checks in `AGENTS.md`.

## Blocked By

- `tickets/081-shared-enforcement-core.md`

## Scope Exclusions

- `security`, `Setup` and the code-file rule for files under `fixtures/`.
- Other folder names for test data (`testdata/`, `samples/`).
