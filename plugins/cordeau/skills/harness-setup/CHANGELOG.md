# Changelog

Read by the `harness-setup` skill. Each entry is written as instructions for a project whose harness has
an earlier version: apply the entries newer than the version in its `cordeau:harness` marker, adapted to
the project, then raise the version in the marker.

## 0.1.0

First version: nothing to apply.

The plugin ships one hook: Claude Code runs `scripts/guardrails.py` before each shell command, and it refuses destructive git
commands and skipped checks. The same script reads the calls of Codex, Cursor and Grok Build and answers each of them in its
own format. A project that holds a copy of this script replaces it with the new one when an entry says so.
