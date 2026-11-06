# Catalog of the harness pieces

Each piece says the problem it solves. Keep the principle, not any example: if the problem does not
exist in this project, the piece has no place here, and you say so in the plan. Tools are chosen from
the documentation of the project's stack, never from this file.

## 1. A hierarchy of sources of truth

**Problem**: without an arbiter, the model fills gaps by inventing scope, or settles alone between
two sources.

- One document rules on **scope**, usually the README of the roadmap. What is not in it does not
  exist. It holds an explicit "Out of scope" list.
- Every other source has a written status: the mockup rules on the interface, except for the listed
  differences; an existing system is a business reference, not a source of code; and so on.
- **A contradiction is reported, never settled in silence.** This is the rule that protects the most.
- **Decisions** are dated and numbered (D1, D2…, with their revisions), and so are **arbitrations**
  (A1…). A "To settle before the phase" section keeps the open questions.

## 2. A roadmap in phases and cards

**Problem**: a vague request gives a vague diff, and a session does not know where the project stands.

- A phase is an increment that can be delivered and tested. Its header says what it delivers, its
  reference documents and the decisions taken with its plan.
- A card holds an **objective**, **tasks**, **dependencies** and the expected tests. A blocking
  question becomes an arbitration card at the top of the phase, handled before any code.
- When a phase computes something (amounts, stock, availability), it carries a **reference scenario
  with figures**, on fictional data. It gives their values to the tests and to acceptance.
- A finished card is marked done in the same commit as its work. The roadmap is the dashboard of the
  project.

## 3. Layered, short `AGENTS.md` files

**Problem**: a single long file dilutes the important rules and costs context at every session.

- One **root** file for what crosses repositories: the workflow, the contracts between repositories,
  the principles.
- One file **per repository** for its own rules: conventions, tooling, architecture, tests, Definition
  of Done. It reads on its own.
- Each rule carries **its reason**, the risk it covers. A rule without a reason is badly applied to
  neighbouring cases.
- **Under 200 lines per file**: beyond that, rules are less well followed. An import saves nothing,
  since the imported file loads at startup.
- An `AGENTS.md` does not paraphrase the code. What concerns only one folder loads only when working
  there: a path rule (`.claude/rules/*.md` for Claude Code) or a file in that folder. Check which one
  your tools discover from the folder where sessions start. What serves only one task (deploying,
  taking screenshots, migrating data) becomes a skill. What explains a module goes in its docstring.

## 4. Up-to-date documentation before any library code

**Problem**: training memory is dated, and the reflexes of a neighbouring stack are wrong in this one.

- The rule is mandatory: Context7 if available, then the official documentation, then the installed
  source code. Never from memory.
- Write **the trap proper to this stack** next to the rule: it is what makes the rule credible.

## 5. "Reinvent nothing", with a trigger

**Problem**: a validator, a sort helper or a uniqueness check written by hand where the framework
already did the work.

- The trigger is concrete: code that *looks like* a framework feature (validation, uniqueness,
  filtering, sorting, pagination, permissions, dates, files).
- The native way is searched **before** writing. If it is set aside, a comment says why.

## 6. A business glossary

**Problem**: the same concept gets three names from one session to the next.

- A table "business word → name in the code", in a document of its own, outside the files loaded at
  every session. A new word enters it before being used. A name that departs from it is a defect.
- It is necessary when documents and code do not share a language. If they share one with a stable
  vocabulary, set it aside and say so.

## 7. Mechanical guardrails rather than prose

**Problem**: a written rule gets forgotten; a rule verified by a machine does not.

- **What a machine can verify is verified by a machine.** The `AGENTS.md` says why, the tool enforces.
- Pre-commit and CI run the same checks: lint and format, migrations up to date, secret detection,
  contract exported and validated.
- Coverage has a floor checked in CI, adapted to the project.
- A contract between repositories is **generated** on one side and checked on the other in CI. The
  push order follows from it.
- "Done" means a green CI, and a successful staging deployment if there is one.

## 8. Tool settings: permissions and hooks

**Problem**: a ban written in an `AGENTS.md` or in memory prevents nothing.

- Each ban that can be stated as a command or a path becomes a versioned setting of the tool. In
  Claude Code, `.claude/settings.json`: a `deny` rule for a file (`Read(.env)`), a `deny` rule or a
  hook for a command.
- A `deny` rule on Bash compares the text of the command: `git -C . push` passes through
  `Bash(git push *)`. A command that must really be blocked goes through a `PreToolUse` hook that reads
  it and refuses (exit code 2, reason on stderr). The Mirepoix plugin already does so for force-push,
  `reset --hard`, `checkout --` and `restore`: add only what is proper to the project.
- Hooks also serve what must happen every time: formatting after a write, or an end-of-task check that
  sends the model back to work with a reason (`Stop`). Check in the documentation how to avoid an
  endless loop.
- An allow list for frequent read and test commands reduces permission prompts.

## 9. A Definition of Done per repository

**Problem**: each session has its own idea of "done".

- A short, numbered, verifiable list: documentation read, checks passed, tests written (error cases and
  permissions included), contract regenerated, CI green, card marked.

## 10. The workflow

**Problem**: the model chains too much, or not enough, and the user loses track.

- The cards concerned and the README are read before any feature, and a non-trivial feature starts with
  a plan: steps, files, tests.
- The pace is written down: one card at a time then stop, or a whole phase when the user asks for it.
- Conventional commits, in the repository concerned, and a push after each card if the remote serves as
  a backup.
- A validation is requested through a short numbered checklist, separate from the report.
- Moving from documents to code is announced.

## 11. The simplification pass at the end of a card

**Problem**: copies and indirections settle in card after card, and cost more to remove later.

- The **method** lives in the `simplification-pass` skill. The **parameters** of the project live in a
  section of its `AGENTS.md`, marked `<!-- mirepoix:simplification-pass -->`: the closing order, the
  shared pieces to compare, the house rules, the test commands to run again, where to note what is seen
  outside the diff.
- Write this section; the skill reads it.

## 12. Memory, for the way of working

**Problem**: a preference corrected once comes back at every session if it is noted nowhere. For tools
that have a memory.

- Memory keeps the user's preferences and feedback, with **why** and **how to apply**.
- **No runbook in memory**: a recurring procedure (deploying, screenshots, server access) becomes a
  skill or a versioned document. Memory is neither versioned nor shared.
- A ban in memory that can become a `deny` rule becomes one (piece 8).

## 13. Public repositories, secrets, data

**Problem**: a public repository is a shop window. Real data or a secret stays there forever.

- Fictional data only, in tests as in the demo set.
- Secrets and server access live in the CI secrets and in the server's `.env` files. Versioned templates
  only keep placeholders.
- No client or third-party name in a public repository. Sensitive documents go in a private one.
- Personal data: store only what a card asks for, and any card that adds some updates the privacy page.

## 14. Local conventions

Time zone (stored in UTC), date and amount formats, language of the interface and of the code. One rule
per subject, and one utility that applies it.

## Traps to avoid

- **Copying thresholds without discussing them.** Full coverage, end-to-end tests against a real back,
  one card at a time: these are choices of a given project. A prototype or a script does not need them.
- **Writing a huge harness on the first day.** The skeleton is enough. Afterwards, each observed trap
  enters at its place, with its reason, in the session that observes it.
- **Describing the code instead of setting the behaviour.** An `AGENTS.md` says what to do and why; the
  code and its comments say how it works.
- **A rule without a check when a check is possible.**
- **Duplicating a rule between the root and a repository.** The root refers to the repository instead.
