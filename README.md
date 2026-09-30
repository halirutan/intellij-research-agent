# IntelliJ Research Agents

This repository manages a local, source-grounded IntelliJ Platform research mirror and installs two OpenCode agents globally:

- `intellij-research-quick`: fast local-source answers.
- `intellij-research`: deeper source, registration, history, and web research.

## Install

Requirements: Python 3.10+, Git, and OpenCode on `PATH`.

```bash
python -m intellij_research install
```

The command clones the repositories listed in `repositories.json` into `sources/`, initializes nested submodules, validates the routing guide, and installs rendered agents into OpenCode's global `agents/` directory. The source mirror can live anywhere; paths are rendered during installation.

Restart OpenCode after installation.

## Update

Update all clean source checkouts, rebuild the local routing index, validate paths, and refresh the installed agents:

```bash
python -m intellij_research update-agent
```

Updates use `git fetch` and fast-forward-only merges. The command refuses dirty repositories and refuses to overwrite manually changed installed agents.

Useful commands:

```bash
python -m intellij_research validate
python -m intellij_research uninstall
python -m intellij_research --source-root /path/to/sources install
```

The tracked `AGENTS.md` is the maintained routing baseline. The Git-ignored `sources/.intellij-research-index.md` records generated path and revision information for the current mirror. Semantic routing-guide maintenance belongs to the prompt in `maintenance/update-agents.md` and should be reviewed by a maintainer before changing the tracked guide.

## Layout

```text
agents/                         OpenCode agent templates
guides/AGENTS.md                source-mirror routing baseline
intellij_research/              cross-platform management CLI
maintenance/update-agents.md    source-change review prompt
repositories.json               explicit upstream manifest
sources/                        read-only upstream clones, excluded from parent Git tracking
```

The upstream repositories are source material and are never modified by this project except for Git checkout metadata and nested-submodule state.
