"""Opt-in GOATED enforcement adapter for Claude Code (standard library only).

The public surface is `run_hook` and `Config`; `goated_hook.py` is the command
Claude Code runs for every configured hook event.

The rules live in the shared core, the `goated_core` package in
`adapters/core/` (ADR 0004). This package translates Claude Code's hook
input and transcript into the event model, calls the core, and puts its
decision back into Claude Code's hook output. When `goated_core` is not
already importable, it is taken from `../../core`, beside this adapter in
its distribution, as the README's install steps place both.

Every hook call starts a fresh interpreter, so the package avoids imports that
cost start-up time: it uses plain classes instead of `dataclasses` (which
imports `inspect`) and does not import `tempfile`. Measure before adding one.
"""

import os
import sys

# The core's folder in the distribution: `<goated-root>/adapters/core/`.
CORE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "core")

try:
    import goated_core  # noqa: F401 - only to learn whether it is importable
except ImportError:
    sys.path.insert(0, CORE_DIR)

from .hooks import Config, run_hook  # noqa: E402 - needs the core on the path

__all__ = ["CORE_DIR", "Config", "run_hook"]
