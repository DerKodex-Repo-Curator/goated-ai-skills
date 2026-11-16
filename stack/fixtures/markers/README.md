# Marker Line Grammar

This file is the single owner of the exact grammar for the three portable
marker lines that GOATED agents write in their replies:

- the **route line**, defined by the `using-goated-ai-skills` router's output
  contract;
- the **justified-skip line**, defined by the shared policy in
  `stack/AGENTS.md`;
- the **design-reads line**, defined by the `software-design-principles`
  skill's workflow.

The router, the shared policy, and the skill say when to write each line; the
skill restates the spelling an agent needs, so it works when installed alone.
This file fixes how the lines are spelled, so framework adapters, measurement
tools, and reviewers parse them the same way. Under ADR 0003 an adapter
enforces these lines but never redefines them; a grammar change lands here
first, with fixtures.

`lines.yaml` holds valid and invalid route and skip line fixtures and
whole-reply fixtures. `design-reads.yaml` holds the design-reads line fixtures
in the same shape; it is a separate file because adapters and the skill-usage
mod embed `lines.yaml` whole. `scripts/validation/markers.py` is the repo's
reference checker; the validator runs it against both files.

## Line Grammar

ABNF-style, where `WS` is one or more spaces or tabs and `OWS` is zero or
more:

```text
route-line  = "goated-route:" WS route-body
route-body  = "direct"
            / "continue"
            / intensity WS "|" WS "requires:" WS skill-list
intensity   = "lightweight" / "standard" / "full"
skill-list  = skill *( OWS "," OWS skill )

skip-line   = "goated-skip:" WS skill ":" WS reason
reason      = text with at least three whitespace-separated words

design-reads-line = "goated-design-reads:" WS ( "none:" WS reason / file-list )
file-list   = file *( OWS "," OWS file )
file        = skill ".md"
            ; a bare reference file name, such as process.md

skill       = 1*( %x61-7A / DIGIT ) *( "-" 1*( %x61-7A / DIGIT ) )
            ; lowercase kebab-case, the same shape as a skill folder name
```

Equivalent regular expressions for one candidate line, where `SKILL` stands
for the skill expression:

```text
skill  [a-z0-9]+(?:-[a-z0-9]+)*
route  ^goated-route:[ \t]+(?:(direct|continue)|(lightweight|standard|full)[ \t]+\|[ \t]+requires:[ \t]+(SKILL(?:[ \t]*,[ \t]*SKILL)*))$
skip   ^goated-skip:[ \t]+(SKILL):[ \t]+(\S.*)$   plus the three-word reason rule
file   SKILL\.md
reads  ^goated-design-reads:[ \t]+(?:none:[ \t]+(\S.*)|(FILE(?:[ \t]*,[ \t]*FILE)*))$   plus the three-word reason rule
```

## Candidate Lines

- A marker is a whole line of the reply. Strip leading and trailing whitespace
  first. A line wrapped in exactly one pair of single backticks is unwrapped
  once, so `` `goated-route: direct` `` counts.
- Lines inside fenced code blocks (opened and closed by a line starting with
  three backticks or three tildes) never count, so documentation can show
  examples without emitting them.
- A marker embedded in prose, a list item, a quote, or a table cell does not
  count.
- Keywords are lowercase and exact. A candidate line that starts with
  `goated-route:`, `goated-skip:`, or `goated-design-reads:`, compared
  case-insensitively, but fails the
  grammar is **malformed**: parsers report it and never treat it as a marker.

## Semantics

- `goated-route: direct`: tiny work that needs no specialist skill.
- `goated-route: <intensity> | requires: <skills>`: the listed specialist
  skills must load before the first write. The list is non-empty and has no
  duplicates; a route that needs no specialist skill is `direct`.
- `goated-route: continue`: a later prompt continues the current task and its
  existing route.
- When one reply contains several valid route lines, the last one wins.
- A reply may contain any number of skip lines; each names one skill.
- The grammar does not check skill names against a registry. An adapter may
  warn about an unknown name but must not reinterpret it.
- A skip reason must be specific to the current action. The three-word minimum
  is only a mechanical floor; reviewers and measurement tools judge the reason.

### Design-reads line

- `goated-design-reads: <files>` names the `software-design-principles`
  references whose conditions hold. The list is non-empty and has no
  duplicates. Spaces or tabs around commas are allowed; a trailing comma is
  not.
- A file is a bare name. A path, such as `references/process.md`, is
  malformed.
- `goated-design-reads: none: <reason>` declares that no condition holds. The
  reason follows the skip line's three-word floor.
- Lines accumulate. The declared set of a reply is the union of the files of
  all its valid design-reads lines, in first-seen order. A later line adds
  files and never removes any; a `none` line adds none. Tools that judge a
  whole turn combine its replies the same way.
- `red-flags.md` may be listed. It adds nothing to the required set, because
  the skill's closing step reads it on every change.
- The grammar does not check file names against the skill's `references/`.
  An unknown name stays in the declared set as written; checkers may report
  it, require nothing for it, and never map it to another file.
