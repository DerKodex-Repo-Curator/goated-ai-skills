"""A translator that maps a tool wrongly, to show the conformance runner
fails what it should (Ticket 083): it makes every file write with the toy
loop's `fetch` tool, which the example adapter judges as an `other` call,
so no write gate ever sees the write."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "adapters" / "example"))

import conformance_translator  # noqa: E402


class WritesAsFetches(conformance_translator.Translator):
    def call(self, call: dict, result: dict):
        if call["kind"] == "file_write":
            call = {"kind": "other"}
        return super().call(call, result)


def make_translator(setup: dict) -> WritesAsFetches:
    return WritesAsFetches(setup)
