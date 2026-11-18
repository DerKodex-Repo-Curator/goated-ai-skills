# Worked Example: An Adapter For A Toy Tool Loop

An example to copy from, not an adapter to install. It shows a complete
adapter for a minimal agent harness with no model and no network:

- `toy_loop.py`: the toy harness, with its own tools, transcript, and hooks.
- `goated_example_adapter.py`: the adapter. It asks the shared core
  (`../core/`) before each tool call, after it, at each prompt, at the
  turn's end, and at a session's start.
- `conformance_translator.py`: its translator for the conformance runner.

[Writing An Adapter](../writing-an-adapter.md) walks through each part. The
example passes every conformance scenario:

```bash
uv run python scripts/run_conformance.py adapters/example/conformance_translator.py
```
