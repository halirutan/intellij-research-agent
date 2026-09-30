# Source Routing Maintenance

The `/update-intellij-research` command is the normal workflow. It runs `prepare-update`, asks the maintainer agent to inspect the update report and changed paths, edit only the candidate index, and runs `finalize-update` after deterministic validation.

The source repositories are read-only evidence. Inspect the full revision range reported by `prepare-update`, review changed paths, and update the candidate only when an agent would otherwise be misled, blocked, or sent to a stale entry point. Verify all referenced paths before finalization. Do not edit upstream repositories, the active index, state, report, or agent templates during this audit.

The tracked `guides/AGENTS.md` is maintained centrally and is not changed by end-user updates. The candidate becomes active only after `finalize-update` validates every literal route, supported glob, and manifest-important path.
