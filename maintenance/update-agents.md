# Source Routing Maintenance

Use this prompt with OpenCode when the tracked routing guide needs semantic maintenance after an upstream update.

The source repositories are read-only evidence. The only intended tracked edit is `guides/AGENTS.md`. Inspect the full commit range reported by `update-agent`, review changed paths, and change the guide only when an agent would otherwise be misled, blocked, or sent to a stale entry point. Verify all referenced paths before finishing. Do not edit upstream repositories, generated indexes, or agent templates during this audit.

The normal `update-agent` command already updates checkouts, generates the local index, validates paths, and refreshes installed agent files. This prompt is for the higher-level human/LLM review of routing quality.
