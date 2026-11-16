# Names, Comments And Obvious Code

Read this when choosing a name, deciding whether and what to comment, checking comments near a change, or making code obvious to a first-time reader.

These are guidelines for judgement. Project instructions, a project's own standards, and the user's requests take priority. `[PP ...]` and `[APoSD ...]` mark which book an idea comes from.

## Contents

- [Names, comments and obvious code](#names-comments-and-obvious-code)
  - `#obvious` Write for the reader
  - `#naming` Choose names with care
  - `#comments` Comment what the code cannot say
  - `#comments-first` Write the comment first
  - `#keeping-comments-true` Keep comments true
  - `#consistency` Be consistent

<!-- id: #readability -->

## Names, comments and obvious code

Obscurity is one of the two causes of complexity (`#complexity-symptoms`). This part is the cure. The aim is code where a reader's first quick guess about what something means turns out to be right.

<!-- id: #obvious -->

### Write for the reader [APoSD ch.18]

**Rule:** Code is obvious when someone can read it quickly and their first guess about what it does is correct.

1. **Design it away.** Change the code so the information is no longer needed, for example by removing a special case.
2. **Lean on what readers already know.** Follow the conventions of the language and the project.
3. **State it.** Use a precise name or a comment.

**Things that hide meaning**

- **Anonymous tuples and pairs** returned from functions. Use a small named type.
- **Code that runs at a distance**, such as event handlers and callbacks. Say in the comment when and by what it is called.
- **Surprises.** A constructor that starts background threads, a function called `get_data` that writes a file. If code does something a reader would not expect, say so right there.
- **Cramped layout.** Use blank lines between the steps of a function, with a short comment opening each step.

> **Red flag: Nonobvious Code.** You cannot tell what a piece of code does or means from a quick read.

> **The principle behind it.** Software should be designed for ease of reading, not ease of writing. A shortcut that saves the writer two minutes costs every later reader.

<!-- id: #naming -->

### Choose names with care [APoSD ch.14] [PP topic 44, Tip 74]

**Rule:** A good name creates the right picture in the reader's mind, is precise, and always means the same thing.

| Weak name | Problem | Better |
| --- | --- | --- |
| `count` | Count of what? | `active_user_count` |
| `x`, `y` for a place in a text file | Suggests screen pixels | `line_index`, `char_index` |
| `blink_status` | What does true mean? | `cursor_visible` |
| `result` for something that is not returned | Misleading and empty | `merged_line` |
| `user` on a shop site | Says nothing about the role | `customer` or `buyer` |
| `deduct_percent(amount)` | Says how, not why. Is amount 0.2 or 20? | `apply_discount(discount: Percentage)` |

- **Test it alone.** If someone saw only this name, how well could they guess what it holds?
- **Name the role,** not the mechanism. Ask "why does this exist?"
- **Booleans read as true-or-false statements:** `is_empty`, `has_children`, `cursor_visible`.
- **One name, one meaning.** Use the same word for the same thing everywhere, and never for anything else.
- **Drop words that add nothing:** `file_object`, `name_string`, `data`.
- **Longer names for wider reach.** `i` is fine in a three-line loop. A value used across a whole module needs a full name.
- **Rename when the meaning drifts.** A wrong name is worse than a meaningless one, because readers believe it. (PP Tip 74)
- **Use the project's words.** Keep a short glossary so code, documents and users all mean the same thing by each term. (PP Tip 80)

> **Red flags: Vague Name, Hard to Pick Name.** **Vague name:** broad enough to mean many things. **Hard to pick name:** if no simple name fits, the thing itself may be doing two jobs. Treat naming trouble as a design signal.

<!-- id: #comments -->

### Comment what the code cannot say [APoSD ch.12, 13] [PP topic 7]

**Rule:** A comment earns its place by telling the reader something they could not get from the code next to it.

**What each kind of comment should contain**

| Kind | Where | What it says |
| --- | --- | --- |
| **Interface** | On every class and function | What it does as seen by the caller. Each argument and the result. Side effects. Errors raised. What the caller must ensure first. Nothing about how it works inside. |
| **Field or variable** | Beside the declaration | What it represents, as a noun. Units, limits, what a missing value means. Not a list of the places that change it. |
| **Inside a function** | Before each step of a long function | What the step achieves and why. Often not needed in short functions. |
| **Cross-module** | Wherever people will find it | A decision that spans several files. Write it once and point to it from the other places. |

> **Red flags: Comment Repeats Code, Implementation Documentation Contaminates Interface.** The first: a comment says only what the code beside it already shows. The second: an interface comment that explains internals the caller does not need. If you cannot describe a function without describing how it works, the function is probably shallow.

**The four excuses for not commenting**

| Excuse | Answer |
| --- | --- |
| "Good code documents itself." | Only the part the language can express. Reasons, meanings and usage rules are not in the code. |
| "I have no time." | Typing is a small part of development. Comments cost a few percent and repay it quickly. |
| "Comments go out of date." | Keep them next to the code, write each thing once, and check them when reviewing changes. |
| "The comments I have seen are useless." | Then write better ones. It is a learnable skill. |

> **Where the books agree and differ.** Both say comments should explain *why*, and both say a comment that restates the code is a DRY violation. They differ on quantity. Ousterhout wants a comment on every class, function and field. Thomas and Hunt warn against commenting everything mechanically. See Where the books differ (`#differences`).

<!-- id: #comments-first -->

### Write the comment first [APoSD ch.15]

**Rule:** Write the interface comment before the body. If it is hard to write, the design is wrong, and you have found out for free.

1. Write the comment for the class: what it represents.
2. Write the signature and comment for each main function, with empty bodies.
3. Adjust until the set reads well together.
4. Add the main fields with their comments.
5. Fill in the bodies.

> **Red flag: Hard to Describe.** A function or variable needs a long comment to describe it completely. Go back and simplify the thing being described.

<!-- id: #keeping-comments-true -->

### Keep comments true [APoSD ch.16]

**Rule:** A comment far from its code will not be updated. Keep each one close, and write each fact once.

- **Close to the code.** Put each comment right above the lines it describes, in the smallest block that covers them.
- **The further away, the more general.** A comment at the top of a file should speak in broad terms, which survive small changes.
- **In the code, not only in the commit message.** If a future reader needs to know why something is the way it is, they will look in the file.
- **Once.** Document each decision in one obvious place and point to it from the others. A broken pointer is easy to notice. A stale copy is not.
- **Do not re-explain other code.** A caller should not describe what the called function does. Link to outside documentation; do not retell it.
- **Read your own diff before committing** and check every comment near a change.

<!-- id: #consistency -->

### Be consistent [APoSD ch.17] [PP topic 44]

**Rule:** Do similar things in similar ways. Then learning one part of the system teaches you the rest.

- **When in Rome.** Before writing in a file, read around it and follow what is there.
- **Write conventions down** where newcomers will find them.
- **Enforce with tools** where you can: formatters, linters, checks before commit. People forget; scripts do not.
- **Do not change a convention because you have a better idea.** A consistent codebase is worth more than a slightly better style in one file. Change it only with real new information, and then change it everywhere.

> **Do not overdo it.** Consistency also means different things should look different. Forcing unlike things into one pattern misleads the reader.
