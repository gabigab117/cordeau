# Harness for an existing project

This file adapts the steps of the skill to a project that already has code. In a conflict, it wins.

Rules marked **if** apply only when the inventory, the exploration and the interview confirm the
condition. Say in the plan which ones you keep and why.

## Two deliverables

1. **A base harness**: what holds whatever the work to come (stack and commands, conventions, tone,
   guardrails, rules on tests and refactoring) and the way of working below. It creates no roadmap and no
   card until the user starts a task.
2. **If the project is large or risky to change, a private state of the project**, outside the repository,
   to help the user decide: the areas of the code and their role, the critical paths, what is tested, the
   riskiest areas to change, refactoring candidates ranked by interest and risk, where to start the tests. It
   ends with three to five options for a first task, each with its interest, its risk and its size.

## An old instruction file

A `CLAUDE.md`, or an `AGENTS.md` without the marker, is sorted, and what stays is rewritten shorter in `AGENTS.md`,
next to the rules of the base. Report the size of both files: after a short old file, the new one can be longer, and
you say why. Show the sorting in the plan:

| Rule found | What happens to it |
|---|---|
| Already covered by a piece of the catalog | Replaced by that piece |
| Proper to this project | Kept, shorter, with its reason |
| Describes the code or the file tree | Dropped |
| Can be verified by a machine | Moves to a hook, a pre-commit check or CI |

Claude Code does not read `AGENTS.md` while a `CLAUDE.md`, `.claude/CLAUDE.md` or `CLAUDE.local.md` exists in
the folder or above it. Remove or move these files only with the user's agreement, given in the plan. Lose
nothing: what is dropped stays in the history of the repository, or in the private document if the old file was
not versioned.

## The way of working, written right away

Write these two rules now, even if no task has started.

- **All work goes through a roadmap** (pieces 2 and 10). A task starts with its roadmap: its objective, its
  decisions, its cards. The user approves it before any code. The harness sets the format of a roadmap and of a
  card, where they live, and the rule to read them before working.
- **The simplification pass at the end of each code change** (piece 11). It applies its own thresholds. Write
  the section it expects, with:
  - the closing order: code and green tests, then the pass, then the security pass if the card reaches a sensitive
    part, then the checks again, then the commit;
  - the shared pieces to compare, found during exploration;
  - the house rules: same behaviour, neutral tone, no reformatting mixed with logic;
  - the test commands to run again;
  - where to note what is seen outside the diff.

## The tone of what is versioned

Harness files, comments, commit messages, pull requests and tickets can be read by those who wrote the code. They
stay factual and neutral.

- They describe what is ("not covered by tests", "called from three views", "depends on the order of the signals")
  and what is being done.
- They carry no judgment on the code or its authors: no adjective, no remark drawn from `git blame`.
- A frank diagnosis stays in the conversation, or in a private document outside the repository.

## Sources of truth

- **The scope is what exists.** Roadmaps come with tasks, and describe what changes, not what is.
- **If the project is in production, its behaviour rules, bugs included**: users rely on it. A surprising behaviour
  is reported and decided. It is never fixed in passing.
- **The shape of the code does not rule.** The `AGENTS.md` separates the conventions to keep, because they are regular
  and consistent with the framework, from the target for new code, where the existing code varies. For each gap, the
  plan proposes and the user decides.
- **Neighbouring files are not a model.** New code follows the conventions kept in the `AGENTS.md`, even when the next
  file does otherwise. Write this rule with its reason: imitating a neighbour spreads its variations.

## A safety net before any change

**If the code has few tests**, nothing proves that a change breaks nothing. The net comes before any refactoring.

- **The likely first task**, to be sized in the private state of the project:
  1. a reproducible local environment: installation, development database, fictional data;
  2. the test tooling: configuration, object factories, a test database of the same engine as production;
  3. end-to-end or integration tests on the critical paths, fixing the current behaviour, with a list of paths drawn up
     with the user;
  4. a CI that runs them at each push.
- **The rule for any change**: before changing untested code, write **characterisation tests** that fix its current
  behaviour, green on the code as it was. Only then change it. A strange behaviour revealed by a test is noted, not
  fixed on the spot.
- **No global coverage floor, but a ratchet.** Total coverage never drops, and the code changed by a diff is covered,
  with a diff coverage tool chosen from the documentation of the stack.

## Refactoring, never in bulk

- **Refactoring is a task, not a side effect.** It happens when the user asks, on the area they name, once the
  characterisation tests are written. It moves in small steps with identical behaviour, each in its commit, tests green
  at each step.
- During another task, no opportunistic rewrite: what would deserve one becomes a proposal.
- **A formatter or a linter comes in file by file.** A touched file is first formatted, in a separate commit with no
  other change, then modified. The `AGENTS.md` gives the exact command to format one file. A full reformatting happens only if the user decides so, in a single commit listed in
  `.git-blame-ignore-revs`.
- Pre-commit only runs on changed files, its default behaviour. Never `--all-files` without the user's agreement,
  including at the verification step of the skill.
- Hooks and CI follow the same limit, so that existing code does not keep them red: no format-after-write hook, and a
  `Stop` hook or a CI job that checks changed files only. Test tooling and the ratchet belong to the first task, not to
  this session. At the verification step, a failure from existing code is reported, never fixed.
- What is seen outside the work area becomes a proposal, noted in the "To take up" section of the current roadmap, never
  an addition to the commit.

## Installed versions

Dependencies can be behind. Documentation is read **for the installed version**, the one in the lockfile, not the latest. An
upgrade is a task of its own, never a side effect.

## Mapping the code

**If the repository is too large to read in one conversation**, use subagents in parallel if your tool has them, one per major
area, and keep only their conclusions: the areas and their responsibilities, the critical paths and the code they go through,
what has tests, dependencies and versions, deployment, the less visible entry points (signals, scheduled tasks, management
commands, webhooks).

The factual map can be versioned in a document of its own, never in an instruction file. The ranking of risks stays
private.

## Extra guardrails

**If the project is in production:**

- A hook blocks anything that touches production: deployment, migrations or commands run with production settings, access to the
  production database. If you cannot tell where the local settings point (an unread `.env`), it also refuses the commands of the
  framework until the user confirms. Build it on the parsing of `scripts/guardrails.py`, not on a regular expression, and remember that
  a text reader leaks: the sandbox is the second wall.
- No writing to real data, even to try.

## Security on existing code

- A dependency audit or a configuration check that already fails is reported, never fixed in passing. The plan says how the
  CI job starts, reporting only or with a dated list of known findings, and the user decides. An upgrade is a task of its own.
- The security rules of the linter follow the limit of any lint: changed files only.
- A command that reads `.env` itself fails in the sandbox. Do not open the file and do not take the command out of the
  sandbox on your own: give it fictional values in front of the command or a test configuration, or let the user decide.
- A flaw seen while exploring is stated as a fact in the conversation or the private document, in a neutral tone, and is never
  fixed during this session. In the versioned security section, name the places, not the flaws.

## Extra interview questions

Add them to those of the skill, and leave out what the code already answers: stay close to a dozen in all.

- Is the former developer reachable for questions? They remain the best source on a surprising behaviour.
- Which paths must never break?
- What is the priority: stabilising, delivering features, and in what proportion?
- Is there a staging environment, demo data, read access to production?
- Who else works, or will work, on the repository and will read the harness files?
- Where to keep roadmaps and private documents (state of the project, decisions)?

## Definition of Done for an existing project

In addition to the one of the catalog. Items 1 and 2 apply if the code has few tests, item 4 if the project is in
production.

1. characterisation tests written before the change, green before and after;
2. changed code covered, total coverage stable or rising;
3. no reformatting mixed with a logic change;
4. behaviour in production unchanged, unless decided in writing;
5. simplification pass done, security pass if the card asks for it, and checks run again after them;
6. card marked done.
