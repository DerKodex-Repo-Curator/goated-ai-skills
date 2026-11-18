"""Behavior tests for inline interpreter scripts that write files (Ticket 093).

Code an interpreter is given inline (`python -c`, `node -e`, a heredoc on
`python -`) is read for the calls that write, remove, or rename a file; such
a script is a shell write, and the `scripted-edit` gate holds one that writes
a project code file. Like the other adapter tests, these drive the hook entry
point (see `claude_code_adapter_support.py`), with a direct look at
`shell.analyze` for each interpreter's table.
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from claude_code_adapter_support import ROUTER, Session, decision, parse, reason
from goated_adapter import shell

HEREDOC_WRITE = "python - <<'EOF'\ntext = 'x = 1'\nopen(\"src/app.py\", \"w\").write(text)\nEOF"
SKIP_LINE = "goated-skip: software-design-principles: one mechanical rename across forty files"
SCRIPTED = "goated-hold: scripted-edit | justified-skip"
BARE_BACKTICKED = re.compile(r"`([a-z][a-z0-9-]*)`")


def hold_line(output: dict) -> str:
    return reason(output).split("\n", 1)[0]


def stop(s: Session) -> dict:
    return parse(s.hook("Stop", stop_hook_active=False, last_assistant_message=""))


class ScriptTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._sessions = 0

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def routed(self, route: str = "goated-route: direct", prompt: str = "Do the task.") -> Session:
        self._sessions += 1
        folder = self.root / f"s{self._sessions}"
        folder.mkdir()
        s = Session(folder, session_id=f"session-{self._sessions}")
        s.prompt(prompt)
        s.load(ROUTER)
        s.say(route)
        return s


class ScriptedEditHoldTests(ScriptTestCase):
    def test_a_heredoc_script_writing_code_is_held_until_a_skip_line(self) -> None:
        s = self.routed()
        held = s.call("Bash", {"command": HEREDOC_WRITE})
        self.assertEqual(hold_line(held), SCRIPTED)
        self.assertIn("app.py", reason(held))
        # Loading the design skill is not the way out: the hold asks for a file edit tool.
        s.load("software-design-principles")
        self.assertEqual(hold_line(s.call("Bash", {"command": HEREDOC_WRITE})), SCRIPTED)
        s.say(SKIP_LINE)
        self.assertEqual(decision(s.run(HEREDOC_WRITE)), "pass")
        # Once it runs, its file counts as changed code.
        self.assertIn("- Proof:", stop(s).get("reason", ""))

    def test_a_turn_with_only_a_reading_script_has_no_changed_code(self) -> None:
        s = self.routed()
        s.run("python - <<'EOF'\nprint(open(\"src/app.py\").read())\nEOF")
        self.assertEqual(stop(s), {})

    def test_the_typed_override_clears_the_hold_for_that_prompt(self) -> None:
        s = self.routed(prompt="Rename the helper everywhere; skip software-design-principles.")
        self.assertEqual(decision(s.call("Bash", {"command": HEREDOC_WRITE})), "pass")
        s.prompt("Now the next file.")
        s.say("goated-route: continue")
        self.assertEqual(hold_line(s.call("Bash", {"command": HEREDOC_WRITE})), SCRIPTED)

    def test_inline_code_options_are_held_the_same_way(self) -> None:
        for command in (
            "python -c \"open('src/app.py', 'w').write('x = 1')\"",
            "python3 -c \"from pathlib import Path; Path('src/app.py').write_text('x')\"",
            "node -e \"require('fs').writeFileSync('src/app.js', 'x')\"",
            "uv run python -c \"import shutil; shutil.copy('a.txt', 'src/app.py')\"",
            "npx node -e \"fs.renameSync('src/a.ts', 'src/b.ts')\"",
            "perl -e 'open(my $fh, \">\", \"src/app.py\") or die'",
            "ruby -e 'File.write(\"lib/app.rb\", \"x\")'",
            "deno eval \"await Deno.writeTextFile('src/app.ts', 'x')\"",
            "bun -e \"await Bun.write('src/app.ts', 'x')\"",
            "node - <<'EOF'\nconst fs = require('fs')\nfs.unlinkSync('src/old.js')\nEOF",
            "python - <<'EOF'\nopen(\"tests/test_app.py\", \"a\").write('x')\nEOF",
        ):
            with self.subTest(command=command):
                s = self.routed()
                self.assertEqual(hold_line(s.call("Bash", {"command": command})), SCRIPTED)

    def test_read_only_scripts_meet_no_hold_and_are_not_writes(self) -> None:
        # Under a route whose pipeline is not met, a write is held and a non-write is not.
        for command in (
            "python -c \"print(1)\"",
            "python - <<'EOF'\nprint(open(\"src/app.py\").read())\nEOF",
            "python - <<'EOF'\nwith open('src/app.py', 'r') as f:\n"
            "    print(f.read().replace('a', 'b'))\nEOF",
            "node -e \"console.log(require('fs').readFileSync('src/app.js', 'utf8'))\"",
            "ruby -e 'puts File.read(\"lib/app.rb\")'",
        ):
            with self.subTest(command=command):
                s = self.routed("goated-route: standard | requires: tdd")
                self.assertEqual(decision(s.call("Bash", {"command": command})), "pass")
        # Near miss: the same script opening its file to write is a write.
        s = self.routed("goated-route: standard | requires: tdd")
        held = s.call("Bash", {"command": "python -c \"open('src/app.py', 'w')\""})
        self.assertEqual(hold_line(held), "goated-hold: pipeline | strict")

    def test_a_script_writing_a_non_code_file_is_a_shell_write_but_not_held(self) -> None:
        command = "python - <<'EOF'\nopen(\"notes.txt\", \"w\").write('done')\nEOF"
        s = self.routed()
        self.assertEqual(decision(s.call("Bash", {"command": command})), "pass")
        piped = self.routed("goated-route: standard | requires: tdd")
        self.assertEqual(hold_line(piped.call("Bash", {"command": command})),
                         "goated-hold: pipeline | strict")

    def test_a_script_writing_only_outside_the_project_meets_no_hold(self) -> None:
        outside = (self.root / "scratch").as_posix()
        s = self.routed()
        command = f"python - <<'EOF'\nopen(\"{outside}/probe.py\", \"w\").write('x')\nEOF"
        self.assertEqual(decision(s.run(command)), "pass")
        self.assertEqual(stop(s), {})
        # Near miss: the same file inside the project.
        inside = f"python - <<'EOF'\nopen(\"{s.project.as_posix()}/probe.py\", \"w\")\nEOF"
        self.assertEqual(hold_line(s.call("Bash", {"command": inside})), SCRIPTED)

    def test_a_write_to_a_path_in_a_variable_is_an_unnamed_code_write(self) -> None:
        command = "python - <<'EOF'\nfor path in paths:\n    open(path, 'w').write(text)\nEOF"
        s = self.routed()
        self.assertEqual(hold_line(s.call("Bash", {"command": command})), SCRIPTED)
        s.say(SKIP_LINE)
        self.assertEqual(decision(s.run(command)), "pass")
        self.assertIn("- Proof:", stop(s).get("reason", ""))

    def test_a_sensitive_path_meets_the_security_gate_first(self) -> None:
        command = "python -c \"open('src/auth/login.py', 'w').write('x')\""
        s = self.routed()
        self.assertEqual(hold_line(s.call("Bash", {"command": command})),
                         "goated-hold: security | justified-skip")
        s.load("code-security-review")
        self.assertEqual(hold_line(s.call("Bash", {"command": command})), SCRIPTED)
        # Near miss: an ordinary code file meets scripted-edit alone.
        t = self.routed()
        plain = "python -c \"open('src/export.py', 'w').write('x')\""
        self.assertEqual(hold_line(t.call("Bash", {"command": plain})), SCRIPTED)

    def test_a_check_through_an_interpreter_is_still_a_check(self) -> None:
        s = self.routed("goated-route: standard | requires: tdd")
        self.assertEqual(decision(s.call("Bash", {"command": "python -m pytest -q"})), "pass")
        command = shell.analyze("uv run python -m pytest -q")
        self.assertTrue(command.is_check)
        self.assertFalse(command.writes)
        # Near miss: inline code is never a check, whatever it prints.
        self.assertFalse(shell.analyze("python -c \"print('pytest passed')\"").is_check)

    def test_the_hold_offers_the_design_skill_only_as_a_skip_line(self) -> None:
        # A bare backticked name reads as a skill to load (friction.py, the mod),
        # and loading the skill does not answer this hold.
        s = self.routed()
        held = reason(s.call("Bash", {"command": HEREDOC_WRITE}))
        self.assertTrue(held.startswith(SCRIPTED + "\n"), held)
        self.assertEqual(set(BARE_BACKTICKED.findall(held)), set())
        self.assertIn("`goated-skip: software-design-principles: <reason>`", held)
        self.assertIn("`skip software-design-principles`", held)


class ScriptedEditFrictionTests(ScriptTestCase):
    """The friction count reads a `scripted-edit` hold as asking for a file edit tool."""

    def friction(self, s: Session) -> int:
        from goated_adapter.state import StateStore

        return StateStore(s.config.state_dir).load(s.session_id)[0].friction

    def test_rewriting_the_named_file_with_an_edit_tool_answers_the_hold(self) -> None:
        s = self.routed()
        self.assertEqual(hold_line(s.call("Bash", {"command": HEREDOC_WRITE})), SCRIPTED)
        self.assertEqual(decision(s.call("Write", {"file_path": "src/app.py",
                                                   "content": "x = 1\n"})), "pass")
        s.prompt("Next thing.")
        self.assertEqual(self.friction(s), 0)

    def test_loading_the_skill_or_writing_another_file_leaves_it_unanswered(self) -> None:
        loaded = self.routed()
        loaded.call("Bash", {"command": HEREDOC_WRITE})
        loaded.load("software-design-principles")
        loaded.prompt("Next thing.")
        self.assertEqual(self.friction(loaded), 1)
        other = self.routed()
        other.call("Bash", {"command": HEREDOC_WRITE})
        other.call("Write", {"file_path": "docs/notes.md", "content": "x\n"})
        other.prompt("Next thing.")
        self.assertEqual(self.friction(other), 1)

    def test_any_edit_tool_write_answers_a_hold_on_an_unnamed_file(self) -> None:
        s = self.routed()
        command = "python -c \"open(path, 'w').write(text)\""
        self.assertEqual(hold_line(s.call("Bash", {"command": command})), SCRIPTED)
        s.call("Write", {"file_path": "src/other.py", "content": "x = 1\n"})
        s.prompt("Next thing.")
        self.assertEqual(self.friction(s), 0)

    def test_a_skip_line_declines_it(self) -> None:
        s = self.routed()
        s.call("Bash", {"command": HEREDOC_WRITE})
        s.say(SKIP_LINE)
        s.run(HEREDOC_WRITE)
        s.prompt("Next thing.")
        self.assertEqual(self.friction(s), 1)


class PipedScriptTests(unittest.TestCase):
    """Code reaching an interpreter's standard input from a text producer (review M2)."""

    def test_code_piped_or_fed_as_a_here_string_is_read(self) -> None:
        for tool, command in (
            ("posix", "cat <<'EOF' | python -\nopen('src/a.py', 'w').write('x')\nEOF"),
            ("posix", "cat <<EOF | python\nopen('src/a.py', 'w').write('x')\nEOF"),
            ("posix", "echo \"open('src/a.py', 'w').write('x')\" | python"),
            ("posix", "printf '%s' \"open('src/a.py', 'w')\" | python3 -"),
            ("posix", "python <<< \"open('src/a.py', 'w').write('x')\""),
            ("posix", "node <<< \"require('fs').writeFileSync('src/a.py', 'x')\""),
            ("powershell", "@'\nopen('src/a.py','w').write('x')\n'@ | python -"),
            ("powershell", "@'\nopen('src/a.py','w').write('x')\n'@ | python"),
            ("powershell", "\"open('src/a.py','w')\" | python -"),
            ("powershell", "Write-Output \"open('src/a.py','w')\" | python"),
        ):
            with self.subTest(command=command):
                result = shell.analyze(command, tool)
                self.assertEqual(result.script_targets, ["src/a.py"])

    def test_text_piped_into_a_script_file_or_from_a_file_is_not_read(self) -> None:
        for tool, command in (
            ("posix", "echo \"open('src/a.py', 'w')\" | python tools/gen.py"),
            ("posix", "cat notes.txt | python -"),
            ("posix", "echo \"open('src/a.py', 'w')\" | grep open"),
            ("posix", "python tools/gen.py <<< \"open('src/a.py', 'w')\""),
            ("posix", "echo \"print(open('src/a.py').read())\" | python"),
            ("powershell", "@'\nprint(1)\n'@ | python -"),
        ):
            with self.subTest(command=command):
                self.assertEqual(shell.analyze(command, tool).script_targets, [])


class ShellExpandedPathTests(unittest.TestCase):
    """A path the shell expands before the interpreter runs is unnamed (review M3)."""

    def test_a_path_the_shell_expands_is_an_unnamed_write(self) -> None:
        for tool, command in (
            ("posix", "python -c \"open('$F', 'w').write('x')\""),
            ("posix", "python -c \"open('src/$NAME.py', 'w')\""),
            ("posix", "python -c \"open('$(ls src | head -1)', 'w')\""),
            ("posix", "python - <<EOF\nopen('$F', 'w').write('x')\nEOF"),
            ("posix", "python - <<EOF\nopen('`echo src/a.py`', 'w')\nEOF"),
            ("posix", "node -e \"require('fs').writeFileSync('$F', 'x')\""),
            ("powershell", "python -c \"open('$env:F','w')\""),
        ):
            with self.subTest(command=command):
                result = shell.analyze(command, tool)
                self.assertEqual((result.script_targets, result.script_unknown_writes),
                                 ([], True))

    def test_a_quoted_delimiter_heredoc_expands_nothing(self) -> None:
        result = shell.analyze("python - <<'EOF'\nopen('$F', 'w').write('x')\nEOF")
        self.assertEqual((result.script_targets, result.script_unknown_writes), (["$F"], False))


class AliasedCallTests(unittest.TestCase):
    """Imported and aliased names, `ruby -i`, and versioned interpreters (review L4)."""

    def test_aliases_and_versioned_interpreters_are_read(self) -> None:
        for command, targets in (
            ("python -c \"import shutil as s; s.move('a.py', 'src/b.py')\"", ["a.py", "src/b.py"]),
            ("python -c \"from shutil import move; move('a.py', 'src/b.py')\"",
             ["a.py", "src/b.py"]),
            ("python -c \"from os import remove; remove('src/a.py')\"", ["src/a.py"]),
            ("python -c \"from os import remove as rm, rename; rm('a.py'); rename('b.py', 'c.py')\"",
             ["a.py", "b.py", "c.py"]),
            ("python -c \"from pathlib import Path as P; P('src/a.py').write_text('x')\"",
             ["src/a.py"]),
            ("python -c \"import gzip; gzip.open('src/a.py.gz', 'wt')\"", ["src/a.py.gz"]),
            ("node -e \"const {writeFileSync: w} = require('fs'); w('src/a.js', 'x')\"",
             ["src/a.js"]),
            ("node -e \"import {rmSync as r} from 'node:fs'; r('build')\"", ["build"]),
            ("ruby -i -pe '$_.sub!(/a/, \"b\")' src/a.py", ["src/a.py"]),
            ("python3.12 -c \"open('src/a.py', 'w')\"", ["src/a.py"]),
        ):
            with self.subTest(command=command):
                self.assertEqual(shell.analyze(command).write_targets, targets)

    def test_look_alike_names_are_not_aliases(self) -> None:
        for command in (
            "python -c \"import shutil as s; print(s.which('git'))\"",
            "python -c \"from os import path; print(path.exists('a.py'))\"",
            "python -c \"import gzip; gzip.open('a.gz').read()\"",
            "node -e \"const {readFileSync: r} = require('fs'); r('a.js')\"",
        ):
            with self.subTest(command=command):
                self.assertFalse(shell.analyze(command).writes, command)


class ScriptWriteTableTests(unittest.TestCase):
    """Each interpreter's write calls, as `shell.analyze` reads them."""

    def targets(self, command: str) -> tuple[list[str], bool]:
        result = shell.analyze(command)
        return result.write_targets, result.unknown_writes

    def test_each_interpreter_names_its_written_files(self) -> None:
        for command, targets in (
            ("python -c \"open('a.py', mode='w')\"", ["a.py"]),
            ("python -c \"open(file='a.py', mode='x')\"", ["a.py"]),
            ("python -c \"import os; os.remove('a.py'); os.rename('b.py', 'c.py')\"",
             ["a.py", "b.py", "c.py"]),
            ("python -c \"import shutil; shutil.move('a.py', 'b.py'); shutil.rmtree('build')\"",
             ["a.py", "b.py", "build"]),
            ("python -c \"from pathlib import Path; Path('a.py').unlink()\"", ["a.py"]),
            ("python -c \"from pathlib import Path; Path('a.py').rename('b.py')\"",
             ["a.py", "b.py"]),
            ("python -c \"from pathlib import Path; Path('a.py').open('w')\"", ["a.py"]),
            ("node -e \"fs.appendFileSync('a.js', 'x'); fs.copyFileSync('a.js', 'b.js')\"",
             ["a.js", "b.js"]),
            ("node -e \"fs.rmSync('build', {recursive: true})\"", ["build"]),
            ("node -e \"fs.openSync('a.js', 'w')\"", ["a.js"]),
            ("node -e \"require('fs').writeFileSync(`a.js`, 'x')\"", ["a.js"]),
            ("perl -e 'open(F, \">a.pm\"); unlink \"b.pm\", \"c.pm\";'", ["a.pm", "b.pm", "c.pm"]),
            ("perl -e 'rename \"a.pm\", \"b.pm\"'", ["a.pm", "b.pm"]),
            ("ruby -e 'File.open(\"a.rb\", \"w\") { |f| f.puts 1 }'", ["a.rb"]),
            ("ruby -e 'FileUtils.mv \"a.rb\", \"b.rb\"'", ["a.rb", "b.rb"]),
            ("ruby -e 'File.delete(\"a.rb\")'", ["a.rb"]),
            ("deno eval \"Deno.removeSync('a.ts')\"", ["a.ts"]),
            ("bun --eval \"Bun.write('a.ts', 'x')\"", ["a.ts"]),
            ("bun run - <<'EOF'\nawait Bun.write('a.ts', 'x')\nEOF", ["a.ts"]),
            ("deno run - <<'EOF'\nDeno.writeTextFileSync('a.ts', 'x')\nEOF", ["a.ts"]),
            ("python3 -I - <<EOF\nopen('a.py', 'w')\nEOF", ["a.py"]),
            # Placed as any shell write's target: from a `cd` the command follows.
            ("cd /work/src && python -c \"open('a.py', 'w')\"", ["/work/src/a.py"]),
        ):
            with self.subTest(command=command):
                self.assertEqual(self.targets(command), (targets, False))

    def test_a_path_that_is_not_a_literal_is_an_unnamed_write(self) -> None:
        for command in (
            "python -c \"open(name, 'w')\"",
            "python -c \"open(f'src/{name}.py', 'w')\"",
            "python -c \"open('src/' + name, 'w')\"",
            "python -c \"p.write_text('x')\"",
            "node -e \"fs.writeFileSync(`src/${name}.js`, 'x')\"",
            "perl -e 'open(my $fh, \">\", $path)'",
            "ruby -e 'File.write(\"lib/#{name}.rb\", \"x\")'",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.targets(command), ([], True))

    def test_reads_and_look_alikes_are_not_writes(self) -> None:
        for command in (
            "python -c \"open('a.py')\"",
            "python -c \"open('a.py', 'rb')\"",
            "python -c \"print('a'.replace('a', 'b'))\"",
            "node -e \"window.open('https://x', '_blank')\"",
            "node -e \"fs.readFileSync('a.js')\"",
            "perl -e 'open(F, \"<a.pm\"); open(G, \"a.pm\")'",
            "ruby -e 'File.open(\"a.rb\") { |f| puts f.read }'",
            # A script file run by name, and a heredoc fed to one, stay unseen.
            "python tools/gen.py",
            "python tools/gen.py <<'EOF'\nopen('a.py', 'w')\nEOF",
            "python -m pytest <<'EOF'\nopen('a.py', 'w')\nEOF",
        ):
            with self.subTest(command=command):
                self.assertFalse(shell.analyze(command).writes, command)


if __name__ == "__main__":
    unittest.main()
