---
name: simplification-pass
description: Light simplification pass on the diff of a card, feature or fix, run at the end of each card before the final tests, the review and the commit. One reviewer instead of the four of /simplify, with a targeted brief and four angles (reuse, simplification, efficiency, level of the fix). Use when a card ends, or when the user asks for a simplification pass (« passe de simplification »), a diff cleanup or a lighter /simplify.
license: MIT
---

# Simplification pass

At the end of each card, one simplification pass on its diff: this is when it costs the least and
sees the most, before copies spread.

The method is the same in every project and is at the end of this file. What changes from one
project to the next (where to look, house rules, test commands, closing order) lives in a marked
section of the project's `AGENTS.md`.

Ask questions in the user's language. Write files and answer in the languages the project chose,
noted on one line in its root `AGENTS.md`.

## When

- At the end of each card, feature or fix, on its diff only.
- **Not for** a change to docs only, to tests only, or to a single line.
- **Small card** (no new logic: wiring a field, texts, a setting): no reviewer. Read the diff
  yourself with the four angles of the "Review method" section, then go to step 4.
- The pass does not look for bugs. For that, use `/code-review` in Claude Code, or the review the
  project provides.

## Step 1: read the project's section

Look for the marker `<!-- mirepoix:simplification-pass -->` in the project's `AGENTS.md` files (at
the root and in each repository). **Search the files themselves**, because a tool can remove HTML
comments from the copy it keeps in context. The heading next to the marker can be anything, in any
language. The section runs from the marker to the next heading of the same or a higher level.

It gives:

- the closing order (where the pass sits relative to the tests, the review and the commit);
- where the shared pieces to reuse live (utilities, components, test helpers…);
- the house rules the pass must respect;
- the test commands to run after the pass;
- where to note what is seen outside the diff (roadmap, card, notes).

No section: stick to the four angles, find the shared folders in one search (`utils`, `lib`,
`helpers`, `components`, `composables`, `core`, `shared`), and tell the user the project has no
section, offering to write one in the language of its documents:

```markdown
<!-- mirepoix:simplification-pass -->
## Simplification pass

- Closing order: …
- Shared pieces: …
- House rules: …
- Test commands: …
- Seen outside the diff: …
```

## Step 2: prepare the brief

The brief replaces the reviewer's search phase: that is where the saving comes from.

1. **The diff**, in `.mirepoix/simplification.diff` at the root of the repository, one file per
   repository. A reviewer can read a file inside the project without asking for permission, which
   is not the case for a file elsewhere. On the first pass, also write `.mirepoix/.gitignore` with
   the single line `*`: git then ignores the folder, with no change to the repository. Write
   `git diff HEAD` plus the untracked files if the card is not committed, otherwise the range of its
   commits. Leave out secret files (`.env`, keys, credentials): an untracked file is not always an
   ignored one. If the file cannot be written, paste the diff into the brief.
2. **The files to compare**, named one by one:
   - the shared modules given by the project's section;
   - the twins of the added code (same feature, same type of file: another form, another hook,
     another service);
   - the open cards or review notes on these files, if any.
3. **The size**: beyond about 1,000 lines of diff, or if the card touches several repositories with
   a lot of code in each, one reviewer per repository. Otherwise, one reviewer.

## Step 3: run the review

Once the diff file is written, take the first option your tool offers.

1. **The `mirepoix:reviewer` agent** (Mirepoix plugin for Claude Code), in the background, with no
   `model` or `effort` override. Its only tools are Read, Grep and Glob, so it cannot change
   anything. While it runs, prepare what comes next (test data, acceptance checks). The prompt
   carries only the brief:

   ```text
   Diff: <path of the file>
   Files to compare: <list>
   Project rules: <house rules from the project's section, in a few lines>
   Method: <the "Review method" section of this file, copied as it is>
   ```

2. **Another read-only subagent**: give it the same brief. Tell the user.
3. **No subagent**: do the review yourself, following the "Review method" section.

## Step 4: apply

- Deduplicate the findings, then apply those that keep the behaviour identical.
- Set aside, with the reason, false positives, anything outside the diff, and any shared piece that
  would cost more lines than it removes.
- A line that no test runs and that the pass changes first gets its test, green on the code as it
  was.
- A defect is fixed in a separate `fix` commit, with its test written first. If the fix changes what
  the user sees, ask for their agreement first.
- What is seen outside the diff is noted where the project's section says, never in the card's
  commit.
- Then run the project's tests: they are what validates the simplified version. Then follow the
  project's closing order.

## Step 5: report

In a few lines to the user: what was simplified, what was set aside and why, the defects awaiting
their decision, and the line balance of the application code.

## Review method

You are running a simplification pass on the diff of a card, feature or fix. You are not looking for
bugs.

Check, for the code in the diff only:

1. **Reuse**: a component, helper, translation key, fixture or native framework function that
   already exists and that the diff rewrites.
2. **Simplification**: a derivable state or value, a copy with a variation, dead code, a needless
   indirection, a comment that no longer matches the code.
3. **Efficiency**: duplicate work or calls, a query rerun for nothing, a cache key shared by mistake
   or badly shared, a needless render, a timer or listener that outlives its use.
4. **Level of the fix**: a special case added to shared code, a workaround where the native
   mechanism would do the job.

Constraints:

- Same behaviour and same rendering: a proposal changes neither an API response, nor a text, nor a
  style, nor the navigation.
- Sharing a piece costs lines (imports, types, docs): two copies are often better than an
  abstraction. From three copies on, propose the shared piece.
- A bug seen in passing: report it separately, marked DEFECT, without fixing it.

Report: at most 10 findings, the most useful first. For each one: file:line, the problem in one
line, its concrete cost, the proposed change (precise enough to apply), and the risk (visible?
changes the behaviour? touches a line that no test runs?). Then, in one line each, what you looked
at and left alone. Under 800 words.
