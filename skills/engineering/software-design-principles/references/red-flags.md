# Red Flags And Fixes

Read this when scanning a finished or in-progress change, reviewing code for design quality, or naming concrete refinement debt.

These are guidelines for judgement. Project instructions, a project's own standards, and the user's requests take priority. `[PP ...]` and `[APoSD ...]` mark which book an idea comes from.

## Contents

- [Red flags and fixes](#red-flags-and-fixes)

<!-- id: #red-flags -->

## Red flags and fixes

Warning signs you can spot in real code, with the usual fix. A red flag is a prompt to look, not proof of a fault: name it, then judge whether the usual fix makes this code simpler to understand and change. The "More" column gives the section id that explains each one; the index in `SKILL.md` says which file holds it. The first fourteen are Ousterhout's named red flags. The rest are warning signs from *The Pragmatic Programmer*.

| Red flag | What you see | Usual fix | More |
| --- | --- | --- | --- |
| **Shallow Module** [APoSD] | An interface almost as complicated as the code behind it. Many tiny classes or one-line methods. | Merge thin pieces into one that does real work behind a small interface. | `#deep-modules` |
| **Information Leakage** [APoSD] | The same decision, such as a file format, is known in more than one module. | Give that knowledge one owner. Merge the modules or pull it into a new one. | `#information-hiding` |
| **Temporal Decomposition** [APoSD] | Code is split by the order things happen: read, then process, then write. | Split by what each piece needs to know. | `#information-hiding` |
| **Overexposure** [APoSD] | To use a common feature, callers must learn about rare ones. | Defaults for the common case. Move rare options out of the main path. | `#information-hiding` |
| **Pass-Through Method** [APoSD] | A method that only hands its arguments to another with a similar signature. | Call the lower one directly, move the behaviour, or merge the classes. | `#layers` |
| **Repetition** [APoSD] | The same non-trivial code appears again and again. | Find the missing abstraction and give it one home. | `#dry` |
| **Special-General Mixture** [APoSD] | A general mechanism contains code for one particular use of it. | Move the special code up into its user. | `#general-purpose` |
| **Conjoined Methods** [APoSD] | You cannot understand one function without reading another. | Merge them, or redraw the boundary so each stands alone. | `#together-apart` |
| **Comment Repeats Code** [APoSD] | A comment says only what the line beside it already shows. | Delete it, or rewrite it to give meaning, units or reasons. | `#comments` |
| **Implementation Documentation Contaminates Interface** [APoSD] | An interface comment explains internals the caller does not need. | Describe only what callers need. If you cannot, the function is shallow. | `#comments` |
| **Vague Name** [APoSD] | A name like `data`, `status`, `result` or `count` that could mean many things. | Name what it holds and its role. Make booleans read as true-or-false statements. | `#naming` |
| **Hard to Pick Name** [APoSD] | No simple name fits. | The thing may be doing two jobs. Look at the design. | `#naming` |
| **Hard to Describe** [APoSD] | A function or variable needs a long comment to describe it fully. | Simplify the interface or split the variable. | `#comments-first` |
| **Nonobvious Code** [APoSD] | A quick read does not tell you what the code does. | Design the confusion away, follow a convention, or state the missing fact. | `#obvious` |
| **Broken window** [PP] | A known flaw left in place. "The rest is a mess anyway." | Fix it now, or mark it clearly as known damage. | `#complexity-incremental` |
| **One change, many edits** [PP] | A single fact changes and several files must be updated "to keep them in step". | Store the fact once and derive the rest. | `#dry` |
| **Stored value that can be derived** [PP] | A total, count or length kept alongside the data it comes from. | Compute it. Hide any cache inside the module. | `#dry` |
| **Merged look-alikes** [PP] | Two rules were combined only because their code matched. | Separate them. They are different knowledge. | `#dry` |
| **Ripple effect** [PP] | A change in one place breaks unrelated places. A bug fix touches many files. | Reduce what each part knows about the others. | `#orthogonality` |
| **Heavy test setup** [PP] | A unit test must build half the system before it can run. | The unit is not independent. Pass its dependencies in. | `#orthogonality` |
| **Train wreck** [PP] | `a.b.c.d.do()` through your own objects. | Ask the first object to do the job. | `#tell-dont-ask` |
| **Global data** [PP] | Functions read or change shared values they were not given. | Pass values in. Wrap what must be shared in an API. | `#global-data` |
| **Deep inheritance** [PP] | Tall class trees. A subclass exposing many methods it never meant to offer. | Interface, delegation or mixin. | `#inheritance` |
| **Vendor calls everywhere** [PP] | A third-party API is called directly throughout the code. | Put it behind one thin layer of your own. | `#reversibility` |
| **Setting to avoid deciding** [PP] [APoSD] | A configuration option nobody knows how to set. | Decide, or work the value out in code. | `#configuration` |
| **Catch, log, re-raise** [PP] | Error handling that only logs and passes the error on, at every level. | Let it rise to one handler that can act. | `#fewer-handlers` |
| **Swallowed error** [PP] | An empty `except`, an ignored return code. | Handle it properly or let it stop the program. | `#crash-early` |
| **"Can never happen"** [PP] | A comment or belief with no check behind it. | Add an assertion or a final branch that raises. | `#assertions` |
| **Open here, close there** [PP] | A file, lock or connection opened in one function and closed in another. | One owner. Use a `with` block. | `#resources` |
| **Misleading name** [PP] | A function that no longer does what its name says. | Rename it now. | `#naming` |
| **"It seems to work"** [PP] | Code arrived at by trial and error that you cannot explain. | Understand it or replace it. Test the assumption. | `#coincidence` |
| **Fix with no test** [PP] | A bug fixed without first reproducing it. | Write the failing test, then fix. | `#testing` |
| **Blaming the platform** [PP] | "It must be a bug in the library." | Rule out your own code first. | `#debugging` |
| **Optimising by feel** [APoSD] [PP] | Speed-ups added without measuring. | Measure, change, measure again. Undo what did not help. | `#performance` |
| **Check, then act** [PP] | Shared data is read, then changed in a separate step. | One step, owned by the resource. | `#shared-state` |
| **Random failures** [PP] | A bug that comes and goes and will not reproduce. | Look for shared state between concurrent tasks. | `#shared-state` |
| **Flags tracking progress** [PP] | Several booleans that together say "where we are". | A state machine written as a table. | `#events` |
| **Nothing runs end to end** [PP] | Weeks of work and no path through the whole system. | Build a thin working slice first. | `#tracer-bullets` |
| **Prototype in production** [PP] | Throw-away code quietly became the real thing. | Rewrite it properly using what it taught you. | `#prototypes` |
| **Manual step** [PP] | A build or release needs a person to follow a list. | Script it and put the script in version control. | `#starter-kit` |
| **Ritual without reason** [PP] | A practice followed because a famous company does it. | Ask what it achieves here. Keep what works. | `#agility` |

After the scan, answer one question about the change itself, not about the code in general:

Name one input that would break this change, and say what happens.
