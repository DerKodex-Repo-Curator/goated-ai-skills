"""Opt-in GOATED enforcement adapter for Claude Code (standard library only).

The public surface is `run_hook` and `Config`; `goated_hook.py` is the command
Claude Code runs for every configured hook event.

Every hook call starts a fresh interpreter, so the package avoids imports that
cost start-up time: it uses plain classes instead of `dataclasses` (which
imports `inspect`) and does not import `tempfile`. Measure before adding one.
"""

from .hooks import Config, run_hook

__all__ = ["Config", "run_hook"]
