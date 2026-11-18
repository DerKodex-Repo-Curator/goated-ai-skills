// The GOATED core's usage log, read as the mod's own events (Ticket 082 in the GOATED repo). Every harness's adapter
// appends to the log through the shared core, in the format `stack/schemas/usage-log.schema.json` documents: JSON
// Lines, one entry per line, each with the log's version, the time in seconds, the adapter's name, the session id, the
// project key and, for a subagent, its id. Its entries are the facts this mod stores, so each turns into the event
// the mod would have made of the same moment, and the hold settlement (`hooks/holds.ts`) counts them as it counts
// what it hears; the core's own `outcome` entries are left aside. Pure: hooks/register.tsx reads the file and hands
// its text here.

import type { AllTime, CloseoutItem, HoldKind, UsageEvent } from '../types'
import { addSession, summarize } from './classify'
import { ROUTE_LINE } from './holds'

/** The log version this reader knows; an entry of any other is refused, not guessed at. */
export const LOG_VERSION = 1
/** The adapter whose sessions this mod hears for itself: its log entries are left to the mod's own reading. */
export const OWN_ADAPTER = 'claude-code'

/** One session's entries as events, with the adapter that logged them and the session's project key. */
export type LoggedSession = { adapter: string; session: string; project: string | null; events: UsageEvent[] }

type Entry = { log: number; t: number; adapter: string; session: string; project: string | null; agent?: string; type: string; [field: string]: unknown }

/**
 * Where the mod looks for the log: the path set in its `usageLogPath` option, else the core's per-user default:
 * `%LOCALAPPDATA%\goated\usage-log.jsonl` on Windows (`localAppData`), else `$XDG_STATE_HOME/goated/`, else
 * `~/.local/state/goated/`. Null when none can be named.
 */
export function usageLogPlace(where: { configured: string; localAppData?: string; xdgStateHome?: string; home?: string }): string | null {
  if (where.configured.trim()) return where.configured.trim()
  const folder = where.localAppData || where.xdgStateHome || (where.home ? `${where.home.replace(/[\\/]+$/, '')}/.local/state` : '')
  return folder ? `${folder.replace(/[\\/]+$/, '')}/goated/usage-log.jsonl` : null
}

/**
 * The sessions a log's text holds, each as the events the mod makes, in the log's order. A line that is not an entry,
 * or an entry of a version other than `LOG_VERSION`, refuses the whole log with a message saying which line and why; a
 * last line cut short, as by a writer that stopped mid-line, is passed over.
 */
export function readUsageLog(text: string): { sessions: LoggedSession[] } | { refused: string } {
  const lines = text.split(/\r?\n/)
  const sessions = new Map<string, LoggedSession>()
  for (const [index, line] of lines.entries()) {
    if (!line.trim()) continue
    let entry: unknown
    try {
      entry = JSON.parse(line)
    } catch {
      if (lines.slice(index + 1).every(rest => !rest.trim())) continue
      return { refused: `line ${index + 1} of the usage log is not JSON` }
    }
    if (typeof entry !== 'object' || entry === null || Array.isArray(entry)) return { refused: `line ${index + 1} of the usage log is not an entry` }
    const e = entry as Entry
    if (e.log !== LOG_VERSION) return { refused: `line ${index + 1} of the usage log is of log version ${JSON.stringify(e.log ?? null)}, which the mod does not know (it knows version ${LOG_VERSION})` }
    const key = `${e.adapter}\n${e.session}`
    const found = sessions.get(key) ?? { adapter: String(e.adapter), session: String(e.session), project: typeof e.project === 'string' ? e.project : null, events: [] }
    sessions.set(key, found)
    found.events.push(...eventsOf(e))
  }
  return { sessions: [...sessions.values()] }
}

/**
 * The events one entry stands for. A hold stands where the core judged it, after every fact it had seen: the call's
 * round trip opens before it, so no load seen earlier counts as its reply's, and its result closes the round trip. A
 * turn the core let end was answered after its last block, so a reply opens before the end.
 */
function eventsOf(e: Entry): UsageEvent[] {
  const t = e.t * 1000
  const agent = e.agent ? { isSubagent: true as const, agent: e.agent } : {}
  const list = (value: unknown) => (Array.isArray(value) ? value.map(String) : [])
  switch (e.type) {
    case 'prompt':
      return [{ kind: 'prompt', t, named: list(e.named), isTimed: true }]
    case 'override':
      return [{ kind: 'override', t, phrases: list(e.phrases) }]
    case 'load':
      return [{ kind: 'load', t, skill: String(e.skill), via: e.cause === 'slash' ? 'slash' : 'tool', isSubagent: Boolean(e.agent) }]
    case 'hold': {
      const nudge: UsageEvent = {
        kind: 'nudge',
        t,
        hook: String(e.gate),
        named: e.gate === 'route-line' ? [ROUTE_LINE] : list(e.named),
        holdKind: e.kind as HoldKind,
        ...(e.stop ? { isStop: true as const } : {}),
        ...(Array.isArray(e.skip_only) ? { skipOnly: list(e.skip_only) } : {}),
        ...(Array.isArray(e.refs) ? { refs: list(e.refs) } : {}),
        ...(Array.isArray(e.items) ? { items: e.items as CloseoutItem[] } : {}),
        ...(Array.isArray(e.brief_added) ? { briefAdded: list(e.brief_added) } : {}),
        ...agent,
      }
      if (e.agent) return [nudge]
      return e.stop ? [nudge, { kind: 'results', t }] : [{ kind: 'response', t }, nudge, { kind: 'results', t }]
    }
    case 'skip':
      return [{ kind: 'skip', t, skill: String(e.skill), reason: String(e.reason), ...agent }]
    case 'route': {
      const route = e.form === 'route' ? { form: 'route' as const, intensity: e.intensity as 'lightweight' | 'standard' | 'full', requires: list(e.requires) } : { form: e.form as 'direct' | 'continue' }
      return [{ kind: 'route', t, ...route, ...agent }]
    }
    case 'ref':
      return [{ kind: 'ref', t, skill: String(e.skill), file: String(e.file), ...(e.read_tool ? { isReadTool: true as const } : {}), ...(e.partial ? { isPartialRead: true as const } : {}), ...(e.agent ? { isSubagent: true as const } : {}) }]
    case 'skill_read':
      return [{ kind: 'read', t, skills: list(e.skills) }]
    case 'file_read':
      return [{ kind: 'file-read', t, file: String(e.file) }]
    case 'change':
      return [{ kind: 'change', t, ...(e.agent ? { isSubagent: true as const } : {}) }]
    case 'turn_end':
      return e.agent ? [{ kind: 'turn-end', t, agent: e.agent, reason: 'answer' }] : [{ kind: 'response', t }, { kind: 'turn-end', t, reason: 'answer' }]
    case 'compaction':
      return [{ kind: 'compact', t }]
    default:
      // `outcome` is the core's own settlement; a type a later minor change adds is not counted here.
      return []
  }
}

/**
 * The all-time totals of the logged sessions other adapters wrote, each summarized as a finished session with the
 * project key the log gives it; null for none. The mod's own adapter's sessions are left out: the mod heard them
 * itself and stores them already.
 */
export function loggedTotal(sessions: readonly LoggedSession[]): AllTime | null {
  return sessions
    .filter(s => s.adapter !== OWN_ADAPTER)
    .reduce<AllTime | null>((total, s) => {
      const { timeline: _, ...summary } = summarize(s.events, true)
      return addSession(total, { ...summary, ...(s.project ? { project: s.project } : {}) })
    }, null)
}
