# Ticket 115: Mocking Pattern For Code Patches

## Parent Spec

`docs/specs/2026-11-18-hook-friction-round-5.md` (R6; AC8, AC5, AC6)

## Type

AFK. Decision M, option 1 (the maintainer, 2026-11-18).

## What To Build

The `mock-or-patch` pattern asks for `tdd`'s mocking reference for a mock
or patch of code, not for test data or a patched environment:

- `monkeypatch` selects only as `monkeypatch.setattr(` or
  `monkeypatch.delattr(`. `setenv`, `delenv`, `setitem`, `delitem`,
  `chdir`, `syspath_prepend` and the bare name (a fixture parameter)
  select nothing.
- A line the edit shows inside a multi-line string, a Python
  triple-quoted string that is not a docstring or a JavaScript template
  literal, is inside a string, so `fake` in invented TOML there
  (`[providers.fake]`, `name = fake`) selects nothing. Where the edit
  does not show where the string opens, the line is read as today.

Checked on main at `bf18b3b`: `[providers.fake]`, `name = fake`,
`monkeypatch.setenv(...)` and `def test_x(monkeypatch):` each select it;
`provider = "fake"` does not (Ticket 100).

The rule lives in the shared core at `adapters/core/goated_core/`:
`reference_reads.PATTERNS`, its comment, and the string reading
(`_without_strings`, or the added lines it is given). The registry's
`reference_patterns` description in `stack/goated-stack.yaml`, the
contract's `reference-reads` row and Registry Reference Signals, and a
conformance scenario change with it, as `AGENTS.md` requires.

**`shell.py`'s pull request reading:** not touched.

## Recommended First Reads

- The parent spec, R6 and decision M.
- `stack/enforcement-contract.md`, the `reference-reads` row and Registry
  Reference Signals.
- The core's `reference_reads.py` (`PATTERNS`, `Pattern.token`,
  `_without_strings`) and `design_reads.py` (`added_code`).
- `tickets/archive/100-core-narrower-reference-triggers.md`.

## Acceptance Criteria

- [ ] In a test file with `tdd` loaded, `monkeypatch.setenv("X", "1")`
      and `def test_x(monkeypatch):` select no mocking reference;
      `monkeypatch.setattr(mod, "f", g)` does.
- [ ] `[providers.fake]` inside a triple-quoted string the edit shows
      selects nothing; the same line as code, and `fake = Fake()`, still
      do.
- [ ] The registry's pattern description stays true of the narrower match.
- [ ] The contract states the rule, and a conformance scenario covers a
      hold and each near miss.
- [ ] The repo checks in `AGENTS.md` pass.

## Expected Proof

- The conformance scenarios through the core.
- The core's reference-reads tests, with the reported lines.
- The repo checks in `AGENTS.md`, including the registry validation.

## Blocked By

- None.

## Overlaps

- `reference_reads.py` with Ticket 113 (the `edit-of-file-kind`
  counting, another function).

## Scope Exclusions

- The registry's other pattern (`sleep-retry-or-timeout`).
- Non-Python and non-JavaScript multi-line string forms.
