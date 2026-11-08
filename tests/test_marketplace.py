import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from intellij_research import cli


class MarketplaceTest(unittest.TestCase):
    def marketplace_repository(self) -> cli.Repository:
        return next(repository for repository in cli.load_repositories() if repository.name == "marketplace-docs")

    def test_manifest_tracks_public_master_with_case_sensitive_entry_points(self) -> None:
        repository = self.marketplace_repository()
        self.assertEqual("https://github.com/JetBrains/marketplace-docs.git", repository.url)
        self.assertEqual("master", repository.branch)
        self.assertFalse(repository.recursive_submodules)
        self.assertIn("README.MD", repository.important_paths)
        self.assertNotIn("README.md", repository.important_paths)
        self.assertIn("marketplace-docs.tree", repository.important_paths)
        for path in (
            "topics/marketplace-general/uploading-a-new-plugin.topic",
            "topics/marketplace-general/plugin-updates.topic",
            "topics/api-reference/api-reference.md",
            "topics/legal-agreements-policies/JetBrains-Marketplace-Approval-Guidelines.topic",
            "topics/paid-plugins-start/paid-plugins.topic",
        ):
            self.assertIn(path, repository.important_paths)

    def test_marketplace_uses_existing_clone_workflow(self) -> None:
        repository = self.marketplace_repository()
        with tempfile.TemporaryDirectory() as directory, patch.object(cli, "run") as run:
            source_root = Path(directory)
            cli.clone_repository(source_root, repository)
            run.assert_called_once_with(
                ["git", "clone", "--branch", "master", repository.url, str(source_root / repository.name)],
                capture=False,
            )

    def test_research_agents_embed_mirror_only_guidance_and_upgrade_fallback(self) -> None:
        source_root = Path("/tmp/opencode/custom mirror with spaces")
        guidance = cli.MARKETPLACE_RESEARCH_GUIDE.read_text(encoding="utf-8").strip().replace(
            "{{SOURCE_ROOT}}", source_root.as_posix()
        )
        for name in ("intellij-research", "intellij-research-quick"):
            with self.subTest(agent=name):
                rendered = cli.render(cli.TEMPLATE_DIR / f"{name}.md.in", source_root)
                self.assertEqual(1, rendered.count(guidance))
                self.assertIn(f"{source_root.as_posix()}/AGENTS.md", rendered)
                self.assertIn(f"{source_root.as_posix()}/marketplace-docs/marketplace-docs.tree", rendered)
                self.assertIn("including current-policy questions", rendered)
                self.assertIn("overrides the general web-research fallback", rendered)
                self.assertIn("checkout revision from the index", rendered)
                self.assertIn("absent locally as unverified", rendered)
                self.assertIn("do not browse", rendered)
                self.assertIn("resolving bare filenames across topic directories", rendered)
                self.assertNotIn("{{", rendered)
                self.assertNotIn(cli.MARKETPLACE_RESEARCH_GUIDE.as_posix(), rendered)

    def test_maintainer_repairs_topic_routes_even_without_marketplace_changes(self) -> None:
        source_root = Path("/tmp/opencode/mirror")
        rendered = cli.render(cli.TEMPLATE_DIR / "intellij-research-maintainer.md.in", source_root)
        self.assertIn("even when no Marketplace files changed", rendered)
        self.assertIn(f"{source_root.as_posix()}/marketplace-docs/marketplace-docs.tree", rendered)
        self.assertIn("preserve existing semantic improvements", rendered)
        self.assertIn("mirror-only revision/staleness boundary", rendered)
        self.assertIn("Do not copy the full topic inventory", rendered)

    def test_shipped_marketplace_routes_are_validated_including_nonimportant_paths(self) -> None:
        repository = self.marketplace_repository()
        # Fixed verified upstream paths, not paths synthesized from the guide under test.
        paths = {
            *repository.important_paths,
            "topics/marketplace-general/publishing-and-listing-your-plugin.topic",
            "topics/marketplace-general/custom-release-channels.topic",
            "topics/marketplace-general/best-practices-for-listing.topic",
            "topics/marketplace-general/analytics-tab.topic",
            "topics/legal-agreements-policies/legal-agreements.topic",
            "topics/api-reference/maven-interface.md",
            "topics/paid-plugins-general-info/technical-implementation.topic",
            "topics/paid-plugins-general-info/billing-and-licensing.topic",
        }
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory)
            checkout = source_root / repository.name
            (checkout / ".git").mkdir(parents=True)
            for relative in paths:
                path = checkout / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("Fixture.\n", encoding="utf-8")
            with patch.object(cli, "load_repositories", return_value=[repository]), patch.object(
                cli, "checkout_section", return_value=f"{cli.CHECKOUTS_HEADING}\nmetadata"
            ):
                cli.install_guide(source_root)
                index = cli.generate_index(source_root)
                self.assertEqual([], cli.validate_navigation(source_root, index))
                maven = checkout / "topics/api-reference/maven-interface.md"
                maven.unlink()
                self.assertEqual(
                    ["Navigation path does not exist: marketplace-docs/topics/api-reference/maven-interface.md"],
                    cli.validate_navigation(source_root, index),
                )
                important = checkout / "topics/marketplace-general/plugin-updates.topic"
                important.unlink()
                errors = cli.validate_navigation(source_root, index)
                self.assertIn(f"Missing important path: {important}", errors)
                self.assertIn(
                    "Navigation path does not exist: marketplace-docs/topics/marketplace-general/plugin-updates.topic",
                    errors,
                )

    def test_seed_distinguishes_marketplace_topics_from_technical_publishing(self) -> None:
        guide = cli.GUIDE.read_text(encoding="utf-8")
        for label in (
            "Build / sign / verify / Gradle publishing",
            "Marketplace upload / vendor setup / listing",
            "Marketplace approval / policies / EULA",
            "Marketplace updates / channels / visibility",
            "Marketplace REST API / Maven downloads",
            "Paid / freemium plugins / license enforcement",
            "Pricing / billing / fees / payouts",
            "Marketplace promotion / ratings / analytics",
        ):
            self.assertIn(label, guide)
        self.assertIn("Marketplace answers use the mirror only", guide)
        self.assertIn("checkout revision from the index", guide)
        self.assertIn("external legal terms", guide)

    def test_topic_route_upgrade_fits_existing_growth_limits(self) -> None:
        guide = cli.GUIDE.read_text(encoding="utf-8").strip()
        older = re.sub(r"## Marketplace Research\n.*?(?=## Skill Discovery)", "", guide, flags=re.DOTALL)
        older = "\n".join(
            line for line in older.splitlines() if "marketplace-docs/" not in line and "Gradle publishing" not in line
        )
        active = f"{cli.ROUTING_HEADING}\n{older}\n{cli.CHECKOUTS_HEADING}\nmetadata"
        candidate = f"{cli.ROUTING_HEADING}\n{guide}\n{cli.CHECKOUTS_HEADING}\nmetadata"
        self.assertEqual([], cli.routing_growth_errors(active, candidate))

    def test_reinstall_exposes_marketplace_fallback_without_replacing_custom_routes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory) / "mirror elsewhere"
            source_root.mkdir()
            active = source_root / cli.ACTIVE_INDEX
            active.write_text(
                f"{cli.ROUTING_HEADING}\nCustom durable route.\n{cli.CHECKOUTS_HEADING}\nold metadata\n"
                f"{cli.RESOLUTION_HEADING}\nResolve paths.\n",
                encoding="utf-8",
            )
            routing_before = cli.routing_content(active.read_text(encoding="utf-8"))
            args = cli.argparse.Namespace(source_root=source_root, config_dir=Path(directory) / "config")
            with patch.object(cli, "prepare_sources", side_effect=cli.install_guide), patch.object(
                cli, "validate_navigation", return_value=[]
            ), patch.object(cli, "checkout_section", return_value=f"{cli.CHECKOUTS_HEADING}\nnew metadata"), patch.object(
                cli, "current_revisions", return_value={}
            ):
                cli.command_install(args)
            self.assertEqual(routing_before, cli.routing_content(active.read_text(encoding="utf-8")))
            self.assertNotIn("marketplace-docs/", active.read_text(encoding="utf-8"))
            self.assertIn("Marketplace upload / vendor setup / listing", (source_root / "AGENTS.md").read_text())
            for name in ("intellij-research", "intellij-research-quick"):
                rendered = (args.config_dir / "agents" / f"{name}.md").read_text(encoding="utf-8")
                self.assertIn(f"{source_root.as_posix()}/AGENTS.md", rendered)
                self.assertIn("If an older index lacks Marketplace routes", rendered)
            metadata = cli.read_metadata(args.config_dir / "agents")
            self.assertEqual(str(source_root), metadata["source_root"])
            self.assertIn("intellij-research", metadata["agents"])
            state = json.loads((source_root / cli.STATE_FILE).read_text(encoding="utf-8"))
            self.assertTrue(state["seeded"])


if __name__ == "__main__":
    unittest.main()
