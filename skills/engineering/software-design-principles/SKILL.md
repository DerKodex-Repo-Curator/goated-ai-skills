---
name: software-design-principles
description: Use when designing or changing a module, interface, abstraction, error-handling path, or configuration surface, or when reviewing code for design quality, complexity, or red flags; not needed for tiny mechanical edits.
metadata:
  goated-category: engineering
---

# Software Design Principles

## Purpose

Keep code easy to understand and easy to change. Two things threaten that:
**dependencies** (code that cannot be understood or changed alone) and
**obscurity** (important information that is not obvious).

This skill holds the design rules, the checks for three moments in a piece of
work, and a reference library that explains each rule. It merges ideas from
*The Pragmatic Programmer* and *A Philosophy of Software Design*, restated in
plain words.

These are guidelines for judgement, not laws. System, user, and project
instructions and a project's own standards take priority over everything here.
If following a rule does not make the code simpler to understand and change,
do not follow it.

## Inputs

- The request, ticket, plan, or diff, and the code around the change.
- Project instructions, standards, and conventions that already settle a
  design question.

## Dependencies

Hard: None.

Soft:
- tdd for test-first order and behavior proof
- design-codebase-architecture when a module boundary or public interface needs a blueprint
- code-refinement when a red flag in recent code needs a scoped, behavior-preserving fix
- diagnose for debugging procedure
- code-security-review for security-sensitive changes

Fallback: Without those skills, apply the rules below directly and read the
references each moment names for the reasoning.

## Workflow

1. Check what already decides the question: project instructions, documented
   standards, and the conventions in the surrounding code. Those win.
2. At the start of design work in a turn, check each moment's **Read now**
   list below and write the design-reads line naming the references whose
   conditions hold. Read them before the work they serve. Write the line again
   when the work changes and a new condition holds. A reference already read
   in this context window need not be read again.
3. Apply the rules for the current moment. Scale the effort to the change: a
   one-line fix needs a glance at the rules, not a design exercise.
4. Before reporting the work as done, read [Red Flags](references/red-flags.md)
   and scan the change against it.
5. In the reply that reports the work, cite the references you read, following
   the citation convention below.

### Design-reads line

Write it on its own line, outside code blocks:

- `goated-design-reads: <file>, <file>` names the references the triggers
  select, by file name, such as `goated-design-reads: process.md, errors.md`;
- `goated-design-reads: none: <reason>` declares a change with no design in
  it, such as `goated-design-reads: none: renames one local variable`.

The line tells the user, and any reviewer, which reasoning the work rests on.
`red-flags.md` is read at step 4 and need not be listed.

### Citations

Cite a section as `file#id`, such as `process.md#design-twice`; the index
below lists every id with its file. The reply that reports the work cites at
least one id from each reference read for it, saying how it shaped the change
or why it did not apply, such as "`errors.md#crash-early`: the parser now
raises on a bad header instead of returning an empty record".

### When rules pull apart

At any moment, when two rules here seem to pull against each other, such as
tests first against a quick spike, or more comments against fewer, read
[Where The Books Differ](references/differences.md) before choosing.

## Rules

### Before changing code

**Read now**, when the condition holds:

- [process.md](references/process.md): a new module or public interface, a
  choice between designs, an unclear requirement, a first slice to pick, or a
  problem that feels stuck.
- [complexity-and-modules.md](references/complexity-and-modules.md): deciding
  where a module boundary goes, what an interface exposes, or whether to split
  or merge code.
- [decoupling.md](references/decoupling.md): the knowledge may already exist
  elsewhere, the change will touch several files, or it adds a setting, global
  data, inheritance, a vendor wrapper, or a data pipeline.

1. Read the surrounding code and follow its conventions for names, layout, and
   error handling. `readability.md#consistency`
2. Find the one module that should own the knowledge you are about to add. If
   it already exists somewhere, use it; do not write a second copy.
   `decoupling.md#dry` `complexity-and-modules.md#information-hiding`
3. For an important interface decision, such as a new module or a public
   function other code will depend on, sketch two interfaces that differ in
   kind and choose the one that is simplest for callers.
   `process.md#design-twice`
4. Write the interface comment first. If it is hard to write, simplify the
   design. `readability.md#comments-first`
5. If requirements are unclear, state the consequences of each reading. Ask,
   or take a stated provisional default when the choice is reversible and
   low-risk. Do not guess silently. `process.md#requirements`

### While writing code

**Read now**, when the condition holds:

- [complexity-and-modules.md](references/complexity-and-modules.md): adding a
  layer, a parameter, or a pass-through function, or splitting or merging
  functions or classes.
- [decoupling.md](references/decoupling.md): adding a setting, reaching into
  another object, or writing the same knowledge in a second place.
- [errors.md](references/errors.md): code that raises, catches, validates,
  asserts, or opens and closes a resource.
- [readability.md](references/readability.md): naming something new, or
  writing a comment or docstring.
- [concurrency.md](references/concurrency.md): more than one task can reach
  the same data, steps are forced into an order, or code handles events.
- [coding.md](references/coding.md): code works for reasons you cannot state,
  you are refactoring or writing tests, or the question is speed.

6. Prefer one deep function or class to several thin ones that forward to each
   other. Judge by depth and independence, not line count.
   `complexity-and-modules.md#deep-modules` `complexity-and-modules.md#layers`
   `complexity-and-modules.md#together-apart`
7. Do not return internal data structures or reach through other objects'
   internals. `decoupling.md#tell-dont-ask`
8. Do not add a parameter, setting, or exception to avoid making a decision.
   Decide, and give a default.
   `complexity-and-modules.md#pull-down` `decoupling.md#configuration`
9. For each possible failure: design it away, handle it once, or stop loudly.
   Never catch an error only to hide it, and never hide one a caller needs.
   `errors.md#error-decision`
10. Rely only on documented behaviour. Do not add calls or retries "until it
    works". If something is unverified, say so. `coding.md#coincidence`
11. Use precise names. If a good name is hard to find, the thing may be doing
    two jobs. `readability.md#naming`
12. Give each public class and function an interface comment that says
    something the signature does not. Inside functions, comment only intent
    and surprises. Never restate the code. `readability.md#comments`
13. Open and close each resource in the same place. `errors.md#resources`
14. Avoid shared changeable state. If it must exist, give it one owner.
    `concurrency.md#shared-state`

### Before reporting the work as done

**Read now**, when the condition holds:

- [red-flags.md](references/red-flags.md): always, at Workflow step 4.
- [coding.md](references/coding.md): the change refactors code or fixes a bug,
  and the file was not already read while writing.
- [readability.md](references/readability.md): the diff adds, changes, or sits
  next to comments, and the file was not already read while writing.

15. The change should look as if the code had been designed for it. Do not
    leave a patch on the side. `coding.md#refactoring`
16. For a bug, show a test that failed before the fix and passes after it.
    `coding.md#testing`
17. Claim "working" only with evidence from this session.
18. Reread the diff. Check every comment near a change is still true, and
    remove leftovers. `readability.md#keeping-comments-true`
19. Scan the change against the red flags. Name any that remain and why.
    `red-flags.md#red-flags`
20. Keep the change within what was asked. Note other problems you saw,
    including known flaws left in place; do not fix them unasked.
    `complexity-and-modules.md#complexity-incremental`

## Checklists

**Before you start**

- [ ] Can I say in one sentence what this is for and how success will be judged?
- [ ] What are the real constraints, and which did I only assume?
- [ ] Which module should own this knowledge?
- [ ] For an important interface, have I sketched two designs?
- [ ] What is the riskiest unknown, and can a quick prototype answer it?
- [ ] What is the smallest end-to-end slice?

**While you code**

- [ ] Is the interface comment written, and short?
- [ ] Does this make the system easier or harder to change?
- [ ] Am I storing each fact once?
- [ ] Can I explain why every line is there?
- [ ] For each failure: design away, handle once, or stop?
- [ ] Am I taking small steps and checking each one?
- [ ] Does something feel harder than it should? Stop and find out why.

**Before you report done, or when reviewing**

- [ ] Does the change look designed in, or patched on?
- [ ] Any red flags left?
- [ ] Would a newcomer's first guess about each name be right?
- [ ] Do comments add something the code cannot say, and are they still true?
- [ ] How many files did this touch, and should it have been fewer?
- [ ] Are there tests, and did I see them fail before they passed?
- [ ] Are resources opened and closed in the same place?
- [ ] Anything secret, or left over from debugging, in the diff?

## Section Index

Cite a section as `file#id`. Each id is an `<!-- id: #name -->` comment in
the file listed here.

| Reference | Read when | Section ids |
| --- | --- | --- |
| [Red Flags](references/red-flags.md) | Before reporting done; reviewing a change | `#red-flags` |
| [Complexity And Modules](references/complexity-and-modules.md) | Placing a module boundary, shaping an interface, splitting or merging code | `#complexity-defined` `#complexity-symptoms` `#complexity-incremental` `#etc` `#strategic` `#deep-modules` `#information-hiding` `#general-purpose` `#layers` `#pull-down` `#together-apart` `#what-matters` `#glossary` |
| [Keeping Code Easy To Change](references/decoupling.md) | Duplicated knowledge, changes across files, settings, global data, inheritance | `#dry` `#orthogonality` `#tell-dont-ask` `#global-data` `#inheritance` `#reversibility` `#configuration` `#pipelines` |
| [Errors And Defensive Code](references/errors.md) | Raising, catching, validating, asserting, managing a resource | `#error-decision` `#define-away` `#fewer-handlers` `#crash-early` `#contracts` `#assertions` `#resources` |
| [Names, Comments And Obvious Code](references/readability.md) | Naming, commenting, checking comments near a change | `#obvious` `#naming` `#comments` `#comments-first` `#keeping-comments-true` `#consistency` |
| [Designing And Planning](references/process.md) | New interface, competing designs, unclear requirement, first slice, stuck problem | `#small-steps` `#design-twice` `#tracer-bullets` `#prototypes` `#requirements` `#puzzles` `#domain-language` `#good-enough` `#starter-kit` `#agility` |
| [While You Are Coding](references/coding.md) | Unexplained working code, refactoring, tests, bug fixes, speed | `#coincidence` `#refactoring` `#testing` `#algorithm-speed` `#performance` `#security` `#debugging` |
| [Events And Concurrency](references/concurrency.md) | Shared data across tasks, forced ordering, events | `#shared-state` `#temporal-coupling` `#events` `#actors` |
| [Where The Books Differ](references/differences.md) | Any moment, when two rules pull apart | `#differences` |

## Output Contract

This skill shapes the work; it does not add a report. It adds only the
design-reads line and the citations defined in the Workflow. In integrated use,
return only material deltas:

- a design decision that needs the user's choice, with the options compared;
- red flags that remain in the change, each with the reason it stays;
- a `refinement-debt` signal when concrete debt remains outside the agreed
  scope.

## Delegation

Main owns design judgement and the final choice. Delegate only a bounded
red-flag scan of a named diff or one constrained alternative design. Require
paths, the flag or option, evidence, and confidence. Without delegation, run
the same checks sequentially.

## Guardrails

- A project's documented standard or established convention outranks a rule
  here, including on comment quantity, test order, function size, and error
  style. Say so when you follow the project over this skill.
- A red flag is a prompt to look, not proof of a fault.
- Keep every limit that comes with a rule. Hiding what callers need, wrapping
  every library, forcing unlike things into one pattern, and designing for
  imagined futures are failures too.
- This skill is not a reason to widen scope or refactor code the task did not
  touch.

## References

The linked support files are listed in the Section Index above. Read each at
the moment its **Read now** condition holds, and when a `file#id` citation
points into it.
