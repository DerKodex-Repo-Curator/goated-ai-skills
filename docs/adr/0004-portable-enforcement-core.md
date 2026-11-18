# ADR 0004: A Portable Enforcement Core Behind One Event Model

## Status

Accepted on 2026-11-18, with the spec
[A Portable Enforcement Core For Any Agent Harness](../specs/2026-11-17-portable-enforcement-core.md)
and Ticket 079, whose closeout records the maintainer's review of the event
model.

This ADR works under [ADR 0003](0003-opt-in-framework-enforcement-adapters.md)
and supersedes nothing. Every exclusion that
[ADR 0002](0002-v2-integrated-stack-foundation.md) keeps from
[ADR 0001](0001-v1-runtime-bootstrap-and-adapter-automation.md), and that ADR
0003 left in force, still holds.

## Context

ADR 0003 lets GOATED ship opt-in enforcement adapters that enforce portable
contracts. Only one exists, for Claude Code, and its rules can be used only
from Claude Code:

- many rules are stated only in the adapter's code and README, though ADR 0003
  says an adapter enforces contracts and never defines them;
- there is no harness-neutral description of a turn, a call, or a decision;
- the rule modules read Claude Code's transcript shape (`Turn` and `Call` in
  `goated_adapter/transcript.py`) and Claude Code's tool names, such as `Edit`,
  `Bash`, and `Skill` (`WRITE_TOOLS`, `SPAWN_TOOLS`, `COMMAND_TOOLS` in
  `goated_adapter/gates.py`);
- the adapter's tests build Claude Code transcripts, so they cannot check any
  other adapter.

The maintainer also runs agents in a plain API tool loop, Pi Agent, and
OpenCode, and is weighing Orca, an environment that runs several agent CLIs
side by side. Those sessions get the skills with no holds.

## Decision

1. **One shared core, thin adapters.** The rules live once, in a Python core
   under `adapters/core/` (Tickets 080 and 081 move them). Each harness gets a
   thin adapter that translates its events into the event model and the
   core's decision back into the harness's own output. We reject a
   reimplementation per harness: the rules are large (the Claude Code adapter
   is about 9,000 lines), change often, and would drift.
2. **The event model is the one seam.** A versioned JSON model,
   `stack/schemas/enforcement-event-model.schema.json`, describes what the
   core needs to judge one event and what it answers. Adapters know a harness
   and the model; the core knows the rules and the model. Neither reaches
   across: the core names no harness tool, and an adapter states no rule.
3. **Two ways to call the core, one answer.** A Python harness imports the
   core and passes a request object. Any other harness runs a command that
   reads one JSON request on standard input and writes one JSON decision on
   standard output. Both return the same decision for the same request.
4. **The contract is a document under `stack/`.**
   `stack/enforcement-contract.md` states every enforced rule in
   harness-neutral words and cites the rules a skill, the shared policy, or
   the registry owns rather than copying them. Adapters cite it; the Claude
   Code README keeps only what is specific to Claude Code.
5. **Conformance scenarios prove adapters.** Scenario files under
   `stack/fixtures/enforcement/` hold a sequence of events and the expected
   decision at each step, in the event model's terms, and name no harness.
   The repo proves them against the Claude Code adapter today (Ticket 079)
   and against the core once it exists; an adapter author runs the same files
   through their adapter.

### The event model, in brief

The schema is the authority; this is its shape.

- **A request** carries the model's version, the session (its id, and whether
  the main agent or a subagent is acting), the project, the turns so far, and
  one event to judge.
- **The event** is one of: a pending call (judged before it runs), a finished
  call (after it ran), the end of a turn, a submitted prompt, or a session
  start. Only a pending call and a turn end can be held; the others return
  notices only, such as the early closeout note (Ticket 096) after a finished
  file write.
- **A call** has a kind, never a tool name: `file_write`, `shell_command`,
  `skill_load`, `file_read`, `spawn`, `commit`, `pull_request`, or `other`.
  Each kind has its own fields: a write's file and its removed and added
  text, a command's text and shell, a read's file and whether it was whole, a
  spawn's brief and whether it starts work now. `line_text` is the one field
  a route or skip line may be read from. A commit or pull request made by a
  shell command stays a `shell_command`; the core reads the command, as it
  does today. The `commit` and `pull_request` kinds are for tools that do
  nothing else. An adapter may label a harness-specific shell command with
  another kind, such as Orca's worker start as a `spawn` (see below), so the
  core never learns a harness's command names.
- **A turn** is an ordered list of entries: the prompt that opened it, with
  who wrote it, then reply texts, finished calls with their results, skill
  loads a person invoked, and background agents that finished. A compaction
  opens a turn of its own. The order is the rules' order: a change read
  counts only after the last change, and a line counts from its call on.
- **The project** is its folders, the working folder, the home folder, the
  agent's own configuration folders (never scratch), and the skills the
  harness can find.
- **A decision** is `allow` or `hold`. A hold carries one or more holds in
  firing order, each with its gate, its kind (`strict` or `justified-skip`)
  and its text, so a joint hold (Ticket 095) is one decision. Any decision
  may carry notices: a fail-open warning, a recorded override, the closeout
  note, or a session-start notice. A notice never holds.
- **Text is split by owner.** The core returns each hold's rule text. The
  adapter adds what only its harness can say, such as where a line can be
  put so the harness keeps it, and which shell call carries it. The adapter
  also strips the blocks its harness inserts into a prompt and moves pasted
  text into `pasted`, so the core never parses a harness's tags.
- **The contract owns the gate list.** The schema checks only a gate name's
  shape; the contract's Gates table lists the gates, and a test compares it
  with the gates the adapter can return.
- **Versions are whole numbers.** `event_model` is a whole number, and every
  change to the model bumps it.

### State

Requests carry the turns, not a stream of events: each request carries every
turn since the last compaction, so the loads, reads, lines, and changes the
rules read all come with it. The core keeps, keyed by the session id the
adapter supplies, only the facts that outlast those turns:

- the current task's route and its `requires:` skills, which carry across a
  compaction;
- whether the session was briefed, which lasts the whole session;
- the turn markers that pick a hold's full or short text and give a
  harness's line advice once per turn, even across calls judged in parallel;
- the friction counts behind the retrospective notice;
- which brief template each spawn followed, for the closeout.

The event model carries none of these, so an adapter never stores or
returns core state.

### What each harness can supply

Researched from public documentation on 2026-11-18. The adapters' own
research steps (spec R9 and R10) confirm this against the installed versions
before anything is built.

| Need | Claude Code | Plain API tool loop | Pi Agent | OpenCode |
| --- | --- | --- | --- | --- |
| Hold a call before it runs, with a reason the agent sees | Yes: `PreToolUse` deny | Yes: the loop owns execution | Yes: `tool_call` returns `{ block: true, reason }` [P1] | V1: `tool.execute.before` throws, shown by example only [O1]; V2: `execute.before` only rewrites input, a permission `evaluate` hook may set `effect = "deny"` with a `message` [O2] |
| Hold the end of a turn | Yes: `Stop` block | Yes | No block; `turn_end` or `agent_before_settle` may return `continue: true` for one more request [P1] | Not documented: V1 only reports `session.idle` [O1]; V2 documents no idle or end hook [O2] |
| The turn so far: prompts, calls with results, reply text | Yes, from the transcript; reply text may be stored as a summary that drops a line | Yes | Yes: `ctx.sessionManager.getBranch()` [P1] | V1: through the SDK `client` [O1]; V2: `ctx.session.context()` [O2] |
| Who wrote a prompt | Yes, from the transcript's origin fields | Yes | Partly: `input` gives `source` of `interactive`, `rpc`, or `extension` [P1] | Not documented [O1] [O2] |
| Skill loads | Yes: the `Skill` tool, or a typed `/<skill>` | Only if the loop defines a skill tool | No skill tool documented: the model reads `SKILL.md`, or `/skill:name` expands it [P2]; the adapter must map a read of an installed `SKILL.md` to `skill_load` | V2: `ctx.skill.list()` only; no load event documented [O2] |
| Compaction | Yes: the transcript's boundary | Only if the loop compacts | Yes: `session_compact` [P1] | V1: `session.compacted` event [O1]; V2: a `compaction` hook [O2] |
| Subagents and their calls | Yes: spawn result names the agent; its own transcript and hooks | Only if the loop spawns | None documented in the extensions page [P1] | No hook for subagents documented [O2] |
| Project and working folder | Yes: `cwd`, `CLAUDE_PROJECT_DIR` | Yes | `ctx.cwd` [P1] | V1: `directory`, `worktree` [O1]; V2: `ctx.location` [O2] |
| Notices into the agent's context | Yes: `additionalContext` | Yes | `before_agent_start` may inject a message; `pi.sendMessage` [P1] | V2: the `context` hook may edit `messages` [O2] |

So the model makes these optional, and the contract will say what an adapter
loses without them:

- **The prompt's author.** An adapter that cannot tell who wrote a prompt
  marks it `unknown`, and the core reads no override from it: no free bypass.
- **Turn-end holds.** An adapter whose harness cannot hold a turn's end,
  such as Pi's, delivers the closeout as a request to continue, and
  documents the gap.
- **Skill loads.** An adapter maps whatever its harness records as a load to
  `skill_load`; where nothing records one, it maps a whole read of an
  installed `SKILL.md`.
- **Subagents.** A harness with none never sends a subagent session or a
  `spawn` result with an agent id; the rules that read them meet nothing.
- **Line fields.** Claude Code may drop a line from stored reply text, so its
  adapter fills `line_text` from a call's description. Another harness whose
  reply text is kept whole leaves `line_text` empty.

### Orca, an environment over other harnesses

Orca is not a harness of its own. It runs other agents' CLIs, such as Claude
Code, Codex and OpenCode, in parallel, each in its own git worktree [R1].
That shapes what an adapter needs there:

- **Holds come from the agent inside.** Orca documents no hook that sees or
  blocks a tool call. It runs the hooks each repository already configures
  for its agent ("Hooks you already have will run when Orca launches the
  agent"), and adds its own hooks only to report an agent's status [R2]. So
  the Claude Code adapter enforces inside Orca as it does anywhere, and an
  agent with no adapter gets no holds there. Orca needs no adapter of its
  own.
- **Each worktree is its own project.** An agent's working folder is its
  worktree, so `project.folders` comes from the agent's own session, as it
  does today.
- **Orca's orchestration is a shell command.** A coordinator agent starts a
  worker with `orca orchestration worker-start --task <taskId>`, and workers
  report back with `orca orchestration send` [R3]. To the agent these are
  shell commands, not spawns, so the `spawn` gate and the closeout's
  subagent rules do not see them unless an adapter labels the worker start
  as a `spawn`, with the task's brief, which it looks up from the task. An
  adapter may do that; the core never learns the command's name.
- **Orca installs skills of its own** into the agents' skill folders, loaded
  through a stub that runs `orca skills get <topic>` [R4]. That load is a
  shell command, not a `skill_load`, so no GOATED rule counts it, and none
  needs to.

### How this stays inside ADRs 0002 and 0003

- **Opt-in only.** The core runs only inside an adapter a user installed.
  Nothing in a skill, the shared policy, or the registry requires it.
- **Enforce, never define.** The contract cites the skill, policy, or
  registry rule each gate enforces. A rule change updates the contract and a
  conformance scenario in the same change.
- **No free bypass.** The model carries who wrote each prompt, so an override
  counts only from a person. An unknown author counts as not a person.
- **Fail open, visibly.** A request the core cannot read, or of an unknown
  version, is answered `allow` with a warning that says so. The core never
  blocks on its own failure.
- **Tested in this repo.** The conformance scenarios run in CI.
- **ADR 0002's exclusions stand.** No installer, no generated plugin
  manifest, no automatic framework detection, no runtime bootstrap a user did
  not opt into, and no orchestration: the core judges calls; the harness runs
  them. The core is local; nothing leaves the machine.

## Consequences

Positive:

- a new harness needs only a thin adapter, in any language, and has
  scenarios to be checked against;
- rules are stated once, in the contract, which cites their owners, and
  enforced once, in the core;
- the Claude Code adapter's behaviour is pinned by harness-neutral scenarios
  before any code moves.

Costs and constraints:

- the event model is a public interface: a breaking change needs a new
  version, and the core refuses versions it does not know;
- a harness with fewer extension points enforces less, and its adapter must
  say what;
- the command form starts a process per call, which a Python harness avoids
  by importing the core;
- the contract, the scenarios, and the adapter README must move together.

## Sources

- [P1] Pi coding agent, Extensions, <https://docs.pi.dev/latest/extensions>,
  read 2026-11-18 (package `@earendil-works/pi-coding-agent`; the page shows
  no version).
- [P2] Pi coding agent, Skills, <https://docs.pi.dev/latest/skills>, read
  2026-11-18.
- [O1] OpenCode V1, Plugins, <https://opencode.ai/v1/docs/plugins/>, read
  2026-11-18.
- [O2] OpenCode, Server plugins,
  <https://opencode.ai/docs/build/plugins/server>, read 2026-11-18 (V2 hooks;
  the V1 object form is supported in OpenCode 1.18.29).
- [R1] Orca, home page, <https://orca.dev/>, read 2026-11-18 (the docs show
  no version).
- [R2] Orca, Agent hooks and memory,
  <https://orca.dev/docs/agents/hooks-memory>, read 2026-11-18.
- [R3] Orca, Orchestration, <https://orca.dev/docs/cli/orchestration>, read
  2026-11-18.
- [R4] Orca, Skills, <https://orca.dev/docs/cli/skills>, read 2026-11-18.
- `adapters/claude-code/goated_adapter/transcript.py`, `gates.py`,
  `hooks.py`, and `adapters/claude-code/README.md` for Claude Code.
