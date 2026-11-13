# Complexity And Modules

Read this when deciding where a module boundary goes, what an interface should expose, whether to split or merge code, or when a term in this skill is unfamiliar.

These are guidelines for judgement. Project instructions, a project's own standards, and the user's requests take priority. `[PP ...]` and `[APoSD ...]` mark which book an idea comes from.

## Contents

- [Complexity, the real enemy](#complexity-the-real-enemy)
  - `#complexity-defined` What complexity is
  - `#complexity-symptoms` Three symptoms, two causes
  - `#complexity-incremental` Complexity arrives in small pieces
  - `#etc` The single test: is it easier to change?
  - `#strategic` Working code is not enough
- [Designing modules](#designing-modules)
  - `#deep-modules` Make modules deep
  - `#information-hiding` Hide design decisions
  - `#general-purpose` Make interfaces somewhat general
  - `#layers` Each layer should add something
  - `#pull-down` Pull complexity downward
  - `#together-apart` Together or apart?
  - `#what-matters` Decide what matters
- [Glossary](#glossary)

<!-- id: #complexity -->

## Complexity, the real enemy

Software is not limited by physics. It is limited by how much of it people can hold in their heads. This part defines the problem so that the rest of the guide can aim at it.

<!-- id: #complexity-defined -->

### What complexity is [APoSD ch.2]

**Rule:** Complexity is anything about the structure of a system that makes it hard to understand or hard to change.

- **The reader decides.** If your code seems simple to you but confuses other people, it is complex. Ask them where they got lost.
- **It is weighted by traffic.** Complexity in a corner nobody visits costs little. Complexity in code people touch every day costs a lot. Hiding a hard thing behind a clean interface is nearly as good as removing it.
- **Fewer lines is not the goal.** Sometimes the longer version is simpler because the reader has less to work out.

> **As a rough formula.** Total complexity = for each part of the system, (how complex that part is) × (how much time developers spend in it), all added up.

<!-- id: #complexity-symptoms -->

### Three symptoms, two causes [APoSD ch.2]

**Rule:** You feel complexity in three ways. It comes from two sources. Learn to name them and you can point at what is wrong.

**Two causes**

- **Dependencies:** code that cannot be understood or changed without looking at other code.
- **Obscurity:** something important is not obvious from reading the code.

**Three symptoms**

1. **Change amplification:** a small change needs edits in many places.
2. **Cognitive load:** you must know a lot to make the change safely.
3. **Unknown unknowns:** you cannot tell what you need to know. This is the worst of the three, because nothing warns you until a bug appears.

Dependencies cause change amplification and cognitive load. Obscurity causes unknown unknowns and adds to cognitive load.

**Questions to ask about any change**

- How many places did I have to edit?
- How much did I have to know before I could do it safely?
- Was there anything I could not have found out by reading the code?

<!-- id: #complexity-incremental -->

### Complexity arrives in small pieces [APoSD ch.2] [PP topic 3]

**Rule:** No single shortcut makes a system unmanageable. Hundreds of small ones do, and each was easy to excuse at the time.

- Fix small problems when you see them. If you cannot fix it now, mark it clearly so it reads as known damage and not as the standard. (PP Tip 5)
- Treat "it is only a small thing" as a reason to care, not a reason to skip.
- Keep clean code clean. People take far more care in a codebase that is visibly looked after.

<!-- id: #etc -->

### The single test: is it easier to change? [PP topic 8, Tip 14]

**Rule:** Good design is easier to change than bad design. Nearly every design principle is a special case of this one.

- Each time you save a file, ask: did that make the system easier or harder to change?
- When you truly cannot tell, make the code **replaceable**. Keep the piece small, separate and behind a clear boundary, so that whatever happens it will not block you.
- Write the situation down and note what you chose. When the code next needs changing, look back and see whether you guessed right. This is how the instinct gets trained.

> **How the two books line up.** ETC and "reduce complexity" are the same goal seen from two sides. Ousterhout describes what makes code hard to work with. Thomas and Hunt describe what you want instead. Use whichever question is easier to answer in the moment.

<!-- id: #strategic -->

### Working code is not enough [APoSD ch.3]

**Rule:** Aim for a good design that also works, and pay for it with a steady 10 to 20 percent of your time.

**What the investment looks like**

- **Before:** sketch a second design before committing to the first. Think about what is likely to change. Write the interface comment.
- **During:** when you find a design problem, fix it properly. Do not patch around it.
- **After a change:** the code should look as if it had been designed with that change in mind from the start. [APoSD ch.16]
- Invest today. There is always another deadline, and postponed cleanups become permanent.

> **Do not overdo it.** This is not big design up front. Nobody can picture a whole system well enough before building it. Make many small investments as you go.

> **The tactical tornado.** Ousterhout's name for the developer who ships faster than anyone by leaving a mess behind. They look productive. The people who maintain their code afterwards pay the real cost.

<!-- id: #modules -->

## Designing modules

A module is any unit with an interface and an implementation: a function, a class, a package, a service. This part is about where to draw the boundaries and what to put behind them. It is the heart of *A Philosophy of Software Design*.

<!-- id: #deep-modules -->

### Make modules deep [APoSD ch.4]

**Rule:** The best modules give you a lot of behaviour through a small, simple interface.

- For each module ask: how much must a caller know, compared with how much this does for them?
- Make the common case need no thought. Give sensible defaults so most callers never see the rare options.
- Do not create a class or function just because small feels tidy.

> **Red flag: Shallow Module.** The interface is barely simpler than the implementation. Lots of tiny classes and one-line methods are the usual sign. Ousterhout calls the habit of making many small classes **classitis**: each class looks simple, but the system as a whole has far more interfaces to learn.

<!-- id: #information-hiding -->

### Hide design decisions [APoSD ch.5] [PP topic 28]

**Rule:** Each design decision (a file format, a data structure, a rule) should be known in exactly one module.

**The trap: splitting by order of events**

A common mistake is to give each stage of a process its own module: one reads, one processes, one writes. Stages that share a file format then each need to know it. Split by what each piece needs to know, not by when it runs.

- When you see the same knowledge in two places, ask: how can I reorganise so only one module knows this?
- Do not return internal data structures. Offer `get_parameter(name)`, not the whole dictionary.
- Marking a field private is not hiding if getters and setters expose it anyway.
- Do the right thing by default. If the module already has the information, it should not ask the caller for it.

> **Red flags: Information Leakage, Temporal Decomposition, Overexposure.** **Leakage:** one decision shows up in several modules. **Temporal decomposition:** the structure mirrors execution order. **Overexposure:** to use a common feature, callers must learn about rare ones.

> **Do not overdo it.** Only hide what callers do not need. If callers truly need a piece of information, such as whether a network message was lost, hiding it makes the module useless to them.

<!-- id: #general-purpose -->

### Make interfaces somewhat general [APoSD ch.6]

**Rule:** Build what you need today, but shape the interface so it is not tied to today's one use.

**Three questions to find the right level**

1. What is the simplest interface that covers everything I need right now?
2. In how many situations will this method be used? If the answer is one, it is probably too specialised.
3. Is this easy to use for what I need today? If not, I have gone too general.

> **Compare with The Pragmatic Programmer.** PP warns against guessing the future ((Tip 43) Avoid Fortune-Telling). The two fit together: do not add *features* you might need, but do choose a *shape* for the interface that does not lock in today's caller.

<!-- id: #layers -->

### Each layer should add something [APoSD ch.7]

**Rule:** If two neighbouring layers look alike, one of them is probably not earning its place.

As a call travels down through a system, the way of thinking about the problem should change at each layer. A layer that only repeats the one under it adds an interface to learn and nothing else.

**Fixing a pass-through method**

Try these in order: let callers use the lower class directly, move behaviour so each class has a clear job, or merge the two classes. A matching signature is fine when real work happens. A dispatcher that picks which function to call is doing a job, and so are several classes that implement one shared interface.

**Pass-through variables**

A related problem is a value handed down through several functions that do not use it, only so the last one can. The usual fix is a context object: one object that holds system-wide settings and shared services, stored by the major objects when they are created. Keep its contents read-only where you can, because it shares most of the dangers of global data (`#global-data`).

> **Red flag: Pass-Through Method.** A method does nothing but hand its arguments to another method with a similar signature. The division of responsibility between the two classes is unclear.

> **Decorators and wrappers.** A wrapper class that adds one small feature to another class is usually shallow. Before writing one, ask whether the feature could live in the class itself, or stand alone.

<!-- id: #pull-down -->

### Pull complexity downward [APoSD ch.8]

**Rule:** When something hard has to be dealt with, the module should deal with it so its callers do not have to.

- Before adding a setting, ask: will the user really know a better value than this code can work out?
- If you must expose a setting, give it a good default.
- Before raising an error upward, ask whether the caller is any better placed to handle it.

> **Do not overdo it.** Pull complexity down only when it belongs with what the module already does, it makes callers simpler, and it makes the interface simpler. A `backspace()` method on a text class fails this test: it drags user-interface knowledge into a module that should not have it.

<!-- id: #together-apart -->

### Together or apart? [APoSD ch.9]

**Rule:** Split code when the pieces are truly independent. Keep it together when you would have to read both pieces to understand either.

| Bring together when | Keep apart when |
| --- | --- |
| The pieces share knowledge, such as the same file format. | One piece is a general mechanism and the other is one particular use of it. |
| They are always used together, in both directions. | One is used in many places without the other. |
| Combining gives callers a simpler interface. | Each can be understood without reading the other. |
| You cannot understand one without reading the other. | Combining would force callers to learn things they do not need. |
| Combining removes repeated code. |  |

Splitting is not free. Every split adds an interface, adds code to connect the pieces, and moves related things further apart. Size alone is a poor reason to split.

**How long should a function be?**

Long enough to do one thing completely. A long function with a simple signature that reads from top to bottom is fine. Split a function in two cases only: a self-contained subtask can be pulled out so that each part reads without the other, or the function does two unrelated jobs that callers want separately.

> **Red flags: Conjoined Methods, Special-General Mixture, Repetition.** **Conjoined methods:** you keep flipping between two functions to follow one idea. Merge them. **Special-general mixture:** a general mechanism contains code for one specific use. Move the specific code up to its user. **Repetition:** the same non-trivial code keeps appearing, so an abstraction is missing.

> **A real disagreement.** Some well-known advice says functions should be only a few lines long. Ousterhout disagrees: once a function fits comfortably on a screen, making it shorter helps little, while each extra function adds an interface. Depth first, then length.

<!-- id: #what-matters -->

### Decide what matters [APoSD ch.21]

**Rule:** Design is choosing the few things that matter, making them prominent, and hiding the rest.

- Look for **leverage**: one mechanism that solves many problems, or one fact that explains many behaviours.
- Shrink the list. Fewer required parameters, fewer settings, fewer places where each important thing is visible.
- Check that the most visible parts of your interface are the most important ones.

<!-- id: #glossary -->

## Glossary

| Term | Meaning |
| --- | --- |
| **Abstraction** | A simplified view of something that leaves out details you do not need. |
| **Assertion** | A check in code for something that should always be true. Failing it means there is a bug. |
| **Change amplification** | One simple change needs edits in many places. |
| **Cognitive load** | How much you must hold in your head to do a task. |
| **Cohesion** | How well the contents of a module belong together around one purpose. |
| **Coupling** | A dependency between two pieces of code, so that they tend to change together. |
| **Deep module** | A module with a simple interface and a lot of behaviour behind it. |
| **Design by contract** | Stating what a function requires, what it guarantees and what stays true. |
| **DRY** | Don't Repeat Yourself. Each piece of knowledge has one home. |
| **ETC** | Easier To Change. The test for choosing between designs. |
| **Information hiding** | Keeping a design decision inside one module so others do not depend on it. |
| **Information leakage** | The same design decision known in more than one module. |
| **Interface** | Everything a user of a module must know to use it, including what only comments can say. |
| **Invariant** | Something that is always true, such as "this list is never empty". |
| **Orthogonal** | Independent. Changing one does not affect the other. |
| **Precondition / postcondition** | What must be true before a call / what the function guarantees after it. |
| **Prototype** | A throw-away experiment built to answer one question. |
| **Refactoring** | Changing the structure of code without changing what it does. |
| **Shallow module** | A module whose interface is nearly as complicated as what it hides. |
| **Strategic / tactical programming** | Investing in the design as you go / only getting the current task working. |
| **Temporal coupling** | A dependency on order in time, such as "call A before B". |
| **Temporal decomposition** | Splitting code by the order things happen, which tends to duplicate knowledge. |
| **Tracer bullet** | A thin, real, end-to-end slice of a system, built first and kept. |
| **Unknown unknown** | Something you need to know to make a change safely, with nothing to tell you it exists. |
