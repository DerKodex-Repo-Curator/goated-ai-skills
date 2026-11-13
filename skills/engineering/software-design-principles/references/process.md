# Designing And Planning

Read this when comparing designs, choosing a first slice, deciding between a prototype and real code, clarifying a requirement, or when a problem feels stuck.

When the `prototype`, `grill-with-docs`, `write-a-spec`, or `writing-plans` skills are installed, they own the procedure for prototypes, clarification, specs, and plans. This file gives the reasoning.

These are guidelines for judgement. Project instructions, a project's own standards, and the user's requests take priority. `[PP ...]` and `[APoSD ...]` mark which book an idea comes from.

## Contents

- [Designing and planning](#designing-and-planning)
  - `#small-steps` Small steps, fast feedback
  - `#design-twice` Design it twice
  - `#tracer-bullets` Tracer bullets: a thin slice that really works
  - `#prototypes` Prototypes: throw-away experiments
  - `#requirements` Requirements are discovered, not collected
  - `#puzzles` When a problem seems impossible
  - `#domain-language` Program close to the problem
  - `#good-enough` Good enough, on purpose
  - `#starter-kit` The three legs: version control, testing, automation
  - `#agility` Do what works

<!-- id: #process -->

## Designing and planning

How to get from a vague request to a design you trust. The shared theme is feedback: you cannot think your way to the right answer in advance, so set things up to learn quickly and cheaply.

<!-- id: #small-steps -->

### Small steps, fast feedback [PP topics 27, 48, Tips 42, 43]

**Rule:** Never move faster than you can check. Your rate of feedback is your speed limit.

**The loop**

1. **Where am I?** Look at the real current state.
2. **Take the smallest useful step** toward where you want to be.
3. **Check, and fix** anything the step broke.

Repeat at every scale: a line of code, a feature, the way the work is organised.

**Signs you are guessing the future**

- Estimating a date months away as a single number.
- Designing for extensions nobody has asked for.
- Predicting what users or technology will look like later.

When you cannot see ahead, do not guess. Make the code easy to replace.

> **Fits with step 3.** Step 3 only works if fixing what you broke is cheap. That is why good design and working in small steps depend on each other.

<!-- id: #design-twice -->

### Design it twice [APoSD ch.11]

**Rule:** For every important design decision, sketch at least two different approaches and compare them before you build.

1. State the decision, for example "the interface of the storage module".
2. Sketch two or three options that differ in kind, not in detail. Only the main functions are needed.
3. List pros and cons. The first question: which is easiest for the calling code to use?
4. Pick one, merge them, or use what you learned to sketch another.

| Option for a text class | Work pushed onto callers | Verdict |
| --- | --- | --- |
| Work with whole lines | Callers must split and join lines for every partial edit | Awkward |
| Work with one character at a time | Callers need a loop for everything, and it is slow | Too low-level |
| Work with any range of text | None. It matches what callers actually do | Chosen |

<!-- id: #tracer-bullets -->

### Tracer bullets: a thin slice that really works [PP topic 12, Tip 20]

**Rule:** When much is unknown, first build one small feature that passes through every layer of the real system.

- Start with the simplest possible version: the project builds, runs and deploys with one trivial feature.
- Choose first the features that carry the most doubt and risk.
- Write tracer code to normal quality. It is the skeleton of the real system and you will keep it.
- Expect to miss. A small amount of code is cheap to change, which is the point.

<!-- id: #prototypes -->

### Prototypes: throw-away experiments [PP topic 13, Tip 21]

**Rule:** A prototype answers one risky question cheaply. Its value is what you learn. The code is thrown away.

|  | Tracer code | Prototype |
| --- | --- | --- |
| **Purpose** | Show how the whole system fits together | Explore one question or risk |
| **Kept?** | Yes. It becomes the skeleton | No. Rewrite properly with what you learned |
| **Quality** | Normal standard, lean but complete | May skip correctness, error handling, style |
| **Form** | Code through every layer | Anything: a script, a sketch, sticky notes |

> **The danger.** A convincing prototype tempts people to ship it. Say clearly, before you start, that it is disposable and cannot be finished. If that message will not be heard, build a tracer instead.

<!-- id: #requirements -->

### Requirements are discovered, not collected [PP topics 45, 52, Tips 75 to 80, 96]

**Rule:** Nobody knows exactly what they want at the start. Your job is to help them find out.

> **Example.** The request: "Free shipping on orders of $50 or more." Does $50 include tax? Shipping itself? If it includes shipping, a $25 book with $30 overnight delivery ships free. Point that out and let the client decide. They now understand their own requirement better.

- **Show, do not describe.** People react far better to something they can click than to a document. Use mock-ups and short iterations.
- **Sit with the users.** Watch or do their job for a day. (Tip 78)
- **Separate the need from today's policy.** "Only managers can view records" is a policy. The need is "only authorised people can view records". Build the general mechanism and store the policy as data. (Tip 79)
- **Keep requirements about need,** not about design or screens. When handed a solution, ask what problem it solves.
- **Ask how success will be judged.** "How will you know this worked, a month after it ships?" The answer is the real goal. (Tip 96)
- **Watch scope.** When a new item comes in, ask what moves out to make room.

> **Link to APoSD.** "Policy is metadata" is the same move as Ousterhout's somewhat general-purpose (`#general-purpose`) interface: build the general mechanism and keep the specific case outside it.

<!-- id: #puzzles -->

### When a problem seems impossible [PP topics 46, 37, Tips 81, 61]

**Rule:** Find the real constraints. Most "impossible" problems rest on a limit you assumed and nobody set.

- List every possible approach, including the ones that seem silly. For each one you rule out, say why. Are you sure? Can you prove it?
- Ask: why am I solving this? Is there a simpler related problem? Must it be done this way? Must it be done at all?
- Deal with the tightest constraint first and fit the rest around it.
- Explain the problem aloud to someone, or to an object on your desk. Saying each step forces out the assumption you were skipping.
- Step away. Answers often arrive while you are doing something else.

**Listen to unease (Tip 61)**

If a task feels much harder than it should, or you keep putting it off, treat that as information. Stop, sketch it, talk it through, or try a throw-away prototype until you can name what is wrong.

<!-- id: #domain-language -->

### Program close to the problem [PP topic 14, Tip 22]

**Rule:** Write code in the words of the problem it solves.

If users talk about orders, refunds and stock, the code should have things called orders, refunds and stock. Code that reads like the domain is easier to check against what people asked for.

> **Do not overdo it.** A small language of its own for one job is rarely worth it. Use an existing format first, then plain functions with well-chosen names. Write a language and parser only when the people using the application will write in it.

<!-- id: #good-enough -->

### Good enough, on purpose [PP topic 5, Tip 8]

**Rule:** How good the software needs to be is a requirement to agree with its users, not something to decide alone.

- Ask how good it needs to be as well as what it needs to do.
- Ship early and learn from real use.
- Know when to stop. A painter who keeps adding layers loses the painting.

> **Does this conflict with strategic programming?.** No. Good-enough is about *scope and polish*: which features, how refined. Strategic programming is about *structure*: whether the code stays easy to change. You can ship a small, rough-edged product on a clean design. That combination is usually the right one.

<!-- id: #starter-kit -->

### The three legs: version control, testing, automation [PP topics 19, 51, Tips 28, 89 to 95]

**Rule:** Every project needs everything in version control, tests that run automatically, and no manual steps.

**Version control**

- Everything goes in: code, configuration, scripts, documents. Even solo, even for a one-week job. (Tip 28)
- The one exception is secrets.
- Builds, tests and releases are triggered by commits and tags, not by a person at a particular machine. (Tip 89)
- A shared or synced folder is not version control.

**Testing**

- Test early, often and automatically. (Tip 90)
- Not done until the tests pass. (Tip 91)
- Unit tests check a part alone. Integration tests check that parts keep their promises to each other, which is where many bugs live.
- Test in conditions close to the real ones.

**Automation**

- No manual procedures. A person following a list will eventually skip a step. (Tip 95)
- Scripts do the same thing every time, and are themselves under version control.
- One "small" manual step left in a build is a large broken window.

<!-- id: #agility -->

### Do what works [PP topics 48, 50, Tips 83, 87, 88]

**Rule:** Being agile means responding to feedback. It is not a set of meetings and job titles.

- Ask of every practice: why are we doing this, and does it work for us?
- Try new ideas on a small scale. Keep what helps and drop the rest.
- The real goal is to be *able* to deliver working software whenever users need it. Shorten the gap between releases step by step. (Tip 88)
- A process that never changes is not agile.

> **Ousterhout's caution.** Working in small increments can slide into tactical programming: one more feature, no time for design. His fix: let the unit of work be an **abstraction**, not a feature. Wait until a feature needs a new abstraction, then design that abstraction properly.
