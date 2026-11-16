# While You Are Coding

Read this when code works for reasons you cannot state, when refactoring, when writing tests or judging them as design feedback, when fixing a bug, or when the question is about speed.

When the `tdd`, `diagnose`, `code-refinement`, or `code-security-review` skills are installed, they own the procedure for test-first work, debugging, cleanup, and security review. This file gives the reasoning.

These are guidelines for judgement. Project instructions, a project's own standards, and the user's requests take priority. `[PP ...]` and `[APoSD ...]` mark which book an idea comes from.

## Contents

- [While you are coding](#while-you-are-coding)
  - `#coincidence` Do not program by coincidence
  - `#refactoring` Refactor early and often
  - `#testing` Tests are design feedback
  - `#algorithm-speed` Know how your code grows
  - `#performance` Performance without the mess
  - `#security` Security basics
  - `#debugging` Debugging

<!-- id: #coding -->

## While you are coding

Coding is not typing in a finished design. Decisions are made every minute. This part covers the habits that keep those decisions deliberate.

<!-- id: #coincidence -->

### Do not program by coincidence [PP topic 38, Tip 62]

**Rule:** If you do not know why your code works, you will not know why it stops working.

| Kind of coincidence | Example | Ask yourself |
| --- | --- | --- |
| Accident of implementation | Relying on the order a library happens to return items in | Is this behaviour documented, or does it just happen today? |
| Accident of context | Assuming a writable current folder, a fast network, an English-speaking user | What am I assuming about where this runs? |
| Close enough | Adding `+ 1` until the number looks right | Do I understand why it was off? |
| Imagined pattern | "It failed twice after lunch, so it must be load" | Have I proved the cause, or guessed it? |
| Copied without understanding | Pasting an answer whose context differs from yours | Could I explain each line? |

- Be able to explain the code, in detail, to someone less experienced. If you cannot, you are relying on luck.
- Rely only on documented behaviour. If unsure, assume the worst.
- Write assumptions down, and check them with assertions and tests. (Tip 34)
- Work from a plan, even a few lines on paper.
- Do not keep code just because it is there. Existing code can be wrong too.

> **For agents.** This is the rule most easily broken by generated code. Do not add calls, retries or parameters "until it works". State what each line is for, verify behaviour against documentation or a test, and say so plainly when something is unverified.

<!-- id: #refactoring -->

### Refactor early and often [PP topic 40, Tip 65] [APoSD ch.16]

**Rule:** Improve the structure of code in small, tested steps, as part of everyday work.

**When to do it**

- You find duplicated knowledge.
- Two things that should be independent turn out to be tangled.
- You understand the problem better than when you wrote the code.
- You just got a test passing. Tidy now, while it is fresh.

**How to do it safely**

1. Do not refactor and add features in the same step.
2. Have good tests first. Run them constantly.
3. Take short steps: rename one thing, move one function, then test.

> **Ousterhout's standard for any change.** Do not ask "what is the smallest change that works?" Ask "what would this code look like if it had been designed with this change in mind?" and move toward that. If you are not making the design better, you are probably making it worse.

<!-- id: #testing -->

### Tests are design feedback [PP topics 41, 51, Tips 66 to 70, 90 to 94] [APoSD ch.19]

**Rule:** The biggest benefit of a test comes from writing it. A test is the first user of your code, and it shows you what the code is like to use.

**Rules both books agree on**

- **Tests make change safe.** Without them people are afraid to improve the design, so it decays.
- **Write a failing test before fixing a bug.** If you fix first, you cannot be sure the test would have caught it. (Tip 31)
- **Find each bug once.** Every bug a person finds gets a test, so no person finds it again. (Tip 94)
- **Test later means test never.** Test as you go.
- **All tests pass, all the time.** A test that is allowed to fail teaches everyone to ignore failures.
- **Treat test code like real code:** clear, independent, maintained.

**Coverage is not the goal**

Every line can run in a test while the bug is still there. What matters is the range of states the program can be in, not the lines executed. (Tip 93) To check that your tests are worth anything, break the code on purpose and confirm a test fails. (Tip 92)

**Property-based testing (Tip 71)**

If you write both the code and its tests, the same wrong assumption can be in both. A property-based test states a rule that must always hold and lets a tool generate many inputs to try to break it. When one fails, copy the failing input into an ordinary test so it is checked every time from then on.

> **On test-driven development.** The books differ on writing tests first as a strict method. See Where the books differ (`#differences`). Both warn about the same failure: taking tiny steps toward passing tests while never deciding where the design is going.

<!-- id: #algorithm-speed -->

### Know how your code grows [PP topic 39, Tips 63, 64]

**Rule:** For every loop, ask how big the input can get and how the cost grows with it.

| Order | Typical code | If 100 items take 1 second, 1,000 items take about |
| --- | --- | --- |
| O(1) | Look up a dictionary key | 1 second |
| O(log n) | Binary search: halve the candidates each time | 1.5 seconds |
| O(n) | One loop over the items | 10 seconds |
| O(n log n) | A good sort; split, solve halves, combine | 15 seconds |
| O(n²) | A loop inside a loop over the same items | 100 seconds |
| O(2ⁿ) | Trying every combination | longer than the age of the universe |

- A nested loop over the same data is the usual culprit. Look for a way to use a dictionary or sort first.
- Check your estimate by timing real code on real data at a few sizes. (Tip 64)
- The fastest-growing option is not always worst. For small inputs a simple loop often beats a clever algorithm, and is easier to get right.

<!-- id: #performance -->

### Performance without the mess [APoSD ch.20] [PP topic 39]

**Rule:** Simple code is usually fast code. Measure before you optimise, and undo any optimisation that did not help.

**Things that are always expensive**

- Network calls, especially over the internet.
- Reading and writing storage.
- Allocating lots of small pieces of memory.
- Jumping around memory instead of reading it in order.

**The routine**

1. **Measure first.** Intuition about what is slow is unreliable, even for experts. Find the few places that really take the time.
2. **Look for a basic fix:** a cache, a better algorithm, a better data structure, fewer network trips.
3. **If there is none, redesign the hot path.** Ask what the least possible work is for the common case. Check for all the special cases once at the start, and send them down a separate, simple path.
4. **Measure again.** If the change did not make a real difference, take it out, unless it also made the code simpler.

<!-- id: #security -->

### Security basics [PP topic 43, Tips 72, 73]

**Rule:** Most break-ins come from carelessness, not clever attacks. After the code works, ask how it could be misused.

| Principle | In practice |
| --- | --- |
| **Keep the attack surface small** | Less code, fewer entry points, fewer services running. Remove unused accounts and features. |
| **Never trust outside data** | Check and clean everything that comes in before it reaches a database, a command or a page. |
| **Least privilege** | Give each part the lowest permission it needs, for the shortest time. |
| **Safe by default** | The out-of-the-box setting is the secure one. |
| **Protect sensitive data** | Encrypt it. Never put passwords, keys or tokens in version control. |
| **Do not leak through output** | Error messages and logs should not reveal internals or personal data. |
| **Apply updates quickly** | Known holes are the ones attackers use first. |
| **Never write your own cryptography** | Use well-known, maintained libraries. Prefer an established sign-in service to building your own. |

<!-- id: #debugging -->

### Debugging [PP topic 20, Tips 29 to 34]

**Rule:** Debugging is problem solving. Reproduce the bug, read what the system tells you, narrow it down by halves, and question what you "know".

- **Fix the problem, not the blame.** It does not matter whose fault it is. (Tip 29)
- **"That's impossible" is always wrong.** It happened. (Tip 30)
- **Suspect your own code first.** The bug is almost never in the language, the operating system or a major library. (Tip 33)
- **"I only changed one thing."** Then that thing is the cause, however unlikely it seems.
- **Do not assume, prove.** A surprising bug means something you trusted is false. Do not skip code because you "know" it works. (Tip 34)
- **Explain it aloud** to a person or an object on your desk, step by step.
- **Keep notes as you go,** so you can return to where you were after a dead end.
- **For problems over time,** such as events and concurrency, add trace output in a consistent format a script can read.

**After a surprising bug**

- [ ] Add or fix the test that should have caught it.
- [ ] If bad data travelled a long way before failing, add an earlier check.
- [ ] Look for the same mistake elsewhere and fix it now.
- [ ] If it came from a wrong assumption, tell the team. Others may share it.
