import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from intellij_research import cli


class CLIHelpersTest(unittest.TestCase):
    def test_render_replaces_all_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            template = Path(directory) / "agent.md.in"
            template.write_text("{{SOURCE_ROOT}}\n{{INDEX_PATH}}", encoding="utf-8")
            source_root = Path(directory) / "sources"
            rendered = cli.render(template, source_root)
            self.assertIn(source_root.as_posix(), rendered)
            self.assertIn((source_root / ".intellij-research-index.md").as_posix(), rendered)
            self.assertNotIn("{{", rendered)

    def test_maintainer_allows_repository_and_exact_update_helpers(self) -> None:
        source_root = Path("/tmp/intellij-research-sources")
        rendered = cli.render(cli.TEMPLATE_DIR / "intellij-research-maintainer.md.in", source_root)
        self.assertIn(f'    "{cli.ROOT.as_posix()}": allow', rendered)
        self.assertIn(f'    "{cli.ROOT.as_posix()}/**": allow', rendered)
        self.assertIn(
            f'    \'python3 -m intellij_research --source-root "{source_root.as_posix()}" prepare-update\': allow',
            rendered,
        )
        self.assertIn(
            f'    \'python3 -m intellij_research --source-root "{source_root.as_posix()}" finalize-update\': allow',
            rendered,
        )

    def test_hash_is_stable(self) -> None:
        self.assertEqual(cli.sha256_text("same"), cli.sha256_text("same"))
        self.assertNotEqual(cli.sha256_text("same"), cli.sha256_text("other"))

    def test_install_agents_rejects_unmanaged_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "agents"
            destination.mkdir()
            source_root = Path(directory) / "sources"
            source_root.mkdir()
            (destination / "intellij-research.md").write_text("custom", encoding="utf-8")
            old_template_dir = cli.TEMPLATE_DIR
            try:
                cli.TEMPLATE_DIR = Path(directory)
                (cli.TEMPLATE_DIR / "intellij-research.md.in").write_text("{{SOURCE_ROOT}}", encoding="utf-8")
                with self.assertRaises(cli.CLIError):
                    cli.install_agents(source_root, destination)
            finally:
                cli.TEMPLATE_DIR = old_template_dir

    def test_install_agents_can_replace_its_own_unchanged_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "agents"
            source_root = root / "sources"
            old_template_dir = cli.TEMPLATE_DIR
            try:
                cli.TEMPLATE_DIR = root / "templates"
                cli.TEMPLATE_DIR.mkdir()
                (cli.TEMPLATE_DIR / "intellij-research.md.in").write_text("{{SOURCE_ROOT}}", encoding="utf-8")
                cli.install_agents(source_root, destination)
                cli.install_agents(source_root, destination)
                metadata = json.loads((destination / cli.INSTALL_METADATA).read_text(encoding="utf-8"))
                self.assertIn("intellij-research", metadata["agents"])
            finally:
                cli.TEMPLATE_DIR = old_template_dir

    def test_generate_index_contains_navigation_and_current_revision_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory)
            repository = cli.Repository("example", "https://example.test/repo.git", "main", False, ("README.md",))
            checkout = source_root / repository.name
            (checkout / ".git").mkdir(parents=True)
            (checkout / "README.md").write_text("example", encoding="utf-8")
            with patch.object(cli, "load_repositories", return_value=[repository]), patch.object(
                cli, "git", side_effect=["main", "0123456789abcdef"]
            ):
                index = cli.generate_index(source_root)
            content = index.read_text(encoding="utf-8")
            self.assertIn("| `example` | `main` | `0123456789ab` |", content)
            self.assertNotIn("Changed Paths", content)
            self.assertNotIn("| Update |", content)
            self.assertNotIn("Important paths", content)

    def test_prepare_candidate_preserves_routing_and_removes_legacy_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory)
            active = source_root / cli.ACTIVE_INDEX
            active.write_text(
                "\n".join([
                    "# Index",
                    cli.ROUTING_HEADING,
                    "Custom durable route.",
                    cli.CHECKOUTS_HEADING,
                    "old metadata",
                    "## Changed Paths",
                    "- `M\tpath/to/file`",
                    cli.RESOLUTION_HEADING,
                    "Resolve paths.",
                    "",
                ]),
                encoding="utf-8",
            )
            with patch.object(cli, "checkout_section", return_value=f"{cli.CHECKOUTS_HEADING}\nnew metadata"):
                candidate = cli.prepare_candidate_index(source_root)
            content = candidate.read_text(encoding="utf-8")
            self.assertIn("Custom durable route.", content)
            self.assertIn("new metadata", content)
            self.assertNotIn("old metadata", content)
            self.assertNotIn("Changed Paths", content)
            self.assertNotIn("M\tpath/to/file", content)

    def test_navigation_rejects_maintenance_evidence(self) -> None:
        content = "\n".join([
            cli.ROUTING_HEADING,
            "Route.",
            cli.CHECKOUTS_HEADING,
            "## Changed Paths",
            "- `R100\told/path\tnew/path`",
            cli.RESOLUTION_HEADING,
        ])
        errors = cli.navigation_content_errors(content)
        self.assertTrue(any("Changed Paths" in error for error in errors))
        self.assertTrue(any("Git diff entries" in error for error in errors))

    def test_navigation_rejects_update_report_metadata(self) -> None:
        content = "\n".join([
            cli.ROUTING_HEADING,
            "# IntelliJ Research Update Report",
            "- Previous revision: `abc`",
            cli.CHECKOUTS_HEADING,
            cli.RESOLUTION_HEADING,
        ])
        errors = cli.navigation_content_errors(content)
        self.assertTrue(any("update report metadata" in error for error in errors))

    def test_navigation_rejects_abnormal_routing_growth(self) -> None:
        active = f"{cli.ROUTING_HEADING}\nRoute.\n{cli.CHECKOUTS_HEADING}\nmetadata"
        candidate = (
            f"{cli.ROUTING_HEADING}\nRoute.\n"
            + "\n".join(f"Added route {number}." for number in range(cli.MAX_ROUTING_GROWTH_LINES + 1))
            + f"\n{cli.CHECKOUTS_HEADING}\nmetadata"
        )
        errors = cli.routing_growth_errors(active, candidate)
        self.assertTrue(any("lines" in error for error in errors))

    def test_navigation_allows_small_routing_improvement(self) -> None:
        active = f"{cli.ROUTING_HEADING}\nRoute.\n{cli.CHECKOUTS_HEADING}\nmetadata"
        candidate = f"{cli.ROUTING_HEADING}\nRoute.\nBetter route.\n{cli.CHECKOUTS_HEADING}\nmetadata"
        self.assertEqual([], cli.routing_growth_errors(active, candidate))

    def test_navigation_rejects_routing_deletion(self) -> None:
        active_routes = "\n".join(f"Route {number}." for number in range(cli.MAX_ROUTING_SHRINK_LINES + 2))
        active = f"{cli.ROUTING_HEADING}\n{active_routes}\n{cli.CHECKOUTS_HEADING}\nmetadata"
        candidate = f"{cli.ROUTING_HEADING}\n{cli.CHECKOUTS_HEADING}\nmetadata"
        errors = cli.routing_growth_errors(active, candidate)
        self.assertTrue(any("shrank" in error for error in errors))

    def test_navigation_rejects_empty_short_routing_guide(self) -> None:
        content = f"{cli.ROUTING_HEADING}\n{cli.CHECKOUTS_HEADING}\nmetadata\n{cli.RESOLUTION_HEADING}"
        errors = cli.navigation_content_errors(content)
        self.assertTrue(any("must not be empty" in error for error in errors))

    def test_reinstall_preserves_existing_routing_and_state_while_migrating_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory)
            active = source_root / cli.ACTIVE_INDEX
            candidate = source_root / cli.CANDIDATE_INDEX
            state = source_root / cli.STATE_FILE
            active.write_text(
                f"{cli.ROUTING_HEADING}\ncustom route\n{cli.CHECKOUTS_HEADING}\nold metadata\n"
                f"## Changed Paths\n- `M\tpath`\n{cli.RESOLUTION_HEADING}\n",
                encoding="utf-8",
            )
            candidate.write_text("custom candidate", encoding="utf-8")
            state.write_text('{"custom": true}\n', encoding="utf-8")
            args = cli.argparse.Namespace(source_root=source_root, config_dir=source_root / "config")
            with patch.object(cli, "prepare_sources"), patch.object(
                cli, "validate_navigation", return_value=[]
            ), patch.object(cli, "checkout_section", return_value=f"{cli.CHECKOUTS_HEADING}\nnew metadata"), patch.object(
                cli, "install_agents"
            ), patch.object(cli, "install_commands"), patch.object(
                cli, "current_revisions", side_effect=AssertionError("must not reseed revisions")
            ):
                cli.command_install(args)
            active_content = active.read_text(encoding="utf-8")
            self.assertIn("custom route", active_content)
            self.assertIn("new metadata", active_content)
            self.assertNotIn("Changed Paths", active_content)
            self.assertEqual("custom candidate", candidate.read_text(encoding="utf-8"))
            self.assertEqual('{"custom": true}\n', state.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
