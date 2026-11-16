# Ticket 040: Skill-Usage Picture Badges Belong To Session Only

## Parent Spec

`docs/specs/2026-11-15-skill-enforcement-adapter.md` (AC7, measurement
display). Agreed by the maintainer on 2026-11-16 after reviewing the All time
picture in real use. This ticket changes only what the pane draws; it counts
nothing new.

## Type

AFK.

## Problem

The skill-usage mod draws one picture for both the Session and All time tabs
(`drawMap` in `adapters/claude-code/skill-usage/hooks/picture.tsx`), so both
carry the same count badges:

- red, on Hooks: holds not followed (`ignored`);
- amber with an outline, pulsing, on Hooks: holds still waiting;
- amber, on References: reference reads made before their skill loaded
  (`refsUnloaded`);
- blue, on Subagents: subagents started (`spawns`).

None of these is an unread count. Each is a running total: it grows for the
whole session, and on All time it is the sum across every stored session, so
it never clears. All time adds the live session without closing its waiting
holds (`hooks/register.tsx`), so a hold waiting right now also pulses on All
time. The maintainer reads All time as the high-level picture, where these
per-case markers do not belong.

Also:

- Amber means two things: waiting on Hooks, and read before loading on
  References.
- The count of reads made before loading appears only as that badge, never
  in text, on either tab.
- The picture's alt text names no badge count.
- The README does not explain the badges, and its Unused bullet sits below
  the tables paragraph instead of in the tab list.

## Decisions (maintainer, 2026-11-16)

1. All time draws no badges: node counts, spokes and the core ring only.
2. Session keeps its badges. The References badge stops using amber, so amber
   means only waiting: it takes the reference-read pink, edged in amber. The
   Session picture's alt text names each badge count that shows.
3. The References table's subtitle, on both tabs, adds
   `· <n> read before their skill loaded` when `n > 0`.

## What To Build

- Give `MapData` (or `drawMap`) a way to draw without badges, and have
  `allTimeTab` use it.
- Recolour the References badge on the Session picture.
- Add the badge counts to the Session picture's alt text.
- Add the read-before-loading count to the References subtitle.
- Explain the picture's nodes and Session badges in the README's pane
  section, and move its Unused bullet back into the tab list.

## Out Of Scope

- Counting, hold settlement and the legacy hook handling in
  `hooks/classify.ts` (Tickets 033 and 039).
- The node counts, spokes and core ring.

## Recommended First Reads

- `adapters/claude-code/skill-usage/README.md`, "The Pane".
- `adapters/claude-code/skill-usage/hooks/picture.tsx`: `drawMap`.
- `adapters/claude-code/skill-usage/hooks/view.tsx`: `sessionTab`,
  `allTimeTab`, `usageTables`.

## Acceptance Criteria

- [x] With holds not followed, holds waiting, reads before loading and
      subagents started, the All time picture draws none of the four badges,
      and still draws the node counts and the core ring. (Test: "the All
      time picture shows node counts and the core ring but no badge, with
      nothing moving"; red before the fix, green after.)
- [x] The Session picture still draws all four; its References badge is
      filled pink and edged amber, not filled amber. (Test: "a subagent read
      flies to Subagents; … counts on a pink badge edged in amber"; the
      Hooks and Subagents badge tests still pass.)
- [x] The Session picture's alt text names the not-followed, waiting,
      read-before-loading and started counts that are above zero. (Test:
      "the Session picture's alt text names each badge it shows, and leaves
      out a count of none", red before the fix; and "badge words name every
      badge count above zero, singular or plural", written after it.)
- [x] On both tabs, the References subtitle says
      `<n> read before their skill loaded` when `n > 0`, and nothing extra
      when `n` is 0. (Test: "the References table's subtitle counts reads
      made before their skill loaded, on both tabs, and says nothing of
      none".)
- [x] The README's pane section names what each node counts and each Session
      badge, says All time draws none, and lists Unused with the other tabs.
      (Manual review of the diff.)
- [x] `claude plugin validate .` and `claude plugin test .` pass in the mod
      folder; the repo's validator, unit tests (default Python and 3.11) and
      context comparison pass. (2026-11-16: validate passed with the same
      five TypeScript warnings main has at `fad2fc8`; 141 mod tests pass;
      322 unit tests OK on the default Python and 3.11, 2 skipped; every
      route meets the 10% reduction target.)
