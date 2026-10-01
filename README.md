# IntelliJ Research Agents

This repository provides source-grounded IntelliJ Platform research through a local mirror of the upstream repositories. It installs these OpenCode definitions globally:

- `intellij-research-quick`: fast, targeted answers from local source.
- `intellij-research`: deeper source, registration, history, and web research.
- `intellij-research-maintainer`: hidden agent used to update the mirror and navigation index.
- `/update-intellij-research`: command that runs the complete update workflow.

## Install

Requirements: Python 3.10+, Git, and OpenCode on `PATH`.

Clone this repository, enter it, and run:

```bash
python3 -m intellij_research install
```

The installer clones the repositories listed in `repositories.json` into `sources/`, initializes recursive submodules, validates the navigation index, and installs the rendered agents and update command into OpenCode's global configuration. Restart OpenCode after installation so it loads the new definitions.

To keep the source mirror or OpenCode configuration elsewhere, use:

```bash
python3 -m intellij_research \
  --source-root /path/to/sources \
  --config-dir /path/to/opencode \
  install
```

Paths are rendered into the installed definitions, so use the same `--source-root` for later maintenance commands.

## Using The Agents

Use `intellij-research-quick` for a focused question that should be answered from a small number of known source locations. Use `intellij-research` when the answer requires a broader implementation trace, registrations, tests, Git history, version context, or web evidence.

Both agents read the validated local navigation index before searching. They treat the mirror as read-only source material and support material claims with source paths and symbols.

## Updating Sources

Run the global OpenCode command for routine mirror updates:

```text
/update-intellij-research
```

The hidden maintainer agent performs the following guarded workflow:

1. Fetch and fast-forward every clean source checkout.
2. Write a complete update report and copy the durable routing guide into a candidate index.
3. Use changed paths as audit evidence to decide whether any semantic routes became stale or misleading.
4. Validate the candidate and promote it only when all checks pass.
5. Refresh the managed OpenCode agent and command definitions.

The active index remains unchanged if validation or finalization fails. Updates refuse dirty source checkouts, unexpected remotes, incorrect branches, and manually modified installed definitions. They never edit files in the upstream repositories; only Git checkout metadata and recursive-submodule state change.

## Upgrading This Repository

After pulling a newer version of this repository, reinstall its definitions before starting OpenCode:

```bash
git pull --ff-only
python3 -m intellij_research install
```

Then start or restart OpenCode and run `/update-intellij-research`. Reinstalling first ensures that the update uses the latest maintainer instructions and permission rules.

`finalize-update` also installs the latest managed definitions, so an update can normally deliver future agent changes itself. However, the update currently in progress still runs with the definitions OpenCode loaded when it started. A repository release that changes the maintainer itself may therefore require the explicit reinstall and restart above. The installer intentionally refuses to overwrite installed definitions that were modified by hand.

For a custom source location, repeat the same option used during installation:

```bash
python3 -m intellij_research --source-root /path/to/sources install
```

## Model Selection

The installed agents do not pin a model. By default, OpenCode uses the model currently configured for the session. When a research agent is called as a subagent, it uses the model selected by the calling or main agent unless the user explicitly configures a model for that research agent.

Start with the least expensive model that produces reliable results:

| Agent | Cost-aware starting point |
| --- | --- |
| `intellij-research-quick` | Use a fast, inexpensive model. Its narrow workflow and local evidence usually do not require extensive reasoning. |
| `intellij-research` | Start with an inexpensive model that has a large context window. If answer quality is too low for complex traces or conflicting evidence, move to a stronger mid-tier model. |
| `intellij-research-maintainer` | Prefer a strong model because it must interpret upstream structural changes and its semantic-routing decisions persist across updates. Updates are infrequent, which limits the cost. |

Context capacity is particularly useful for `intellij-research`, which may collect evidence across many files and repositories before deciding what is relevant. For example, GPT-5.6 Luna can be an economical starting point because it combines low cost with a 1-million-token context window. A flagship model is not required for ordinary research if a cheaper model produces sufficiently accurate, source-grounded answers.

## Maintenance Commands

The OpenCode update command is the recommended interface. These direct helpers are useful for installation, validation, or troubleshooting:

```bash
python3 -m intellij_research validate
python3 -m intellij_research prepare-update
python3 -m intellij_research finalize-update
python3 -m intellij_research uninstall
python3 -m intellij_research --source-root /path/to/sources install
```

The active `sources/.intellij-research-index.md` is the cumulative validated navigation authority used by the research agents. It contains durable semantic routing and current checkout revisions, never update deltas. The update report owns commit ranges and complete changed-path lists. The candidate index, update report, and revision state are Git-ignored maintenance files. The tracked `guides/AGENTS.md` remains the installation and fallback seed and is not edited by end-user updates.

## Layout

```text
agents/                         OpenCode agent templates
commands/                       OpenCode command templates
guides/AGENTS.md                source-mirror routing baseline
intellij_research/              cross-platform management CLI
maintenance/update-agents.md    source-change review guidance
repositories.json               explicit upstream manifest
sources/                        read-only upstream clones, excluded from Git
```
