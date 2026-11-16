/**
 * When something happened. `isEarlier`: rebuilt from the session's history
 * when the mod loaded mid-session, so `t` is the load time, not the event's.
 */
export type Stamp = { t: number; isEarlier?: true }

/** One observation, in the same neutral shape the transcript backfill uses. */
export type UsageEvent = Stamp &
  (
    /**
     * `isTimed`: recorded by a version that records code changes, so its turn's reads can be timed. Prompts stored by
     * earlier versions lack it: their turns' code changes were never recorded, so their reads have no moment.
     */
    | { kind: 'prompt'; named: string[]; isTimed?: true }
    /** `id`: the Skill call's tool_use id, so a call whose result is an error (`refused`) loaded nothing. */
    | { kind: 'load'; id?: string; skill: string; via: 'tool' | 'slash'; isSubagent: boolean }
    /** `isSubagent`: the hook spoke to a subagent, not the main agent; `agent`: which subagent, so its own turn end settles it. */
    /** `holdKind`: an adapter hold (`goated-hold:`), whose `hook` is its gate; `isStop`: it held a `Stop`, not a call. */
    /** `skipOnly`: the named skills the hold offers only as a skip line, which no load answers. */
    | { kind: 'nudge'; hook: string; named: string[]; holdKind?: HoldKind; isStop?: true; skipOnly?: string[]; isSubagent?: true; agent?: string }
    /** A `goated-skip: <skill>: <reason>` line in a reply: the agent (or the subagent `agent`) declined a skill for this turn. */
    | { kind: 'skip'; skill: string; reason: string; isSubagent?: true; agent?: string }
    /**
     * A turn ended: the main agent's, or the subagent `agent`'s. A nudge it leaves open can no longer be followed.
     * `reason`: why, as Claude Code says it (`answer`, `aborted` by you, `refusal`, `error`); absent in events kept before it was read.
     */
    | { kind: 'turn-end'; agent?: string; reason?: 'answer' | 'aborted' | 'refusal' | 'error' }
    | { kind: 'read'; skills: string[] }
    /** A supporting file of a skill read, such as `references/x.md`, by the main agent or a subagent. */
    | { kind: 'ref'; skill: string; file: string; isSubagent?: true }
    /** A subagent reading a skill's SKILL.md, the skill's body, without the Skill tool. */
    | { kind: 'body'; skill: string; isSubagent: true; agent?: string }
    /** A winning `goated-route:` line in a reply, by the main agent or the subagent `agent`. */
    | ({ kind: 'route'; isSubagent?: true; agent?: string } & Route)
    /**
     * A reply's `goated-design-reads:` lines, by the main agent or the subagent `agent`: the union of the files they
     * declare, each once, and the reason of each `none` line.
     */
    | { kind: 'design-reads'; files: string[]; noneReasons: string[]; isSubagent?: true; agent?: string }
    /** The adapter's notice that it recorded overrides you typed, each phrase lowercased. */
    | { kind: 'override'; phrases: string[] }
    /** An Agent tool call starting a subagent, by the main agent or the subagent `agent`. */
    /** `id`: the call's tool_use id, so a refusal of the call (`refused`) can take it back. */
    | { kind: 'spawn'; id?: string; agentType: string; description: string; isSubagent?: true; agent?: string }
    /** The start message a SubagentStart hook gave the subagent `agent`; only in events stored by earlier versions. */
    | { kind: 'subagent-start'; agent?: string }
    /** A main-agent call the adapter holds like a write: an edit, or a spawn that hands work on. */
    | { kind: 'write'; id?: string }
    /**
     * A code change, as the adapter counts one where the mod can see it: an edit tool's call on a code file, by the
     * main agent or a subagent. `id`: the call's tool_use id, so a refused call changed nothing.
     */
    | { kind: 'change'; id?: string; isSubagent?: true }
    /** A call whose result was an error, such as one the adapter held: it did not run, so its spawn or write did not happen. */
    | { kind: 'refused'; id: string }
    /**
     * Boundaries of the main agent's round trips: a reply begins (`response`), then
     * its tool results come back (`results`). Each marks only the first row of its
     * stretch, so a hold can tell what the reply holding its call already did.
     */
    | { kind: 'response' }
    | { kind: 'results' }
    | { kind: 'compact' }
  )

/**
 * Turns that wrote, by whether a route line came before the first write
 * (`routed`), only after it (`late`), or not at all (`none`). A turn runs
 * from one typed prompt to the next.
 */
export type WritingTurns = { routed: number; late: number; none: number }

/** A route line as the marker grammar reads it (stack/fixtures/markers/README.md in the GOATED repo). */
export type Route = { form: 'direct' | 'continue' } | { form: 'route'; intensity: 'lightweight' | 'standard' | 'full'; requires: string[] }
export type RouteForm = Route['form']

/** A design-reads line as the marker grammar reads it: the reference files it declares, or `none` with a reason. */
export type DesignReads = { form: 'files'; files: string[] } | { form: 'none'; reason: string }

/** Design-reads lines counted: in how many replies each file was declared, and how many lines declared `none`. */
export type DesignReadCounts = { files: Record<string, number>; none: number }

/** An adapter hold's kind, from its `goated-hold: <gate> | <kind>` first line. */
export type HoldKind = 'strict' | 'justified-skip'

/** What subagents did: how many were started, got a start message, and read a skill body. */
export type SubagentCounts = { spawns: number; starts: number; bodyReads: number }

/** Why a skill loaded. */
export type Origin = 'user-slash' | 'user-named' | 'hook-nudged' | 'router-routed' | 'self-initiated' | 'subagent'

/**
 * What became of one skill a hook named. `declined`: a skip line said why it does not apply. `pending`: the turn is still open.
 * `already loaded`: only in summaries stored by earlier versions.
 */
export type Outcome = 'followed' | 'read files' | 'already loaded' | 'declined' | 'ignored' | 'pending'

/** Whether the router loaded before any other tool, where a router rule was active; summaries stored by earlier versions may carry it, and current ones are always `off`. */
export type RouterStatus = 'first' | 'late' | 'never' | 'off'

export type Counts<K extends string> = Partial<Record<K, number>>

export type SessionSummary = {
  loads: Record<string, Counts<Origin>>
  nudges: Record<string, Counts<Outcome>>
  router: RouterStatus
  lastUsed: Record<string, number>
  /** Reads of each skill's supporting files, by skill then file; absent in summaries stored before they were counted. */
  refs?: Refs
  /** Of those reads, how many came before their skill had loaded (since the last compaction); absent in summaries stored before they were counted. */
  refsUnloaded?: number
  /** The same reads by their moment in the turn; absent in summaries stored before moments were recorded, whose reads have none. */
  refMoments?: RefMoments
} & Measures

/**
 * What the adapter and the marker grammar add to a summary. Each is absent in
 * summaries stored before it was counted, so older history still reads.
 */
export type Measures = {
  /** Winning route lines, by form. */
  routes?: Counts<RouteForm>
  writingTurns?: WritingTurns
  /** Adapter holds, by kind; what became of them is in `nudges`, by gate. */
  holds?: Counts<HoldKind>
  /** Overrides you typed, by phrase. */
  overrides?: Record<string, number>
  subagents?: SubagentCounts
  /** Design-reads lines, by file declared, and `none` declarations. */
  designReads?: DesignReadCounts
}

/** How often each supporting file was read, by skill then path within the skill, such as `references/x.md`. */
export type Refs = Record<string, Record<string, number>>

/**
 * When in its turn a supporting file was read, against the turn's code changes: before the first, between two, after
 * the last, or in a turn that changed no code (`no-change`). A turn runs from one typed prompt to the next.
 */
export type RefMoment = 'before' | 'between' | 'after' | 'no-change'

/** Reads of supporting files by skill, then path within the skill, then moment. */
export type RefMoments = Record<string, Record<string, Counts<RefMoment>>>

/**
 * One row of the activity log. A nudge is one row whatever becomes of it:
 * each skill it named carries its own status, which changes as the session
 * goes (pending, then followed, declined or ignored).
 */
export type TimelineEntry = Stamp &
  (
    | { kind: 'prompt' }
    /** `isSubagent`: a subagent loaded it, whatever caused the load. */
    | { kind: 'load'; skill: string; origin: Origin; isSubagent?: true }
    /** `holdKind`: set for an adapter hold, whose `hook` is its gate. `repeats`: how many times it held in a row, asking the same, when more than once. */
    | { kind: 'nudge'; hook: string; skills: NudgedSkill[]; holdKind?: HoldKind; repeats?: number; isSubagent?: true }
    /** `isLoaded`: the skill had loaded (since the last compaction) when its file was read. */
    | { kind: 'ref'; skill: string; file: string; isLoaded: boolean; isSubagent?: true }
    | ({ kind: 'route'; isSubagent?: true } & Route)
    | { kind: 'design-reads'; files: string[]; noneReasons: string[]; isSubagent?: true }
    | { kind: 'override'; phrases: string[] }
    /** `isHeld`: the call was refused, so no subagent started. */
    | { kind: 'spawn'; agentType: string; description: string; isHeld?: true; isSubagent?: true }
    | { kind: 'subagent-start' }
    | { kind: 'body'; skill: string; isSubagent: true }
    | { kind: 'compact' }
  )

/**
 * One skill a nudge named and what became of it; `at`: when it settled, absent
 * while waiting or for a session that ended with it open; `reason`: why it was
 * declined.
 */
export type NudgedSkill = { skill: string; status: Outcome; at?: number; reason?: string }

export type AllTime = {
  sessions: number
  loads: Record<string, Counts<Origin>>
  nudges: Record<string, Counts<Outcome>>
  router: Counts<RouterStatus>
  lastUsed: Record<string, number>
  refs?: Refs
  refsUnloaded?: number
  refMoments?: RefMoments
} & Measures

/**
 * The skills the session lists for the model, and whether the listing was cut
 * to its budget. `own`: the user's and the project's skills, the ones the
 * Unused tab is about, as opposed to built-in and plugin skills.
 */
export type Available = { names: string[]; own: string[]; total: number; included: number }

export type Tab = 'session' | 'all' | 'unused'

declare module 'claude-code' {
  interface PluginState {
    'skill-usage': {
      events: Shaped<UsageEvent[]>
      /** The session id the events belong to; another id means `/clear` started a new session. */
      owner: string | null
      /** The session id whose history was read into `events`, so it is read once per session. */
      backfilled: string | null
      /** What was stored for this session before a resume, added to what is observed since. */
      baseline: Shaped<SessionSummary | null>
      available: Shaped<Available | null>
      allTime: Shaped<AllTime | null>
      tab: Tab
      /** When `/skill-usage preview` started; the picture plays its script until it has run. */
      preview: number | null
      lastError: string | null
    }
  }
}
