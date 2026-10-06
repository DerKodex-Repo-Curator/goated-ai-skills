# Guided Manual Procedure

Read this in automate mode when the remaining setup steps are ones only a human
can perform: creating an account, clicking through a third-party dashboard,
approving access, or entering a credential. The goal is a short walkthrough the
human follows once, not replay logic the agent runs.

Steps the agent can perform itself belong in ordinary automation, covered by
[Automation And Safety](automation-and-safety.md).

## Scope The Procedure

Read the project before asking: environment templates, setup docs, container
and task-runner files, and CI configuration. Every referenced secret or
variable is a value the procedure must produce.

List the stages in order and confirm the list with the user. Scoping is done
when, for every captured value, you know:

- where the human obtains it;
- where it must end up (a local environment file, a secret store, both, or
  nowhere, because the stage is a pure action);
- whether it is secret.

## Write Each Stage

- One stage, one focused task, in dependency order.
- State the exact path the human follows: which page to open, what to select,
  where the value appears, and which variable it fills.
- Where the current screen or command is not known, say so and ask or check
  the official documentation. Never invent a step that may not exist.
- Put a confirmation before any irreversible action, and say what it changes.
- End each stage with an observable result the human can check.

## Handle Secrets

The human enters a secret directly at its destination. The walkthrough names
the variable and the destination; it never asks the human to paste a secret
into the conversation, and never echoes, logs, or stores one. Tracked recipes
and scripts carry variable names and acquisition instructions only.

## Choose The Form

Prefer the lightest form that works for the project's supported platforms:

1. An ordered checklist in the setup recipe, with each step marked manual.
2. An interactive script, only when the user asks for one or the procedure
   will be repeated. Follow the project's existing script language and
   conventions; do not assume one shell on every platform.

A procedure built for a single run is disposable. Track it only when the user
wants a repeatable path.

## Verify Without Running It

A guided procedure blocks on human input and may open external pages, so do not
execute it end to end. Check it statically:

- every value from scoping is captured and lands where scoping said;
- every secret or variable name matches the reference in project configuration
  exactly;
- any script passes the syntax or lint check the project already uses.

Mark each stage `unverified` until the human reports its observable result.
