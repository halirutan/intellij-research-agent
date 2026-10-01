# AGENTS Guide: IntelliJ Plugin Development Sources

This workspace is read-only reference material for IntelliJ plugin development. Use it to find correct docs, APIs, extension points, and build tooling internals. Resolve every path below relative to the directory containing this file.

## Fast Routing Map

| If you need... | Start here | Then jump to |
|---|---|---|
| Official plugin docs / conceptual guidance | `intellij-sdk-docs/topics/intro/welcome.topic` | `intellij-sdk-docs/topics/appendix/resources/explore_api.md` |
| Extension point lists | `intellij-sdk-docs/topics/appendix/resources/ep_lists/intellij_platform_extension_point_list.md` | XML declarations under `intellij-community/platform/*/resources/` |
| `plugin.xml` structure | `intellij-sdk-docs/topics/basics/plugin_structure/plugin_configuration_file.md` | `intellij-community/plugins/devkit/devkit-core/src/dom/IdeaPlugin.java` |
| Real EP declarations and registrations | `intellij-community/platform/platform-impl/resources/intellij.platform.ide.impl.xml` | related module resource XML files |
| Action system APIs | `intellij-sdk-docs/topics/basics/action_system.md` | `intellij-community/platform/editor-ui-api/src/com/intellij/openapi/actionSystem` |
| PSI / parser / language support | `intellij-sdk-docs/topics/basics/architectural_overview/psi.md` | `intellij-community/platform/core-api/src/com/intellij/lang` and `intellij-community/platform/core-api/src/com/intellij/psi` |
| Indexing / stubs / dumb mode | `intellij-sdk-docs/topics/basics/indexing_and_psi_stubs.md` | `intellij-community/platform/indexing-api/src/com/intellij/util/indexing` |
| Settings / Configurable EPs | `intellij-sdk-docs/topics/basics/settings.md` | `intellij-community/platform/ide-core/resources/intellij.platform.ide.core.xml` |
| Threading / read-write actions | `intellij-sdk-docs/topics/basics/architectural_overview/threading/threading_model.md` | `intellij-community/platform/core-api/src/com/intellij/openapi/application` |
| New plugin starter layout | `intellij-platform-plugin-template/README.md` | `intellij-platform-plugin-template/src/main/resources/META-INF/plugin.xml` |
| Grammar-Kit / BNF / PSI generation | `GrammarKitDoc/docs/index.md` | `GrammarKitDoc/docs/integration/parser-definition.md` |

## Repository Roles

- `intellij-sdk-docs/`: canonical SDK documentation source.
- `intellij-community/`: IntelliJ Platform APIs, implementations, registrations, and tests.
- `intellij-platform-gradle-plugin/`: IntelliJ Platform Gradle Plugin implementation.
- `gradle-changelog-plugin/`: Gradle Changelog Plugin implementation.
- `intellij-platform-plugin-template/`: current plugin project skeleton.
- `GrammarKitDoc/`: Grammar-Kit documentation and plugin source.

## EP Discovery

1. Start from the SDK extension-point list.
2. Open the EP declaration in the relevant platform resource XML.
3. Find registration examples in platform or bundled-plugin resource XML files.
4. Follow the implementation package to the EP interface or bean class.
5. Inspect DevKit indexes if `plugin.xml` behavior remains unclear.

The generated `.intellij-research-index.md` beside this guide starts from this routing baseline, preserves validated semantic improvements across updates, and records current checkout revisions. It never contains changed-path audit data.
