# Route And Skip Line Grammar

This file is the single owner of the exact grammar for the two portable marker
lines that GOATED agents write in their replies:

- the **route line**, defined by the `using-goated-ai-skills` router's output
  contract;
- the **justified-skip line**, defined by the shared policy in
  `stack/AGENTS.md`.

The router and the shared policy say when to write each line. This file fixes
how the lines are spelled, so framework adapters, measurement tools, and
reviewers parse them the same way. Under ADR 0003 an adapter enforces these
lines but never redefines them; a grammar change lands here first, with
fixtures.

`lines.yaml` holds valid and invalid line fixtures and whole-reply fixtures.
`scripts/validation/markers.py` is the repo's reference checker; the validator
runs it against `lines.yaml`.

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

skill       = 1*( %x61-7A / DIGIT ) *( "-" 1*( %x61-7A / DIGIT ) )
            ; lowercase kebab-case, the same shape as a skill folder name
```

Equivalent regular expressions for one candidate line, where `SKILL` stands
for the skill expression:

```text
skill  [a-z0-9]+(?:-[a-z0-9]+)*
route  ^goated-route:[ \t]+(?:(direct|continue)|(lightweight|standard|full)[ \t]+\|[ \t]+requires:[ \t]+(SKILL(?:[ \t]*,[ \t]*SKILL)*))$
skip   ^goated-skip:[ \t]+(SKILL):[ \t]+(\S.*)$   plus the three-word reason rule
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
  `goated-route:` or `goated-skip:`, compared case-insensitively, but fails the
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
