// Generated from one synthetic Claude Code session driven through the adapter with the core's usage log on (tests/usage_log_session.py) by
// `uv run python tests/test_skill_usage_mod.py --write`; do not edit by hand.
// tests/test_skill_usage_mod.py fails when this copy drifts from its source.

export const USAGE_LOG_SESSION = {
  "steps": [
    {
      "row": {
        "door": "prompt",
        "message": {
          "content": [
            {
              "type": "text",
              "text": "Add CSV export, test-first with tdd."
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "response",
        "message": {
          "content": [
            {
              "type": "tool_use",
              "id": "toolu_0001",
              "name": "Edit",
              "input": {
                "file_path": "src/export.py",
                "old_string": "limit = 1",
                "new_string": "limit = 2"
              }
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "tool-result",
        "message": {
          "content": [
            {
              "type": "tool_result",
              "tool_use_id": "toolu_0001",
              "content": "PreToolUse:Edit hook error: goated-hold: router-first | strict\nLoad the `using-goated-ai-skills` skill with the Skill tool before the first write, spawn, or command of a task, and follow the route it selects. Reads stay free, and so does a shell command made only of read-only commands, such as cat, grep, ls, git diff, or git branch, perhaps after a leading cd, with no output redirect but 2>/dev/null. If that skill is not installed, tell the user: they can type `skip routing` in their prompt to proceed without it.\n\ngoated-hold: route-line | strict\nBefore the first write or spawn after a user prompt, end routing with a route line on its own line, as the router's output contract defines: `goated-route: direct`, `goated-route: <intensity> | requires: <skills>`, or `goated-route: continue` when this prompt continues the current task or, in a session with no task yet, work begun elsewhere. A route line in reply text may not be seen: Claude Code records a message only after this check, and can store the text of a message that makes a tool call as a summary that drops the line. A line in the description field of a shell or agent call, or in a Skill call's args, is read as written and counts from that call on. Put the route line on its own line there, in this call's description if it has one or else in a call made in an earlier message of this turn (a call in the same message is not seen yet), and make the call again. If that is held again, tell the user they can type `skip routing` in their prompt.\nThis call has no field for a line: put it on its own line in the description of a Bash call with the command true, then make this call again in a later message.",
              "is_error": true
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "response",
        "message": {
          "content": [
            {
              "type": "tool_use",
              "id": "toolu_0002",
              "name": "Skill",
              "input": {
                "skill": "using-goated-ai-skills"
              }
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "tool-result",
        "message": {
          "content": [
            {
              "type": "tool_result",
              "tool_use_id": "toolu_0002",
              "content": "ok",
              "is_error": false
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "response",
        "message": {
          "content": [
            {
              "type": "text",
              "text": "goated-route: standard | requires: tdd, doc-sync"
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "response",
        "message": {
          "content": [
            {
              "type": "tool_use",
              "id": "toolu_0003",
              "name": "Edit",
              "input": {
                "file_path": "src/export.py",
                "old_string": "limit = 1",
                "new_string": "limit = 2"
              }
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "tool-result",
        "message": {
          "content": [
            {
              "type": "tool_result",
              "tool_use_id": "toolu_0003",
              "content": "PreToolUse:Edit hook error: goated-hold: pipeline | strict\nThe current route requires `tdd`, `doc-sync` before the first write or spawn. Load each with the Skill tool and follow it. A load counts until the next compaction, in this turn or an earlier one. If one does not apply, write a corrected route line without it; the last route line wins. Put the route line on its own line in a shell or agent call's description or a Skill call's args, as this turn's first such hold explained, or tell the user they can type `skip routing` in their prompt.\nThis call has no field for a line: put it on its own line in the description of a Bash call with the command true, then make this call again in a later message.",
              "is_error": true
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "response",
        "message": {
          "content": [
            {
              "type": "tool_use",
              "id": "toolu_0004",
              "name": "Skill",
              "input": {
                "skill": "tdd"
              }
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "tool-result",
        "message": {
          "content": [
            {
              "type": "tool_result",
              "tool_use_id": "toolu_0004",
              "content": "ok",
              "is_error": false
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "response",
        "message": {
          "content": [
            {
              "type": "tool_use",
              "id": "toolu_0005",
              "name": "Skill",
              "input": {
                "skill": "doc-sync"
              }
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "tool-result",
        "message": {
          "content": [
            {
              "type": "tool_result",
              "tool_use_id": "toolu_0005",
              "content": "ok",
              "is_error": false
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "response",
        "message": {
          "content": [
            {
              "type": "tool_use",
              "id": "toolu_0006",
              "name": "Read",
              "input": {
                "file_path": "/opt/agent/.claude/skills/tdd/references/test-design.md"
              }
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "tool-result",
        "message": {
          "content": [
            {
              "type": "tool_result",
              "tool_use_id": "toolu_0006",
              "content": "ok",
              "is_error": false
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "response",
        "message": {
          "content": [
            {
              "type": "tool_use",
              "id": "toolu_0007",
              "name": "Edit",
              "input": {
                "file_path": "src/export.py",
                "old_string": "limit = 1",
                "new_string": "limit = 2"
              }
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "tool-result",
        "message": {
          "content": [
            {
              "type": "tool_result",
              "tool_use_id": "toolu_0007",
              "content": "ok",
              "is_error": false
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "hook-context",
        "message": {
          "content": [
            {
              "type": "text",
              "text": "<system-reminder>\nStop hook blocking error from command: \"python /tools/goated-adapter/goated_hook.py\": goated-hold: closeout | justified-skip\nBefore finishing this turn, which changed code:\n- Proof: no test, lint, build, or check command ran after the last code change. Run the relevant check, or, if none can run, write `goated-skip: verification-before-completion: <reason>` and tell the user it is unverified.\n- Docs: after your last code change, read the change itself and check whether durable docs now drift: print its diff with a git diff or git show command, or Read a file you changed; a listing of names or counts, such as --stat or --name-only, does not count. Or write `goated-skip: doc-sync: <reason>`.\nA skip line must name the skill and give a reason of three or more words.\n</system-reminder>"
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "response",
        "message": {
          "content": [
            {
              "type": "text",
              "text": "goated-skip: verification-before-completion: the change has no test yet and the next turn adds one\ngoated-skip: software-design-principles: one constant changes with no design in it\ngoated-skip: doc-sync: no durable docs describe the export limit"
            }
          ]
        }
      }
    },
    {
      "turnEnd": "answer"
    },
    {
      "row": {
        "door": "prompt",
        "message": {
          "content": [
            {
              "type": "text",
              "text": "Skip routing and show the diff."
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "hook-context",
        "message": {
          "content": [
            {
              "type": "text",
              "text": "GOATED Claude Code adapter: recorded your override for this prompt: \"Skip routing\"."
            }
          ]
        }
      }
    },
    {
      "row": {
        "door": "response",
        "message": {
          "content": [
            {
              "type": "text",
              "text": "goated-route: direct"
            }
          ]
        }
      }
    },
    {
      "turnEnd": "answer"
    }
  ],
  "log": [
    {
      "log": 1,
      "t": 1.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "prompt",
      "named": [
        "tdd"
      ]
    },
    {
      "log": 1,
      "t": 2.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "hold",
      "gate": "router-first",
      "kind": "strict",
      "named": [
        "using-goated-ai-skills"
      ]
    },
    {
      "log": 1,
      "t": 3.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "hold",
      "gate": "route-line",
      "kind": "strict",
      "named": []
    },
    {
      "log": 1,
      "t": 4.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "load",
      "skill": "using-goated-ai-skills",
      "cause": "hold"
    },
    {
      "log": 1,
      "t": 5.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "route",
      "form": "route",
      "intensity": "standard",
      "requires": [
        "tdd",
        "doc-sync"
      ]
    },
    {
      "log": 1,
      "t": 6.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "outcome",
      "gate": "router-first",
      "outcome": "answered"
    },
    {
      "log": 1,
      "t": 7.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "outcome",
      "gate": "route-line",
      "outcome": "answered"
    },
    {
      "log": 1,
      "t": 8.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "hold",
      "gate": "pipeline",
      "kind": "strict",
      "named": [
        "tdd",
        "doc-sync"
      ]
    },
    {
      "log": 1,
      "t": 9.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "load",
      "skill": "tdd",
      "cause": "named"
    },
    {
      "log": 1,
      "t": 10.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "load",
      "skill": "doc-sync",
      "cause": "hold"
    },
    {
      "log": 1,
      "t": 11.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "file_read",
      "file": "275604462b6c71a2"
    },
    {
      "log": 1,
      "t": 12.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "skill_read",
      "skills": [
        "tdd"
      ]
    },
    {
      "log": 1,
      "t": 13.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "ref",
      "skill": "tdd",
      "file": "references/test-design.md",
      "read_tool": true
    },
    {
      "log": 1,
      "t": 14.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "outcome",
      "gate": "pipeline",
      "outcome": "answered"
    },
    {
      "log": 1,
      "t": 15.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "change"
    },
    {
      "log": 1,
      "t": 16.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "hold",
      "gate": "closeout",
      "kind": "justified-skip",
      "named": [
        "verification-before-completion",
        "doc-sync"
      ],
      "skip_only": [
        "verification-before-completion",
        "doc-sync"
      ],
      "items": [
        {
          "label": "Proof",
          "skill": "verification-before-completion"
        },
        {
          "label": "Docs",
          "skill": "doc-sync"
        }
      ],
      "stop": true
    },
    {
      "log": 1,
      "t": 17.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "skip",
      "skill": "verification-before-completion",
      "reason": "the change has no test yet and the next turn adds one"
    },
    {
      "log": 1,
      "t": 18.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "skip",
      "skill": "software-design-principles",
      "reason": "one constant changes with no design in it"
    },
    {
      "log": 1,
      "t": 19.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "skip",
      "skill": "doc-sync",
      "reason": "no durable docs describe the export limit"
    },
    {
      "log": 1,
      "t": 20.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "outcome",
      "gate": "closeout",
      "outcome": "declined"
    },
    {
      "log": 1,
      "t": 21.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "turn_end"
    },
    {
      "log": 1,
      "t": 22.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "prompt",
      "named": []
    },
    {
      "log": 1,
      "t": 23.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "override",
      "phrases": [
        "skip routing"
      ]
    },
    {
      "log": 1,
      "t": 24.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "route",
      "form": "direct"
    },
    {
      "log": 1,
      "t": 25.0,
      "adapter": "claude-code",
      "session": "recorded-session",
      "project": "0123456789",
      "type": "turn_end"
    }
  ],
  "logText": "{\"log\": 1, \"t\": 1.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"prompt\", \"named\": [\"tdd\"]}\n{\"log\": 1, \"t\": 2.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"hold\", \"gate\": \"router-first\", \"kind\": \"strict\", \"named\": [\"using-goated-ai-skills\"]}\n{\"log\": 1, \"t\": 3.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"hold\", \"gate\": \"route-line\", \"kind\": \"strict\", \"named\": []}\n{\"log\": 1, \"t\": 4.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"load\", \"skill\": \"using-goated-ai-skills\", \"cause\": \"hold\"}\n{\"log\": 1, \"t\": 5.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"route\", \"form\": \"route\", \"intensity\": \"standard\", \"requires\": [\"tdd\", \"doc-sync\"]}\n{\"log\": 1, \"t\": 6.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"outcome\", \"gate\": \"router-first\", \"outcome\": \"answered\"}\n{\"log\": 1, \"t\": 7.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"outcome\", \"gate\": \"route-line\", \"outcome\": \"answered\"}\n{\"log\": 1, \"t\": 8.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"hold\", \"gate\": \"pipeline\", \"kind\": \"strict\", \"named\": [\"tdd\", \"doc-sync\"]}\n{\"log\": 1, \"t\": 9.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"load\", \"skill\": \"tdd\", \"cause\": \"named\"}\n{\"log\": 1, \"t\": 10.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"load\", \"skill\": \"doc-sync\", \"cause\": \"hold\"}\n{\"log\": 1, \"t\": 11.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"file_read\", \"file\": \"275604462b6c71a2\"}\n{\"log\": 1, \"t\": 12.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"skill_read\", \"skills\": [\"tdd\"]}\n{\"log\": 1, \"t\": 13.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"ref\", \"skill\": \"tdd\", \"file\": \"references/test-design.md\", \"read_tool\": true}\n{\"log\": 1, \"t\": 14.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"outcome\", \"gate\": \"pipeline\", \"outcome\": \"answered\"}\n{\"log\": 1, \"t\": 15.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"change\"}\n{\"log\": 1, \"t\": 16.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"hold\", \"gate\": \"closeout\", \"kind\": \"justified-skip\", \"named\": [\"verification-before-completion\", \"doc-sync\"], \"skip_only\": [\"verification-before-completion\", \"doc-sync\"], \"items\": [{\"label\": \"Proof\", \"skill\": \"verification-before-completion\"}, {\"label\": \"Docs\", \"skill\": \"doc-sync\"}], \"stop\": true}\n{\"log\": 1, \"t\": 17.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"skip\", \"skill\": \"verification-before-completion\", \"reason\": \"the change has no test yet and the next turn adds one\"}\n{\"log\": 1, \"t\": 18.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"skip\", \"skill\": \"software-design-principles\", \"reason\": \"one constant changes with no design in it\"}\n{\"log\": 1, \"t\": 19.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"skip\", \"skill\": \"doc-sync\", \"reason\": \"no durable docs describe the export limit\"}\n{\"log\": 1, \"t\": 20.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"outcome\", \"gate\": \"closeout\", \"outcome\": \"declined\"}\n{\"log\": 1, \"t\": 21.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"turn_end\"}\n{\"log\": 1, \"t\": 22.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"prompt\", \"named\": []}\n{\"log\": 1, \"t\": 23.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"override\", \"phrases\": [\"skip routing\"]}\n{\"log\": 1, \"t\": 24.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"route\", \"form\": \"direct\"}\n{\"log\": 1, \"t\": 25.0, \"adapter\": \"claude-code\", \"session\": \"recorded-session\", \"project\": \"0123456789\", \"type\": \"turn_end\"}\n"
} as const
