# Where The Books Differ

Read this when two rules in this skill seem to pull apart: tests first, comment quantity, error handling, configuration, function size, planning ahead, or small increments.

These are guidelines for judgement. Project instructions, a project's own standards, and the user's requests take priority. `[PP ...]` and `[APoSD ...]` mark which book an idea comes from.

## Contents

- [Where the books differ](#where-the-books-differ)
- [When Other Instructions Decide](#when-other-instructions-decide)

<!-- id: #differences -->

## Where the books differ

The two books agree on far more than they dispute. These are the places where they pull apart, with a suggested way to hold both.

| Topic | The Pragmatic Programmer | A Philosophy of Software Design | A workable position |
| --- | --- | --- | --- |
| **Writing tests first** | Useful, especially for beginners, because thinking about the test improves the design. Warns against following it blindly with no idea of the destination. | Against it as a method. It focuses attention on getting features to pass and leaves no natural moment to design. One exception: write a failing test before fixing a bug. | Always have tests, and always write the failing test first for a bug. For new work, sketch the design (or write the interface comments) before the first test, so the tests check a design and do not replace one. |
| **How many comments** | Comment the "why". Do not comment every function mechanically, since that creates a second thing to keep up to date. | Comment every class, every function and every field. It is cheaper than deciding case by case, and the interface comment is the abstraction. | Every public class and function gets an interface comment that says something the signature does not. Inside functions, comment only intent and surprises. Both books reject comments that repeat the code. When a user or project asks for more, or the readers are programmers at a beginner or intermediate level, use the opt-in Reader-first comments profile (`#reader-first-comments`). |
| **Error handling** | Be paranoid. Check assumptions everywhere and crash early. | Too much error handling causes bugs. Design errors away and handle the rest in few places. | They address different cases. Use the decision flow (`#error-decision`): design away what you can, crash on broken assumptions, and handle outside failures once. |
| **Configuration** | Put changeable values outside the code so behaviour can change without a rebuild. | Every setting pushes a decision onto the user. Work the value out automatically where you can. | Settings for facts about the environment. No settings for decisions the code could make. Defaults for everything. |
| **Size of functions and classes** | Favours small, single-purpose, independent parts. | Warns that many small parts mean many interfaces. Prefers fewer, deeper modules. | Judge by independence and depth, not by line count. Split when the pieces can be understood separately. Merge when you must read them together. |
| **Planning for the future** | Do not guess the future. Make code easy to replace. | Make interfaces somewhat general, and think about likely changes. | Do not build features you might need. Do choose interface shapes that are not tied to one caller. Generality in the interface, not in the feature list. |
| **Working in small increments** | Central. Small steps and constant feedback at every level. | Agrees design must evolve, but warns that feature-by-feature work becomes tactical. | Small steps, with each step leaving the design a little better. The unit of work is an abstraction, not only a feature. |

## When Other Instructions Decide

The "workable position" column is this skill's default. It gives way whenever something with higher priority has already decided:

- **Tests first.** When the `tdd` skill or a project rule governs the work, it decides the order: production behaviour waits for a failing test. This skill only adds the design moment before that first test.
- **How many comments.** A project's or user's comment standard wins, whether it asks for more comments or fewer.
- **Function size, configuration, error handling.** Follow the project's documented conventions and the code around the change (`#consistency`).
- **Small increments.** The agreed scope of the task decides how much to improve. Note design problems outside it; do not fix them unasked.
