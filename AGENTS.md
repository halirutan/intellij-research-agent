# IntelliJ Research Agent

## Purpose

This repository publishes and manages two globally installable OpenCode agents for source-grounded IntelliJ Platform research:

- `intellij-research-quick`: targeted local-source answers.
- `intellij-research`: deeper implementation, registration, history, and web research.

It also installs the global `/update-intellij-research` command and maintains a local mirror of the upstream IntelliJ repositories.

## Repository Layout

- `agents/*.md.in`: rendered OpenCode agent templates. Edit these, not installed files.
- `commands/*.md.in`: rendered global OpenCode command templates.
- `guides/AGENTS.md`: tracked seed/fallback guide copied into the source mirror.
- `intellij_research/`: Python 3.10+ CLI and installation logic.
- `repositories.json`: authoritative upstream repository, branch, and important-path manifest.
- `maintenance/update-agents.md`: navigation-maintenance rules for the maintainer agent.
- `tests/`: Python unit tests.
- `sources/`: Git-ignored, read-only upstream clones created by installation. Never edit source files there.

Generated files under `sources/`:

- `.intellij-research-index.md`: cumulative validated semantic navigation and current checkout revisions used by research agents.
- `.intellij-research-index.candidate.md`: maintainer-only candidate; never use as research guidance.
- `.intellij-research-update-report.md`: revisions and changed paths for the current update.
- `.intellij-research-state.json`: last successfully finalized revisions; internal bookkeeping.

## Permissions

The supported installed runtime is OpenCode 1.18.33. Agent templates must use legacy singular `permission:` frontmatter, not native `permissions:`. The installer renders the full absolute source path and both the exact source-root and descendant external-directory rules. Verify effective permissions with:

```bash
opencode debug agent intellij-research-quick
```

Do not assume a template change is active until the agents are reinstalled and OpenCode is restarted.

## Install And Use

From the repository root:

```bash
python -m intellij_research install
```

This clones all manifest repositories into `sources/`, initializes recursive submodules, validates important paths, renders agents and `/update-intellij-research` into the global OpenCode config, and records ownership hashes. Installation refuses to overwrite unmanaged or manually modified files.

After installation, restart OpenCode. Research agents read the active navigation index before searching source repositories.

To install into another OpenCode config or source location:

```bash
python -m intellij_research --source-root /path/to/sources --config-dir /path/to/opencode install
```

## Update Workflow

Users should run the single OpenCode command:

```text
/update-intellij-research
```

The hidden maintainer agent runs `prepare-update`, which copies the active routing guide into the candidate and refreshes current checkout revisions. The maintainer reviews the complete update report and changed paths as audit evidence, edits only candidate semantic routing when needed, verifies navigation, then runs `finalize-update`. Finalization rejects maintenance leakage and abnormal growth and validates literal paths, supported globs, manifest-important paths, and repository state before atomically promoting the candidate. If validation fails, the previous active index remains valid.

Direct helpers are available when debugging:

```bash
python -m intellij_research validate
python -m intellij_research prepare-update
python -m intellij_research finalize-update
python -m intellij_research uninstall
```

Updates refuse dirty source checkouts and use fetch plus fast-forward-only merges. Do not use unrestricted `git pull` or modify upstream checkout files. Tracked `guides/AGENTS.md` is maintained centrally; end-user updates must not edit it.

## Development

Run before committing:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile intellij_research/*.py tests/*.py
python3 -m json.tool repositories.json >/dev/null
git diff --check
```

When changing templates, reinstall into a test config or the intended global config and inspect `opencode debug agent`. Never commit `sources/`, generated indexes, installation metadata, Python caches, or other local state.
