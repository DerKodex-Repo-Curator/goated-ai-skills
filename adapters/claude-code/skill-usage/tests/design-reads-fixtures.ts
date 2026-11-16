// Generated from stack/fixtures/markers/design-reads.yaml by
// `uv run python tests/test_skill_usage_mod.py --write`; do not edit by hand.
// tests/test_skill_usage_mod.py fails when this copy drifts from its source.

export const DESIGN_READS_FIXTURES = {
  "schema_version": "1.0.0",
  "design_reads_lines": {
    "valid": [
      {
        "line": "goated-design-reads: process.md",
        "expect": {
          "form": "files",
          "files": [
            "process.md"
          ]
        }
      },
      {
        "line": "goated-design-reads: process.md, errors.md",
        "expect": {
          "form": "files",
          "files": [
            "process.md",
            "errors.md"
          ]
        }
      },
      {
        "line": "goated-design-reads: process.md,errors.md ,  readability.md",
        "expect": {
          "form": "files",
          "files": [
            "process.md",
            "errors.md",
            "readability.md"
          ]
        }
      },
      {
        "line": "goated-design-reads: red-flags.md",
        "expect": {
          "form": "files",
          "files": [
            "red-flags.md"
          ]
        }
      },
      {
        "line": "goated-design-reads: unknown-file.md",
        "expect": {
          "form": "files",
          "files": [
            "unknown-file.md"
          ]
        }
      },
      {
        "line": "goated-design-reads: none: renames one local variable",
        "expect": {
          "form": "none",
          "reason": "renames one local variable"
        }
      },
      {
        "line": "goated-design-reads:\tnone:\tedits only test fixture data",
        "expect": {
          "form": "none",
          "reason": "edits only test fixture data"
        }
      }
    ],
    "invalid": [
      {
        "line": "goated-design-reads:",
        "why": "the file list is non-empty"
      },
      {
        "line": "goated-design-reads: none",
        "why": "none needs a colon and a reason"
      },
      {
        "line": "goated-design-reads: none:",
        "why": "the none reason is non-empty"
      },
      {
        "line": "goated-design-reads: none: already read",
        "why": "the none reason has at least three words"
      },
      {
        "line": "goated-design-reads: references/process.md",
        "why": "a file is a bare name, not a path"
      },
      {
        "line": "goated-design-reads: process",
        "why": "a file name keeps its .md extension"
      },
      {
        "line": "goated-design-reads: Process.md",
        "why": "file names are lowercase"
      },
      {
        "line": "goated-design-reads: process.md, process.md",
        "why": "the file list has no duplicates"
      },
      {
        "line": "goated-design-reads: process.md,",
        "why": "no trailing comma"
      },
      {
        "line": "goated-design-reads: process.md errors.md",
        "why": "files are comma-separated"
      },
      {
        "line": "goated-design-reads:process.md",
        "why": "whitespace is required after the prefix colon"
      },
      {
        "line": "goated-design-reads: process.md#design-twice",
        "why": "the line names files, not section ids"
      }
    ]
  },
  "design_reads_replies": [
    {
      "identifier": "later-lines-add-files",
      "text": "goated-design-reads: process.md, errors.md\nThe change also needs a lock.\ngoated-design-reads: errors.md, concurrency.md\n",
      "expect": {
        "files": [
          "process.md",
          "errors.md",
          "concurrency.md"
        ],
        "lines": [
          {
            "form": "files",
            "files": [
              "process.md",
              "errors.md"
            ]
          },
          {
            "form": "files",
            "files": [
              "errors.md",
              "concurrency.md"
            ]
          }
        ],
        "malformed": []
      }
    },
    {
      "identifier": "none-removes-nothing",
      "text": "goated-design-reads: readability.md\ngoated-design-reads: none: the rest only renames locals\n",
      "expect": {
        "files": [
          "readability.md"
        ],
        "lines": [
          {
            "form": "files",
            "files": [
              "readability.md"
            ]
          },
          {
            "form": "none",
            "reason": "the rest only renames locals"
          }
        ],
        "malformed": []
      }
    },
    {
      "identifier": "backtick-wrapped-line-counts",
      "text": "`goated-design-reads: process.md`\n",
      "expect": {
        "files": [
          "process.md"
        ],
        "lines": [
          {
            "form": "files",
            "files": [
              "process.md"
            ]
          }
        ],
        "malformed": []
      }
    },
    {
      "identifier": "prose-list-and-fence-do-not-count",
      "text": "I would write goated-design-reads: errors.md here.\n- `goated-design-reads: coding.md`\n\n```text\ngoated-design-reads: concurrency.md\n```\n",
      "expect": {
        "files": [],
        "lines": [],
        "malformed": []
      }
    },
    {
      "identifier": "malformed-design-reads-are-reported",
      "text": "goated-design-reads: references/process.md\nGoated-Design-Reads: process.md\ngoated-design-reads: errors.md\n",
      "expect": {
        "files": [
          "errors.md"
        ],
        "lines": [
          {
            "form": "files",
            "files": [
              "errors.md"
            ]
          }
        ],
        "malformed": [
          "goated-design-reads: references/process.md",
          "Goated-Design-Reads: process.md"
        ]
      }
    }
  ]
} as const
