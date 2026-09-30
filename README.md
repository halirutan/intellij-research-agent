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

Use the single OpenCode command to update all clean source checkouts, review navigation changes, validate paths, and promote the new navigation atomically:

```bash
/update-intellij-research
```

The command runs the hidden maintainer agent. It uses `prepare-update` to fetch and fast-forward the sources, writes an update report and candidate index, asks the maintainer to inspect changed paths and edit only the candidate, then runs `finalize-update`. The previous active index remains in use if validation fails. Updates use `git fetch` and fast-forward-only merges. The command refuses dirty repositories and refuses to overwrite manually changed installed definitions.

Useful commands:

```bash
python -m intellij_research validate
python -m intellij_research prepare-update
python -m intellij_research finalize-update
python -m intellij_research uninstall
python -m intellij_research --source-root /path/to/sources install
```

The active `sources/.intellij-research-index.md` is the validated navigation authority used by the research agents. The candidate index, update report, and revision state are Git-ignored maintenance files. The tracked `guides/AGENTS.md` remains the seed/fallback baseline and is not edited by end-user updates.

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
