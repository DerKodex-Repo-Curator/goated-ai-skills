# Events And Concurrency

Read this when more than one task can reach the same data, when steps are forced into an order, or when choosing how to handle events.

These are guidelines for judgement. Project instructions, a project's own standards, and the user's requests take priority. `[PP ...]` and `[APoSD ...]` mark which book an idea comes from.

## Contents

- [Events and concurrency](#events-and-concurrency)
  - `#shared-state` Shared state is incorrect state
  - `#temporal-coupling` Remove ordering you do not need
  - `#events` Four ways to handle events
  - `#actors` Share nothing: actors and blackboards

<!-- id: #concurrency -->

## Events and concurrency

Real programs respond to things that happen at unpredictable times, and often do several things at once. Both are hard mainly for one reason: shared state. This part is drawn from *The Pragmatic Programmer*.

<!-- id: #shared-state -->

### Shared state is incorrect state [PP topic 34, Tips 57, 58]

**Rule:** If two pieces of running code can both change the same data, neither can trust what it just read.

- List everything changeable that more than one task can reach. That includes files, database rows and the current folder, not only variables.
- Replace "check, then act" with one call that the owner of the data performs as a single step.
- Do not rely on every caller remembering to lock. Put the protection inside the resource.
- Failures that come and go at random are usually concurrency bugs. (Tip 58)
- Best of all, redesign so the state is not shared.

<!-- id: #temporal-coupling -->

### Remove ordering you do not need [PP topic 33, Tip 56]

**Rule:** Code often forces steps into a fixed order that the problem never asked for. Find the real dependencies.

- Write down the steps. For each, ask what truly has to be finished first.
- Look for waiting that is not your code's work: network calls, storage, a person. Other work can go on during it.
- Look for chunks that are independent of each other. They can run side by side and be combined at the end.
- Then judge whether the gain is worth the extra care. What *could* overlap is not always worth overlapping.

> **Link to APoSD.** A function that only works if another was called first is a hidden part of its interface. Ousterhout would ask you to remove the rule if you can, and document it clearly if you cannot.

<!-- id: #events -->

### Four ways to handle events [PP topic 29]

**Rule:** Pick a deliberate strategy for responding to events. Otherwise the handling spreads through the code as flags and special cases.

| Strategy | What it is | Use when | Cost |
| --- | --- | --- | --- |
| **State machine** | A set of named states, plus a table saying which event moves you from which state to which | The logic is "where are we in the process?", and you find yourself adding boolean flags | Does not suit everything |
| **Observer** | A source keeps a list of functions to call when something happens | Simple notification within one program | Each observer must register with the source, and usually runs straight away, blocking it |
| **Publish and subscribe** | Senders post to named channels. Receivers listen to channels. Neither knows the other | Senders and receivers should be independent, or are in different programs | Hard to see who handles what |
| **Streams** | Treat events as a list that keeps growing, and filter, combine and transform them like a list | You react to combinations or timing, such as "three failures within five minutes" | A library and a style to learn |

> **Link to APoSD.** Ousterhout warns that event-driven code is hard to follow, because nothing in the text shows what calls a handler. If you use it, say in each handler's comment when and by what it is called.

<!-- id: #actors -->

### Share nothing: actors and blackboards [PP topics 35, 36, Tips 59, 60]

**Rule:** The safest way to deal with shared state is to design it out.

| Approach | Where the state lives | How parts communicate | Main cost |
| --- | --- | --- | --- |
| Shared state with locks | In memory everyone can reach | Directly, guarded by locks | Very easy to get wrong |
| **Actors** | Private to each actor | One-way messages. Each actor handles one message at a time | The flow is indirect |
| **Blackboard** | As facts posted in one shared place | Parts post facts and react to facts. They do not know each other | Hard to follow without good tracing |
