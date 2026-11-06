# Mirepoix

> The aromatic base for every AI-coded project.

**Status: beta, version 0.1.0.** Expect changes between versions.

Mirepoix is a harness for AI-coded projects, in two parts:

- **Skills** in the standard [Agent Skills](https://agentskills.io) format, for Claude Code, Codex, Grok Build, Cursor and other tools.
- **A Claude Code plugin**, distributed from this repository, that adds what only Claude Code can do: hooks and a review agent.

## Install

Claude Code:

```bash
claude plugin marketplace add gabigab117/mirepoix
claude plugin install mirepoix@gabigab117
```

Other tools:

```bash
npx skills add gabigab117/mirepoix
```

## Update

Claude Code leaves auto-update off for third-party marketplaces. Turn it on under **Marketplaces** in `/plugin`, or update by hand:

```bash
claude plugin marketplace update gabigab117
claude plugin update mirepoix@gabigab117
```

Other tools:

```bash
npx skills update
```

## Tests

```bash
uv run --no-project --python 3.14 --with pytest pytest tests
```

The suite also runs on Python 3.12 and 3.13.

## Later

Candidates for a future version, not part of this one:

- Life in production: logs, error tracking, backups.
- Dependency updates: Dependabot or Renovate.

## License

[MIT](LICENSE)
