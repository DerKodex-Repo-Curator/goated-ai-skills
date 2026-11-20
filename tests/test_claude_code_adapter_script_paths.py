"""Behavior tests for where an inline script's writes go (Ticket 097).

A write call whose path is a name the same script binds once, at its top
level and before the call, to one string literal writes that literal's
file. Any other unnamed write is inside the project wherever the command
runs. Like the other adapter tests, these
drive the hook entry point (see `claude_code_adapter_support.py`), with a
direct look at `shell.analyze` for the reading itself.
"""

from __future__ import annotations

import time
import unittest

from claude_code_adapter_support import decision, reason
from goated_core import shell
from test_claude_code_adapter_scripts import SCRIPTED, ScriptTestCase, hold_line, stop

# The command a lead was held on, as reported: a markdown edit through a once-bound name.
REPORTED = (
    "python - <<'EOF'\n"
    "p = \"notes.md\"\n"
    "text = open(p).read()\n"
    "open(p, \"w\").write(text.replace(\"a\", \"b\"))\n"
    "EOF"
)
UNNAMED = "python - <<'EOF'\nfor p in paths:\n    open(p, 'w').write(text)\nEOF"


def heredoc(*lines: str) -> str:
    return "python - <<'EOF'\n" + "\n".join(lines) + "\nEOF"


def read(command: str) -> tuple[list[str], bool]:
    result = shell.analyze(command)
    return result.script_targets, result.script_unknown_writes


class OnceBoundNameTests(unittest.TestCase):
    """A name bound once to one literal is that literal; any other binding is not."""

    def test_the_reported_script_writes_the_file_it_binds(self) -> None:
        self.assertEqual(read(REPORTED), (["notes.md"], False))
        self.assertEqual(read("python -c \"p = 'notes.md'; open(p, 'w')\""), (["notes.md"], False))

    def test_a_path_receiver_reads_a_once_bound_name(self) -> None:
        command = heredoc("from pathlib import Path", "p = \"notes.md\"",
                          "Path(p).write_text('x')")
        self.assertEqual(read(command), (["notes.md"], False))

    def test_any_other_binding_leaves_the_path_unnamed(self) -> None:
        for lines in (
            ("p = input()",),
            ("import os", "p = os.environ[\"F\"]"),
            ("p = f\"{name}.md\"",),
            ("p = \"a\" + ext",),
            ("p = \"a.md\"", "p = \"b.md\""),
            ("p = \"a.md\"", "p += \".md\""),
            ("p = \"a.md\"", "p = p + \".md\""),
            ("for name in names:", "    p = \"a.md\""),
            ("if ready:", "    p = \"a.md\""),
            ("def target():", "    p = \"a.md\"", "    return p"),
            ("class Paths:", "    p = \"a.md\""),
            ("p = \"a.md\"", "for p in paths:", "    pass"),
            ("p = \"a.md\"", "def f(p):", "    pass"),
            ("p = \"a.md\"", "with open('x') as p:", "    pass"),
            ("p = \"a.md\"", "import p"),
            ("p = \"a.md\"", "try:", "    pass", "except OSError as p:", "    pass"),
            ("p = \"a.md\"", "[p for p in paths]"),
            ("p = \"a.md\"", "del p"),
            ("p = q = \"a.md\"",),
            ("p = subprocess.check_output(['ls'])",),
        ):
            with self.subTest(lines=lines):
                self.assertEqual(read(heredoc(*lines, "open(p, 'w')")), ([], True))

    def test_a_binding_after_the_write_call_leaves_it_unnamed(self) -> None:
        self.assertEqual(read(heredoc("open(p, 'w')", "p = \"a.md\"")), ([], True))
        self.assertEqual(read("python -c \"open(p, 'w'); p = 'a.md'\""), ([], True))
        # Near miss: the same binding before the call.
        self.assertEqual(read(heredoc("p = \"a.md\"", "open(p, 'w')")), (["a.md"], False))

    def test_javascript_reads_a_const_or_a_let_never_assigned_again(self) -> None:
        for code in (
            "const p = 'notes.md'\nrequire('fs').writeFileSync(p, 'x')",
            "let p = 'notes.md';\nconst fs = require('fs');\nfs.writeFileSync(p, fs.readFileSync(p))",
            "var p = \"notes.md\"; fs.writeFileSync(p, 'x')",
        ):
            with self.subTest(code=code):
                self.assertEqual(read(f"node - <<'EOF'\n{code}\nEOF"), (["notes.md"], False))
        for code in (
            "let p = 'a.md'; p = 'b.py'; fs.writeFileSync(p, 'x')",
            "let p = 'a.md'; p += '.py'; fs.writeFileSync(p, 'x')",
            "const p = `${name}.md`; fs.writeFileSync(p, 'x')",
            "const p = process.env.F; fs.writeFileSync(p, 'x')",
            "const p = 'a' + ext; fs.writeFileSync(p, 'x')",
            "if (ok) { const p = 'a.md'; fs.writeFileSync(p, 'x') }",
            "const p = 'a.md'; function f(p) { fs.writeFileSync(p, 'x') }",
            "const p = 'a.md'; for (const p of all) fs.writeFileSync(p, 'x')",
            "const p = 'a.md'; ({p} = other); fs.writeFileSync(p, 'x')",
            "fs.writeFileSync(p, 'x'); const p = 'a.md'",
        ):
            with self.subTest(code=code):
                self.assertEqual(read(f"node - <<'EOF'\n{code}\nEOF"), ([], True))

    def test_perl_and_ruby_names_stay_unnamed(self) -> None:
        # Their strings can change in place (`$p =~ s///`, `p << "x"`), so a name is not read.
        self.assertEqual(read("perl -e 'my $p = \"a.md\"; open(my $fh, \">\", $p)'"), ([], True))
        self.assertEqual(read("ruby -e 'p = \"a.md\"; File.write(p, \"x\")'"), ([], True))

    def test_a_literal_the_shell_may_have_expanded_is_unnamed(self) -> None:
        expanded = "python - <<EOF\np = \"$HOME/x.md\"\nopen(p, 'w')\nEOF"
        self.assertEqual(read(expanded), ([], True))
        self.assertEqual(read("python -c \"p = '$F'; open(p, 'w')\""), ([], True))
        # Near miss: a quoted delimiter expands nothing, so the literal is the path.
        self.assertEqual(read(expanded.replace("<<EOF", "<<'EOF'")), (["$HOME/x.md"], False))

    def test_one_bound_path_and_one_unnamed_write_are_both_read(self) -> None:
        command = heredoc("p = \"notes.md\"", "open(p, 'w')", "open(other, 'w')")
        self.assertEqual(read(command), (["notes.md"], True))


class OnceBoundHoldTests(ScriptTestCase):
    def test_the_reported_case_under_claude_meets_no_scripted_edit_hold(self) -> None:
        command = "cd ~/.claude/goated-notes && " + REPORTED
        s = self.routed()
        self.assertEqual(decision(s.call("Bash", {"command": command})), "pass")
        # It is still a shell write there, so routing judges it.
        self.assertEqual(shell.analyze(command).write_targets, ["~/.claude/goated-notes/notes.md"])
        piped = self.routed("goated-route: standard | requires: tdd")
        self.assertEqual(hold_line(piped.call("Bash", {"command": command})),
                         "goated-hold: pipeline | strict")

    def test_a_once_bound_code_file_in_the_project_is_held_by_name(self) -> None:
        s = self.routed()
        held = s.call("Bash", {"command": REPORTED.replace("notes.md", "src/app.py")})
        self.assertEqual(hold_line(held), SCRIPTED)
        self.assertIn("\"app.py\"", reason(held))
        self.assertNotIn("names only at run time", reason(held))

    def test_a_script_is_judged_for_its_bound_path_and_its_unnamed_write(self) -> None:
        s = self.routed()
        both = heredoc("p = \"notes.md\"", "open(p, 'w')", "open(other, 'w')")
        self.assertIn("names only at run time", reason(s.call("Bash", {"command": both})))
        # Near miss: the bound write alone is a markdown file.
        alone = heredoc("p = \"notes.md\"", "open(p, 'w')")
        self.assertEqual(decision(s.call("Bash", {"command": alone})), "pass")
        code = heredoc("p = \"src/app.py\"", "open(p, 'w')", "open(other, 'w')")
        self.assertIn("\"app.py\"", reason(s.call("Bash", {"command": code})))


class TempFolderPathTests(unittest.TestCase):
    """A path built from the system temp folder is outside the project, so it
    is neither a named file nor an unnamed write (round 6, R12)."""

    def test_a_python_path_from_the_temp_folder_writes_no_project_file(self) -> None:
        for lines in (
            ("import os, tempfile", "open(os.path.join(tempfile.gettempdir(), 'x.txt'), 'w')"),
            ("import tempfile", "d = tempfile.mkdtemp()", "p = d + '/x.txt'", "open(p, 'w')"),
            ("import os, tempfile", "with tempfile.TemporaryDirectory() as d:",
             "    open(os.path.join(d, 'x.txt'), 'w')"),
            ("import os", "open(os.path.join(os.environ['TEMP'], 'x.txt'), 'w')"),
            ("import os", "open(os.getenv('TMPDIR') + '/x.txt', 'w')"),
            ("from tempfile import gettempdir", "from pathlib import Path",
             "Path(gettempdir(), 'x.txt').write_text('1')"),
            ("import tempfile", "open(f'{tempfile.gettempdir()}/x.txt', 'w')"),
        ):
            with self.subTest(lines=lines):
                self.assertEqual(read(heredoc(*lines)), ([], False))

    def test_a_javascript_path_from_the_temp_folder_writes_no_project_file(self) -> None:
        for code in ("fs.writeFileSync(path.join(os.tmpdir(), 'x.txt'), '1')",
                     "fs.writeFileSync(`${os.tmpdir()}/x.txt`, '1')",
                     "fs.writeFileSync(process.env.TMPDIR + '/x.txt', '1')"):
            with self.subTest(code=code):
                self.assertEqual(read(f"node - <<'EOF'\n{code}\nEOF"), ([], False))

    def test_a_temp_path_that_may_leave_the_temp_folder_stays_unnamed(self) -> None:
        for lines in (
            ("import os, tempfile",
             "open(os.path.join(tempfile.gettempdir(), '..', 'src', 'app.py'), 'w')"),
            ("import os, tempfile", "open(os.path.join(ROOT, tempfile.gettempdir()), 'w')"),
            ("import tempfile", "d = tempfile.mkdtemp()", "d = ROOT", "open(d + '/x', 'w')"),
            ("import os", "open(os.path.join(os.environ['HOME'], 'x.txt'), 'w')"),
            # A default for an unset variable may be a project folder.
            ("import os", "open(os.path.join(os.environ.get('TMPDIR', '.'), 'x.txt'), 'w')"),
            ("import os", "open(os.getenv('TMP', ROOT) + '/x.txt', 'w')"),
        ):
            with self.subTest(lines=lines):
                self.assertEqual(read(heredoc(*lines)), ([], True))

    def test_shell_text_in_an_expanded_temp_path_stays_unnamed(self) -> None:
        command = "python -c \"import os, tempfile; open(os.path.join(tempfile.gettempdir(), '$F'), 'w')\""
        self.assertEqual(read(command), ([], True))


class TempFolderHoldTests(ScriptTestCase):
    def test_a_script_writing_under_the_temp_folder_meets_no_scripted_edit_hold(self) -> None:
        s = self.routed()
        temp = heredoc("import os, tempfile",
                       "open(os.path.join(tempfile.gettempdir(), 'out.txt'), 'w').write('1')")
        self.assertEqual(decision(s.call("Bash", {"command": temp})), "pass")
        # Near miss: the same script writing a run-time path inside the project is held.
        inside = heredoc("import os", "open(os.path.join(ROOT, 'out.txt'), 'w').write('1')")
        self.assertEqual(hold_line(s.call("Bash", {"command": inside})), SCRIPTED)


class UnnamedWriteAfterACdTests(ScriptTestCase):
    """An unnamed write is inside the project wherever the command runs: a
    script reaches project files from any folder (Ticket 097 review)."""

    def test_an_unnamed_write_after_a_cd_outside_is_still_held(self) -> None:
        scratch = (self.root / "scratch").as_posix()
        for script in (
            UNNAMED,
            heredoc("import os", "ROOT = '{project}'",
                    "open(os.path.join(ROOT, 'src/app.py'), 'w').write('x')"),
            "python -c \"import sys; open(sys.argv[1], 'w')\" {project}/src/app.py",
            heredoc("from pathlib import Path", "(Path('{project}') / 'src/app.py').write_text('x')"),
            heredoc("import os", "open(os.environ['PROJ'] + '/src/app.py', 'w')"),
            heredoc("import os", "os.chdir('{project}')", "open(name, 'w')"),
            "node -e \"require('fs').writeFileSync(require('path').join('{project}', "
            "'src/app.py'), 'x')\"",
        ):
            with self.subTest(script=script):
                s = self.routed()
                command = f"cd {scratch} && " + script.replace("{project}", s.project.as_posix())
                self.assertEqual(hold_line(s.call("Bash", {"command": command})), SCRIPTED)

    def test_a_run_unnamed_write_after_a_cd_outside_counts_as_changed_code(self) -> None:
        s = self.routed()
        s.say("goated-skip: software-design-principles: a probe rewrite across scratch files")
        s.run(f"cd {(self.root / 'scratch').as_posix()} && {UNNAMED}")
        self.assertIn("- Proof:", stop(s).get("reason", ""))
        # Near miss: a named markdown file written there is no code change.
        t = self.routed()
        t.run(f"cd {(self.root / 'scratch').as_posix()} && " + heredoc("open('n.md', 'w')"))
        self.assertEqual(stop(t), {})


class UnseenRebindingTests(unittest.TestCase):
    """Code that may bind a name the text does not show reads no name (review)."""

    def test_a_javascript_statement_going_on_past_its_line_is_not_read(self) -> None:
        for code in (
            "const p = 'notes.md'\n  .replace('notes.md', 'src/app.py')\nfs.writeFileSync(p, 'x')",
            "const p = 'src/app'\n  + '.py'\nfs.writeFileSync(p, 'x')",
            "const p = 'notes.md'\n  ? 'src/app.py' : ''\nfs.writeFileSync(p, 'x')",
        ):
            with self.subTest(code=code):
                self.assertEqual(read(f"node - <<'EOF'\n{code}\nEOF"), ([], True))
        # Near miss: a next line that starts a new statement ends the binding.
        ended = "const p = 'notes.md'\n\nfs.writeFileSync(p, 'x')"
        self.assertEqual(read(f"node - <<'EOF'\n{ended}\nEOF"), (["notes.md"], False))

    def test_code_the_shell_may_expand_reads_no_name_when_it_holds_an_expansion(self) -> None:
        for command in (
            "X=\"var p='src/app.py'\"; node -e \"var p='notes.md'; $X; "
            "require('fs').writeFileSync(p,'x')\"",
            "X='p = \"src/app.py\"'; python - <<EOF\np = \"notes.md\"\n$X\nopen(p, 'w')\nEOF",
            "python - <<EOF\np = \"notes.md\"\n# `date`\nopen(p, 'w')\nEOF",
        ):
            with self.subTest(command=command):
                self.assertEqual(read(command), ([], True))
        # Near misses: no expansion in the code, or a quoted heredoc, which expands nothing.
        self.assertEqual(read("node -e \"var p='notes.md'; require('fs').writeFileSync(p,'x')\""),
                         (["notes.md"], False))
        self.assertEqual(read(heredoc("p = \"notes.md\"", "# $X", "open(p, 'w')")),
                         (["notes.md"], False))

    def test_code_that_binds_names_dynamically_reads_no_name(self) -> None:
        for lines in (("exec(\"p = 'src/app.py'\")",), ("eval('1')",),
                      ("globals()['p'] = 'src/app.py'",), ("vars()['p'] = 'src/app.py'",),
                      ("import sys", "sys.modules[__name__].p = 'src/app.py'"),
                      ("from helpers import *",),
                      ("import __main__", "__main__.p = 'src/app.py'")):
            with self.subTest(lines=lines):
                self.assertEqual(read(heredoc("p = \"notes.md\"", *lines, "open(p, 'w')")),
                                 ([], True))
        for code in ("var p = 'notes.md'; eval(\"p = 'src/app.py'\"); fs.writeFileSync(p, 'x')",
                     "var p = 'notes.md'; globalThis.p = 'src/app.py'; fs.writeFileSync(p, 'x')",
                     "var p = 'notes.md'\nwith ({p: 'src/app.py'}) { fs.writeFileSync(p, 'x') }"):
            with self.subTest(code=code):
                self.assertEqual(read(f"node - <<'EOF'\n{code}\nEOF"), ([], True))
        # Near miss: a plain import, or a JavaScript namespace import, binds no hidden name.
        self.assertEqual(read(heredoc("import sys", "p = \"notes.md\"", "open(p, 'w')")),
                         (["notes.md"], False))
        namespaced = "import * as fs from 'fs'\nconst p = 'notes.md'\nfs.writeFileSync(p, 'x')"
        self.assertEqual(read(f"node - <<'EOF'\n{namespaced}\nEOF"), (["notes.md"], False))


class ReadingTimeTests(unittest.TestCase):
    def test_many_declarations_are_read_in_linear_time(self) -> None:
        declarations = 5000
        js = "\n".join(f"const v{i} = 'file{i}.md';" for i in range(declarations))
        py = "\n".join(f'v{i} = "file{i}.md"' for i in range(declarations))
        started = time.perf_counter()
        self.assertEqual(read(f"node - <<'EOF'\n{js}\nfs.writeFileSync(v1, 'x')\nEOF"),
                         (["file1.md"], False))
        self.assertEqual(read(heredoc(py, "open(v1, 'w')")), (["file1.md"], False))
        self.assertLess(time.perf_counter() - started, 1.0)


class RunTimeFileWordingTests(ScriptTestCase):
    """R4 (decision J1): a file named only at run time is of unknown kind, not code."""

    RUN_TIME = "a file it names only at run time, whose kind cannot be told"

    def test_a_run_time_file_is_named_as_of_unknown_kind_in_both_forms(self) -> None:
        s = self.routed()
        full = reason(s.call("Bash", {"command": UNNAMED}))
        self.assertIn(self.RUN_TIME + ", so it is held as code would be", full)
        self.assertNotIn("counts as code", full)
        self.assertNotIn("the code file", full)
        short = reason(s.call("Bash", {"command": UNNAMED}))
        self.assertIn("Still unmet", short)
        self.assertIn(self.RUN_TIME, short)
        self.assertNotIn("counts as code", short)

    def test_a_named_code_file_is_still_the_code_file(self) -> None:
        s = self.routed()
        held = reason(s.call("Bash", {"command": heredoc("open('src/app.py', 'w')")}))
        self.assertIn("writes the code file \"app.py\".", held)
        self.assertNotIn("kind cannot be told", held)

    def test_a_command_doing_both_names_each_in_its_own_words(self) -> None:
        s = self.routed()
        both = heredoc("open('src/app.py', 'w')", "open(other, 'w')")
        held = reason(s.call("Bash", {"command": both}))
        self.assertIn("writes the code file \"app.py\" and " + self.RUN_TIME, held)


if __name__ == "__main__":
    unittest.main()
