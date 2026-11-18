"""The GOATED enforcement core: the rules every adapter calls (ADR 0004).

The core judges events in the event model's terms
(`stack/schemas/enforcement-event-model.schema.json`) and knows no
harness. It keeps the session facts that outlast a request, keyed by the
session id the caller supplies, under a folder the caller may choose.

Two ways in:

- `decide(request, settings)`: one request, as the schema shapes it, in;
  one decision out, both plain JSON-shaped values. `goated_judge.py`, beside
  this package, is the same call as a command over standard input and
  output, for a harness in another language.
- `judge`: the same rules at the level of the model's Python objects, for an
  adapter that builds turns itself and fills the hold texts' wording slots
  (`wording`) in its harness's words, as the Claude Code adapter does.

Standard library only. Every command call starts a fresh interpreter, so the
package avoids imports that cost start-up time: it uses plain classes
instead of `dataclasses` (which imports `inspect`) and does not import
`tempfile`. Measure before adding one.
"""
