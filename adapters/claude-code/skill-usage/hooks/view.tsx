// The pane's drawing and the report's words: one function per tab, from plain
// data to an element tree, and the markdown report. No engine calls here;
// register.tsx reads the state and passes it in.
//
// Laid out the way the Work Map mod (lot-map) is: one picture, one line that
// says where things stand, then a feed with one row per event, newest first.
// Colour carries meaning and nothing else: green for what succeeded, pale green
// for a nudge declined with a reason, amber for a nudge still waiting, red for a
// nudge not followed. Text colours are theme
// keys, so the rows read on a light theme too; the picture carries its own
// dark palette with rules that repaint it on a light surface.

import type { ElementTable, RenderSurface } from 'claude-code'

import type { AllTime, Available, Counts, Measures, Origin, Outcome, Refs, RouteForm, SessionSummary, TimelineEntry } from '../types'
import { ANY_SPECIALIST, NO_SUBAGENTS, ORIGINS, OUTCOMES, ROUTE_LINE, total } from './classify'

/** Where a drawing goes: the surface's elements and its name. */
export type View = { ui: ElementTable<RenderSurface>; surface: RenderSurface }

// ---------- words -----------------------------------------------------------------

/** The map's stations: who caused a skill to load. Short enough to sit under a node. */
const STATION: Record<Origin, string> = {
  'user-slash': 'Your /cmd',
  'user-named': 'You asked',
  'hook-nudged': 'Hooks',
  'router-routed': 'Router',
  'self-initiated': 'Agent',
  subagent: 'Subagents',
}
/** Why a skill loaded, as the feed says it. */
const BECAUSE: Record<Origin, string> = {
  'user-slash': 'you typed it',
  'user-named': 'you asked for it',
  'hook-nudged': 'after a hook',
  'router-routed': 'router picked it',
  'self-initiated': 'the agent chose it',
  subagent: 'a subagent chose it',
}
/** The GOATED hooks by what they do, not by their internal labels: the adapter's gates first, then earlier hand-written hooks. */
const HOOK: Record<string, string> = {
  'router-first': 'router-first hold',
  'route-line': 'route-line hold',
  pipeline: 'pipeline hold',
  'router-rule': 'GOATED router rule',
  'route-hold': 'route check',
  'design-hold': 'design check',
  design: 'design tip',
  'design-new-file': 'new-file tip',
  'security-hold': 'security check',
  security: 'security tip',
  'commit-hold': 'commit check',
  'pr-hold': 'PR check',
  'spawn-hold': 'spawn brief check',
  'merge-conflict': 'merge conflict',
  diagnose: 'repeated failure',
  closeout: 'closeout check',
}
const hookName = (hook: string) => HOOK[hook] ?? hook
/** What became of one skill a hook asked for. */
const RESULT: Record<Outcome, string> = {
  followed: 'loaded',
  'read files': 'files read',
  'already loaded': 'already loaded',
  declined: 'declined',
  ignored: 'not loaded',
  pending: 'waiting',
}
const skillName = (skill: string) => (skill === ANY_SPECIALIST ? 'a specialist skill' : skill === ROUTE_LINE ? 'a route line' : skill)
/** A route line's form, as the pane counts it. */
const ROUTE_FORM: Record<RouteForm, string> = { direct: 'direct', continue: 'continue', route: 'routed' }
const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

// ---------- meaning ---------------------------------------------------------------

/**
 * How a piece of the pane reads: plain, dim, one of the three meanings, a
 * decline (`declined`, a paler green: handled, by saying why the skill does not
 * apply), or a reference read (`read`), in the picture's pink.
 */
type Meaning = 'good' | 'waiting' | 'bad'
type Tone = 'plain' | 'dim' | Meaning | 'declined' | 'read'
/** A paler green than success, readable on a light or a dark theme; no theme key is one. */
export const DECLINED_COLOR = '#8fcfa8'
/**
 * Theme keys, so the meanings follow the person's theme: green, amber, red. No
 * theme key is pink or pale green, so reference reads and declines take fixed
 * colours between the picture's dark and light ones, readable on either.
 */
const COLOR: Record<Tone, string | undefined> = { plain: undefined, dim: undefined, good: 'success', waiting: 'warning', bad: 'error', declined: DECLINED_COLOR, read: '#e0679b' }
const OUTCOME_TONE: Record<Outcome, Meaning | 'declined'> = { followed: 'good', 'read files': 'good', 'already loaded': 'good', declined: 'declined', ignored: 'bad', pending: 'waiting' }
/** Outcomes that count as handled: the skill acted on, or declined with a reason. */
const isHandled = (o: Outcome) => OUTCOME_TONE[o] === 'good' || o === 'declined'

/** What the agent handled (acted on or declined), of the nudges that are settled; `declined`: how many of those were declines. */
export function followCounts(c: Counts<Outcome>): { acted: number; settled: number; pending: number; declined: number } {
  const declined = c.declined ?? 0
  const acted = (c.followed ?? 0) + (c['read files'] ?? 0) + (c['already loaded'] ?? 0) + declined
  return { acted, settled: acted + (c.ignored ?? 0), pending: c.pending ?? 0, declined }
}

/** A follow rate's meaning: green from 80%, amber from 40%, red below. */
const rateTone = (acted: number, settled: number): 'dim' | Meaning => (settled === 0 ? 'dim' : acted / settled >= 0.8 ? 'good' : acted / settled >= 0.4 ? 'waiting' : 'bad')

// ---------- picture ---------------------------------------------------------------

// The Work Map's palettes, so the two panes sit together, plus a blue for skills loading, the three meanings,
// a rose pink for reference reads, and `mist`, a light grey for small words that must read against the ground.
// Each moving part has its own hue, so a load (blue) never reads as a nudge (amber) or a reference read (pink).
const DARK = { ground: '#0a0c11', raised: '#12151c', line: '#272c36', spoke: '#1a1e27', bone: '#ebe6dc', ash: '#9ba1ab', dim: '#6b7280', accent: '#e1ac6e', hot: '#f0c595', red: '#e8654f', green: '#5fcf8f', mint: '#b2e6c6', amber: '#ffa62b', load: '#6cb6ff', read: '#f07aa8', mist: '#cfd4dc' }
const LIGHT: typeof DARK = { ground: '#f5f2ea', raised: '#ffffff', line: '#cfc9bc', spoke: '#e3ded2', bone: '#1f2228', ash: '#5f6570', dim: '#8b909a', accent: '#b8762a', hot: '#8f560f', red: '#c5402b', green: '#23824f', mint: '#5fa97e', amber: '#b86b00', load: '#2a6fc9', read: '#c2457a', mist: '#3f454e' }
/** Repaints the dark picture where the surface around it is light; a surface that drops the rules keeps the dark one. */
const LIGHT_RULES = `<style>@media (prefers-color-scheme: light){${(Object.keys(DARK) as (keyof typeof DARK)[])
  .map(k => `[fill="${DARK[k]}"]{fill:${LIGHT[k]}}[stroke="${DARK[k]}"]{stroke:${LIGHT[k]}}`)
  .join('')}}</style>`
const PICTURE_TONE: Record<Meaning, string> = { good: DARK.green, waiting: DARK.amber, bad: DARK.red }
/** Each coloured tone in the picture's palette, for the small rings in the tables. */
const TONE_HEX: Partial<Record<Tone, string>> = { ...PICTURE_TONE, declined: DARK.mint, read: DARK.read }

const W = 420, H = 372, CX = 210, CY = 180, RX = 150, RY = 132, NODE = 21, CORE = 40
const FONT = 'font-family="SF Mono, ui-monospace, Menlo, Consolas, monospace"'
/** The longest file name shown beside the References station; a longer one is cut to an ellipsis. */
const LABEL_CHARS = 22
const RIM = `paint-order="stroke" stroke="${DARK.ground}" stroke-width="3.5" stroke-linejoin="round"`

/**
 * How long each part of a moment takes, slow enough to follow by eye: one leg
 * of a dot's flight, the ripple at SKILLS, the ring easing to its new share, a
 * settled trail fading. Moments queue one after another with `GAP_MS` between,
 * and one that would wait more than `MAX_WAIT_MS` is skipped, so a burst of
 * events never builds a backlog that plays long after the fact.
 */
const LEG_MS = 1000
const RIPPLE_MS = 1400
/** A moment's slot runs this long past its last arrival, so the arrival is seen before the next moment moves. */
const LAND_MS = 800
/** The ring just outside a node that shows what it received: held this long in that colour, then fading this slowly. */
const ARRIVE_HOLD_MS = 1400
const ARRIVE_FADE_MS = 3000
/** How far outside a node's border its arrival ring sits, clear of the border's own ring. */
const ARRIVE_GAP = 4
/** How far a ripple spreads past where it starts, in the picture's units. */
const RIPPLE_GROW = 26
/** Once spread, a ripple lingers at its widest and fades this slowly, so it can be seen after it lands; the next moment does not wait for it. */
const RIPPLE_FADE_MS = 3000
const EASE_MS = 900
/** A settled trail holds in its result's colour long enough to read, then fades. */
const TRAIL_HOLD_MS = 6000
const TRAIL_FADE_MS = 2000
const GAP_MS = 450
const MAX_WAIT_MS = 12_000
/**
 * Each moment waits at least this long after it happened before it moves. The
 * desktop appears to show a new picture a second time a moment after it is
 * drawn, which restarts the picture's clock; a moment already moving would
 * visibly jump back, while one that has not started yet loses nothing. That
 * second showing was seen landing around half a second after the redraw, and
 * a moment is recorded slightly before its redraw, so the lead-in keeps a margin.
 */
const LEAD_MS = 1000
/** One breath of the waiting badge. */
const BREATH_MS = 1800
/** One breath of an agent's border while a nudge to it holds: quicker than the badge's, to read as a decision under way. */
const HOLD_BREATH_MS = 1100

// Small stroke icons, drawn around (0, 0).
const ICON: Record<Origin, string> = {
  'user-slash': 'M-3.5 6 L3.5 -6',
  'user-named': 'M-7 -5 h14 v9 h-8 l-4 4 v-4 h-2 z',
  'hook-nudged': 'M2 -7.5 a1.8 1.8 0 1 0 0.01 0 M2 -4 v6 a4 4 0 0 1 -8 0 v-1',
  'router-routed': 'M0 -7 L7 0 L0 7 L-7 0 Z M-3 0 h6 M1 -2 l2 2 l-2 2',
  'self-initiated': 'M0 -7 Q1 -1 7 0 Q1 1 0 7 Q-1 1 -7 0 Q-1 -1 0 -7 Z',
  subagent: 'M-4 -4 v8 M-4 1 q0 -5 8 -5 M-4 -5.5 a1.6 1.6 0 1 0 0.01 0 M-4 5.5 a1.6 1.6 0 1 0 0.01 0 M5.5 -4 a1.6 1.6 0 1 0 0.01 0',
}
/** An open book, for the References node. */
const BOOK = 'M0 -3.5 Q-2.5 -5 -6 -4.5 v8 Q-2.5 3 0 4.5 Q2.5 3 6 3.5 v-8 Q2.5 -5 0 -3.5 Z M0 -3.5 v8'
/** A page with its corner folded, as a reference read flies it. */
const PAGE = 'M-3.5 -4.5 h4.5 l2.5 2.5 v6.5 h-7 z'

type Point = { x: number; y: number }
const n1 = (v: number) => (Math.round(v * 10) / 10).toString()
const escapeXml = (s: string) => s.replace(/[<>&"]/g, ch => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' })[ch] ?? ch)
/** A moment on the drawing's own clock, which starts at zero each time it is drawn; a past moment is negative. */
const at = (ms: number) => `${(ms / 1000).toFixed(3)}s`
/** A node on the map: where it sits and its radius. */
type MapNode = { p: Point; r: number }
/** Each node on the map: a station a load can come from, or References, where reference reads come from. */
type Spot = Origin | 'references'
/** The stations on the ring, clockwise from the top. */
const RING: readonly Spot[] = ['user-slash', 'user-named', 'hook-nudged', 'references', 'self-initiated', 'router-routed']
/**
 * Subagents: a small node just below Agent, which starts each subagent, joined
 * to it by a thin line. A hook, a skill load or a reference read reaches a
 * subagent directly, not through Agent, so its own lines run straight to it.
 * Placed clear of Agent's label and of the ways from Hooks and References to Agent.
 */
const SUBAGENTS: MapNode = { p: { x: 126, y: 304 }, r: 14 }
function nodeOf(spot: Spot): MapNode {
  if (spot === 'subagent') return SUBAGENTS
  const a = (RING.indexOf(spot) * 2 * Math.PI) / RING.length
  return { p: { x: CX + RX * Math.sin(a), y: CY - RY * Math.cos(a) }, r: NODE }
}
/** Where a straight line from `from` to `to` meets the circle of radius `r` around `from`. */
function edge(from: Point, to: Point, r: number): Point {
  const len = Math.hypot(to.x - from.x, to.y - from.y) || 1
  return { x: from.x + ((to.x - from.x) * r) / len, y: from.y + ((to.y - from.y) * r) / len }
}

/** A dot's way between two nodes' rims: straight, or bowed around the core when the straight line would cross it. */
type Path = { a: Point; b: Point; via?: Point }

function between(fromNode: MapNode, toNode: MapNode): Path {
  const from = fromNode.p, to = toNode.p
  const dx = to.x - from.x, dy = to.y - from.y
  const len = Math.hypot(dx, dy) || 1
  // How close the straight line comes to the core's centre.
  const k = Math.max(0, Math.min(1, ((CX - from.x) * dx + (CY - from.y) * dy) / (len * len)))
  const gap = Math.hypot(from.x + k * dx - CX, from.y + k * dy - CY)
  if (gap > CORE + 16) return { a: edge(from, to, fromNode.r), b: edge(to, from, toNode.r) }
  // A quadratic curve peaks halfway to its control point, so a control point 130 out puts the curve's peak about 65 from the core's centre.
  const via = { x: CX + (-dy / len) * 130, y: CY + (dx / len) * 130 }
  return { a: edge(from, via, fromNode.r), b: edge(to, via, toNode.r), via }
}

const pathD = ({ a, b, via }: Path) =>
  via ? `M${n1(a.x)} ${n1(a.y)} Q${n1(via.x)} ${n1(via.y)} ${n1(b.x)} ${n1(b.y)}` : `M${n1(a.x)} ${n1(a.y)} L${n1(b.x)} ${n1(b.y)}`

/** A dot that travels along `path`, starting `begin` ms from now on the drawing's clock (negative: already under way). */
function pulse(path: Path, color: string, begin: number): string {
  const timing = `begin="${at(begin)}" dur="${at(LEG_MS)}" fill="freeze"`
  return (
    `<circle r="3.8" fill="${color}" opacity="0">` +
    `<animateMotion path="${pathD(path)}" ${timing}/>` +
    `<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.1;.88;1" ${timing}/></circle>`
  )
}

/** A page that flies along `path` as `pulse`'s dot does, filled pink and edged in `outline`. */
function page(path: Path, outline: string, begin: number): string {
  const timing = `begin="${at(begin)}" dur="${at(LEG_MS)}" fill="freeze"`
  return (
    `<g class="ref-page" opacity="0">` +
    `<animateMotion path="${pathD(path)}" ${timing}/>` +
    `<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.1;.88;1" ${timing}/>` +
    `<path d="${PAGE}" fill="${DARK.read}" stroke="${outline}" stroke-width="1.3" stroke-linejoin="round"/></g>`
  )
}

/**
 * The read file's base name beside the References station: shown as its page
 * leaves (`begin`), held while it flies and the reader's ring holds, then fading
 * with that ring. `cutAt`: when the next page leaves, so two names never sit on each other.
 */
function refLabel(file: string, begin: number, cutAt?: number): string {
  const base = file.split('/').pop() ?? file
  const name = base.length > LABEL_CHARS ? `${base.slice(0, LABEL_CHARS - 1)}…` : base
  const total = LEG_MS + ARRIVE_HOLD_MS + ARRIVE_FADE_MS
  const shown = (0.1 * LEG_MS) / total
  const held = (LEG_MS + ARRIVE_HOLD_MS) / total
  const { p, r } = nodeOf('references')
  return (
    `<text class="ref-label" x="${n1(p.x + r + 5)}" y="${n1(p.y + 3)}" ${FONT} font-size="9" ${RIM} fill="${DARK.read}" opacity="0">${escapeXml(name)}` +
    `<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;${shown.toFixed(3)};${held.toFixed(3)};1" begin="${at(begin)}" dur="${at(total)}" fill="freeze"/>` +
    (cutAt === undefined ? '' : `<set attributeName="opacity" to="0" begin="${at(cutAt)}" fill="freeze"/>`) +
    `</text>`
  )
}

/**
 * The ring just outside a node's border that shows what it received, in that
 * colour: lit from `begin` (ms from now), held, then fading slowly. Drawn as it
 * stands, animating only what is to come; `isStill` draws it with nothing moving.
 * A node's own border ring stays free for what still holds there.
 */
function arrival({ p, r }: MapNode, color: string, begin: number, isStill = false): string {
  const whole = ARRIVE_HOLD_MS + ARRIVE_FADE_MS
  const since = -begin
  if (since >= whole) return ''
  const lit = since < 0 ? 0 : since <= ARRIVE_HOLD_MS ? 1 : 1 - (since - ARRIVE_HOLD_MS) / ARRIVE_FADE_MS
  const ring = `class="arrival" cx="${n1(p.x)}" cy="${n1(p.y)}" r="${r + ARRIVE_GAP}" fill="none" stroke="${color}" stroke-width="2" opacity="${n1(lit)}"`
  if (isStill) return lit > 0 ? `<circle ${ring}/>` : ''
  return `<circle ${ring}><animate attributeName="opacity" values="1;1;0" keyTimes="0;${(ARRIVE_HOLD_MS / whole).toFixed(3)};1" begin="${at(begin)}" dur="${at(whole)}" fill="freeze"/></circle>`
}

/** A ring that spreads from `p` and fades, starting `begin` ms from now. */
function ripple(p: Point, r: number, color: string, begin: number): string {
  const timing = `begin="${at(begin)}" dur="${at(RIPPLE_MS + RIPPLE_FADE_MS)}" fill="freeze"`
  // Where the spreading ends and the slow fade begins, as a share of the whole.
  const spread = (RIPPLE_MS / (RIPPLE_MS + RIPPLE_FADE_MS)).toFixed(3)
  const wide = r + RIPPLE_GROW
  return (
    `<circle cx="${n1(p.x)}" cy="${n1(p.y)}" r="${r}" fill="none" stroke="${color}" stroke-width="2.4" opacity="0">` +
    // Spreads fast and eases to its widest, then holds there while it fades slowly away.
    `<animate attributeName="r" values="${r};${wide};${wide}" keyTimes="0;${spread};1" calcMode="spline" keySplines=".2 .6 .4 1;0 0 1 1" ${timing}/>` +
    `<animate attributeName="opacity" values=".95;.75;0" keyTimes="0;${spread};1" calcMode="spline" keySplines="0 0 1 1;.4 0 .6 1" ${timing}/></circle>`
  )
}

/** A dotted line, as the way a nudge or a page took is drawn. */
const DOTTED = 'fill="none" stroke-width="1.4" stroke-linecap="round" stroke-dasharray="1.5 4.5"'

/**
 * The dotted way a reference read's page took, in `color`: fading in behind the
 * page as it flies from `begin` (ms from now), holding while the reader's ring
 * holds, then fading out. Drawn as it stands, animating only what is to come,
 * like `trail`; `isStill` draws the same line with nothing moving.
 */
function readTrail(path: Path, color: string, begin: number, isStill = false): string {
  const landed = LEG_MS + ARRIVE_HOLD_MS
  const whole = landed + TRAIL_FADE_MS
  const since = -begin
  if (since >= whole) return ''
  const shown = since <= 0 ? 0 : since < LEG_MS ? (0.6 * since) / LEG_MS : since < landed ? 0.6 : 0.6 * (1 - (since - landed) / TRAIL_FADE_MS)
  const line = `class="ref-trail" d="${pathD(path)}" ${DOTTED} stroke="${color}" opacity="${n1(shown)}"`
  if (isStill) return shown > 0 ? `<path ${line}/>` : ''
  const k = (ms: number) => (ms / whole).toFixed(3)
  return `<path ${line}><animate attributeName="opacity" values="0;.6;.6;0" keyTimes="0;${k(LEG_MS)};${k(landed)};1" begin="${at(begin)}" dur="${at(whole)}" fill="freeze"/></path>`
}

/**
 * The dotted way a nudge took from Hooks to its agent, in amber while it waits.
 * `appear`: when its dot sets off, so the trail fades in behind the dot.
 * `settle`: when its result sets off back to Hooks, so the amber gives way to
 * that colour behind the result's dot, which holds, then fades out.
 * Times are ms from now. Each path is drawn as it stands now and animates only
 * what is still to come: a frame shows the right line from its first paint
 * instead of relying on an old animation replaying, and `isStill` draws the
 * very same lines with nothing moving, for the copy under the frame.
 */
function trail(path: Path, opts: { appear?: number; settle?: { begin: number; color: string }; fadeOut?: number }, isStill = false): string {
  const dots = `d="${pathD(path)}" ${DOTTED}`
  const { appear, settle } = opts
  const isSettled = settle !== undefined && settle.begin <= -LEG_MS
  let out = ''
  // Amber while it waits: hidden before its dot sets off, fading in behind it, then standing.
  if (!isSettled) {
    let shown = appear === undefined || appear <= -LEG_MS ? 0.6 : appear >= 0 ? 0 : (0.6 * -appear) / LEG_MS
    // Set aside at your next message while still waiting: it fades out, and the badge alone counts it.
    const { fadeOut } = opts
    if (fadeOut !== undefined && fadeOut < 0) shown *= Math.max(0, 1 - -fadeOut / TRAIL_FADE_MS)
    // The result's dot under way: the amber gives way behind it.
    if (settle && settle.begin < 0) shown *= 1 - -settle.begin / LEG_MS
    let anims = ''
    if (!isStill && appear !== undefined && appear > -LEG_MS) anims += `<animate attributeName="opacity" values="0;.6" begin="${at(appear)}" dur="${at(LEG_MS)}" fill="freeze"/>`
    if (!isStill && settle) anims += `<animate attributeName="opacity" values=".6;0" begin="${at(settle.begin)}" dur="${at(LEG_MS)}" fill="freeze"/>`
    if (!isStill && fadeOut !== undefined && fadeOut > -TRAIL_FADE_MS) {
      anims += `<animate attributeName="opacity" values=".6;0" begin="${at(fadeOut)}" dur="${at(TRAIL_FADE_MS)}" fill="freeze"/>`
    }
    if (anims) out += `<path ${dots} stroke="${DARK.amber}" opacity="${n1(shown)}">${anims}</path>`
    else if (shown > 0) out += `<path ${dots} stroke="${DARK.amber}" opacity="${n1(shown)}"/>`
  }
  // The result's colour is a path of its own rather than a recoloured stroke, so the light theme's rules recolour it too.
  if (settle) {
    const since = -settle.begin
    const total = TRAIL_HOLD_MS + TRAIL_FADE_MS
    if (since >= total) return out
    const shown = since < 0 ? 0 : since < LEG_MS ? (0.7 * since) / LEG_MS : since <= TRAIL_HOLD_MS ? 0.7 : 0.7 * (1 - (since - TRAIL_HOLD_MS) / TRAIL_FADE_MS)
    const k = (ms: number) => (ms / total).toFixed(3)
    const anim = isStill
      ? ''
      : `<animate attributeName="opacity" values="0;.7;.7;0" keyTimes="0;${k(LEG_MS)};${k(TRAIL_HOLD_MS)};1" begin="${at(settle.begin)}" dur="${at(total)}" fill="freeze"/>`
    if (anim) out += `<path ${dots} stroke="${settle.color}" opacity="${n1(shown)}">${anim}</path>`
    else if (shown > 0) out += `<path ${dots} stroke="${settle.color}" opacity="${n1(shown)}"/>`
  }
  return out
}

/**
 * When the turn a nudge was sent in ended, at your next message, if it has: a
 * trail still waiting then is set aside and fades, so a nudge that stays open
 * all session (the router rule) does not hold a line on the picture for hours.
 * A nudge sent before any message (at session start) belongs to the turn your
 * first message begins, so it is set aside at the message after that.
 */
function setAsideAt(timeline: readonly TimelineEntry[], row: number): number | undefined {
  let isInTurn = timeline.slice(0, row).some(e => e.kind === 'prompt')
  for (let i = row + 1; i < timeline.length; i++) {
    const e = timeline[i]
    if (e?.kind !== 'prompt') continue
    if (isInTurn) return e.t
    isInTurn = true
  }
  return undefined
}

/**
 * The border of the agent a nudge spoke to, in the hook's amber: from when the
 * nudge's dot lands (`land`) while it holds, ending when the agent sends its
 * result back to Hooks (`settle`). `release`: when it stopped holding without
 * a result (set aside at your next message), so the amber fades. Times are ms from now; drawn as
 * it stands, animating only what is to come, like `trail`. While it holds,
 * the amber breathes (phased to `now`, so a rebuilt frame carries on in step):
 * the border thickens and brightens and a soft glow swells around it, as a
 * decision still being made; the still copy holds it steady.
 */
function agentBorder({ p, r }: MapNode, o: { land: number; settle?: number; release?: number; now: number }, isStill = false): string {
  const ring = (color: string) => `cx="${n1(p.x)}" cy="${n1(p.y)}" r="${r}" fill="none" stroke="${color}" stroke-width="1.8"`
  let out = ''
  // Amber while it holds.
  let shown = o.land > 0 ? 0 : 1
  let anims = ''
  if (!isStill && o.land > 0) anims += `<set attributeName="opacity" to="1" begin="${at(o.land)}" fill="freeze"/>`
  if (o.settle !== undefined) {
    if (o.settle <= 0) shown = 0
    else if (!isStill) anims += `<set attributeName="opacity" to="0" begin="${at(o.settle)}" fill="freeze"/>`
  } else if (o.release !== undefined) {
    if (o.release <= 0) shown *= Math.max(0, 1 - -o.release / TRAIL_FADE_MS)
    if (!isStill && o.release > -TRAIL_FADE_MS) anims += `<animate attributeName="opacity" values="1;0" begin="${at(o.release)}" dur="${at(TRAIL_FADE_MS)}" fill="freeze"/>`
  }
  if (anims || (shown > 0 && !isStill)) {
    const breath = `begin="${at(-(o.now % HOLD_BREATH_MS || HOLD_BREATH_MS))}" dur="${at(HOLD_BREATH_MS)}" repeatCount="indefinite"`
    out +=
      `<g opacity="${n1(shown)}">${anims}` +
      `<circle cx="${n1(p.x)}" cy="${n1(p.y)}" r="${r + 3}" fill="none" stroke="${DARK.amber}" stroke-width="7" opacity="0"><animate attributeName="opacity" values="0;.35;0" ${breath}/></circle>` +
      `<circle ${ring(DARK.amber)}><animate attributeName="opacity" values=".55;1;.55" ${breath}/><animate attributeName="stroke-width" values="2;4.6;2" ${breath}/></circle></g>`
  } else if (shown > 0) out += `<circle ${ring(DARK.amber)} opacity="${n1(shown)}"/>`
  return out
}

/** Everything the picture says: loads per station, the core's words, the hooks' tallies, and reference reads (`refsUnloaded`: of those, the ones made before their skill loaded). */
/** `spawns`: subagents started, which light Subagents even when none loaded a skill. */
type MapData = { loads: Record<Origin, number>; title: string; subtitle: string; outcomes: Counts<Outcome>; refs: number; refsUnloaded: number; spawns: number }

/**
 * The session's feed and the time it is drawn at, from which the picture plays
 * its moments. `isStill`: draw where things stand (waiting trails included)
 * without playing anything, for the still copy under the animated frame.
 */
type Moments = { now: number; timeline: readonly TimelineEntry[]; isStill?: true }

/**
 * One moment the picture plays, at its slot in the queue: a skill load, a nudge
 * sent (`row`: its feed row), a nudge's skills settling, with how many of
 * them were handled and how many of those were declines, or one of a skill's
 * supporting files read.
 */
type PlayBody =
  | { kind: 'load'; origin: Origin; isSubagent?: true }
  | { kind: 'ref'; file: string; isLoaded: boolean; isSubagent?: true }
  | { kind: 'sent'; row: number }
  | { kind: 'settle'; row: number; acted: number; settled: number; declined: number }
export type Play = { start: number } & PlayBody
/** How many of the latest moments the queue holds: enough for any burst, few enough that an old one never matters. */
const QUEUE_SIZE = 40
/** Each moment's slot: a load and a read are round trips of two legs; a nudge's sending and its result flying back are one leg each. */
const LENGTH: Record<Play['kind'], number> = { load: 2 * LEG_MS + LAND_MS, ref: 2 * LEG_MS + LAND_MS, sent: LEG_MS + LAND_MS, settle: LEG_MS + LAND_MS }

/**
 * The last `QUEUE_SIZE` moments in the order they happened, each given a slot:
 * a lead-in after it happened, or once the one before has finished and a gap
 * has passed, whichever is later. The queue depends on what happened and never
 * on the clock, so every redraw computes the same one: an animation picks up
 * exactly where it was, and an idle redraw never changes the picture's text.
 * Rows rebuilt from history never play.
 */
export function playQueue(timeline: readonly TimelineEntry[]): Play[] {
  const raw: ({ t: number } & PlayBody)[] = []
  timeline.forEach((e, row) => {
    if (e.isEarlier) return
    if (e.kind === 'load') raw.push({ t: e.t, kind: 'load', origin: e.origin, ...(e.isSubagent ? { isSubagent: true as const } : {}) })
    // Each read is its own moment, however close together, so a burst shows as that many pages.
    if (e.kind === 'ref') raw.push({ t: e.t, kind: 'ref', file: e.file, isLoaded: e.isLoaded, ...(e.isSubagent ? { isSubagent: true as const } : {}) })
    if (e.kind !== 'nudge') return
    raw.push({ t: e.t, kind: 'sent', row })
    // Skills that settled at the same moment settle together.
    for (const when of [...new Set(e.skills.flatMap(s => (s.at === undefined ? [] : [s.at])))]) {
      const group = e.skills.filter(s => s.at === when)
      raw.push({ t: when, kind: 'settle', row, acted: group.filter(s => isHandled(s.status)).length, settled: group.length, declined: group.filter(s => s.status === 'declined').length })
    }
  })
  // A stable sort: a nudge's sending stays ahead of a settling at the same moment.
  raw.sort((a, b) => a.t - b.t)
  const plays: Play[] = []
  let free = -Infinity
  for (const { t, ...body } of raw.slice(-QUEUE_SIZE)) {
    const start = Math.max(t + LEAD_MS, free)
    if (start - t > MAX_WAIT_MS) continue
    plays.push({ start, ...body } as Play)
    free = start + LENGTH[body.kind] + GAP_MS
  }
  return plays
}

/** How far apart the preview's moments happen: longer than the longest moment and its gap, so none waits. */
const PREVIEW_STEP_MS = 3300

/**
 * `/skill-usage preview`: one of every moment the picture can play, a step
 * apart from `start`: a load from each station, then a nudge to Agent that is
 * followed (green) and one to Subagents that is not (red); then a nudge to
 * Agent that waits while Agent reads a reference after loading its skill, so
 * the two dotted ways show together, before it is followed; and last a read by
 * a subagent without loading the skill (edged amber). Drawn on the picture
 * only; nothing here is counted or listed.
 */
export function previewTimeline(start: number): TimelineEntry[] {
  const at = (step: number) => start + step * PREVIEW_STEP_MS
  const loads: TimelineEntry[] = (['user-slash', 'user-named', 'router-routed', 'self-initiated', 'subagent', 'hook-nudged'] as const).map((origin, i) => ({
    t: at(i),
    kind: 'load',
    skill: 'preview',
    origin,
  }))
  return [
    ...loads,
    { t: at(6), kind: 'nudge', hook: 'commit-hold', skills: [{ skill: 'commit-message', status: 'followed', at: at(7) }] },
    { t: at(8), kind: 'nudge', hook: 'design-hold', skills: [{ skill: 'software-design-principles', status: 'ignored', at: at(9) }], isSubagent: true },
    { t: at(10), kind: 'nudge', hook: 'pr-hold', skills: [{ skill: 'pr-description', status: 'followed', at: at(12) }] },
    { t: at(11), kind: 'ref', skill: 'software-design-principles', file: 'references/red-flags.md', isLoaded: true },
    { t: at(13), kind: 'ref', skill: 'tdd', file: 'references/mocking.md', isLoaded: false, isSubagent: true },
  ]
}

/** How long a preview lasts: its last moment's round trip, then the longest an arrival ring or a settled trail stays on screen. */
export const PREVIEW_MS = 13 * PREVIEW_STEP_MS + LEAD_MS + 2 * LEG_MS + Math.max(ARRIVE_HOLD_MS + ARRIVE_FADE_MS, TRAIL_HOLD_MS + TRAIL_FADE_MS)

/**
 * Where skill loads came from. A spoke wears thicker the more loads came from
 * its station; the ring around the core fills with the share of settled hook
 * nudges that were followed, in the rate's colour. On Hooks, a red dot counts
 * nudges not followed and an amber badge, breathing, counts those still waiting.
 *
 * With `moments`, what just happened plays on top, one moment at a time in its
 * queue slot (`playQueue`). Whatever a node sends comes back to whoever receives
 * it, and the receiver's outer ring (`arrival`) takes that colour, holds, and
 * fades; its own border ring stays for what still holds there.
 * - A skill load sends a blue dot from the station that caused it to SKILLS,
 *   which ripples, and the skill's text flies on to the agent that loaded it
 *   (Agent, or Subagents), ringing it blue.
 * - A nudge sends an amber dot from Hooks to the agent it spoke to, leaving a
 *   dotted amber trail while it waits, and the agent's border breathes amber
 *   (`agentBorder`). When it settles, the agent sends the result back to Hooks
 *   as a green or red dot, the trail taking that colour behind it, and Hooks'
 *   ring takes it; the core's ring eases to its new share.
 * - A reference read sends a small pink request from its reader to References,
 *   and the page flies back (edged amber when its skill had not loaded),
 *   leaving a dotted pink way, its file's name beside References as it leaves;
 *   the reader's ring turns pink.
 * References counts reads, with an amber badge for those made without loading.
 * Subagents is a small node beside Agent, which starts each one; everything
 * reaches it directly.
 */
function drawMap(d: MapData, moments?: Moments): string {
  const c = DARK
  const f = followCounts(d.outcomes)
  const ignored = d.outcomes.ignored ?? 0
  const core: Point = { x: CX, y: CY }
  const hooks = nodeOf('hook-nudged')
  const hooksAt = hooks.p
  const refs = nodeOf('references')
  const now = moments?.now ?? 0
  let body = `<rect width="${W}" height="${H}" rx="12" fill="${c.ground}"/>`
  for (const [rx, ry] of [[62, 56], [98, 86], [134, 117]]) {
    body += `<ellipse cx="${CX}" cy="${CY}" rx="${rx}" ry="${ry}" fill="none" stroke="${c.line}" stroke-width=".7" opacity=".45" stroke-dasharray="2 5"/>`
  }
  /** A node's spoke to the core: thicker the more traffic (`n`) it carried, and worn in the accent colour once it carried any. */
  const spoke = ({ p, r }: MapNode, n: number, attrs = '') => {
    const a = edge(core, p, CORE + 8)
    const b = edge(p, core, r)
    const worn = Math.min(1, Math.log2(1 + n) / 5)
    const line = `<line${attrs} x1="${n1(a.x)}" y1="${n1(a.y)}" x2="${n1(b.x)}" y2="${n1(b.y)}" stroke-width="${n1(1 + 2.8 * worn)}" stroke-linecap="round"`
    return `${line} stroke="${c.spoke}"/>` + (n > 0 ? `${line} stroke="${c.accent}" opacity="${n1(0.25 + worn * 0.55)}"/>` : '')
  }
  /** A node with its icon, its name and its count beneath, lit once it carried any traffic; a small node's words are smaller. */
  const station = ({ p, r }: MapNode, icon: string, name: string, n: number, isLit = n > 0) => {
    const isSmall = r < NODE
    return (
      `<circle cx="${n1(p.x)}" cy="${n1(p.y)}" r="${r}" fill="${c.raised}" stroke="${isLit ? c.accent : c.line}" stroke-width="1.2"/>` +
      `<path transform="translate(${n1(p.x)} ${n1(p.y)})" d="${icon}" fill="none" stroke="${isLit ? c.hot : c.ash}" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>` +
      `<text x="${n1(p.x)}" y="${n1(p.y + r + (isSmall ? 13 : 15))}" text-anchor="middle" ${FONT} font-size="${isSmall ? 10 : 11.5}" ${RIM} fill="${isLit ? c.bone : c.mist}">${name}</text>` +
      (isLit ? `<text x="${n1(p.x)}" y="${n1(p.y + r + (isSmall ? 26 : 29))}" text-anchor="middle" ${FONT} font-size="10.5" font-weight="700" ${RIM} fill="${c.bone}">${n}</text>` : '')
    )
  }
  let nodes = ''
  for (const spot of [...RING, 'subagent' as const]) {
    const node = nodeOf(spot)
    if (spot === 'subagent') {
      // Lit by a spawn as well as a load, so a subagent that loads no skill still shows; its spawn count on a badge.
      const badge = { x: n1(node.p.x + node.r * 0.8), y: node.p.y - node.r * 0.8 }
      body += spoke(node, d.loads[spot])
      nodes +=
        station(node, ICON[spot], STATION[spot], d.loads[spot], d.loads[spot] > 0 || d.spawns > 0) +
        (d.spawns > 0
          ? `<g class="spawn-badge"><circle cx="${badge.x}" cy="${n1(badge.y)}" r="6.5" fill="${c.load}"/>` +
            `<text x="${badge.x}" y="${n1(badge.y + 3)}" text-anchor="middle" ${FONT} font-size="8.5" font-weight="700" fill="${c.ground}">${d.spawns > 99 ? '99+' : d.spawns}</text></g>`
          : '')
      continue
    }
    if (spot !== 'references') {
      body += spoke(node, d.loads[spot])
      nodes += station(node, ICON[spot], STATION[spot], d.loads[spot])
      continue
    }
    // References counts reads, and reads made before their skill loaded on an amber badge, like the red not-followed one on Hooks.
    const badge = { x: n1(node.p.x - node.r * 0.74), y: node.p.y - node.r * 0.74 }
    body += spoke(node, d.refs, ' class="refs-spoke"')
    nodes +=
      `<g class="refs-node">${station(node, BOOK, 'References', d.refs)}` +
      (d.refsUnloaded > 0
        ? `<circle cx="${badge.x}" cy="${n1(badge.y)}" r="7.5" fill="${c.amber}"/>` +
          `<text x="${badge.x}" y="${n1(badge.y + 3.1)}" text-anchor="middle" ${FONT} font-size="9" font-weight="700" fill="${c.ground}">${d.refsUnloaded > 99 ? '99+' : d.refsUnloaded}</text>`
        : '') +
      `</g>`
  }
  // Agent starts each subagent: a thin line between the two, along which nothing flies.
  {
    const agent = nodeOf('self-initiated')
    const a = edge(agent.p, SUBAGENTS.p, agent.r)
    const b = edge(SUBAGENTS.p, agent.p, SUBAGENTS.r)
    body += `<line class="started-by" x1="${n1(a.x)}" y1="${n1(a.y)}" x2="${n1(b.x)}" y2="${n1(b.y)}" stroke="${c.line}" stroke-width="1.2" stroke-linecap="round"/>`
  }
  // Badges on Hooks: red for not followed, amber breathing for still waiting.
  const corner = NODE * 0.74
  let badges = ''
  if (ignored > 0) {
    badges +=
      `<circle cx="${n1(hooksAt.x - corner)}" cy="${n1(hooksAt.y - corner)}" r="7.5" fill="${c.red}"/>` +
      `<text x="${n1(hooksAt.x - corner)}" y="${n1(hooksAt.y - corner + 3.1)}" text-anchor="middle" ${FONT} font-size="9" font-weight="700" fill="${c.ground}">${ignored > 99 ? '99+' : ignored}</text>`
  }
  if (f.pending > 0) {
    badges +=
      // Phased to the clock, so a rebuilt picture's badge breathes on in step instead of restarting.
      `<g><animate attributeName="opacity" values="1;.4;1" begin="${at(-(now % BREATH_MS || BREATH_MS))}" dur="${at(BREATH_MS)}" repeatCount="indefinite"/>` +
      `<circle cx="${n1(hooksAt.x + corner)}" cy="${n1(hooksAt.y - corner)}" r="8" fill="${c.raised}" stroke="${c.amber}" stroke-width="1.2"/>` +
      `<text x="${n1(hooksAt.x + corner)}" y="${n1(hooksAt.y - corner + 3)}" text-anchor="middle" ${FONT} font-size="8.5" fill="${c.amber}">×${f.pending}</text></g>`
  }

  // What just happened plays over the still picture, in queue order; what still waits holds as a dotted trail under the stations.
  const timeline = moments?.timeline ?? []
  // The still copy plays nothing, but its trails follow the same queue, so it matches the frame drawn over it.
  const queue = moments ? playQueue(timeline) : []
  const plays = moments?.isStill ? [] : queue
  const agentAt = (isSubagent: boolean) => nodeOf(isSubagent ? 'subagent' : 'self-initiated')
  /** A dot's leg between a node's rim and the core's. */
  const toCore = ({ p, r }: MapNode): Path => ({ a: edge(p, core, r), b: edge(core, p, CORE + 8) })
  const fromCore = ({ p, r }: MapNode): Path => ({ a: edge(core, p, CORE + 8), b: edge(p, core, r) })
  // Red if any was not handled, pale green if every one was declined, else green.
  const resultColor = (p: Extract<Play, { kind: 'settle' }>) => (p.acted < p.settled ? c.red : p.declined === p.settled ? c.mint : c.green)
  /** Whoever a load's skill text reaches: the subagent that loaded it, or else Agent. */
  const loaderOf = (p: Extract<Play, { kind: 'load' }>) => agentAt(p.isSubagent === true || p.origin === 'subagent')
  const agentOf = (row: number) => {
    const e = timeline[row]
    return agentAt(e?.kind === 'nudge' && e.isSubagent === true)
  }
  let flights = ''
  let easingActed = 0
  let easingSettled = 0
  let easeStart: number | undefined
  plays.forEach((p, i) => {
    const begin = p.start - now
    if (p.kind === 'ref') {
      // The request goes out, and the page comes back once it lands.
      const reader = agentAt(p.isSubagent === true)
      const next = plays.slice(i + 1).find(q => q.kind === 'ref')
      flights +=
        pulse(between(reader, refs), c.read, begin) +
        page(between(refs, reader), p.isLoaded ? c.read : c.amber, begin + LEG_MS) +
        refLabel(p.file, begin + LEG_MS, next && next.start + LEG_MS - now)
    } else if (p.kind === 'load') {
      // The cause's dot reaches SKILLS, and the skill's text flies on to whoever loaded it.
      const loader = loaderOf(p)
      flights += pulse(toCore(nodeOf(p.origin)), c.load, begin) + ripple(core, CORE + 6, c.load, begin + LEG_MS) + pulse(fromCore(loader), c.load, begin + LEG_MS)
    } else if (p.kind === 'sent') {
      flights += pulse(between(hooks, agentOf(p.row)), c.amber, begin)
    } else {
      flights += pulse(between(agentOf(p.row), hooks), resultColor(p), begin)
    }
  })
  // A settling still easing (or still queued) has not reached the ring yet; the still copy counts it too, to match.
  for (const p of queue) {
    if (p.kind !== 'settle' || now >= p.start + EASE_MS) continue
    easingActed += p.acted
    easingSettled += p.settled
    easeStart = Math.max(easeStart ?? -Infinity, p.start)
  }
  let trails = ''
  let borders = ''
  timeline.forEach((e, row) => {
    if (e.kind !== 'nudge') return
    const isWaiting = e.skills.some(s => s.status === 'pending')
    const sent = queue.find(p => p.kind === 'sent' && p.row === row)
    const settle = [...queue].reverse().find((p): p is Extract<Play, { kind: 'settle' }> => p.kind === 'settle' && p.row === row)
    const isFading = !isWaiting && settle !== undefined && now < settle.start + TRAIL_HOLD_MS + TRAIL_FADE_MS
    if (!isWaiting && !isFading) return
    const aside = isWaiting ? setAsideAt(timeline, row) : undefined
    if (aside !== undefined && now >= aside + TRAIL_FADE_MS) return
    borders += agentBorder(
      agentOf(row),
      {
        land: sent ? sent.start + LEG_MS - now : -Infinity,
        now,
        ...(isFading && settle ? { settle: settle.start - now } : {}),
        ...(aside !== undefined ? { release: aside - now } : {}),
      },
      moments?.isStill,
    )
    trails += trail(
      between(hooks, agentOf(row)),
      {
        ...(sent ? { appear: sent.start - now } : {}),
        ...(isFading && settle ? { settle: { begin: settle.start - now, color: resultColor(settle) } } : {}),
        ...(aside !== undefined ? { fadeOut: aside - now } : {}),
      },
      moments?.isStill,
    )
  })
  // What each node received, on its outer ring, and a page's dotted way: from the same queue in the frame and the still
  // copy, so the two match.
  for (const p of queue) {
    const begin = p.start - now
    if (p.kind === 'ref') {
      const reader = agentAt(p.isSubagent === true)
      trails += readTrail(between(refs, reader), c.read, begin + LEG_MS, moments?.isStill)
      borders += arrival(reader, c.read, begin + 2 * LEG_MS, moments?.isStill)
    } else if (p.kind === 'load') {
      borders += arrival(loaderOf(p), c.load, begin + 2 * LEG_MS, moments?.isStill)
    } else if (p.kind === 'settle') {
      borders += arrival(hooks, resultColor(p), begin + LEG_MS, moments?.isStill)
    }
  }
  body += trails + nodes + borders + badges + flights

  // The core, its ring of nudges followed in the rate's colour, and the share above its name.
  const share = f.settled === 0 ? 0 : Math.round((f.acted / f.settled) * 100)
  const tone = rateTone(f.acted, f.settled)
  const ring = `cx="${CX}" cy="${CY}" r="${CORE + 5}" fill="none" stroke-width="2.4"`
  let fill = ''
  if (f.settled > 0) {
    // Until its settling plays, the ring shows the share before it, then eases to the share now.
    const before = f.settled - easingSettled
    // A preview's settlings are not in the counts, so the share before them is clamped to what the counts allow.
    const from = before <= 0 ? share : Math.min(100, Math.max(0, Math.round(((f.acted - easingActed) / before) * 100)))
    const isEasing = easeStart !== undefined && from !== share
    // Held still, the ring shows the share before until its easing is halfway, then the share now.
    if (moments?.isStill && isEasing && now >= (easeStart ?? now) + EASE_MS / 2) easingActed = easingSettled = 0
    const ease = isEasing && !moments?.isStill ? `<animate attributeName="stroke-dasharray" values="${from} 100;${share} 100" begin="${at((easeStart ?? now) - now)}" dur="${at(EASE_MS)}" fill="freeze"/>` : ''
    fill = `<circle ${ring} stroke="${tone === 'dim' ? c.ash : PICTURE_TONE[tone]}" pathLength="100" stroke-dasharray="${isEasing && easingSettled > 0 ? from : share} 100" stroke-linecap="round" transform="rotate(-90 ${CX} ${CY})">${ease}</circle>`
  }
  body +=
    `<circle cx="${CX}" cy="${CY}" r="${CORE + 8}" fill="${c.accent}" opacity=".08"/>` +
    `<circle cx="${CX}" cy="${CY}" r="${CORE}" fill="${c.raised}" stroke="${c.line}" stroke-width="1.3"/>` +
    `<circle ${ring} stroke="${c.line}" opacity=".7"/>` +
    fill +
    `<text x="${CX}" y="${CY - 19}" text-anchor="middle" ${FONT} font-size="8" fill="${c.mist}">${f.settled > 0 ? `${share}% followed` : '–'}</text>` +
    `<text x="${CX}" y="${CY + 2}" text-anchor="middle" ${FONT} font-size="13" letter-spacing="2" fill="${c.bone}">${escapeXml(d.title)}</text>` +
    `<text x="${CX}" y="${CY + 17}" text-anchor="middle" ${FONT} font-size="9" fill="${c.mist}">${escapeXml(d.subtitle)}</text>`
  // Twice the viewBox, so the picture fills whatever room the pane gives it.
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W * 2}" height="${H * 2}">${LIGHT_RULES}${body}</svg>`
}

/**
 * The last picture drawn under each title, with what it shows (`shows`): the
 * data, the queue of moments, and each nudge's state, but not the time; and
 * when it was drawn. See `picture` for why the same text is handed back.
 */
const lastDrawn = new Map<string, { shows: string; source: string; drawnAt: number }>()

/** Forgets every cached picture, so the next one is drawn at its own time: for a pane about to show another tab. */
export function forgetPictures() {
  lastDrawn.clear()
}

/** When the last of these moments, a settled trail's fade included, has finished: after it the picture is still. */
function quietAt(plays: readonly Play[]): number {
  // A load, a read or a result ends on an arrival ring, whose slow fade outlasts the moment's slot; a nudge's sending stands as its trail.
  const ring = ARRIVE_HOLD_MS + ARRIVE_FADE_MS
  const lingers = { load: 2 * LEG_MS + ring, ref: 2 * LEG_MS + ring, sent: LEG_MS, settle: Math.max(LEG_MS + ring, TRAIL_HOLD_MS + TRAIL_FADE_MS) }
  return Math.max(-Infinity, ...plays.map(p => p.start + lingers[p.kind]))
}

/**
 * The picture's size in CSS pixels, in its proportions. Both layers need a
 * height: the frame given none falls back to a small default and shrinks the
 * drawing into it. A surface narrows a picture wider than its pane but keeps
 * its height, leaving blank bands above and below, so the width is one a
 * docked pane holds without narrowing.
 */
const FRAME_WIDTH = 460
const FRAME_HEIGHT = Math.round((FRAME_WIDTH * H) / W)
/**
 * The widest a tab is laid out, in cells of the surface's code font: about the
 * picture's width, so in a wide pane a row's time, rate or count stays beside
 * its words instead of drifting to the far edge. A narrower pane takes its own width.
 */
export const PANE_COLUMNS = 64

/**
 * The picture, in the surface's sandboxed frame (`isInteractive`), where SMIL
 * animation runs. The desktop rebuilds a pane at every redraw: an image is
 * always replaced, which restarts its clock and makes moving dots jump back,
 * while a frame whose text is unchanged is kept, its clock running on. So the
 * text is rebuilt only when what the picture shows changes; otherwise the
 * last one is handed back as it was. A finished moment stays in the text,
 * invisible, so its ending never forces a rebuild while another dot flies.
 * Once everything in it has finished, the next redraw draws it afresh at that
 * time: a frame mounted again (another tab, a reopened pane) starts its clock
 * at zero and would otherwise replay moments long past.
 */
function picture(v: View, d: MapData, alt: string, moments?: Moments) {
  if (v.surface === 'terminal' || !('Svg' in v.ui)) return null
  const { Svg } = v.ui as ElementTable<'desktop'>
  const plays = moments ? playQueue(moments.timeline) : []
  // Whole nudge rows: their state, their agent and their trail all change the drawing.
  const nudges = moments ? moments.timeline.filter(e => e.kind === 'nudge') : []
  // A waiting trail set aside by your next message changes the drawing too, and is quiet once it has faded.
  const asides = moments
    ? moments.timeline.flatMap((e, row) => (e.kind === 'nudge' && e.skills.some(x => x.status === 'pending') ? [setAsideAt(moments.timeline, row) ?? null] : []))
    : []
  const shows = JSON.stringify([d, plays, nudges, asides])
  const now = moments?.now ?? 0
  const quiet = Math.max(quietAt(plays), ...asides.map(t => (t === null ? -Infinity : t + TRAIL_FADE_MS)))
  let drawn = lastDrawn.get(d.title)
  const isStale = drawn !== undefined && drawn.drawnAt < quiet && now >= quiet
  if (drawn?.shows !== shows || isStale) {
    drawn = { shows, source: drawMap(d, moments), drawnAt: now }
    lastDrawn.set(d.title, drawn)
  }
  // A new frame shows blank while it loads, so a still copy of where things stand sits under it, as a plain image
  // drawn at every redraw: the swap to a new frame shows the copy for that instant instead of a flash.
  const still = drawMap(d, moments && { ...moments, isStill: true })
  const { Box } = v.ui
  return (
    <Box position="relative">
      <Svg source={still} alt={alt} width={FRAME_WIDTH} height={FRAME_HEIGHT} />
      <Box position="absolute" top={0} left={0}>
        <Svg source={drawn.source} alt={alt} isInteractive width={FRAME_WIDTH} height={FRAME_HEIGHT} />
      </Box>
    </Box>
  )
}

// ---------- rows ------------------------------------------------------------------

// Text takes no mono, size or weight props on this build (the test kit refuses them on every surface), so rows line
// up by real columns, not by padding words in a monospaced face.

/** A run of words in one tone, so one line can carry several meanings. */
type Run = { text: string; tone?: Tone }

/** Words in runs, each run in its own tone; `wrap` lets a long line continue below instead of being cut. */
function words(v: View, runs: Run[], tone: Tone, isWrapped: boolean) {
  const { Text } = v.ui
  const paint = (t: Tone) => ({ color: COLOR[t], dimColor: t === 'dim' })
  if (runs.length === 1) return <Text {...paint(runs[0]?.tone ?? tone)} wrap={isWrapped ? 'wrap' : 'truncate-end'}>{runs[0]?.text}</Text>
  return (
    <Text {...paint(tone)} wrap={isWrapped ? 'wrap' : 'truncate-end'}>
      {runs.map(r => (r.tone && r.tone !== tone ? <Text {...paint(r.tone)}>{r.text}</Text> : r.text))}
    </Text>
  )
}

/**
 * One cell of a row: words in runs, or a drawn element such as a meter; a
 * fixed width in cells, or the room left over (`grow`), which wraps rather than cuts.
 */
type Cell = { runs?: Run[]; node?: ReturnType<typeof words>; width?: number; grow?: true; isRight?: true; tone?: Tone; canShrink?: true }
const cell = (text: string, rest: Omit<Cell, 'runs'> = {}): Cell => ({ runs: [{ text }], ...rest })

/** One line of the pane in columns, as the Work Map's feed: a mark, a kind, the words, and a time at the right. */
function row(v: View, cells: Cell[], tone: Tone) {
  const { Box } = v.ui
  return (
    <Box flexDirection="row" gap={1} alignItems="flex-start">
      {cells.map(c =>
        c.grow ? (
          <Box flexGrow={1} flexShrink={1} minWidth={0}>{c.node ?? words(v, c.runs ?? [], c.tone ?? tone, true)}</Box>
        ) : c.canShrink ? (
          // A name column: its full width when there is room, cut short rather than pushing the row past a narrow pane.
          <Box flexShrink={1} width={c.width} minWidth={6}>{c.node ?? words(v, c.runs ?? [], c.tone ?? tone, false)}</Box>
        ) : (
          <Box flexShrink={0} minWidth={c.width ?? 1} justifyContent={c.isRight ? 'flex-end' : 'flex-start'}>{c.node ?? words(v, c.runs ?? [], c.tone ?? tone, false)}</Box>
        ),
      )}
    </Box>
  )
}

function line(v: View, text: string, tone: Tone = 'plain') {
  return words(v, [{ text }], tone, true)
}

function title(v: View, text: string, note?: string) {
  const { Box, Text } = v.ui
  return (
    <Box marginTop={1} flexDirection="row" gap={1}>
      <Text bold>{text}</Text>
      {note && <Text dimColor wrap="truncate-end">{note}</Text>}
    </Box>
  )
}

/** The smallest fill a non-zero part gets, as a share of its bar, so one load in a hundred still shows. */
const MIN_SHARE = 0.03

/**
 * A bar `width` cells long: one solid fill per coloured part, in order from
 * the left, each as wide as its share of `whole` (the parts' sum unless given,
 * so a list can scale every bar to its largest). Dim parts leave empty space,
 * not a grey track. Widths are percentages, so a graphical surface draws them
 * exactly (3% and 14% differ) where the terminal rounds to whole cells.
 */
function meter(v: View, parts: { n: number; tone: Tone }[], width: number, whole?: number) {
  const { Box } = v.ui
  const of = whole ?? parts.reduce((s, p) => s + p.n, 0)
  const pct = parts.map(p => (of > 0 && p.n > 0 ? Math.round(Math.max(MIN_SHARE, p.n / of) * 100) : 0))
  // The minimum a small part keeps comes out of the largest, so the fills never add up past the bar.
  const over = pct.reduce((s, n) => s + n, 0) - 100
  const largest = pct.indexOf(Math.max(...pct))
  if (over > 0) pct[largest] = (pct[largest] ?? 0) - over
  return (
    <Box flexDirection="row" width={width} height={1}>
      {parts.map((p, i) =>
        (pct[i] ?? 0) > 0 && p.tone !== 'dim' && p.tone !== 'plain' ? <Box width={`${pct[i]}%`} height={1} backgroundColor={COLOR[p.tone]} /> : null,
      )}
    </Box>
  )
}

/**
 * A count as a small ring, filled clockwise from the top with each part's
 * share of `whole` (the parts' sum unless given), as the picture's core ring
 * fills, in the picture's colours and repainted on a light theme like it; a
 * bar (`meter`) `width` cells long where the surface draws no vectors.
 */
function dial(v: View, parts: { n: number; tone: Tone }[], width: number, alt: string, whole?: number) {
  if (v.surface === 'terminal' || !('Svg' in v.ui)) return meter(v, parts, width, whole)
  const { Svg } = v.ui as ElementTable<'desktop'>
  const of = whole ?? parts.reduce((sum, p) => sum + p.n, 0)
  const ring = 'cx="8" cy="8" r="5.5" fill="none" stroke-width="3"'
  let from = 0
  let arcs = ''
  for (const p of parts) {
    const hex = TONE_HEX[p.tone]
    if (!hex || of <= 0 || p.n <= 0) continue
    // As on a bar, a small part keeps a sliver, and the parts never wrap past the top.
    const len = Math.min(100 - from, Math.round(Math.max(MIN_SHARE, p.n / of) * 100))
    arcs += `<circle ${ring} stroke="${hex}" pathLength="100" stroke-dasharray="${len} 100" stroke-dashoffset="${-from}" transform="rotate(-90 8 8)"/>`
    from += len
  }
  const source = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16">${LIGHT_RULES}<circle ${ring} stroke="${DARK.line}"/>${arcs}</svg>`
  return <Svg source={source} alt={alt} width={16} height={16} />
}

function clock(t: number): string {
  const d = new Date(t)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const percent = (part: number, whole: number) => (whole === 0 ? '–' : `${Math.round((part / whole) * 100)}%`)

function sumOutcomes(nudges: Record<string, Counts<Outcome>>): Counts<Outcome> {
  const out: Counts<Outcome> = {}
  for (const c of Object.values(nudges)) for (const k of OUTCOMES) out[k] = (out[k] ?? 0) + (c[k] ?? 0)
  return out
}

function byOrigin(loads: Record<string, Counts<Origin>>): Record<Origin, number> {
  const out = Object.fromEntries(ORIGINS.map(o => [o, 0])) as Record<Origin, number>
  for (const c of Object.values(loads)) for (const o of ORIGINS) out[o] += c[o] ?? 0
  return out
}

/** The one line under the picture: where things stand, in words, each count in its meaning's colour. */
function standing(loadCount: number, outcomes: Counts<Outcome>): Run[] {
  const f = followCounts(outcomes)
  const ignored = outcomes.ignored ?? 0
  const runs: Run[] = [{ text: plural(loadCount, 'skill load') }]
  if (f.settled + f.pending === 0) return [...runs, { text: ' · no hook nudges yet', tone: 'dim' }]
  runs.push({ text: ' · hooks: ' }, { text: `${f.acted - f.declined} followed`, tone: 'good' })
  if (f.declined) runs.push({ text: ' · ' }, { text: `${f.declined} declined`, tone: 'declined' })
  if (ignored) runs.push({ text: ' · ' }, { text: `${ignored} not`, tone: 'bad' })
  if (f.pending) runs.push({ text: ' · ' }, { text: `${f.pending} waiting`, tone: 'waiting' })
  return runs
}

/**
 * The status line: the session's skills, its hooks in the pane's words with
 * counts of none left out, and the router rule in a word.
 */
export function statusText(s: SessionSummary): string {
  const f = followCounts(sumOutcomes(s.nudges))
  const hooks = [`${f.acted - f.declined} followed`, ...(f.declined ? [`${f.declined} declined`] : []), ...(f.settled > f.acted ? [`${f.settled - f.acted} not`] : []), ...(f.pending ? [`${f.pending} waiting`] : [])]
  const router = { first: 'router ✓', late: 'router late', never: 'router ✗', off: '' }[s.router]
  return [`skills ${Object.keys(s.loads).length}`, f.settled + f.pending > 0 ? `hooks: ${hooks.join(' · ')}` : '', router].filter(Boolean).join(' · ')
}

const ROUTER_LINE: Record<SessionSummary['router'], [string, Tone]> = {
  first: ['GOATED router rule: router loaded first', 'good'],
  late: ['GOATED router rule: router loaded, but after other tools', 'waiting'],
  never: ['GOATED router rule: router not loaded yet', 'bad'],
  off: ['GOATED router rule: not seen this session', 'dim'],
}

/**
 * A feed row: its mark, kind and words. A nudge reads as one sentence whatever
 * became of it, each skill it named in the colour of its own result, so a row
 * where one skill loaded and another did not shows both.
 */
function feedRow(entry: TimelineEntry): { mark: string; kind: string; runs: Run[]; tone: Tone; reasons?: string[] } {
  switch (entry.kind) {
    case 'prompt':
      return { mark: '›', kind: 'You', runs: [{ text: 'new message' }], tone: 'dim' }
    case 'compact':
      return { mark: '↻', kind: 'Context', runs: [{ text: 'compacted · checks re-armed' }], tone: 'dim' }
    case 'route': {
      const what = entry.form === 'route' ? `${entry.intensity} · requires ${entry.requires.join(', ')}` : entry.form
      return { mark: '⇢', kind: 'Route', runs: [{ text: what }, ...(entry.isSubagent ? [{ text: ' · by a subagent', tone: 'dim' as const }] : [])], tone: 'plain' }
    }
    case 'override':
      return { mark: '›', kind: 'You', runs: [{ text: `you typed ${entry.phrases.map(p => `"${p}"`).join(', ')}` }], tone: 'waiting' }
    case 'spawn': {
      const task = entry.description ? `: ${entry.description}` : ''
      return { mark: '⑂', kind: 'Spawn', runs: [{ text: `${entry.agentType} started${task}` }, ...(entry.isSubagent ? [{ text: ' · by a subagent', tone: 'dim' as const }] : [])], tone: 'plain' }
    }
    case 'subagent-start':
      return { mark: '⑂', kind: 'Spawn', runs: [{ text: 'a subagent received its start message' }], tone: 'dim' }
    case 'body':
      return { mark: '↳', kind: 'Read', runs: [{ text: `${entry.skill} › SKILL.md`, tone: 'read' }, { text: ' · by a subagent', tone: 'dim' }], tone: 'read' }
    case 'ref': {
      const who = entry.isSubagent ? 'by a subagent, ' : ''
      const note = entry.isLoaded ? `${who}after loading it` : `${who}skill not loaded`
      // Amber when its skill had not loaded, as the page's edge is on the picture.
      return { mark: '↳', kind: 'Ref', runs: [{ text: `${entry.skill} › ${entry.file}`, tone: 'read' }, { text: ` · ${note}`, tone: entry.isLoaded ? 'dim' : 'waiting' }], tone: 'read' }
    }
    case 'load':
      // A subagent's load for another reason, such as a hook asking, still says where it happened.
      const where = entry.isSubagent && entry.origin !== 'subagent' ? ', in a subagent' : ''
      return { mark: '+', kind: 'Skill', runs: [{ text: entry.skill, tone: 'good' }, { text: ` · ${BECAUSE[entry.origin]}${where}`, tone: 'dim' }], tone: 'good' }
    case 'nudge': {
      const statuses = entry.skills.map(s => s.status)
      const tone: Tone =
        statuses.includes('ignored') ? 'bad'
        : statuses.includes('pending') ? 'waiting'
        : statuses.length > 0 && statuses.every(s => s === 'declined') ? 'declined'
        : 'good'
      const reasons = entry.skills.flatMap(s => (s.status === 'declined' && s.reason ? [s.reason] : []))
      const runs: Run[] = [{ text: `${hookName(entry.hook)} → `, tone: 'plain' }]
      if (entry.skills.length === 0) runs.push({ text: 'no skill named', tone: 'dim' })
      entry.skills.forEach((s, i) => {
        if (i > 0) runs.push({ text: ', ', tone: 'plain' })
        runs.push({ text: `${skillName(s.skill)} ${RESULT[s.status]}`, tone: OUTCOME_TONE[s.status] })
      })
      const mark = tone === 'bad' ? '✕' : tone === 'waiting' ? '●' : tone === 'declined' ? '↷' : '✓'
      return { mark, kind: 'Hook', runs, tone, ...(reasons.length > 0 ? { reasons } : {}) }
    }
  }
}

/** Each count of a table that is not zero, as `<n> <label>`, joined by commas; empty when none is. */
const countWords = (c: Counts<string> | undefined, label: (k: string) => string = k => k) =>
  Object.entries(c ?? {}).flatMap(([k, n]) => (n ? [`${n} ${label(k)}`] : [])).join(', ')
const routeWords = (m: Measures) => countWords(m.routes, k => ROUTE_FORM[k as RouteForm] ?? k)
const holdWords = (m: Measures) => countWords(m.holds)

/**
 * Route lines, adapter holds, overrides and subagents in one line of words,
 * each part only when it has a count; undefined when none has.
 */
function measuresText(m: Measures): string | undefined {
  const sub = m.subagents ?? NO_SUBAGENTS
  const subParts = [
    ...(sub.spawns ? [`${sub.spawns} started`] : []),
    ...(sub.starts ? [plural(sub.starts, 'start message')] : []),
    ...(sub.bodyReads ? [`${sub.bodyReads} skill ${sub.bodyReads === 1 ? 'body' : 'bodies'} read`] : []),
  ]
  const overrides = total(m.overrides)
  const parts = [
    ['Routes', routeWords(m)],
    ['Adapter holds', holdWords(m)],
    ['Overrides', overrides ? String(overrides) : ''],
    ['Subagents', subParts.join(', ')],
  ].flatMap(([name, text]) => (text ? [`${name}: ${text}`] : []))
  return parts.length > 0 ? parts.join(' · ') : undefined
}

// ---------- tabs ------------------------------------------------------------------

/** The live tab: the picture with what just happened playing on it, where things stand, and the newest rows. */
/** `preview`: when `/skill-usage preview` started, while it runs; the picture plays its script instead of the session. */
export function sessionTab(v: View, s: SessionSummary, timeline: TimelineEntry[], rows: number, now: number, preview?: number | null) {
  const { Box } = v.ui
  const outcomes = sumOutcomes(s.nudges)
  const loads = byOrigin(s.loads)
  const loadCount = Object.values(loads).reduce((a, b) => a + b, 0)
  const [routerText, routerTone] = ROUTER_LINE[s.router]
  const feed = timeline.slice(-rows).reverse()
  return (
    <Box flexDirection="column">
      {picture(
        v,
        { loads, outcomes, title: 'SKILLS', subtitle: `${Object.keys(s.loads).length} loaded`, refs: readCount(s.refs), refsUnloaded: s.refsUnloaded ?? 0, spawns: s.subagents?.spawns ?? 0 },
        `Skill loads this session by who caused them: ${ORIGINS.map(o => `${STATION[o]} ${loads[o]}`).join(', ')}. Reference files read: ${readCount(s.refs)}.`,
        { now, timeline: preview != null && now < preview + PREVIEW_MS ? previewTimeline(preview) : timeline },
      )}
      {words(v, standing(loadCount, outcomes), 'plain', true)}
      {line(v, routerText, routerTone)}
      {measuresText(s) && line(v, measuresText(s) ?? '', 'plain')}
      {title(v, 'Activity', 'newest first')}
      {feed.length === 0
        ? line(v, 'Nothing yet. Skills and hook nudges show here as they happen.', 'dim')
        : feed.map((entry, i) => {
            const r = feedRow(entry)
            // A row rebuilt from history has no time of its own, only the mod's load time.
            const when = entry.isEarlier ? 'earlier' : clock(entry.t)
            const shown = row(v, [cell(r.mark, { width: 1 }), cell(r.kind, { width: 7 }), { runs: r.runs, grow: true }, cell(when, { width: 7, isRight: true, tone: 'dim' })], r.tone)
            if (!r.reasons) return shown
            // A decline's reason shows while the pointer is on its row (the keyed Box is the hover scope); the
            // terminal has no pointer, so there it is always shown, on its own line under the row.
            const reason = words(v, [{ text: `reason: ${r.reasons.join('; ')}` }], 'declined', true)
            return (
              <Box key={`feed-${entry.t}-${i}`} flexDirection="column">
                {shown}
                {v.surface === 'terminal' ? (
                  <Box paddingLeft={10}>{reason}</Box>
                ) : (
                  <Box display="none" hover={{ display: 'flex' }} paddingLeft={10}>
                    {reason}
                  </Box>
                )}
              </Box>
            )
          })}
      {usageTables(v, s, rows, ' this session')}
    </Box>
  )
}

/**
 * Each hook with how often its nudges were followed, as a bar, and each skill
 * with its loads and what most often caused them: for all time, or for one
 * session (`suffix` names which in the titles).
 */
function usageTables(v: View, counts: { nudges: Record<string, Counts<Outcome>>; loads: Record<string, Counts<Origin>>; refs?: Refs }, rows: number, suffix: string) {
  const { Box } = v.ui
  const hooks = Object.entries(counts.nudges).sort(([, x], [, y]) => total(y) - total(x))
  const skills = Object.entries(counts.loads).sort(([, x], [, y]) => total(y) - total(x))
  const most = Math.max(1, ...skills.map(([, c]) => total(c)))
  const refs = refRows(counts.refs)
  const mostRead = Math.max(1, ...refs.map(r => r.n))
  const nameWidth = Math.min(26, Math.max(12, ...hooks.map(([h]) => hookName(h).length), ...skills.slice(0, rows).map(([s]) => s.length)) + 1)
  // The column a count's ring sits in, as wide as its heading; a bar there on the terminal.
  const BAR = 8
  return (
    <Box flexDirection="column">
      {title(v, `Hooks${suffix}`, 'how often each nudge was followed')}
      {hooks.length === 0
        ? line(v, 'No GOATED hook has nudged yet.', 'dim')
        : [
            row(v, [cell('hook', { width: nameWidth, canShrink: true }), cell('followed', { width: BAR }), cell('', { grow: true }), cell('rate', { width: 4, isRight: true })], 'dim'),
            ...hooks.map(([hook, c]) => {
              const f = followCounts(c)
              const counts: Run[] = [{ text: `${f.acted} of ${f.settled}`, tone: 'dim' }]
              if (f.declined) counts.push({ text: ` · ${f.declined} declined`, tone: 'declined' })
              if (f.pending) counts.push({ text: ` · ${f.pending} waiting`, tone: 'waiting' })
              return row(
                v,
                [
                  cell(hookName(hook), { width: nameWidth, tone: 'plain', canShrink: true }),
                  { node: dial(v, [{ n: f.acted, tone: 'good' }, { n: f.settled - f.acted, tone: 'bad' }], BAR, `${f.acted} of ${f.settled} followed`), width: BAR },
                  { runs: counts, grow: true },
                  cell(percent(f.acted, f.settled), { width: 4, isRight: true }),
                ],
                rateTone(f.acted, f.settled),
              )
            }),
          ]}
      {title(v, `Skills${suffix}`, 'what most often makes each one load')}
      {skills.length === 0
        ? line(v, 'No skill has loaded yet.', 'dim')
        : [
            row(v, [cell('skill', { width: nameWidth, canShrink: true }), cell('loads', { width: BAR }), cell('mostly', { grow: true }), cell('', { width: 4 })], 'dim'),
            ...skills.slice(0, rows).map(([skill, c]) => {
              const top = ORIGINS.reduce((best, o) => ((c[o] ?? 0) > (c[best] ?? 0) ? o : best), ORIGINS[0] as Origin)
              const n = total(c)
              return row(
                v,
                [
                  cell(skill, { width: nameWidth, canShrink: true }),
                  { node: dial(v, [{ n, tone: 'good' }], BAR, plural(n, 'load'), most), width: BAR },
                  cell(BECAUSE[top], { grow: true, tone: 'dim' }),
                  cell(String(n), { width: 4, isRight: true }),
                ],
                'plain',
              )
            }),
          ]}
      {title(v, `References${suffix}`, "each skill's supporting files read, most read first")}
      {refs.length === 0
        ? line(v, 'No skill reference file has been read yet.', 'dim')
        : [
            row(v, [cell('skill › file', { grow: true }), cell('reads', { width: BAR }), cell('', { width: 4 })], 'dim'),
            ...refs.slice(0, rows).map(r =>
              row(
                v,
                [
                  { runs: [{ text: r.skill }, { text: ` › ${r.file}`, tone: 'dim' }], grow: true },
                  { node: dial(v, [{ n: r.n, tone: 'read' }], BAR, plural(r.n, 'read'), mostRead), width: BAR },
                  cell(String(r.n), { width: 4, isRight: true }),
                ],
                'plain',
              ),
            ),
          ]}
    </Box>
  )
}

/** How many supporting files were read in all, rereads included. */
const readCount = (refs: Refs | undefined) => Object.values(refs ?? {}).reduce((sum, files) => sum + total(files), 0)

/** Each skill file read and how often, most read first; equal counts A to Z, so the order holds between redraws. */
function refRows(refs: Refs | undefined): { skill: string; file: string; n: number }[] {
  return Object.entries(refs ?? {})
    .flatMap(([skill, files]) => Object.entries(files).map(([file, n]) => ({ skill, file, n })))
    .sort((a, b) => b.n - a.n || `${a.skill}/${a.file}`.localeCompare(`${b.skill}/${b.file}`))
}

/** Totals across sessions: the still picture, each hook's follow rate as a bar, and what makes each skill load. */
export function allTimeTab(v: View, all: AllTime, rows: number) {
  const { Box } = v.ui
  const outcomes = sumOutcomes(all.nudges)
  const loads = byOrigin(all.loads)
  const loadCount = Object.values(loads).reduce((a, b) => a + b, 0)
  const ruled = (all.router.first ?? 0) + (all.router.late ?? 0) + (all.router.never ?? 0)
  const first = all.router.first ?? 0
  return (
    <Box flexDirection="column">
      {picture(
        v,
        { loads, outcomes, title: 'ALL TIME', subtitle: plural(all.sessions, 'session'), refs: readCount(all.refs), refsUnloaded: all.refsUnloaded ?? 0, spawns: all.subagents?.spawns ?? 0 },
        `Skill loads across ${plural(all.sessions, 'session')} by who caused them: ${ORIGINS.map(o => `${STATION[o]} ${loads[o]}`).join(', ')}. Reference files read: ${readCount(all.refs)}.`,
      )}
      {words(v, [{ text: `${plural(all.sessions, 'session')} · ` }, ...standing(loadCount, outcomes)], 'plain', true)}
      {line(
        v,
        ruled === 0 ? 'GOATED router rule: not seen yet' : `GOATED router rule: router loaded first in ${first} of ${plural(ruled, 'session')}`,
        ruled === 0 ? 'dim' : rateTone(first, ruled),
      )}
      {measuresText(all) && line(v, measuresText(all) ?? '', 'plain')}
      {usageTables(v, all, rows, '')}
    </Box>
  )
}

/**
 * Your own skills: how many have ever loaded, as a bar, then two lists: those
 * that loaded, most loaded first, each with its share of all their loads as a
 * bar and a percentage; and those that never have, A to Z.
 */
export function unusedTab(v: View, all: AllTime, avail: Available | null) {
  const { Box } = v.ui
  if (!avail) return line(v, 'The skill list is read at your next message.', 'dim')
  const byName = (a: string, b: string) => a.localeCompare(b)
  const unused = avail.own.filter(s => !all.loads[s]).sort(byName)
  const loadsOf = (s: string) => total(all.loads[s])
  // Most loaded first; equal counts A to Z, so the order never shuffles between redraws.
  const loaded = avail.own.filter(s => all.loads[s]).sort((a, b) => loadsOf(b) - loadsOf(a) || byName(a, b))
  const allLoads = loaded.reduce((sum, s) => sum + loadsOf(s), 0)
  // Bars scale to the most loaded skill, so it fills its column and every other bar keeps its true proportion to it.
  const mostLoads = Math.max(1, ...loaded.map(loadsOf))
  const SHARE_BAR = 16
  return (
    <Box flexDirection="column">
      {avail.included < avail.total && line(v, `✕ Only ${avail.included} of ${avail.total} skills fit the skill listing: the rest are invisible to Claude.`, 'bad')}
      {title(v, 'Your skills', `across ${plural(all.sessions, 'session')}`)}
      {row(
        v,
        [
          { node: meter(v, [{ n: loaded.length, tone: 'good' }], 24, avail.own.length), width: 24 },
          {
            runs: [
              { text: `${loaded.length} of ${avail.own.length} have loaded`, tone: rateTone(loaded.length, avail.own.length) },
              { text: ` · ${percent(loaded.length, avail.own.length)}`, tone: 'dim' },
            ],
            grow: true,
          },
        ],
        'plain',
      )}
      {line(v, `${plural(avail.names.length - avail.own.length, 'built-in and plugin skill')} are not counted here.`, 'dim')}
      {title(v, `Loaded · ${loaded.length}`, `most loaded first; each one's share of all ${allLoads} loads, bars to scale`)}
      {loaded.length === 0
        ? line(v, 'None of your skills has loaded yet.', 'dim')
        : loaded.map(s =>
            row(
              v,
              [
                cell('✓', { width: 1 }),
                cell(s, { grow: true }),
                { node: meter(v, [{ n: loadsOf(s), tone: 'good' }], SHARE_BAR, mostLoads), width: SHARE_BAR },
                cell(percent(loadsOf(s), allLoads), { width: 4, isRight: true, tone: 'plain' }),
                cell(`×${loadsOf(s)}`, { width: 4, isRight: true, tone: 'dim' }),
              ],
              'good',
            ),
          )}
      {title(v, `Never loaded · ${unused.length}`, unused.length > 0 ? 'A to Z; candidates for a hook nudge or a better description' : undefined)}
      {unused.length === 0
        ? line(v, 'Every one of your skills has loaded at least once.', 'good')
        : unused.map(s => row(v, [cell('·', { width: 1 }), cell(s, { grow: true })], 'dim'))}
    </Box>
  )
}

// ---------- report ----------------------------------------------------------------

/** `/skill-usage report`: the All time and Unused tabs as markdown, in the pane's own words. */
export function reportText(all: AllTime, avail: Available | null): string {
  const out = [`# Skill usage: ${plural(all.sessions, 'session')}`, '', '## Hooks', '']
  for (const [hook, c] of Object.entries(all.nudges).sort(([, x], [, y]) => total(y) - total(x))) {
    const f = followCounts(c)
    const parts = OUTCOMES.filter(k => c[k]).map(k => `${RESULT[k]} ${c[k]}`)
    out.push(`- ${hookName(hook)}: ${f.acted} of ${f.settled} followed (${percent(f.acted, f.settled)})${parts.length ? ` · ${parts.join(' · ')}` : ''}`)
  }
  const ruled = (all.router.first ?? 0) + (all.router.late ?? 0) + (all.router.never ?? 0)
  out.push('', ruled === 0 ? 'GOATED router rule: not seen yet.' : `GOATED router rule: router loaded first in ${all.router.first ?? 0} of ${plural(ruled, 'session')}.`)
  out.push('', '## Skills', '')
  for (const [skill, c] of Object.entries(all.loads).sort(([, x], [, y]) => total(y) - total(x))) {
    out.push(`- ${skill}: ${total(c)} (${ORIGINS.filter(o => c[o]).map(o => `${BECAUSE[o]} ${c[o]}`).join(' · ')})`)
  }
  const overrides = Object.entries(all.overrides ?? {}).sort(([, x], [, y]) => y - x).map(([phrase, n]) => `"${phrase}" ${n}`)
  const sub = all.subagents ?? NO_SUBAGENTS
  out.push('', '## Routes and adapter holds', '')
  out.push(`- Route lines: ${routeWords(all) || 'none'}`)
  out.push(`- Adapter holds: ${holdWords(all) || 'none'}`)
  out.push(`- Overrides: ${overrides.join(' · ') || 'none'}`)
  out.push(`- Subagents: ${sub.spawns} started · ${plural(sub.starts, 'start message')} · ${sub.bodyReads} skill bodies read`)
  const refs = refRows(all.refs)
  out.push('', '## References', '')
  if (refs.length === 0) out.push('(none read yet)')
  for (const r of refs) out.push(`- ${r.skill} › ${r.file}: ${r.n}`)
  const unused = (avail?.own ?? []).filter(s => !all.loads[s])
  out.push('', `## Your skills never loaded (${unused.length})`, '', unused.join(', ') || '(none)')
  if (avail && avail.included < avail.total) out.push('', `Only ${avail.included} of ${avail.total} skills fit the skill listing.`)
  return out.join('\n')
}
