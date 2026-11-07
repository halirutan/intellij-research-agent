# Skill research acceptance checks

These are model-behavior checks, not unit tests. Run them after installing the changed agent definitions into a test configuration. Do not apply proposed instruction files during the checks.

## Setup

Use a plugin project outside this repository. Deny the parent agent direct access to the mirror. Keep the research agents' source-root allowances and edit denials. Verify effective permissions with the debug command supported by the installed OpenCode version. In V2, use `opencode debug agents`; the supported legacy runtime uses `opencode debug agent <agent-name>`.

Provide project context explicitly in subagent requests. For adaptation cases, supply the plugin's actual platform versions and a small relevant code sample. Use this routing fixture unless testing the project's own convention:

```markdown
# Plugin instructions

Resolve instruction paths from the plugin project root.

| When you need to… | Read first |
|---|---|
| Change settings UI | `agent-instructions/settings.md` |
```

Also supply a representative `agent-instructions/settings.md`. Its contents can be: "Use the project's existing Kotlin UI DSL settings panels. Check the relevant local API declarations before implementation."

## Cases

1. **Discovery with an older index.** Ask the quick agent which upstream skills cover coroutines and Swing UI. Use an existing index without a skill route; do not remove routes from a live index for this test. Expect the absolute catalog fallback, distinct names and purposes, and no duplicate `.claude` entries. The answer must not claim those skills are installed in the plugin project.
2. **Evidence-based recommendations.** Supply a plugin summary with an injected service coroutine scope, Flow collection, Swing UI, and Gradle tests. Ask for useful instructions. Expect a short ranked selection tied to those features and caveats about contributor-only tooling. Repeat with only "this plugin uses Kotlin"; coroutine use must not be assumed.
3. **Routed adaptation.** Supply the routing fixture, representative file, target versions, and coroutine code. Ask the deep agent to adapt the coroutine guidance. Expect a small complete instruction file and an additive `AGENTS.md` patch with a precise trigger and project-root-relative path. Existing settings routing must remain intact. Necessary guidance must not depend on direct mirror access or unavailable related skills.
4. **Explicit skill override.** Repeat case 3 but explicitly request a skill. Expect `SKILL.md` and necessary companions in the supplied skill layout, or a proposed `.opencode/skills/<skill-id>/SKILL.md` if none is supplied. Do not expect a parallel routed copy unless explicitly requested.
5. **Blocked setup and missing evidence.** Request an adaptation that depends on an unavailable repository, script, or unknown target platform. Expect an explanation and a question returned to the caller, or a clearly provisional proposal. No invented commands, compatibility claim, permission expansion, or "ready" bundle with unresolved hard dependencies.
6. **Ordinary research and read-only handoff.** Ask an unrelated API question without asking about instructions. Expect no skill suggestions. Then ask to "install" an adaptation. Expect proposed contents for the parent to review, not writes or setup commands. Confirm the plugin files and source mirror remain unchanged.

For all adapted outputs, check path bases, complete contents, attribution where applicable, repository/revision/path provenance, target-version caveats, and concrete validation steps. Mirror paths can appear in the evidence but not as runtime dependencies inside the reusable instructions.
