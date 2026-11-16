// Generated from stack/fixtures/markers/lines.yaml by
// `uv run python tests/test_skill_usage_mod.py --write`; do not edit by hand.
// tests/test_skill_usage_mod.py fails when this copy drifts from its source.

export const MARKER_FIXTURES = {
  "schema_version": "1.0.0",
  "route_lines": {
    "valid": [
      {
        "line": "goated-route: direct",
        "expect": {
          "form": "direct"
        }
      },
      {
        "line": "goated-route: continue",
        "expect": {
          "form": "continue"
        }
      },
      {
        "line": "goated-route: lightweight | requires: commit-message",
        "expect": {
          "form": "route",
          "intensity": "lightweight",
          "requires": [
            "commit-message"
          ]
        }
      },
      {
        "line": "goated-route: standard | requires: tdd, doc-sync",
        "expect": {
          "form": "route",
          "intensity": "standard",
          "requires": [
            "tdd",
            "doc-sync"
          ]
        }
      },
      {
        "line": "goated-route: full | requires: write-a-spec,design-codebase-architecture , spec-to-tickets",
        "expect": {
          "form": "route",
          "intensity": "full",
          "requires": [
            "write-a-spec",
            "design-codebase-architecture",
            "spec-to-tickets"
          ]
        }
      },
      {
        "line": "goated-route:\tstandard\t|\trequires:\ttdd",
        "expect": {
          "form": "route",
          "intensity": "standard",
          "requires": [
            "tdd"
          ]
        }
      }
    ],
    "invalid": [
      {
        "line": "goated-route: Direct",
        "why": "keywords are lowercase"
      },
      {
        "line": "Goated-Route: direct",
        "why": "the prefix is lowercase"
      },
      {
        "line": "goated-route:direct",
        "why": "whitespace is required after the colon"
      },
      {
        "line": "goated-route: direct | requires: tdd",
        "why": "direct takes no skill list"
      },
      {
        "line": "goated-route: continue | requires: tdd",
        "why": "continue takes no skill list"
      },
      {
        "line": "goated-route: standard",
        "why": "an intensity needs a requires list"
      },
      {
        "line": "goated-route: standard | requires:",
        "why": "the requires list is non-empty"
      },
      {
        "line": "goated-route: medium | requires: tdd",
        "why": "intensity is lightweight, standard, or full"
      },
      {
        "line": "goated-route: standard requires: tdd",
        "why": "the pipe separator is required"
      },
      {
        "line": "goated-route: standard | requires: tdd, tdd",
        "why": "the requires list has no duplicates"
      },
      {
        "line": "goated-route: standard | requires: TDD",
        "why": "skill names are lowercase kebab-case"
      },
      {
        "line": "goated-route: standard | requires: tdd,",
        "why": "no trailing comma"
      },
      {
        "line": "goated-route: standard | requires: tdd doc-sync",
        "why": "skills are comma-separated"
      },
      {
        "line": "goated-route: direct.",
        "why": "no trailing punctuation"
      }
    ]
  },
  "skip_lines": {
    "valid": [
      {
        "line": "goated-skip: doc-sync: change touches only test fixtures",
        "expect": {
          "skill": "doc-sync",
          "reason": "change touches only test fixtures"
        }
      },
      {
        "line": "goated-skip: code-security-review: no trust boundary, auth, or data path changed",
        "expect": {
          "skill": "code-security-review",
          "reason": "no trust boundary, auth, or data path changed"
        }
      },
      {
        "line": "goated-skip:\thandoff:\twork finishes in this turn",
        "expect": {
          "skill": "handoff",
          "reason": "work finishes in this turn"
        }
      }
    ],
    "invalid": [
      {
        "line": "goated-skip: doc-sync",
        "why": "a reason is required"
      },
      {
        "line": "goated-skip: doc-sync:",
        "why": "the reason is non-empty"
      },
      {
        "line": "goated-skip: doc-sync: n/a",
        "why": "the reason has at least three words"
      },
      {
        "line": "goated-skip: doc-sync: not needed",
        "why": "the reason has at least three words"
      },
      {
        "line": "goated-skip: Doc-Sync: change touches only fixtures",
        "why": "skill names are lowercase kebab-case"
      },
      {
        "line": "goated-skip: doc-sync, handoff: both are not relevant here",
        "why": "one skill per skip line"
      },
      {
        "line": "goated-skip:doc-sync: change touches only fixtures",
        "why": "whitespace is required after the prefix colon"
      },
      {
        "line": "goated-skip: doc-sync:change touches only fixtures",
        "why": "whitespace is required after the skill colon"
      }
    ]
  },
  "replies": [
    {
      "identifier": "route-after-prose",
      "text": "Route chosen for the fixture work.\n\ngoated-route: standard | requires: tdd\n",
      "expect": {
        "route": {
          "form": "route",
          "intensity": "standard",
          "requires": [
            "tdd"
          ]
        },
        "skips": [],
        "malformed": []
      }
    },
    {
      "identifier": "backtick-wrapped-markers",
      "text": "`goated-route: direct`\n`goated-skip: doc-sync: change touches only test fixtures`\n",
      "expect": {
        "route": {
          "form": "direct"
        },
        "skips": [
          {
            "skill": "doc-sync",
            "reason": "change touches only test fixtures"
          }
        ],
        "malformed": []
      }
    },
    {
      "identifier": "backtick-unwrapping-strips-inside",
      "text": "` goated-skip: handoff: work finishes in this turn `\n`goated-route: direct `\n",
      "expect": {
        "route": {
          "form": "direct"
        },
        "skips": [
          {
            "skill": "handoff",
            "reason": "work finishes in this turn"
          }
        ],
        "malformed": []
      }
    },
    {
      "identifier": "backtick-unwrapping-keeps-inner-backticks",
      "text": "`goated-skip: doc-sync: the `README` is unchanged`\n",
      "expect": {
        "route": null,
        "skips": [
          {
            "skill": "doc-sync",
            "reason": "the `README` is unchanged"
          }
        ],
        "malformed": []
      }
    },
    {
      "identifier": "carriage-returns-end-lines",
      "text": "goated-skip: handoff: work finishes in this turn\rgoated-route: direct\r\n",
      "expect": {
        "route": {
          "form": "direct"
        },
        "skips": [
          {
            "skill": "handoff",
            "reason": "work finishes in this turn"
          }
        ],
        "malformed": []
      }
    },
    {
      "identifier": "fenced-examples-do-not-count",
      "text": "The grammar allows:\n\n```text\ngoated-route: full | requires: wayfinder\ngoated-skip: handoff: work finishes in this turn\n```\n\ngoated-route: continue\n",
      "expect": {
        "route": {
          "form": "continue"
        },
        "skips": [],
        "malformed": []
      }
    },
    {
      "identifier": "last-valid-route-wins",
      "text": "goated-route: direct\nScope grew after reading the ticket.\ngoated-route: standard | requires: writing-plans, tdd\n",
      "expect": {
        "route": {
          "form": "route",
          "intensity": "standard",
          "requires": [
            "writing-plans",
            "tdd"
          ]
        },
        "skips": [],
        "malformed": []
      }
    },
    {
      "identifier": "embedded-markers-do-not-count",
      "text": "I would write goated-route: direct here.\n- goated-route: direct\n> goated-skip: doc-sync: change touches only test fixtures\n",
      "expect": {
        "route": null,
        "skips": [],
        "malformed": []
      }
    },
    {
      "identifier": "malformed-lines-are-reported",
      "text": "goated-route: medium | requires: tdd\ngoated-skip: doc-sync: n/a\nGoated-Route: direct\n",
      "expect": {
        "route": null,
        "skips": [],
        "malformed": [
          "goated-route: medium | requires: tdd",
          "goated-skip: doc-sync: n/a",
          "Goated-Route: direct"
        ]
      }
    },
    {
      "identifier": "several-skips",
      "text": "goated-route: lightweight | requires: commit-message\ngoated-skip: doc-sync: change touches only test fixtures\ngoated-skip: handoff: work finishes in this turn\n",
      "expect": {
        "route": {
          "form": "route",
          "intensity": "lightweight",
          "requires": [
            "commit-message"
          ]
        },
        "skips": [
          {
            "skill": "doc-sync",
            "reason": "change touches only test fixtures"
          },
          {
            "skill": "handoff",
            "reason": "work finishes in this turn"
          }
        ],
        "malformed": []
      }
    }
  ]
} as const
