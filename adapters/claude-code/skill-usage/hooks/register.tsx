// Skill usage: watches every row added to the conversation, turns the ones
// that matter into neutral events (classify.ts labels them), and shows the
// result in a pane, the status line and `/skill-usage report`.
//
// The session's events live in $.state. Each finished main turn writes the
// session's summary to $.store under its own key (`s:<session id>`), and
// rereads the others: the all-time view is the sum of the other sessions'
// summaries, of the older sessions folded into one total (`older`), plus this
// one, live. Observing never breaks the conversation: a failure is kept in
// `lastError` and shown in the pane until the next successful save.

import { atom, read, update } from 'claude-code'
import type { EngineInterface as Dollar, Register, SessionAppendInput } from 'claude-code'

import type { AllTime, Available, DeclaredReferences, SessionSummary, Tab, UsageEvent } from '../types'
import { addSession, allTimeOf, closeOpen, DATA_VERSION, historyEvents, isObservedRow, mergeSummaries, rowEvents, short, summarize } from './classify'
import type { HistoryMessage } from './classify'
import type { View } from './meaning'
import { forgetPictures, PREVIEW_MS } from './picture'
import { errorText } from './holds'
import { newSalt, projectKey } from './project'
import { declaredReferences, REGISTRY_FROM_MOD } from './registry'
import { allTimeTab, PANE_COLUMNS, reportText, sessionTab, statusText, unusedTab } from './view'

const PANE = 'skill-usage'
const SESSION_KEY = 's:'
const LEGACY_STORE_KEY = 'sessions' // an earlier layout kept every session under one key
/** The total of the sessions folded out of the store once more than `MAX_SESSIONS` others were kept. */
const OLDER_KEY = 'older'
/** The install's salt for project keys (hooks/project.ts). */
const SALT_KEY = 'project-salt'
const MAX_EVENTS = 5000
const MAX_SESSIONS = 300
const OWN_SOURCES = new Set(['userSettings', 'projectSettings'])

// Bump the shape tag whenever what a stored event means changes: a reload then drops the session's events instead of
// misreading them. `events-2`: Ticket 033 stopped reading the retired hand-written hooks. Ticket 050 added code
// changes without a bump: events stored before it hold none, so their prompts lack `isTimed` and their turns' reads
// count with no moment. `events-3`: Ticket 075 added closeout items to holds and cut skip reasons; holds stored
// before it have no items. The backfill mark carries the same tag, so a session whose events a bump dropped reads its
// history again, as a mod that loaded mid-session does, instead of going on with what it observes from then on.
// `events-4`: Ticket 076 added side sessions; the tag now follows the data version, which each summary carries too.
const EVENTS_SHAPE = `events-${DATA_VERSION}`
const events = atom({ plugin: 'skill-usage', key: 'events' } as const, [], { shape: EVENTS_SHAPE })
const owner = atom({ plugin: 'skill-usage', key: 'owner' } as const, null)
const backfilled = atom({ plugin: 'skill-usage', key: 'backfilled' } as const, null, { shape: EVENTS_SHAPE })
const baseline = atom({ plugin: 'skill-usage', key: 'baseline' } as const, null, { shape: 'summary-1' })
const available = atom({ plugin: 'skill-usage', key: 'available' } as const, null, { shape: 'available-2' })
const declared = atom({ plugin: 'skill-usage', key: 'declared' } as const, null, { shape: 'declared-1' })
// `all-time-2`: Ticket 076 added totals by project and the earlier versions' holds.
const allTime = atom({ plugin: 'skill-usage', key: 'allTime' } as const, null, { shape: 'all-time-2' })
const project = atom({ plugin: 'skill-usage', key: 'project' } as const, null)
const allProject = atom({ plugin: 'skill-usage', key: 'allProject' } as const, null)
const tab = atom({ plugin: 'skill-usage', key: 'tab' } as const, 'session')
const lastError = atom({ plugin: 'skill-usage', key: 'lastError' } as const, null)
const preview = atom({ plugin: 'skill-usage', key: 'preview' } as const, null)

type Stored = { t: number; summary: SessionSummary }

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    await $.command.register({ name: 'skill-usage', description: 'Skill usage pane; `/skill-usage preview` plays every animation, `/skill-usage report` prints the all-time report' })
    try {
      await claimSession($)
      await knownSkills($, true)
      await readRegistry($)
      await backfill($)
      showStatus($, await liveSummary($))
    } catch (error) {
      await noteError($, error)
    }
    void $.ui.open({ id: PANE, title: 'Skill usage' })
    return started
  })

  on('session.append', async ($, e, next) => {
    const appended = await next(e)
    try {
      await observeRow($, e)
    } catch (error) {
      await noteError($, error)
    }
    return appended
  })

  on('turn.complete', async ($, e, next) => {
    // Every hook hears a subagent's turn end too: it settles that subagent's nudges. Only the main loop's is saved.
    try {
      await record($, [{ kind: 'turn-end', t: await $.clock.now(), reason: e.reason, ...(e.agentId ? { agent: e.agentId } : {}) }])
      if (!e.agentId) {
        await persist($, false)
        // Sessions running beside this one store their turns too: reread them, so All time stays current.
        await loadAllTime($, await claimSession($))
      }
    } catch (error) {
      await noteError($, error)
    }
    return next(e)
  })

  on('session.end', async ($, e, next) => {
    try {
      await persist($, true)
    } catch (error) {
      await noteError($, error)
    }
    return next(e)
  })

  on('command.run', { command: 'skill-usage' }, async ($, e) => {
    const arg = e.args.trim()
    if (arg === 'report') return { text: reportText(addSession(await read($, allTime), await liveSummary($)), await read($, available), await read($, declared)) }
    await $.ui.open({ id: PANE, title: 'Skill usage' })
    if (arg === 'preview') {
      // The picture shows the Session tab's map, so the preview switches to it.
      await update($, tab, () => 'session')
      forgetPictures()
      const start = await $.clock.now()
      await update($, preview, () => start)
      return { text: `Playing every animation on the Session tab's picture for about ${Math.round(PREVIEW_MS / 1000)} seconds. Nothing in it is counted.` }
    }
    return { text: 'Skill usage pane opened. `/skill-usage preview` plays every animation; `/skill-usage report` prints the all-time report.' }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    const v: View = { ui: $.ui.resolve(e), surface: e.surface }
    const { Box, Button, Text } = v.ui
    const current = await read($, tab)
    const session = summarize(await read($, events))
    // The project key as kept: a render reads it and never asks the session, which liveSummary does.
    const own = (await read($, project)) || undefined
    const live = mergeSummaries(await read($, baseline), { ...session, ...(own ? { project: own } : {}) })
    const error = await read($, lastError)
    // The Work Map's feed length: enough to follow a turn, short enough to stay under the picture.
    const rows = 16
    const tabs: [Tab, string][] = [['session', 'Session'], ['all', 'All time'], ['unused', 'Unused']]
    const now = await $.clock.now()
    const body =
      current === 'session' ? sessionTab(v, live, session.timeline, rows, now, await read($, preview))
      : current === 'all' ? allTimeTab(v, addSession(await read($, allTime), live), rows, { shown: await read($, allProject), ...(own ? { own } : {}), choose: key => update($, allProject, () => key) }, await read($, declared))
      : unusedTab(v, addSession(await read($, allTime), live), await read($, available))

    return (
      <Box flexDirection="column" gap={1} paddingX={1}>
        <Box gap={1}>
          {tabs.map(([id, label]) => (
            <Button key={`tab-${id}`} label={label} variant={current === id ? 'primary' : 'secondary'} onPress={() => (forgetPictures(), update($, tab, () => id))} />
          ))}
        </Box>
        {error && (
          <Box borderStyle="round" borderColor="#E5735F" paddingX={1}>
            <Text color="#E5735F" wrap="truncate-end">Observer error: {error}</Text>
          </Box>
        )}
        {/* Inside the pane's padding, and no wider than the picture, so each row's columns stay together. */}
        <Box flexDirection="column" width={Math.min(e.props.bodyColumns - 2, PANE_COLUMNS)}>
          {body}
        </Box>
      </Box>
    )
  })
}

/**
 * The skills the session lists for the model, read once and kept. Reading the
 * listing needs a bound session, so only `refresh` callers (session start, a
 * prompt) try again when it was not available yet.
 */
async function knownSkills($: Dollar, refresh = false): Promise<string[]> {
  const kept = await read($, available)
  if (kept || !refresh) return kept?.names ?? []
  const usage = await $.session.usage({ breakdown: 'summary' })
  const skills = usage.context.breakdown?.skills
  if (!skills) return []
  const list: Available = {
    names: skills.skillFrontmatter.map(s => short(s.name)),
    own: skills.skillFrontmatter.filter(s => OWN_SOURCES.has(s.source)).map(s => short(s.name)),
    total: skills.totalSkills,
    included: skills.includedSkills,
  }
  await update($, available, () => list)
  return list.names
}

/**
 * Reads the references the installed GOATED registry declares, once per session start, so a registry edited since
 * shows in the next session: the registry the adapter reads by default, `<goated-root>/stack/goated-stack.yaml`, three
 * folders above the mod's own. A missing or unreadable file, an expected state for a mod installed without GOATED, or
 * one that is no registry, leaves none, and the pane shows reads as it would without the registry.
 */
async function readRegistry($: Dollar) {
  const text = await $.fs.read(`${$.plugin.root}/${REGISTRY_FROM_MOD}`).catch(() => '')
  await update($, declared, () => declaredReferences(text))
}

/**
 * Makes sure the kept events belong to the running session. Another id means
 * `/clear` started a new session (session.start does not run for it): the old
 * one is saved as finished and the events start over. Fresh state for an id
 * the store already has means a resume: what was stored becomes the baseline.
 */
async function claimSession($: Dollar): Promise<string> {
  const id = await $.session.id()
  const held = await read($, owner)
  if (held === id) return id
  if (held !== null) {
    await save($, held, true)
    await update($, events, () => [])
  }
  const stored = (await $.store.get(SESSION_KEY + id)) as Stored | undefined
  await update($, baseline, () => (stored ? closeOpen(stored.summary) : null))
  await update($, owner, () => id)
  await loadAllTime($, id)
  return id
}

/**
 * Once per session, rebuilds the events from the session's history, so a mod
 * that loaded mid-session (a hot reload, an install) shows what came before.
 * History covers what was observed live too, so it replaces the events. A
 * resumed session the store already has keeps a stored baseline instead: what
 * the store holds now, which, when a shape bump dropped the events, includes
 * the stretch since the resume that the dropped events covered. Runs from
 * session.start alone: after `/clear` the new session is observed from its
 * first row.
 */
async function backfill($: Dollar) {
  const id = await $.session.id()
  if ((await read($, backfilled)) === id) return
  await update($, backfilled, () => id)
  if (await read($, baseline)) {
    const stored = (await $.store.get(SESSION_KEY + id)) as Stored | undefined
    if (stored) await update($, baseline, () => closeOpen(stored.summary))
    return
  }
  const history = (await $.session.messages({ as: 'api' })) as HistoryMessage[]
  const rebuilt = historyEvents(history, await knownSkills($), await $.clock.now())
  await update($, events, () => rebuilt.slice(-MAX_EVENTS))
}

/**
 * All-time totals from every other stored session and the older sessions'
 * total. Past the cap, the oldest sessions fold into that total: it is stored
 * before their keys are removed, so a failure between the two can count a
 * session twice but never lose one. Two sessions folding at the same moment
 * can count the same session twice too.
 */
async function loadAllTime($: Dollar, id: string) {
  await $.store.delete(LEGACY_STORE_KEY)
  const keys = (await $.store.keys()).filter(k => k.startsWith(SESSION_KEY))
  const sessions: [string, Stored][] = []
  for (const key of keys) {
    const value = (await $.store.get(key)) as Stored | undefined
    if (value) sessions.push([key, value])
  }
  const older = ((await $.store.get(OLDER_KEY)) as AllTime | undefined) ?? null
  const result = allTimeOf(sessions, older, MAX_SESSIONS, SESSION_KEY + id)
  if (result.folded.length > 0) {
    await $.store.set(OLDER_KEY, result.older)
    for (const key of result.folded) await $.store.delete(key)
  }
  // Every write redraws the pane: rewrite only what changed, as most turns change no other session.
  if (JSON.stringify(await read($, allTime)) !== JSON.stringify(result.total)) await update($, allTime, () => result.total)
}

/** This session so far: the stored baseline plus what was observed since, with its project key when it has one. */
async function liveSummary($: Dollar, isFinal = false): Promise<SessionSummary> {
  const { timeline: _, ...summary } = summarize(await read($, events), isFinal)
  const key = await projectOf($)
  return mergeSummaries(await read($, baseline), { ...summary, ...(key ? { project: key } : {}) })
}

/**
 * This session's project key, worked out once and kept: `''` in the state when no folder could be read, so the session
 * is stored with no project rather than not at all, and the lookups are not tried at every row. Only the key is kept,
 * never the folder.
 */
async function projectOf($: Dollar): Promise<string | undefined> {
  const kept = await read($, project)
  if (kept !== null) return kept || undefined
  const folder = await projectFolder($)
  const key = folder === undefined ? '' : await projectKey(folder, await installSalt($))
  await update($, project, () => key)
  return key || undefined
}

/**
 * The project folder: the repository's root, the main working tree's for a worktree, so a repository's worktrees count
 * as one project; outside a repository, or when that lookup fails, the session's project root; undefined when that
 * fails too. A project key is a label on the summary, so a failed lookup leaves the session unlabelled, not unstored.
 */
async function projectFolder($: Dollar): Promise<string | undefined> {
  try {
    const repo = await $.session.repo()
    if (repo) return repo.root
  } catch {
    // No repository answer: the session root stands in below.
  }
  try {
    return await $.session.root()
  } catch {
    return undefined
  }
}

/**
 * The install's salt for project keys, kept in the store so a project keeps its key across sessions; made on first
 * use. Two sessions making it at the same moment each read back the one written last, though one may already have
 * used its own for its key.
 */
async function installSalt($: Dollar): Promise<string> {
  const kept = await $.store.get(SALT_KEY)
  if (typeof kept === 'string') return kept
  await $.store.set(SALT_KEY, newSalt())
  return String(await $.store.get(SALT_KEY))
}

async function persist($: Dollar, isFinal: boolean) {
  await save($, await claimSession($), isFinal)
}

/** Stores a session's summary; a session with no prompt or skill load is not one worth counting. */
async function save($: Dollar, id: string, isFinal: boolean) {
  const list = await read($, events)
  const prior = await read($, baseline)
  if (!prior && !list.some(ev => ev.kind === 'prompt' || ev.kind === 'load')) return
  await $.store.set(SESSION_KEY + id, { t: await $.clock.now(), summary: await liveSummary($, isFinal) } satisfies Stored)
  // Every write redraws the pane, and a redraw reloads the picture: clear only what is set.
  if ((await read($, lastError)) !== null) await update($, lastError, () => null)
}

async function record($: Dollar, add: UsageEvent[]) {
  if (add.length === 0) return
  await claimSession($)
  await update($, events, old => [...old, ...add].slice(-MAX_EVENTS))
  showStatus($, await liveSummary($))
}

function showStatus($: Dollar, s: SessionSummary) {
  $.ui.status(statusText(s))
}

async function noteError($: Dollar, error: unknown) {
  await update($, lastError, () => errorText(error))
}

/**
 * Records one conversation row's events. Rows come in conversation order, so
 * a prompt always precedes the rows of its turn; a prompt typed mid-turn is
 * folded into the running turn by another door and starts nothing.
 */
async function observeRow($: Dollar, e: SessionAppendInput) {
  if (!isObservedRow(e)) return
  const kept = await read($, events)
  const isPrompt = e.door === 'prompt' || e.door === 'command'
  let lastBoundary: 'response' | 'results' | undefined
  for (let i = kept.length - 1; i >= 0 && !lastBoundary; i--) {
    const kind = kept[i]?.kind
    if (kind === 'response' || kind === 'results') lastBoundary = kind
  }
  const seen = { lastKind: kept.at(-1)?.kind, lastBoundary }
  await record($, rowEvents(e, await knownSkills($, isPrompt), await $.clock.now(), seen))
}
