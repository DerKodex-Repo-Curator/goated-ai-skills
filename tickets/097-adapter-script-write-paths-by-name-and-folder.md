# Ticket 097: Script Writes Read A Once-Bound Path

The file name keeps "and folder" from the first draft; the folder rule was
dropped in review (see What To Build).

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
  - the binding comes after the write call;
  - the code may bind a name unseen: code the shell may expand holding `$`
    or a backtick anywhere, or code using `exec`, `eval`, `globals`,
    `vars`, `sys.modules`, `globalThis`, a star import or a JavaScript
    `with`;
  - a JavaScript statement goes on past its line (the next line opens
    with `.`, `+`, `?` or another operator).
- **Unnamed writes stay inside.** An unnamed write is inside the project
  wherever the command runs, as before this ticket. A rule placing it in a
  known folder outside the project was built and then dropped in review
  (maintainer decision): a script reaches project files from any folder
  (`os.path.join(ROOT, …)`, `sys.argv[1]`, `Path('<project>') / …`,
  `os.environ`, `os.chdir`, Node's `path.join`).
- **What clears the reported case.** The once-bound name: the write is to
  `notes.md`, which is not a code file, so `scripted-edit` does not hold
  it. Routing and the path gates still judge it as a shell write.
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
      `~/.claude` (or anywhere), a `python - <<'EOF'` script that binds
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
      project is still held by `scripted-edit`, and once run counts as
      changed code: a loop variable, `os.path.join(ROOT, 'src/app.py')`,
      `sys.argv[1]`, `Path('<project>') / 'src/app.py'`, `os.environ`,
      `os.chdir` then a write, and Node's `path.join`.
- [ ] A JavaScript binding whose statement goes on past its line
      (`.replace(…)`, `+ '.py'`, `? … : …` on the next line) is unnamed.
- [ ] Code the shell may expand that holds `$` or a backtick reads no
      name, and so does code using `exec`, `eval`, `globals`, `vars`,
      `sys.modules`, `globalThis`, a star import or `with`.
- [ ] 5,000 declarations are read in under a second.
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
