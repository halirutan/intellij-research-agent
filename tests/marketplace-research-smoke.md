# Marketplace research acceptance checks

These are model-behavior checks, not unit tests. Install the changed definitions into a test configuration with the Marketplace checkout present. Do not edit upstream files or remove routes from a live index to construct fixtures.

## Cases

1. **Upload and listing.** Ask the quick agent how to publish a first plugin and prepare its vendor/listing information. Expect Marketplace upload/listing topics and relevant local links, not just SDK Gradle instructions. Follow Writerside links across topic directories rather than assuming sibling files.
2. **Technical publishing.** Ask how the Gradle publishing task works or how to sign and verify a plugin. Expect SDK docs and Gradle sources first; Marketplace docs supplement service-side requirements rather than replace technical implementation evidence.
3. **Updates and distribution.** Ask about release channels, hidden updates, REST uploads, and Maven downloads. Expect the matching Marketplace topics or API-reference Markdown, with focused reads rather than a mirror-wide search.
4. **Paid and freemium.** Ask about paid-plugin setup, freemium license enforcement, billing, fees, and payouts. Expect routes through the paid-plugin and billing sections and their local links. Do not infer platform-version compatibility from the current checkout alone.
5. **Current policy and missing legal terms.** Ask both agents for today's approval criteria and the complete developer agreement. Expect the locally mirrored approval guidelines with the index revision and staleness caveat; the externally linked agreement must be identified as unverified if absent locally. Neither agent should browse, invent terms, or guarantee today's requirements.
6. **Older index fallback.** Use a test index predating Marketplace routes, retaining a custom durable route. Expect the agents to consult the refreshed source-root `AGENTS.md` and Marketplace tree. Reinstall must preserve the custom route. During a subsequent update audit, expect the maintainer to repair missing topic routes even when no Marketplace paths changed, preserving existing improvements and passing growth/path validation.
7. **Promotion and analytics.** Ask about listing quality, ratings, discoverability, and download/sales statistics. Expect the listing/analytics routes and the Marketplace tree for focused related-topic discovery.

For every answer, verify local `path:line-line` evidence, Marketplace checkout revision, honest evidence gaps, no web calls for Marketplace questions, and no edits to the mirror or caller's project. These checks do not replace unit tests or imply live Marketplace policy verification.
