import json
import tempfile
import unittest
from pathlib import Path

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
                self.assertIn("intellij-research", metadata["files"])
            finally:
                cli.TEMPLATE_DIR = old_template_dir


if __name__ == "__main__":
    unittest.main()
