# Ticket 097: Script Writes Read A Once-Bound Path And A Known Outside Folder

## Parent Spec

`docs/specs/2026-11-17-adapter-hold-delivery-and-coverage.md` (R5, R6, R9;
AC9, AC16, AC17, AC13, AC15)

## Type

AFK.

## Problem

Ticket 093 made the adapter read inline interpreter code for file writes.
A write call's file is the string literal it names; any other path is an
unnamed write, which counts as a code file inside the project, so the
`scripted-edit` gate holds it.

That rule held a plain markdown edit outside the project. The command
opened with a `cd` to a folder outside the project, then ran:

```text
python - <<'EOF'
p = "notes.md"
text = open(p).read()
open(p, "w").write(text.replace("a", "b"))
EOF
```

The hold said: "An inline script in this command writes a file it names
only at run time, which counts as code." The script names its file two
lines above the write, and the command says which folder it runs in. The
adapter read neither.

## What To Build

- **A once-bound name is its literal.** When a write call's path is a
  name, and the same inline script binds that name exactly once, at its
  top level and before the call, to one string literal, the path is that
  literal. The usual rules then apply: the file is placed from the
  command's folder, and judged as code or not by its own name.
  - Python: `p = "notes.md"`. JavaScript: `const p = 'notes.md'`, and
    `let` or `var` when nothing assigns the name again.
  - The same reading applies where a path is already read as a literal:
    a call's path argument, and the argument of a `Path(...)` receiver.
  - Perl and Ruby follow the same rule where the binding is as plain
    (`my $p = 'notes.md';`, `p = 'notes.md'`). If either cannot be read
    safely, leave it unnamed and say so in the closeout and the README.
- **Everything else stays unnamed.** The path is not read when:
  - the name is bound more than once anywhere in the script, or changed
    (`p += "x"`, `p = p + "x"`);
  - the binding is inside a loop, branch, function, class or other block,
    or the name is also a parameter, a loop variable, an import or a
    `with` or `except` name;
  - the bound value is not one string literal with no run-time part: an
    f-string, a template string with `${}`, a concatenation, `input()`,
    an environment variable, a command's output, a call;
  - the shell may have expanded the code, and the literal holds `$` or a
    backtick, as Ticket 093's rule for literals already says;
  - the binding comes after the write call.
- **A known folder outside the project.** When the command's starting
  folder is known from a leading `cd` to a literal path, as the adapter
  already follows it, and that folder is certainly outside, an unnamed
  write is placed in that folder, not inside the project. "Certainly
  outside" is Ticket 087's rule: not in the project, in no git checkout
  and not under the user's `~/.claude` folder. Otherwise the unnamed
  write is inside the project, as today: no leading `cd`, a `cd` the
  adapter cannot follow, a folder inside any checkout or under
  `~/.claude`.
- **What clears the reported case.** The reported command ran under
  `~/.claude`, so the folder rule does not move it outside: routing and
  the path gates still judge it. The once-bound name is what clears it:
  the write is to `notes.md`, which is not a code file, so `scripted-edit`
  does not hold it.
- Keep `script_writes.writes` the one place that reads inline code, and
  the placement of a write with the other shell writes.
- Update the README's Shell writes section and the `scripted-edit` row,
  and the Known Limits item on what a script's reading misses. Regenerate
  the hold texts for the skill-usage mod if a text changes.

## Recommended First Reads

- The parent spec: R5, R6, AC9, AC16, AC17, Constraints, Risks.
- `adapters/claude-code/goated_adapter/script_writes.py`, all of it:
  `writes`, `_call_writes`, `_literal`, `_path_receiver`,
  `_resolve_aliases`.
- `adapters/claude-code/goated_adapter/shell.py`: where `script_writes`
  is called, how a leading `cd` sets a segment's folder, and
  `unknown_writes`.
- `adapters/claude-code/goated_adapter/actions.py`: `check_action`'s
  shell branch around `_scripted_edit_hold`, `UNNAMED_FILES`,
  `_changed_paths`, `_in_project`.
- `adapters/claude-code/goated_adapter/gates.py`: the outside-the-project
  rule Ticket 087 gave the routing holds.
- `tests/test_claude_code_adapter_scripts.py`.
- `adapters/claude-code/README.md`: Shell writes.
- `tickets/093-adapter-inline-script-writes.md` and
  `tickets/087-adapter-routing-orientation-by-reads-and-outside-writes.md`.

## Acceptance Criteria

- [ ] The reported case: after a leading `cd` to a folder under
      `~/.claude`, a `python - <<'EOF'` script that binds
      `p = "notes.md"`, reads it and writes `open(p, "w")` meets no
      `scripted-edit` hold. It still counts as a shell write there, so
      routing judges it.
- [ ] The same script with `p = "src/app.py"`, run in the project, is
      held by `scripted-edit`, and the hold names the file.
- [ ] Each of these is still an unnamed write: `p = input()`,
      `p = os.environ["F"]`, `p = f"{name}.md"`, `p = "a" + ext`, a name
      bound twice, `p += ".md"` after the binding, a binding inside a
      `for` loop, inside an `if`, inside a function, and a binding after
      the write call.
- [ ] `Path(p).write_text(...)` with `p = "notes.md"` bound once is a
      write to `notes.md`.
- [ ] JavaScript: `const p = 'notes.md'` and `let p = 'notes.md'` with no
      later assignment are read. `let p = 'a.md'; p = 'b.py'`, a template
      string with `${}`, and `const p = process.env.F` are unnamed.
- [ ] In code the shell may have expanded, `p = "$HOME/x.md"` is unnamed.
- [ ] An unnamed write after a leading `cd` to a temp folder outside the
      project, any git checkout and `~/.claude` is placed there: no
      `scripted-edit` hold, no routing hold, and no closeout item.
- [ ] An unnamed write after a `cd` into another git checkout is inside
      the project, and so is one after a `cd` to a folder under
      `~/.claude`, after a `cd` the adapter cannot follow, and with no
      leading `cd`.
- [ ] A script with one once-bound path and one unnamed write is judged
      for both.
- [ ] Every case Ticket 093's tests cover gives the same answer, except
      where a test asserted that a once-bound name is unnamed; each such
      change is named in the closeout.

## Expected Proof

- Adapter tests for each criterion. The held and unnamed cases above are
  the near misses for the cases that pass.
- The repo checks in `AGENTS.md`, on Python 3.11 and 3.14, and the mod's
  tests.

## Blocked By

- `tickets/093-adapter-inline-script-writes.md` (merged).

## Scope Exclusions

- Following a name through a function call, an attribute, a container or
  another name (`q = p`).
- Evaluating string operations: joins, formatting, `os.path.join`.
- A script file run by name, and the other forms Ticket 093 left as Known
  Limits.
- Changing what `scripted-edit` requires or what clears it.
- The outside-the-project rule itself, which stays Ticket 087's.
