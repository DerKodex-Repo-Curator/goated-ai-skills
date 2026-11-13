# Keeping Code Easy To Change

Read this when knowledge is duplicated, one change touches many files, code reaches through other objects, or the question is about global data, inheritance, vendor wrappers, settings, or data pipelines.

These are guidelines for judgement. Project instructions, a project's own standards, and the user's requests take priority. `[PP ...]` and `[APoSD ...]` mark which book an idea comes from.

## Contents

- [Keeping code easy to change](#keeping-code-easy-to-change)
  - `#dry` DRY: say each thing once
  - `#orthogonality` Orthogonality: keep unrelated things unrelated
  - `#tell-dont-ask` Do not reach through objects
  - `#global-data` Avoid global data
  - `#inheritance` Be wary of inheritance
  - `#reversibility` Keep decisions reversible
  - `#configuration` Configuration: outside the code, but not a dumping ground
  - `#pipelines` Think in transformations

<!-- id: #decoupling -->

## Keeping code easy to change

The modules reference is about what goes inside a module. This part is about the connections between modules. It is the heart of *The Pragmatic Programmer*: fewer connections, and each fact stored once.

<!-- id: #dry -->

### DRY: say each thing once [PP topic 9, Tip 15]

**Rule:** Every piece of knowledge should have one clear, authoritative home in the system.

DRY is about knowledge: a rule, a format, a decision. It is not "never have two pieces of code that look alike". The test: when one fact changes, do you have to edit more than one place? If yes, that fact is duplicated, even when the two places look nothing alike, such as code and a comment, or a database schema and a class.

**Same code is not always the same knowledge**

Two pieces of code that only happen to agree today are different knowledge. Leave them apart. Merging them creates a dependency where none existed, and the first time one rule changes the merged code has to be split again.

**Where duplication hides**

| Kind | Example | Fix |
| --- | --- | --- |
| In code | The same formatting rule written in five print statements | Give the rule one named function |
| In comments | A comment that restates the rules the code implements | Clear names, and comments that say why |
| In data | A stored total that can be worked out from the rows | Compute it. If you must cache it, hide the cache inside the module |
| Across a boundary | Your code and an external API both hard-code the same field list | Generate one from the other, or validate against one shared definition |
| Between people | Two developers each write their own date helper | Talk often, and make shared code easy to find (Tip 16) |

> **The same idea in APoSD.** Ousterhout's **information leakage** is DRY seen from the design side: one decision known in several modules. His **Repetition** red flag is the code-level version. Both books also agree on documentation: write each explanation once and point to it from elsewhere.

<!-- id: #orthogonality -->

### Orthogonality: keep unrelated things unrelated [PP topic 10, Tip 17]

**Rule:** Two parts are orthogonal when you can change one without touching the other.

**What you gain**

- Changes stay local, so they are quicker to make and to test.
- A fault in one part is contained and that part can be replaced.
- You are less locked in to one vendor or library, because it only touches a small area.

- Write "shy" code: it shows nothing it does not need to, and relies on nothing it does not need.
- Use your tests as a meter. If a unit test must set up half the system first, the unit is not independent.
- Count how many files each bug fix touched. Scattered fixes mean coupled code.
- Do not use real-world identifiers you do not control (phone numbers, email addresses) as keys. They change.

> **DRY and orthogonality work as a pair.** DRY removes duplicated knowledge *within* the system. Orthogonality removes dependencies *between* its parts. In Ousterhout's terms, both reduce change amplification.

<!-- id: #tell-dont-ask -->

### Do not reach through objects [PP topic 28, Tips 44 to 46]

**Rule:** Ask an object to do the job. Do not pull out its insides and do the job yourself.

- **Tell, don't ask.** Do not make decisions based on another object's internal state and then update it. (Tip 45)
- **One dot as a rule of thumb.** Be suspicious of `a.b.c.d` in your own application code. Splitting the chain across temporary variables does not fix it. (Tip 46)
- **Exception:** chains through things that will not change are fine, such as the language's own library (`names.sort()[0].upper()`), and pipelines of data transformations (`#pipelines`).

> **This is information hiding again.** A chain such as `customer.orders.totals.add(...)` leaks the structure of customer, orders and totals into every caller. See Hide design decisions (`#information-hiding`).

<!-- id: #global-data -->

### Avoid global data [PP topic 28, Tips 47, 48]

**Rule:** Global data is an invisible extra parameter to every function in the program.

- Pass what a function needs as parameters.
- If something truly must be shared everywhere, wrap it in an API you control so its form can change later. (Tip 48)
- See Shared state (`#shared-state`) for why this becomes dangerous with concurrency.

<!-- id: #inheritance -->

### Be wary of inheritance [PP topic 31, Tips 51 to 54] [APoSD ch.19]

**Rule:** Inheriting code from a parent class ties you to every detail of that parent. There are three cheaper ways to get what you wanted.

| What you wanted | Use instead | In Python |
| --- | --- | --- |
| "These different things can be treated alike" | **An interface.** A list of required methods, with no code inherited. (Tip 52) | `typing.Protocol` or an abstract base class |
| "I want to reuse that behaviour" | **Delegation.** Hold a helper object and call it. "Has a" beats "is a". (Tip 53) | Keep the helper as a field and forward to it |
| "Several classes need the same few methods" | **A mixin.** A small named set of functions added to a class. (Tip 54) | A small mixin class, or plain shared functions |

<!-- id: #reversibility -->

### Keep decisions reversible [PP topic 11, Tips 18, 19]

**Rule:** No decision is final. Build so that the big ones are cheap to undo.

- Put third-party services behind your own thin layer. Calls to a vendor's API scattered through the code are what make a switch impossible.
- Split code into components early, even if they all run in one process.
- Do not adopt an architecture because it is fashionable. Ask what problem it solves for you. (Tip 19)

> **Do not overdo it.** A wrapper around every library is its own kind of clutter, and Ousterhout would call many of them shallow. Wrap the things that are expensive to replace and likely to change: the database, payment, authentication, anything you pay a vendor for.

<!-- id: #configuration -->

### Configuration: outside the code, but not a dumping ground [PP topic 32, Tip 55] [APoSD ch.8]

**Rule:** Values that differ between environments belong outside the code. Decisions you could have made yourself do not belong in settings at all.

| Put in configuration | Do not put in configuration |
| --- | --- |
| Addresses, ports, credentials, log levels | Values the code could measure or work out for itself |
| Values set by the outside world, such as tax rates | A choice you were unsure about and did not want to make |
| Anything that differs between test and production | Options nobody will ever change |

- Read settings through a small API. Do not let the whole program read a global settings dictionary.
- Give every setting a sensible default.
- Keep secrets out of version control.
- For each new setting ask Ousterhout's question: will the person setting this really know a better value than the code can find?

<!-- id: #pipelines -->

### Think in transformations [PP topic 30, Tips 49, 50]

**Rule:** Every program turns input into output. Design it as a chain of small steps that each change the data a little.

Start from the requirement, name the input and the output, then find the steps between. Each step is a function that takes data in one form and returns it in the next. Each step can be tested alone and reused wherever its input fits, and there is no hidden state to set up.

**Errors in a pipeline**

Do not pass along raw values that might be missing. Have each step report whether it worked, and stop at the first failure. The simplest form is to raise from the failing step and catch once around the whole pipeline, which is the single high handler described in `#fewer-handlers`.
