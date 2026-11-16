// Generated from the Claude Code adapter's output (goated_adapter), driven with synthetic sessions by
// `uv run python tests/test_skill_usage_mod.py --write`; do not edit by hand.
// tests/test_skill_usage_mod.py fails when this copy drifts from its source.

export const ADAPTER_TEXTS = {
  "routerFirst": "goated-hold: router-first | strict\nLoad the `using-goated-ai-skills` skill with the Skill tool before the first write, spawn, or command of a task, and follow the route it selects. Reads stay free. If that skill is not installed, tell the user: they can type `skip routing` in their prompt to proceed without it.",
  "routeLine": "goated-hold: route-line | strict\nBefore the first write or spawn after a user prompt, end routing with a route line on its own line, as the router's output contract defines: `goated-route: direct`, `goated-route: <intensity> | requires: <skills>`, or `goated-route: continue` when this prompt continues the current task. Claude Code records a message only after this check, so a route line in the same message as this call is not visible yet: if you wrote one there, make the call again.",
  "pipeline": "goated-hold: pipeline | strict\nThe current route requires `tdd`, `doc-sync` before the first write or spawn. Load each with the Skill tool and follow it; only loads after the route line that started this task count, so load again if you loaded it earlier. If one does not apply, write a corrected route line without it; the last route line wins.",
  "overrideNotice": "GOATED Claude Code adapter: recorded your override for this prompt: \"Skip routing\"."
} as const
