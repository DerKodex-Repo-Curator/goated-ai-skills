# Errors And Defensive Code

Read this when deciding whether to raise, catch, assert, validate, or redesign around a failure, or when a resource is opened and closed.

These are guidelines for judgement. Project instructions, a project's own standards, and the user's requests take priority. `[PP ...]` and `[APoSD ...]` mark which book an idea comes from.

## Contents

- [Errors and defensive code](#errors-and-defensive-code)
  - `#error-decision` Which kind of problem is this?
  - `#define-away` Define errors out of existence
  - `#fewer-handlers` Handle errors in fewer places
  - `#crash-early` Crash early
  - `#contracts` Design by contract
  - `#assertions` Assert what "cannot happen"
  - `#resources` Finish what you start

<!-- id: #errors -->

## Errors and defensive code

The two books seem to disagree here. One says check everything and crash early. The other says too much error handling is itself a major source of bugs. They are describing two different kinds of problem, and the first idea below shows how to tell them apart.

<!-- id: #error-decision -->

### Which kind of problem is this? [PP] [APoSD]

**Rule:** Design away the errors you can, handle expected failures in as few places as possible, and crash loudly on anything that should be impossible.

**The decision flow**

Ask these in order for each thing that can go wrong.

1. **Could the operation be redefined so this case is normal behaviour?** If yes, define it away. No error exists. (`#define-away`)
2. **Is it an expected failure from outside,** such as bad user input, a missing file, or a network timeout? If yes, handle it once: low down so callers never see it, or high up in one handler for many failures. (`#fewer-handlers`)
3. **Is it a broken assumption,** such as "this can never happen" or a caller breaking the contract? If yes, crash early: assert, stop, report. (`#crash-early`, `#assertions`)
4. **Does the caller truly need to know, and can it do something useful about it?** If yes, raise it and document it as part of the interface. (`#contracts`)

If the answer to 4 is no, go back to 1. Raising an error nobody can act on only moves the problem.

<!-- id: #define-away -->

### Define errors out of existence [APoSD ch.10]

**Rule:** The best way to handle an error is to design the operation so the error cannot happen.

> **Do not overdo it.** Only define away errors nobody needs to hear about. If a caller needs to know that a payment failed or a message was lost, swallowing it is a serious bug. Hide what is unimportant, expose what is important.

<!-- id: #fewer-handlers -->

### Handle errors in fewer places [APoSD ch.10] [PP topic 24]

**Rule:** Raising an error is easy. Handling it is the hard part. So reduce the number of places that handle.

| Technique | Where the handler lives | Example |
| --- | --- | --- |
| **Mask** | Low down, inside the module. Callers never find out. | A network layer resends a lost packet by itself. |
| **Aggregate** | One handler high up that catches many kinds of failure. | A web server catches any error from a request in one place and returns an error page. |
| **Just crash** | Nowhere. Print what you know and stop. | Out of memory, a corrupted internal structure. |

<!-- id: #crash-early -->

### Crash early [PP topic 24, Tip 38]

**Rule:** When something impossible happens, stop. A dead program does far less damage than a confused one that keeps running.

- Do not catch errors you cannot do anything useful about.
- Read error messages. They are information, not noise. (Tip 32)
- Give every `match` or `if/elif` chain a final branch that raises, so an unexpected value is noticed.
- If there is tidying to do (close files, release locks), do it, and then stop.

<!-- id: #contracts -->

### Design by contract [PP topic 23, Tip 37]

**Rule:** For every function, decide what it requires, what it promises, and what always stays true. Write that down.

- Be strict about what you accept and promise as little as you can. A function that accepts anything and promises everything needs a huge amount of code.
- Checking that a user typed a sensible value is **not** a precondition. Bad input from outside is normal and needs ordinary validation, at the edge of the system.
- Find the few rules that must never be broken across the whole system, such as "never charge a card twice". Write them where everyone will see them.

> **Link to APoSD.** Ousterhout asks for the same information in every interface comment: behaviour, each argument, the result, side effects, exceptions, and anything the caller must ensure first. He adds: keep preconditions few. Each one is something every caller has to remember.

<!-- id: #assertions -->

### Assert what "cannot happen" [PP topic 25, Tip 39]

**Rule:** Whenever you think "that could never happen", add a check that proves it.

- **Assertions are for bugs, not for expected errors.** Never use one to validate user input or check that a file exists.
- **No side effects.** The check must not change anything. Code that behaves differently when checks are switched off is a trap.
- **Leave them on.** Testing does not find every bug, and production is a rougher place than your test machine. Switch off only a check that is measurably too slow.

> **Python note.** Python removes `assert` statements when run with the `-O` flag. For a check that must never be skipped, write `if not condition: raise ...` yourself.

<!-- id: #resources -->

### Finish what you start [PP topic 26, Tips 40, 41]

**Rule:** The code that opens a resource should be the code that closes it, and the two should sit close together.

- Keep the life of a resource inside the smallest block you can. (Tip 41)
- Release several resources in the reverse of the order you took them.
- Always take the same resources in the same order everywhere. This avoids two pieces of code each waiting for what the other holds.
- Think about slow build-up too: log files, temporary files, old rows. Is anything clearing them?

> **Link to APoSD.** Ousterhout makes the same point as a complexity issue: a function that allocates something and expects the caller to free it adds to what every caller must remember.
