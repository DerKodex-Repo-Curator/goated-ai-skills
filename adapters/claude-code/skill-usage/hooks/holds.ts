// Hold settlement: what became of each adapter hold. A hold asks; a load, a
// read of a skill's files, a skip line or a route line answers; a turn ends
// and settles what is left. Pure, like classify.ts, which reads the events and
// feeds them here in order.

import type { Counts, HoldKind, NudgedSkill, Outcome, RouteForm, TimelineEntry, UsageEvent } from '../types'

/** The adapter's route-line hold asks for a route line, which no skill load settles. */
export const ROUTE_LINE = '(route line)'

/** The adapter's gate for a route's required skills. */
const PIPELINE_GATE = 'pipeline'
/** The adapter's closeout gate, which holds a commit (Ticket 059) as well as a `Stop`, asking for the same items. */
const CLOSEOUT_GATE = 'closeout'
/** Gates whose named skills are alternatives, one of which answers the hold: the spawn hold's `handoff` or `subagent-driven-development`. */
const ALTERNATIVE_GATES = new Set(['spawn'])
/**
 * How many times in a row Claude Code lets a `Stop` hook block before it ends
 * the turn anyway (2.1.325, seen in Ticket 034's runs). A turn that ends after
 * that many blocks did not get past the hold.
 */
const STOP_BLOCK_LIMIT = 9

/** An event's time, as a timeline row carries it. */
export const stamp = (e: UsageEvent) => (e.isEarlier ? { t: e.t, isEarlier: true as const } : { t: e.t })

/** Adds one to `key` in `row` of a count table. */
export function bump<K extends string>(table: Record<string, Counts<K>>, row: string, key: K) {
  const counts = (table[row] ??= {})
  counts[key] = (counts[key] ?? 0) + 1
}

export type NudgeRow = TimelineEntry & { kind: 'nudge' }

/** The hold settlement of one session, fed its events in order. */
export type HoldSettlement = {
  /**
   * Takes the next event of the session. Returns the log row a hold opens, for
   * the caller to place in its timeline; none for any other event, or for a
   * hold that joins an earlier row of its gate as a repeat. The row's marks
   * change as later events settle it. Feed no Skill call that failed: it
   * loaded nothing, so it answers nothing.
   */
  observe(e: UsageEvent): NudgeRow | undefined
  /** Whether a hold asked for `skill` in the running typed-prompt turn, settled or not. */
  wasAsked(skill: string): boolean
  /**
   * Settles what is still open, `ignored` once the session is over (`isFinal`),
   * else `pending`, and returns what became of the holds by gate (`nudges`)
   * and how many held, by kind (`holds`). Call it once, after the last event.
   */
  finish(isFinal: boolean): { nudges: Record<string, Counts<Outcome>>; holds: Counts<HoldKind> }
}

/**
 * A new hold settlement. Each hold asks for one or more skills, or a route
 * line; an ask stays open until a load, a read of the skill's files, a skip
 * line or a route line answers it, or its loop's turn ends. A blocked `Stop`
 * (the closeout's hold) is settled by whether the adapter let the turn end.
 */
export function holdSettlement(): HoldSettlement {
  const nudges: Record<string, Counts<Outcome>> = {}
  const holds: Counts<HoldKind> = {}
  let turnNudged = new Set<string>()
  // One open ask per nudge: the skills any one of which answers it (`anyOf`; more than one only for a gate whose skills
  // are alternatives), and its mark on the nudge's own log row, so settling it updates that row.
  // `agent`: the subagent it spoke to, absent for the main agent; that loop's turn end settles it.
  // `isStrict`: an adapter hold that only loading the skill clears; a skip line never declines it.
  // `row`: the nudge's log row, which a repeat of the same hold in the turn joins.
  // `isCloseout`: a closeout item, on a `Stop` or a commit, which the `Stop` that ends the turn judges again.
  // `isSkipOnly`: a skill the hold offers only as a skip line, which no load answers.
  // `isSkipRejected`: a blocked `Stop` asked for it after a skip line, so that skip line did not clear it.
  // `refs`, `needsLine`: what a design hold that offers its skill only as a skip line asks instead: a Read of each
  // design reference still unread, and a design-reads line. It is followed once both are in, as the adapter judges.
  type Open = { hook: string; anyOf: string[]; agent?: string; isStrict?: true; isCloseout?: true; isSkipOnly?: true; isSkipRejected?: true; refs?: Set<string>; needsLine?: boolean; mark: NudgedSkill; row: NudgeRow }
  /** Whether an ask is a design hold's, answered by its reads and line rather than by any read of the skill's files. */
  const asksDesign = (n: Open) => n.refs !== undefined || n.needsLine !== undefined
  /** Settles a design hold's ask once nothing it asked is missing; `outcome` names what came last. */
  const settleDesign = (n: Open, outcome: Outcome, by: UsageEvent) => {
    if (!n.refs?.size && !n.needsLine) settle(m => m === n, outcome, by)
  }
  let open: Open[] = []
  /** Whether an open ask is answered by loading `skill`. */
  const answers = (n: Open, skill: string) => !n.isSkipOnly && n.anyOf.includes(skill)
  // The adapter holds of each loop's running turn, by agent ('' for the main agent) and gate: the row a repeat joins,
  // and every ask the row made, settled or not.
  type GateRow = { row: NudgeRow; asks: Open[] }
  const turnHolds = new Map<string, GateRow>()
  const gateKey = (hook: string, agent?: string) => `${agent ?? ''}|${hook}`
  const sameAsk = (n: Open, ask: readonly string[]) => n.anyOf.join(' ') === ask.join(' ')
  const forgetHolds = (agent?: string) => {
    for (const key of [...turnHolds.keys()]) if (key.startsWith(`${agent ?? ''}|`)) turnHolds.delete(key)
  }
  // The main turn's blocked `Stop`s: how many so far, and the asks the latest one made.
  let stopBlocks = 0
  let lastStopAsks: Open[] = []
  // Skip lines written in each loop's running turn, by agent ('' for the main agent) then skill, with their reasons.
  const skipped = new Map<string, Map<string, string>>()
  const skipsOf = (agent?: string) => skipped.get(agent ?? '') ?? new Map<string, string>()
  const skipReason = (anyOf: readonly string[], agent?: string) => anyOf.map(s => skipsOf(agent).get(s)).find(r => r !== undefined)
  // The main agent's round trip a held call belongs to: what its reply did before the call. Claude Code records a call
  // only after its hold returns, so a route line or load beside the held call reaches the adapter one call late.
  type Reply = { route?: RouteForm; loads: Set<string> }
  let reply: Reply = { loads: new Set() }
  let answeredReply: Reply = reply
  let isInResults = false
  // Whether the main agent replied since the last blocked `Stop`: a turn that then ends got past that hold.
  let hasRepliedSinceStop = false
  // Whether the session has a task a `continue` route line can continue, as the adapter's route-line hold checks.
  let hasTask = false

  // `by`: the event that settled it, whose time the row keeps so the picture can show the moment; a rebuilt event has no real time.
  // `chosen`: for an ask with alternatives, the skill that answered it, which its row then names.
  const settle = (matches: (n: Open) => boolean, outcome: Outcome, by?: UsageEvent, chosen?: string) => {
    open = open.filter(n => {
      if (!matches(n)) return true
      bump(nudges, n.hook, outcome)
      n.mark.status = outcome
      if (chosen && n.anyOf.length > 1) n.mark.skill = chosen
      if (by && !by.isEarlier) n.mark.at = by.t
      return false
    })
  }
  /** Takes back a settled ask's outcome and opens it again: the adapter asked for it again, so it was not met. */
  const reopen = (n: Open) => {
    if (open.includes(n)) return
    const counts = nudges[n.hook]
    const was = n.mark.status
    if (counts?.[was]) counts[was] = (counts[was] ?? 1) - 1
    if (counts && counts[was] === 0) delete counts[was]
    if (was === 'declined') n.isSkipRejected = true
    n.mark.status = 'pending'
    delete n.mark.at
    delete n.mark.reason
    open.push(n)
  }
  /**
   * A loop's turn is over: what it left open can no longer be followed, so each is declined (a skip line said why) or
   * ignored. A closeout item, asked by a blocked `Stop` or a held commit, is the exception. The adapter judges every
   * `Stop` it is given against every closeout item, so a main turn that ended
   * as an answer (not interrupted, nor ended by an error) after the agent replied to the last block got past it: what
   * that block asked was met, by a check run, a fix or a load the hold cannot name. Claude Code ends a turn after
   * `STOP_BLOCK_LIMIT` blocks whatever the hook says, and then what the last block asked was not met; what an earlier
   * block asked and the last did not, the adapter judged met. A close at the next prompt (a turn end the mod did not
   * see, and rebuilt history) cannot tell a pass from an interruption, so it passes nothing.
   */
  const closeTurn = (isInLoop: (n: Open) => boolean, by: UsageEvent) => {
    const isAnswer = by.kind === 'turn-end' && !by.agent && (by.reason === undefined || by.reason === 'answer')
    const isPassed = isAnswer && hasRepliedSinceStop && stopBlocks < STOP_BLOCK_LIMIT
    if (isAnswer && stopBlocks >= STOP_BLOCK_LIMIT) for (const n of lastStopAsks) reopen(n)
    const ending = open.filter(isInLoop)
    for (const n of ending) {
      const reason = n.isStrict || n.isSkipRejected ? undefined : skipReason(n.anyOf, n.agent)
      if (reason !== undefined) n.mark.reason = reason
      const isMet = n.isCloseout === true && (isPassed || (isAnswer && !lastStopAsks.includes(n)))
      settle(m => m === n, reason !== undefined ? 'declined' : isMet ? 'followed' : 'ignored', by)
    }
  }
  /** A new ask on a gate's row, open until something answers it. A blocked `Stop` has judged every skip line before it. */
  const addAsk = (held: GateRow, e: UsageEvent & { kind: 'nudge' }, ask: string[]): Open => {
    const mark: NudgedSkill = { skill: ask.join(' or '), status: 'pending' }
    held.row.skills.push(mark)
    const isSkipOnly = ask.every(skill => e.skipOnly?.includes(skill))
    const n: Open = {
      hook: e.hook,
      anyOf: ask,
      ...(e.agent ? { agent: e.agent } : {}),
      ...(e.holdKind === 'strict' ? { isStrict: true as const } : {}),
      ...(e.isStop ? { isSkipRejected: true as const } : {}),
      ...(e.holdKind && e.hook === CLOSEOUT_GATE && !e.agent ? { isCloseout: true as const } : {}),
      ...(isSkipOnly ? { isSkipOnly: true as const } : {}),
      ...(isSkipOnly && e.refs?.length ? { refs: new Set(e.refs) } : {}),
      ...(isSkipOnly && e.needsLine ? { needsLine: true } : {}),
      mark,
      row: held.row,
    }
    held.asks.push(n)
    for (const skill of ask) turnNudged.add(skill)
    open.push(n)
    return n
  }
  /**
   * An adapter hold of a gate that already held in this turn, asking for nothing its earlier holds did not: it joins
   * their row as a repeat and counts once. A held call retried while its asks still wait, or held again because the
   * adapter had not yet seen the load or skip line beside the retry, settles nothing new; what the earlier holds asked
   * and this one no longer does was met. A blocked `Stop` that blocks again joins the turn's closeout row whatever it
   * asks: the adapter has seen every reply by then, so an ask it repeats after a load or a skip line was not met, and
   * opens again. A hold that asks for nothing, or a call's hold that asks for anything new, is a row of its own.
   */
  const joinRepeat = (e: UsageEvent & { kind: 'nudge' }, asks: readonly string[][]): boolean => {
    const held = turnHolds.get(gateKey(e.hook, e.agent))
    if (!held || asks.length === 0) return false
    const known = (ask: readonly string[]) => held.asks.find(n => sameAsk(n, ask))
    if (!e.isStop && !asks.every(known)) return false
    held.row.repeats = (held.row.repeats ?? 1) + 1
    const asked = asks.map(ask => {
      const n = known(ask)
      if (!n) return addAsk(held, e, [...ask])
      if (e.isStop) reopen(n)
      return n
    })
    if (e.isStop) lastStopAsks = asked
    else settle(n => held.asks.includes(n) && !asked.includes(n), 'followed', e)
    return true
  }
  /** What the held call's own reply already did for `ask`, which the adapter could not see yet: the answering skill, or none. */
  const answeredInReply = (ask: readonly string[], e: UsageEvent & { kind: 'nudge' }) => {
    if (e.agent) return undefined
    const own = isInResults ? answeredReply : reply
    if (ask[0] === ROUTE_LINE) return own.route && (own.route !== 'continue' || hasTask) ? ROUTE_LINE : undefined
    return ask.find(s => own.loads.has(s))
  }
  /** A hold asks: its row, unless it joins an earlier one; an ask its own reply or an earlier skip line answered settles at once. */
  const hold = (e: UsageEvent & { kind: 'nudge' }): NudgeRow | undefined => {
    if (e.holdKind) holds[e.holdKind] = (holds[e.holdKind] ?? 0) + 1
    if (e.isStop) {
      hasRepliedSinceStop = false
      stopBlocks += 1
    }
    // A gate whose skills are alternatives asks once; any other nudge asks for each skill it names.
    const asks = ALTERNATIVE_GATES.has(e.hook) && e.named.length > 1 ? [e.named] : e.named.map(s => [s])
    if (joinRepeat(e, asks)) return undefined
    const row: NudgeRow = {
      ...stamp(e),
      kind: 'nudge' as const,
      hook: e.hook,
      skills: [] as NudgedSkill[],
      ...(e.holdKind ? { holdKind: e.holdKind } : {}),
      ...(e.isSubagent ? { isSubagent: true as const } : {}),
    }
    // A hold's asks are records of the turn, so a repeat of the hold finds them, settled or not.
    const held: GateRow = { row, asks: [] }
    if (asks.length > 0) turnHolds.set(gateKey(e.hook, e.agent), held)
    for (const ask of asks) {
      const n = addAsk(held, e, ask)
      const inReply = e.isStop ? undefined : answeredInReply(ask, e)
      const reason = e.holdKind === 'strict' || e.isStop ? undefined : skipReason(ask, e.agent)
      if (inReply !== undefined) settle(m => m === n, 'followed', e, inReply)
      else if (reason !== undefined) {
        // Declined before it was asked, earlier in the same turn.
        n.mark.reason = reason
        settle(m => m === n, 'declined', e)
      }
    }
    if (e.isStop) lastStopAsks = held.asks.slice()
    return row
  }

  const observe = (e: UsageEvent): NudgeRow | undefined => {
    switch (e.kind) {
      case 'prompt':
        // Anything still open belongs to a turn that is over, a turn end the mod did not see included.
        closeTurn(() => true, e)
        skipped.clear()
        turnHolds.clear()
        stopBlocks = 0
        lastStopAsks = []
        turnNudged = new Set(open.flatMap(n => n.anyOf))
        reply = answeredReply = { loads: new Set() }
        isInResults = false
        break
      case 'response':
        reply = { loads: new Set() }
        isInResults = false
        hasRepliedSinceStop = true
        break
      case 'results':
        if (!isInResults) answeredReply = reply
        isInResults = true
        break
      case 'nudge':
        return hold(e)
      case 'skip': {
        const own = skipsOf(e.agent)
        own.set(e.skill, e.reason)
        skipped.set(e.agent ?? '', own)
        for (const n of open.filter(n => n.anyOf.includes(e.skill) && n.agent === e.agent && !n.isStrict)) {
          n.mark.reason = e.reason
          settle(m => m === n, 'declined', e)
        }
        break
      }
      case 'turn-end':
        closeTurn(n => n.agent === e.agent, e)
        skipped.delete(e.agent ?? '')
        forgetHolds(e.agent)
        if (!e.agent) {
          stopBlocks = 0
          lastStopAsks = []
        }
        break
      case 'load':
        if (!e.isSubagent && e.via === 'tool') reply.loads.add(e.skill)
        settle(n => answers(n, e.skill), 'followed', e, e.skill)
        break
      case 'read':
        settle(n => !asksDesign(n) && n.anyOf.some(s => e.skills.includes(s)), 'read files', e, e.skills.find(s => open.some(n => n.anyOf.includes(s))))
        break
      case 'ref':
        // Only the Read tool counts as a design hold's read, as the adapter counts it; a subagent's reads are its own.
        if (!e.isReadTool || e.isSubagent) break
        for (const n of open.filter(n => !n.agent && n.refs !== undefined)) {
          if (n.refs?.delete(e.file.split('/').pop() ?? '')) settleDesign(n, 'read files', e)
        }
        break
      case 'design-reads':
        for (const n of open.filter(n => n.needsLine && n.agent === e.agent)) {
          n.needsLine = false
          settleDesign(n, 'followed', e)
        }
        break
      case 'body':
        // A subagent reading a skill's body settles only what was asked of that subagent.
        settle(n => n.anyOf.includes(e.skill) && n.agent === e.agent, 'read files', e, e.skill)
        break
      case 'route':
        if (!e.agent) reply.route = e.form
        // A `continue` with no task to continue does not answer a route-line hold: the adapter holds it too.
        if (e.form !== 'continue' || hasTask || e.agent) settle(n => n.anyOf[0] === ROUTE_LINE && n.agent === e.agent, 'followed', e)
        if (!e.agent && e.form !== 'continue') hasTask = true
        // The pipeline hold says to drop a skill that does not apply by writing a corrected route line, the last one
        // winning: a new route that no longer requires a held skill follows that hold. `continue` keeps the route.
        if (e.form !== 'continue') {
          const requires: readonly string[] = e.form === 'route' ? e.requires : []
          settle(n => n.hook === PIPELINE_GATE && n.agent === e.agent && !n.anyOf.some(s => requires.includes(s)), 'followed', e)
        }
        break
    }
    return undefined
  }

  return {
    observe,
    wasAsked: skill => turnNudged.has(skill),
    finish: isFinal => {
      settle(() => true, isFinal ? 'ignored' : 'pending')
      return { nudges, holds }
    },
  }
}
