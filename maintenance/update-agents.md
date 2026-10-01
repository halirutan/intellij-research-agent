# Source Routing Maintenance

The `/update-intellij-research` command is the normal workflow. It runs `prepare-update`, copies the active semantic navigation into a candidate, refreshes machine-owned checkout revisions, asks the maintainer agent to inspect the update report, and runs `finalize-update` after deterministic validation.

The source repositories, revision ranges, and changed paths are read-only audit evidence, not navigation content. Inspect the full revision range and update only the candidate's `Routing Guide` when an agent would otherwise be misled, blocked, or sent to a stale entry point. Prefer fixing existing routes over adding routes, do not add paths merely because they are new, and make no change when the current routing remains accurate. Verify all referenced paths before finalization. Do not edit upstream repositories, the active index, state, report, checkout metadata, or agent templates during this audit.

The tracked `guides/AGENTS.md` is the install/fallback seed and is not changed by end-user updates. The candidate becomes active only after `finalize-update` rejects maintenance leakage and abnormal growth and validates every literal route, supported glob, and manifest-important path.
