---
name: pr-description
description: Use when the user asks to draft or revise a pull request or merge request description.
metadata:
  goated-category: engineering
---

# PR Description

## Purpose

Draft the body of a pull request from the actual change set so a reviewer can
see what changed, the evidence that it works, and how risky it is to merge.

This skill is read-only. It returns description text and never opens, edits,
labels, merges, or publishes a pull request.

## Inputs

- User request, originating intent, and the target-project root.
- The change under review: commits and diff since a fixed point, or a supplied patch.
- An existing pull request template or contribution guide, when the project has one.
- Verification evidence: test output, command results, screenshots, review gates, skipped checks, or known failures.
- The project's documented domain language, when present.

## Dependencies

Hard: None.

Soft:
- verification-before-completion before the description claims passing checks, completion, or review readiness
- commit-message when the user also wants commit text for the same change

Fallback: Without Git metadata, a spec, or verification evidence, describe the
inspected patch, state lower confidence, and leave Evidence marked as not
gathered rather than inventing checks.

## Workflow

1. Fix the scope:
   - Identify the base the change will merge into. Use the one the user names; otherwise infer it from the branch upstream or the project's trunk, and say which you used.
   - Read the commit list and the diff against that base with read-only commands. Include untracked files the change depends on.
   - If the diff contains unrelated work, describe only the change the request is about and name what you left out.

2. Choose the shape:
   - Follow the project's pull request template when one exists, filling its sections from the steps below.
   - Otherwise use Summary, Evidence, and Merge Risk.

3. Write the Summary:
   - Lead with one or two sentences on what changes for a user or maintainer and why.
   - Add the smallest view that makes the key point clear, placed next to the sentence it supports. Read [Summary Views](references/summary-views.md) to pick one.
   - Use the project's own terms. Skip preamble and restated ticket text; link the ticket or spec instead.

4. Write the Evidence:
   - Show before and after: the failing and then passing check, the old and new output, or screenshots for a visual change.
   - Use only evidence that was actually produced for this change. Name the command or check and its observed result.
   - When no evidence exists, say so plainly and list what a reviewer would need to run.

5. Write the Merge Risk:
   - Reversibility: say whether the change can be rolled back cheaply, or whether it includes a migration, deletion, public contract change, or other step that is hard to undo.
   - Blast radius: name what could be affected beyond the changed code, such as consumers, data, configuration, performance, or other platforms.
   - State what the reviewer should look at hardest.

6. Self-check and return:
   - Confirm every claim matches the inspected diff, not the original plan.
   - Remove secrets, private data, and internal identifiers that do not belong in the project's public history.
   - Return the finished description first.

## Output Contract

Return the description in one block the user can paste:

````markdown
```markdown
## Summary

<what changes and why, with the smallest clarifying view>

## Evidence

- **Before:** <failing check, old output, or screenshot>
- **After:** <passing check, new output, or screenshot>

## Merge Risk

**Reversibility:** <easy to roll back | hard to undo, and why>

**Blast radius:** <what could be affected beyond the changed code>
```
````

After the block, include only material context: the base used when it was
inferred, excluded changes, and evidence gaps. In integrated use, return the
description plus any scope or risk delta to the main agent, not a competing
task closeout.

## Delegation

Main owns scope, wording, and risk judgment. Delegate only bounded diff reading,
evidence collection, or a draft review, and require inspected paths, commands,
and findings. Without delegation, run the same steps sequentially.

## Guardrails

- Do not open, edit, label, merge, close, or comment on a pull request, and do not push, without separate explicit authorization.
- Draft from the inspected diff, not from the ticket or plan alone.
- Claim that tests, CI, reviews, or security checks passed only with evidence; keep skipped checks and failures visible.
- Report risk as it is. A hard-to-undo step is stated even when the change is small.

## References

- [Summary Views](references/summary-views.md) - read when choosing how to show the change in the Summary.
