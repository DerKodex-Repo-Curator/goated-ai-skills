"""Behavior tests for where an inline script's writes go (Ticket 097).

A write call whose path is a name the same script binds once, at its top
level and before the call, to one string literal writes that literal's
file. An unnamed write, after a leading `cd` to a folder certainly outside
the project (outside any git checkout and `~/.claude`), is placed in that
folder rather than inside the project. Like the other adapter tests, these
drive the hook entry point (see `claude_code_adapter_support.py`), with a
direct look at `shell.analyze` for the reading itself.
"""

from __future__ import annotations

import unittest

from claude_code_adapter_support import decision, reason
from goated_adapter import shell
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


class OutsideFolderTests(ScriptTestCase):
    """An unnamed write after a leading `cd` to a folder certainly outside is placed there."""

    def test_an_unnamed_write_in_a_temp_folder_meets_no_hold_and_no_closeout(self) -> None:
        scratch = self.root / "scratch"
        scratch.mkdir()
        s = self.routed()
        command = f"cd {scratch.as_posix()} && {UNNAMED}"
        self.assertEqual(decision(s.run(command)), "pass")
        self.assertEqual(stop(s), {})
        # Near miss: the same script with no leading `cd` is inside the project.
        t = self.routed()
        self.assertEqual(hold_line(t.call("Bash", {"command": UNNAMED})), SCRIPTED)

    def test_an_unnamed_write_anywhere_else_is_inside_the_project(self) -> None:
        checkout = self.root / "other-checkout"
        (checkout / ".git").mkdir(parents=True)
        scratch = self.root / "scratch"
        scratch.mkdir()
        for start in (
            f"cd {checkout.as_posix()} && ",
            f"cd {(checkout / 'sub').as_posix()} && ",
            "cd ~/.claude/goated-notes && ",
            "cd $SCRATCH && ",
            f"cd {scratch.as_posix()}; ",  # A `cd` that may have failed is not followed.
            "",
        ):
            with self.subTest(start=start):
                s = self.routed()
                self.assertEqual(hold_line(s.call("Bash", {"command": start + UNNAMED})), SCRIPTED)

    def test_a_shell_write_with_no_name_stays_inside_after_a_cd(self) -> None:
        # Only an inline script's unnamed write is placed; `git apply` and the like are not.
        scratch = self.root / "scratch"
        scratch.mkdir()
        s = self.routed()
        s.run(f"cd {scratch.as_posix()} && git apply fix.patch")
        self.assertIn("- Proof:", stop(s).get("reason", ""))


if __name__ == "__main__":
    unittest.main()
