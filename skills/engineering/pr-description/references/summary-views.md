# Summary Views

Read this when writing the Summary of a pull request description. A view is a
compact picture of the change that a reviewer can take in before opening the
diff. Pick the one that matches what changed. Most descriptions need one view;
a few need two; none need all of them.

Keep only the calls, files, states, and names needed to make the point. A view
that reproduces the diff adds nothing.

## Pick By What Changed

| What changed | View |
| --- | --- |
| A rule, algorithm, or decision | Short pseudocode |
| Who calls what, or the order of calls | Indented call tree |
| Where responsibilities live | Shallow file tree with one-line roles |
| How components or services talk | Sequence or flow diagram |
| A small change inside a known shape | Diff sketch of that shape |
| A mostly new unit | The whole target shape |

## Examples

Logic as pseudocode:

```text
on save
  if content is unchanged
    return the cached result
  write the new content
  return a fresh result
```

Control flow as a call tree:

```text
submit_order
  validate_cart
  reserve_stock
    notify_warehouse
  charge_payment
```

Responsibilities as a file tree:

```text
src/
  commands/    parses user actions
  sessions/    owns session state
  transport/   sends requests
```

A change inside an existing shape, as a diff sketch. Match the sketch to the
subject: a call tree for control flow, a file tree for layout, pseudocode for
logic.

```diff
 submit_order
   validate_cart
+  check_credit_limit
   reserve_stock
-  charge_payment
+  charge_payment
+    record_receipt
```

Use a diagram language such as Mermaid only when the relationship is genuinely
graph-shaped and the project's review tool renders it. Otherwise indented text
reads everywhere.

## Evidence Strength

Rank evidence by how directly it shows the behavior:

1. A screenshot or recording, for a visual change.
2. Output from running the change: the test that failed and now passes, or old
   and new command output.
3. A reasoned argument from the code. Use it only when nothing can be run, and
   say that it was not executed.
