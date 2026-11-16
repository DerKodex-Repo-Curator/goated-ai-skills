# Ticket 031: Claude Code Adapter, Action And Closeout Gates

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (R5 action gates and
closeout, R6, R7 references and content checks, R8 commit override, R9)

## Type

AFK.

## What To Build

Extend the adapter with these gates, none of which allows a free retry.

**Strict holds:**

- **Commit:** `commit-message`.
- **PR creation:** `pr-description`.
- **Agent or session spawns:** `handoff` in spawn-brief mode, or
  `subagent-driven-development`. The brief must have been read via
  `references/spawn-brief.md` and must carry the template's required sections.

**Justified-skip holds:**

- **Design:** `software-design-principles`.
- **Security:** `code-security-review`.

**Closeout:** after a turn that changed code, require fresh proof, plus:

- `doc-sync` when behavior or interfaces changed;
- `handoff` when work is left unfinished;
- the `software-design-principles` red-flags reference when design applied.

**Shell writes:** a `Bash` or `PowerShell` command that writes files meets the
same route-line and pipeline gates as an `Edit` (maintainer decision,
2026-11-16). Ticket 030 holds shell commands only at router-first. Recognize at
least:

- output redirects (`>`, `>>`) and `tee`;
- in-place edits such as `sed -i`;
- `Set-Content`, `Out-File`, and `Add-Content`;
- `cp`, `mv`, and `rm`, and their PowerShell equivalents;
- `git apply` and `git checkout -- <path>`.

Reads, test runs, and `git status` stay free.

**Rules for every hold:**

- A hold stops firing once its skill has been applied for that action.
- A user-supplied commit message, recorded from the user's prompt, stands the
  commit hold down.
- Action gates apply inside subagents.

Re-evaluate the personal trial's cooldowns against the no-free-retry rule
instead of copying them.

## Recommended First Reads

- The spec's R5–R9.
- Ticket 030's adapter structure and tests.
- `skills/agent-workflows/handoff/references/spawn-brief.md` and
  `skills/engineering/commit-message/SKILL.md`, the contracts for the content
  checks.

## Acceptance Criteria

- [x] Unit tests prove each of these:
  - [x] each strict hold blocks until its skill loads in the current turn;
  - [x] a `goated-skip` line passes design, security, and closeout holds, but
        never strict ones;
  - [x] an unchanged retry never passes;
  - [x] a missing required-reference read keeps the hold;
  - [x] a brief missing a required section is held;
  - [x] a commit message breaking the `commit-message` contract is held;
  - [x] a user-typed commit message stands the commit hold down;
  - [x] a hold does not refire after compliance;
  - [x] action gates apply in subagents;
  - [x] each shell-write pattern listed above meets the route-line and
        pipeline holds, while reads, test runs, and `git status` stay free.
- [x] The tests run in CI on Python 3.11 and 3.14.
- [x] Hold messages follow one documented format that the mod can parse.

## Closeout

Completed on 2026-11-16. A code review's findings were fixed before merge.
A live check then found that interactive Claude Code records a tool call in
the transcript only after its PreToolUse hook returns, so the adapter now
judges each call from the hook input. Checked live in an interactive session:
router-first, route-line, spawn, design, and closeout holds fired and cleared.
Known cost: a route or skip line written in the same message as the held call
is not yet visible, so the agent repeats the call once.

## Expected Proof

- Unit-test and validator output.

## Blocked By

- `tickets/archive/030-claude-code-adapter-routing-gates.md`

## Scope Exclusions

- The skill-usage mod (Ticket 032).
- Installing the adapter on the maintainer's machine (Ticket 033).
