# Cordeau

> The straight line for every AI-coded project.

**Beta, version 0.1.0.** Expect changes between versions.

A cordeau is the line a mason stretches so that every row stays straight. A harness does that for AI coding sessions: instructions, a roadmap, automatic checks and settings keep them consistent. Cordeau sets one up for your project. It interviews you, shows you what it will write, writes it, then proves that the checks refuse a bad commit.

You need Python 3 (`python3`), and Claude Code 2.1.277 or later for the plugin. The plan names any other tool, such as `pre-commit`.

## How it works

1. You ask, in your project: "set up the harness". It never starts on its own.
2. It reads the project and the documentation of its tools, then asks about a dozen questions. Nothing is written yet.
3. You approve a plan that shows each file, the exact content of each setting, hook and check, and what is left out, with the reason.
4. It writes the files. Then it tries the checks on a fake secret and a lint defect, tries the sandbox on a fictional secret file, and measures its files.

On an existing project, it changes no existing code.

Then, at the end of each card (a task of the roadmap), two passes review the uncommitted diff: one to simplify it, one to find security flaws.

## What you get

| Piece | What it does | Works with |
|---|---|---|
| `harness-setup` skill | Sets up or updates the harness, whatever the stack | Agent Skills tools |
| `simplification-pass` skill | Reads the diff of a card for reuse, needless complexity, wasted work and fixes at the wrong level | Agent Skills tools |
| `security-pass` skill | Reads the diff of a card for access, input, secrets, dependencies, configuration and weakened guardrails | Agent Skills tools |
| Git hook | Refuses force-push, `reset --hard`, `checkout --`, `restore`, `clean -f` and skipped checks when the agent tries them | Claude Code plugin |
| `reviewer` agent | Fresh, read-only reader used by both passes | Claude Code plugin |

## What it writes in your project

| File | Role |
|---|---|
| `AGENTS.md`, at the root and in each repository | Rules with their reason, under 200 lines per file |
| Roadmap | Phases and cards: what is in scope, and where the project stands |
| `.pre-commit-config.yaml` | Lint, format, secret detection and security rules at each commit |
| CI file | The same checks, plus a dependency audit |
| `.claude/settings.json` | With Claude Code: sandbox, denied files, end-of-task checks |

Tools are chosen for your stack from their official documentation: Ruff and `pip-audit` on a Python project, `gosec` and `govulncheck` on a Go one, for example. A piece your project does not need is left out, and the plan says why.

## Install

```bash
# Claude Code
claude plugin marketplace add gabigab117/cordeau
claude plugin install cordeau@gabigab117

# Other tools
npx skills add gabigab117/cordeau
```

## Use it

Say it to your agent, in any language:

| Say | What happens |
|---|---|
| "Set up the harness for this project" | `harness-setup` recognises the situation and starts the interview |
| "Update the harness" | Applies what changed since the version noted in `AGENTS.md`, and shows the diff |
| "Run the simplification pass" | Simplifies the diff of the card, with the tests run again |
| "Run the security pass" | Reports the flaws of the diff, and fixes them with a test written first |

## Update

Claude Code leaves auto-update off for third-party marketplaces. Turn it on under **Marketplaces** in `/plugin`, or update by hand:

```bash
# Claude Code
claude plugin marketplace update gabigab117
claude plugin update cordeau@gabigab117

# Other tools
npx skills update
```

## What Cordeau runs on your machine

| What | When | Reads | Writes | Network |
|---|---|---|---|---|
| `guardrails.py`, the hook of the plugin | Before each shell command of Claude Code | The command, and whether a path it names exists | Nothing | None |
| `inventory.py` | When `harness-setup` starts | The manifests of the project, never a `.env` | Nothing | None |
| `reviewer` agent | During a pass | Project files, with Read, Grep and Glob only | Nothing | None |
| `harness-setup`, once you approve the plan | Once, then at each update | The project, never a `.env` | The planned files, `git init`, `pre-commit install --install-hooks` | Downloads the pinned checks |
| The two passes | At the end of a card | The diff | `.cordeau/*.diff`, ignored by git | `security-pass` checks new dependencies on their registry |
| The checks written in your project | At commit, in CI, at the end of a task | Your code | Their caches | What you approved in the plan |

The scripts use the Python standard library only. Each change to a hook is noted in the [changelog](plugins/cordeau/skills/harness-setup/CHANGELOG.md). Cordeau has no telemetry. `npx skills` is a third-party tool with its own anonymous telemetry: `DISABLE_TELEMETRY=1` turns it off.

Limits:

- The hook reads the text of a command: it stops accidents, not an attacker. A script that calls git itself goes through. To really protect a branch, use the protection rules of your git host.
- Without `python3` on the `PATH`, Claude Code shows a hook error at each command, and the command runs.
- The sandbox runs on macOS, Linux and WSL2. Linux and WSL2 need `bubblewrap` and `socat`. Without them, and on native Windows, commands run unsandboxed.
- The sandbox blocks some everyday commands, such as `git remote add`, or `go get` and `pnpm install` on macOS. They go through once you approve them.
- To turn the plugin off: `claude plugin disable cordeau@gabigab117`.

## What has been tested

Tested with Claude Code on macOS, on fictional projects: an empty folder, an old Django application without tests, and a small Go API. The sandbox, the hook and the checks were tried for real, by making them refuse.

Not tried yet: Codex, Cursor and Grok Build, Linux and Windows, Node as the main stack, a CI running on GitHub.

## Tests

```bash
uv run --no-project --python 3.14 --with pytest pytest tests  # also on 3.12 and 3.13
```

## Later, not in this version

- Life in production: logs, error tracking, backups.
- Dependency updates: Dependabot or Renovate.

## License

[MIT](LICENSE)
