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
matching reference for the reasoning.

## Workflow

1. Check what already decides the question: project instructions, documented
   standards, and the conventions in the surrounding code. Those win.
2. Apply the rules for the current moment. Scale the effort to the change: a
   one-line fix needs a glance at the rules, not a design exercise.
3. Read a reference only when you need the reasoning, a limit, or an example
   for a specific rule. Look up its section id in the index below.
4. Before reporting the work as done, read [Red Flags](references/red-flags.md)
   and scan the change against it.
5. When explaining a design choice, cite the section id, such as
   `#design-twice`.

## Rules

### Before changing code

1. Read the surrounding code and follow its conventions for names, layout, and
   error handling. `#consistency`
2. Find the one module that should own the knowledge you are about to add. If
   it already exists somewhere, use it; do not write a second copy. `#dry`
   `#information-hiding`
3. For an important interface decision, such as a new module or a public
   function other code will depend on, sketch two interfaces that differ in
   kind and choose the one that is simplest for callers. `#design-twice`
4. Write the interface comment first. If it is hard to write, simplify the
   design. `#comments-first`
5. If requirements are unclear, state the consequences of each reading. Ask,
   or take a stated provisional default when the choice is reversible and
   low-risk. Do not guess silently. `#requirements`

### While writing code

6. Prefer one deep function or class to several thin ones that forward to each
   other. Judge by depth and independence, not line count. `#deep-modules`
   `#layers` `#together-apart`
7. Do not return internal data structures or reach through other objects'
   internals. `#tell-dont-ask`
8. Do not add a parameter, setting, or exception to avoid making a decision.
   Decide, and give a default. `#pull-down` `#configuration`
9. For each possible failure: design it away, handle it once, or stop loudly.
   Never catch an error only to hide it, and never hide one a caller needs.
   `#error-decision`
10. Rely only on documented behaviour. Do not add calls or retries "until it
    works". If something is unverified, say so. `#coincidence`
11. Use precise names. If a good name is hard to find, the thing may be doing
    two jobs. `#naming`
12. Give each public class and function an interface comment that says
    something the signature does not. Inside functions, comment only intent
    and surprises. Never restate the code. `#comments`
13. Open and close each resource in the same place. `#resources`
14. Avoid shared changeable state. If it must exist, give it one owner.
    `#shared-state`

### Before reporting the work as done

15. The change should look as if the code had been designed for it. Do not
    leave a patch on the side. `#refactoring`
16. For a bug, show a test that failed before the fix and passes after it.
    `#testing`
17. Claim "working" only with evidence from this session.
18. Reread the diff. Check every comment near a change is still true, and
    remove leftovers. `#keeping-comments-true`
19. Scan the change against the red flags. Name any that remain and why.
    `#red-flags`
20. Keep the change within what was asked. Note other problems you saw,
    including known flaws left in place; do not fix them unasked.
    `#complexity-incremental`

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

Other skills cite sections of this skill by id. Each id is an
`<!-- id: #name -->` comment in the file listed here.

| Reference | Section ids |
| --- | --- |
| [Red Flags](references/red-flags.md) | `#red-flags` |
| [Complexity And Modules](references/complexity-and-modules.md) | `#complexity-defined` `#complexity-symptoms` `#complexity-incremental` `#etc` `#strategic` `#deep-modules` `#information-hiding` `#general-purpose` `#layers` `#pull-down` `#together-apart` `#what-matters` `#glossary` |
| [Keeping Code Easy To Change](references/decoupling.md) | `#dry` `#orthogonality` `#tell-dont-ask` `#global-data` `#inheritance` `#reversibility` `#configuration` `#pipelines` |
| [Errors And Defensive Code](references/errors.md) | `#error-decision` `#define-away` `#fewer-handlers` `#crash-early` `#contracts` `#assertions` `#resources` |
| [Names, Comments And Obvious Code](references/readability.md) | `#obvious` `#naming` `#comments` `#comments-first` `#keeping-comments-true` `#consistency` |
| [Designing And Planning](references/process.md) | `#small-steps` `#design-twice` `#tracer-bullets` `#prototypes` `#requirements` `#puzzles` `#domain-language` `#good-enough` `#starter-kit` `#agility` |
| [While You Are Coding](references/coding.md) | `#coincidence` `#refactoring` `#testing` `#algorithm-speed` `#performance` `#security` `#debugging` |
| [Events And Concurrency](references/concurrency.md) | `#shared-state` `#temporal-coupling` `#events` `#actors` |
| [Where The Books Differ](references/differences.md) | `#differences` |

## Output Contract

This skill shapes the work; it does not add a report. In integrated use,
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

The linked support files are listed in the Section Index above. Read one at
the workflow steps above or when a rule's section id points into it.
