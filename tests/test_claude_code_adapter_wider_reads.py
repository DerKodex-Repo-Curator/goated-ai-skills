"""More read-only commands pass before the router loads (Ticket 088).

Before the router loads, `router-first` passes a shell command made only of
plain reads. These forms join them: a leading `cd` to a literal path, git
subcommands that only read, simple text tools, a backslash or `//` inside a
single-quoted argument, and a Bash `2>/dev/null`. Each is admitted only
without the options that make it write a file or run another program, and a
near miss of each, such as one of those options, is held.
"""

from __future__ import annotations

import unittest

from claude_code_adapter_support import ROUTER, decision, reason
from test_claude_code_adapter_reads import READS, ReadsTestCase, hold_line

# Each passes before the router loads.
WIDER_READS = [
    # The ticket's kept forms.
    ("Bash", "cd sub && ls"),
    ("Bash", "git branch"),
    ("Bash", "git rev-parse HEAD"),
    ("Bash", "git ls-files"),
    ("Bash", "pwd"),
    ("Bash", "sort a.txt | uniq"),
    ("Bash", r"grep -n 'def\s+x' a.py"),
    ("Bash", "ls 2>/dev/null"),
    ("Bash", "true"),
    # A leading `cd` to a literal path, then plain reads.
    ("Bash", "cd ./sub && git status"),
    ("Bash", "cd /tmp/x; cat a"),
    ("Bash", "cd ~ && ls"),
    ("Bash", "cd sub"),
    ("PowerShell", "cd sub; Get-ChildItem"),
    # git subcommands that only read.
    ("Bash", "git branch -a"),
    ("Bash", "git branch -vv"),
    ("Bash", "git branch --show-current"),
    ("Bash", "git branch --list 'feat*'"),
    ("Bash", "git branch -l"),
    ("Bash", "git branch --contains HEAD"),
    ("Bash", "git branch --merged main -r"),
    ("Bash", "git branch --sort=-committerdate --format='%(refname)'"),
    ("Bash", "git rev-parse --show-toplevel"),
    ("Bash", "git rev-parse --abbrev-ref HEAD"),
    ("Bash", "git ls-files -m src"),
    ("Bash", "git blame a.py"),
    ("Bash", "git blame -L 1,5 a.py"),
    ("Bash", "git worktree list"),
    ("Bash", "git worktree list --porcelain"),
    ("Bash", "git remote"),
    ("Bash", "git remote -v"),
    ("Bash", "git remote get-url origin"),
    ("Bash", "git -C sub branch --show-current"),
    # Simple text tools.
    ("Bash", "echo hi"),
    ("Bash", "echo 'goated-skip: tdd: no behaviour changes here'"),
    ("Bash", "cut -d, -f1 a.csv"),
    ("Bash", "tr a-z A-Z < a.txt"),
    ("Bash", "diff a.txt b.txt"),
    ("Bash", "diff -u a.txt b.txt"),
    ("Bash", "stat a.py"),
    ("Bash", "file a.py"),
    ("Bash", "file -b a.py"),
    ("Bash", "which python"),
    ("Bash", ":"),
    ("Bash", "true goated-skip: tdd: nothing to test"),
    ("Bash", "uniq -c a.txt"),
    ("Bash", "uniq -f 1 a.txt"),
    ("Bash", "sort -u -k 2 a.txt"),
    ("Bash", "sort -rn a.txt | head"),
    ("PowerShell", "pwd"),
    ("PowerShell", "echo hi"),
    # A backslash or `//` inside a single-quoted argument.
    ("Bash", "grep -rn 'http://example.com' src"),
    ("Bash", r"rg 'a\b' src"),
    ("Bash", r"tr '\n' ' ' < a.txt"),
    ("Bash", r"grep -c 'a\\b' a.py"),
    ("PowerShell", r"Get-Content 'src\a.py'"),
    ("Bash", r"cat 'a b' 'c\d'"),
    ("Bash", r"grep -e 'a\b' -e 'c\d' a.py # it's a note"),
    # `2>/dev/null` in Bash, where `/dev/null` is the null device.
    ("Bash", "grep -rn x src 2>/dev/null | wc -l"),
    ("Bash", "cat a 2> /dev/null"),
    ("Bash", "cd sub 2>/dev/null && ls"),
]

# Each is held before the router loads: a near miss of a form above.
WIDER_HELD = [
    # git branch with a name to create, or an option that changes or edits.
    ("Bash", "git branch new-name"),
    ("Bash", "git branch -a new-name"),
    # Before git 2.23, `-l` meant `--create-reflog`, so this created `feat`.
    ("Bash", "git branch -l feat"),
    ("Bash", "git branch -d old"),
    ("Bash", "git branch -D old"),
    ("Bash", "git branch -m a b"),
    ("Bash", "git branch -c a b"),
    ("Bash", "git branch -f x HEAD"),
    ("Bash", "git branch --track x origin/x"),
    ("Bash", "git branch -u origin/x"),
    ("Bash", "git branch --set-upstream-to=origin/x"),
    ("Bash", "git branch --unset-upstream"),
    # `--edit-description` opens an editor; git takes `--edit` for it too.
    ("Bash", "git branch --edit-description"),
    ("Bash", "git branch --edit"),
    ("Bash", "git branch --column"),
    # git remote with a change, or one that contacts the remote.
    ("Bash", "git remote add o url"),
    ("Bash", "git remote remove o"),
    ("Bash", "git remote rename a b"),
    ("Bash", "git remote set-url o url"),
    ("Bash", "git remote prune o"),
    ("Bash", "git remote update"),
    ("Bash", "git remote show origin"),
    ("Bash", "git remote -v add o url"),
    # git worktree beyond `list`.
    ("Bash", "git worktree add ../x"),
    ("Bash", "git worktree remove x"),
    ("Bash", "git worktree prune"),
    ("Bash", "git worktree"),
    # Options that run a program the repository's config names, or set one.
    ("Bash", "git blame --textconv a.py"),
    ("Bash", "git -c core.pager=sh branch"),
    ("Bash", "git -p branch"),
    # echo with a redirect into a file.
    ("Bash", "echo x > f"),
    ("Bash", "echo x >> f"),
    ("Bash", "echo x | tee f"),
    ("Bash", "echo x 2>/dev/null > f"),
    ("PowerShell", "echo x > f"),
    # A leading cd that is not a plain path, or a non-read after it.
    ("Bash", "cd sub && rm f"),
    ("Bash", "cd sub && ls > out.txt"),
    ("Bash", "cd sub && ls && rm f"),
    ("Bash", "cd $HOME && ls"),
    ("Bash", "cd - && ls"),
    ("Bash", "cd a b && ls"),
    ("Bash", "cd '//host/share' && ls"),
    ("Bash", "ls && cd sub && ls"),
    ("Bash", "pushd sub && ls"),
    # sort's options that write a file or run a program.
    ("Bash", "sort -o out.txt a.txt"),
    ("Bash", "sort -uo out.txt a.txt"),
    ("Bash", "sort --output=out.txt a.txt"),
    ("Bash", "sort --out=out.txt a.txt"),
    ("Bash", "sort --compress-program=sh a.txt"),
    ("Bash", "sort --compress=sh a.txt"),
    ("Bash", "sort -T tmp a.txt"),
    ("Bash", "sort --temporary-directory=tmp a.txt"),
    # uniq writes its second file argument.
    ("Bash", "uniq a.txt out.txt"),
    ("Bash", "uniq -c a.txt out.txt"),
    # diff's `--paginate` pipes the output through `pr`.
    ("Bash", "diff -l a b"),
    ("Bash", "diff -ql a b"),
    ("Bash", "diff --paginate a b"),
    ("Bash", "diff --pag a b"),
    # file's `-C` writes a compiled magic file; `-z` runs decompressors;
    # `-m` takes a colon-separated list of magic files.
    ("Bash", "file -C -m magic"),
    ("Bash", "file --compile -m magic"),
    ("Bash", "file -z a.gz"),
    ("Bash", "file -Z a.gz"),
    ("Bash", "file -bz a.gz"),
    ("Bash", "file --uncompress a.gz"),
    ("Bash", "file -m magic a"),
    # A backslash outside a whole single-quoted argument, and `//` that may
    # start a UNC path inside one.
    ("Bash", r'grep -n "def\s+x" a.py'),
    ("Bash", r"grep -n def\\s a.py"),
    ("Bash", r"grep -n x'\s' a.py"),
    ("Bash", r"grep -n 'x'\s a.py"),
    ("Bash", "grep -n '// TODO' a.c"),
    ("Bash", r"cat '\\host\share\a'"),
    ("Bash", r"cat '/\host/share/a'"),
    ("Bash", "rg x '--ignore-file=//host/share/a'"),
    ("Bash", r"rg x '--ignore-file=\\host\share\a'"),
    ("Bash", "cat 'a,//host/share/a'"),
    ("PowerShell", r"Get-Content src\a.py"),
    ("PowerShell", r"Get-Content '\\host\share\a'"),
    ("Bash", r"grep -n 'a$' a.py"),
    # A quote that closes a quoted word is not one that opens an argument:
    # bash escapes the quote after `\`, while PowerShell starts a string
    # there and runs `Remove-Item`.
    ("PowerShell", r"cat 'x '\' '; Remove-Item b; ''"),
    ("Bash", r"cat 'x '\' '; rm b; ''"),
    ("PowerShell", r"cat 'x '\'' '; Remove-Item b; ''"),
    # A redirect other than standard error into the null device.
    ("Bash", "ls 2> errors.txt"),
    ("Bash", "ls 2>> errors.txt"),
    ("Bash", "ls > /dev/null"),
    ("Bash", "ls &>/dev/null"),
    ("Bash", "ls 2>/dev/null > out.txt"),
    ("Bash", "ls 2>/dev/nullx"),
    ("PowerShell", "Get-Content a 2>/dev/null"),
    # A new form joined with a non-read is held whole.
    ("Bash", "pwd && rm f"),
    ("Bash", "git branch; git push"),
    ("Bash", "sort a.txt | sh"),
    ("Bash", "echo x | xargs rm"),
    ("Bash", "true && make-it"),
    ("Bash", "git rev-parse HEAD && git commit -m x"),
    ("Bash", "diff a b | tee out.txt"),
]


class WiderPlainReadsTests(ReadsTestCase):
    def test_the_wider_reads_pass_router_first(self) -> None:
        for tool, command in WIDER_READS:
            with self.subTest(command=command):
                s = self.fresh()
                self.assertEqual(decision(s.call(tool, {"command": command})), "pass")

    def test_their_near_misses_are_held_by_router_first(self) -> None:
        for tool, command in WIDER_HELD:
            with self.subTest(command=command):
                s = self.fresh()
                held = s.call(tool, {"command": command})
                self.assertEqual(hold_line(held), "goated-hold: router-first | strict")

    def test_every_earlier_plain_read_still_passes(self) -> None:
        for tool, command in READS:
            with self.subTest(command=command):
                s = self.fresh()
                self.assertEqual(decision(s.call(tool, {"command": command})), "pass")

    def test_once_the_router_loads_a_new_form_is_judged_as_before(self) -> None:
        s = self.fresh()
        s.load(ROUTER)
        self.assertEqual(decision(s.call("Bash", {"command": "git branch"})), "pass")
        held = s.call("Bash", {"command": "echo x > f"})
        self.assertEqual(hold_line(held), "goated-hold: route-line | strict")

    def test_the_hold_names_the_wider_reads(self) -> None:
        held = reason(self.fresh().call("Bash", {"command": "pytest"}))
        self.assertIn("after a leading cd", held)
        self.assertIn("2>/dev/null", held)


if __name__ == "__main__":
    unittest.main()
