from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "repositories.json"
GUIDE = ROOT / "guides" / "AGENTS.md"
TEMPLATE_DIR = ROOT / "agents"
DEFAULT_SOURCE_ROOT = ROOT / "sources"
INSTALL_METADATA = ".intellij-research-install.json"
ACTIVE_INDEX = ".intellij-research-index.md"
CANDIDATE_INDEX = ".intellij-research-index.candidate.md"
UPDATE_REPORT = ".intellij-research-update-report.md"
STATE_FILE = ".intellij-research-state.json"


class CLIError(RuntimeError):
    pass


@dataclass(frozen=True)
class Repository:
    name: str
    url: str
    branch: str
    recursive_submodules: bool
    important_paths: tuple[str, ...]


def load_repositories() -> list[Repository]:
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CLIError(f"Cannot read {MANIFEST}: {error}") from error
    return [
        Repository(
            name=item["name"],
            url=item["url"],
            branch=item["branch"],
            recursive_submodules=bool(item.get("recursive_submodules", False)),
            important_paths=tuple(item.get("important_paths", [])),
        )
        for item in data
    ]


def run(command: list[str], cwd: Path | None = None, *, capture: bool = True) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
        )
    except FileNotFoundError as error:
        raise CLIError(f"Required command is not available: {command[0]}") from error
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "").strip()
        raise CLIError(f"Command failed ({error.returncode}): {' '.join(command)}\n{detail}") from error
    return result.stdout.strip() if capture else ""


def git(repo: Path, *args: str) -> str:
    return run(["git", "-C", str(repo), *args])


def ensure_git() -> None:
    run(["git", "--version"])


def ensure_clean(repo: Path) -> None:
    if git(repo, "status", "--porcelain"):
        raise CLIError(f"Refusing to update dirty repository: {repo}")


def ensure_expected_remote(repo: Path, expected: str) -> None:
    actual = git(repo, "remote", "get-url", "origin")
    if actual != expected:
        raise CLIError(f"Unexpected origin for {repo}: expected {expected}, found {actual}")


def checkout_path(source_root: Path, repository: Repository) -> Path:
    return source_root / repository.name


def clone_repository(source_root: Path, repository: Repository) -> None:
    destination = checkout_path(source_root, repository)
    if destination.exists():
        if not (destination / ".git").exists():
            raise CLIError(f"Expected a Git checkout at {destination}, but it is not one")
        ensure_expected_remote(destination, repository.url)
        current_branch = git(destination, "branch", "--show-current")
        if current_branch != repository.branch:
            raise CLIError(f"{destination} is on branch {current_branch!r}; expected {repository.branch!r}")
        return
    command = ["git", "clone", "--branch", repository.branch]
    if repository.recursive_submodules:
        command.append("--recurse-submodules")
    command.extend([repository.url, str(destination)])
    print(f"Cloning {repository.name}")
    run(command, capture=False)


def update_repository(source_root: Path, repository: Repository, *, fetch: bool = True) -> tuple[str, str, list[str]]:
    checkout = checkout_path(source_root, repository)
    if not (checkout / ".git").exists():
        raise CLIError(f"Missing checkout: {checkout}. Run install first.")
    ensure_clean(checkout)
    ensure_expected_remote(checkout, repository.url)
    before = git(checkout, "rev-parse", "HEAD")
    current_branch = git(checkout, "branch", "--show-current")
    if current_branch != repository.branch:
        raise CLIError(f"{checkout} is on branch {current_branch!r}; expected {repository.branch!r}")
    if fetch:
        run(["git", "-C", str(checkout), "fetch", "--prune", "origin", repository.branch], capture=False)
    run(["git", "-C", str(checkout), "merge", "--ff-only", f"origin/{repository.branch}"], capture=False)
    run(["git", "-C", str(checkout), "submodule", "update", "--init", "--recursive"], capture=False)
    after = git(checkout, "rev-parse", "HEAD")
    changed = git(checkout, "diff", "--name-status", before, after).splitlines() if before != after else []
    return before, after, changed


def install_guide(source_root: Path) -> None:
    source_root.mkdir(parents=True, exist_ok=True)
    target = source_root / "AGENTS.md"
    content = GUIDE.read_text(encoding="utf-8")
    if target.exists() and target.read_text(encoding="utf-8") != content:
        print(f"Refreshing generated baseline: {target}")
    target.write_text(content, encoding="utf-8")


def path_state(source_root: Path, repository: Repository, relative: str) -> str:
    path = checkout_path(source_root, repository) / relative
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "file"
    return "MISSING"


def write_atomic(path: Path, content: str | bytes) -> None:
    if isinstance(content, str):
        temporary = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False)
    else:
        temporary = tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False)
    with temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def generate_index(source_root: Path, revisions: dict[str, tuple[str, str, list[str]]] | None = None, destination: Path | None = None) -> Path:
    revisions = revisions or {}
    lines = [
        "# IntelliJ Research Navigation Index",
        "",
        "Use this validated local index as the primary navigation guide for the IntelliJ source mirror. Resolve paths relative to the mirror root.",
        "",
        f"Mirror root: `{source_root}`",
        "",
        "## Routing Guide",
        "",
        GUIDE.read_text(encoding="utf-8").strip(),
        "",
        "## Checkouts",
        "",
        "| Repository | Branch | Revision | Update | Important paths |",
        "|---|---|---|---|---|",
    ]
    for repository in load_repositories():
        checkout = checkout_path(source_root, repository)
        if (checkout / ".git").exists():
            branch = git(checkout, "branch", "--show-current")
            revision = git(checkout, "rev-parse", "HEAD")
            before, after, changed = revisions.get(repository.name, (revision, revision, []))
            update = "unchanged" if before == after else f"{before[:12]} -> {after[:12]}"
            paths = ", ".join(
                f"`{item}` ({path_state(source_root, repository, item)})" for item in repository.important_paths
            )
            lines.append(f"| `{repository.name}` | `{branch}` | `{revision[:12]}` | {update} ({len(changed)} paths) | {paths} |")
        else:
            lines.append(f"| `{repository.name}` | - | - | missing | - |")
    lines.extend(["", "## Changed Paths", ""])
    for repository in load_repositories():
        changed = revisions.get(repository.name, ("", "", []))[2]
        if changed:
            lines.append(f"### {repository.name}")
            lines.extend(f"- `{item}`" for item in changed)
            lines.append("")
    lines.extend(["## Resolution", "", "Resolve paths in the routing guide relative to the directory containing this file.", ""])
    index = destination or source_root / ACTIVE_INDEX
    write_atomic(index, "\n".join(lines) + "\n")
    return index


def current_revisions(source_root: Path) -> dict[str, str]:
    return {
        repository.name: git(checkout_path(source_root, repository), "rev-parse", "HEAD")
        for repository in load_repositories()
    }


def write_update_report(source_root: Path, revisions: dict[str, tuple[str, str, list[str]]]) -> Path:
    lines = [
        "# IntelliJ Research Update Report",
        "",
        "Generated by `python -m intellij_research prepare-update`. Review this report before finalizing navigation.",
        "",
    ]
    for repository in load_repositories():
        before, after, changed = revisions[repository.name]
        lines.extend([
            f"## {repository.name}",
            "",
            f"- Previous revision: `{before}`",
            f"- Current revision: `{after}`",
            f"- Changed paths: {len(changed)}",
            "",
        ])
        lines.extend(f"- `{item}`" for item in changed)
        lines.append("")
    report = source_root / UPDATE_REPORT
    write_atomic(report, "\n".join(lines))
    return report


def read_state(source_root: Path) -> dict[str, Any]:
    path = source_root / STATE_FILE
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise CLIError(f"Invalid research state: {path}") from error


def validate_navigation(source_root: Path, navigation: Path) -> list[str]:
    errors = validate(source_root)
    if not navigation.is_file():
        return [*errors, f"Missing navigation index: {navigation}"]
    known_repositories = {repository.name: repository for repository in load_repositories()}
    for token in re.findall(r"`([^`]+)`", navigation.read_text(encoding="utf-8")):
        if "/" not in token or token.startswith(("http://", "https://")):
            continue
        repository_name, relative = token.split("/", 1)
        repository = known_repositories.get(repository_name)
        if repository is None:
            continue
        candidate = relative.removesuffix("/**")
        root = checkout_path(source_root, repository)
        exists = any(root.glob(relative)) if any(character in relative for character in "*?[") else (root / candidate).exists()
        if not exists:
            errors.append(f"Navigation path does not exist: {repository_name}/{relative}")
    return errors


def validate(source_root: Path) -> list[str]:
    errors: list[str] = []
    if not GUIDE.is_file():
        errors.append(f"Missing baseline guide: {GUIDE}")
    if not (source_root / "AGENTS.md").is_file():
        errors.append(f"Missing installed guide: {source_root / 'AGENTS.md'}")
    for repository in load_repositories():
        checkout = checkout_path(source_root, repository)
        if not (checkout / ".git").exists():
            errors.append(f"Missing checkout: {checkout}")
            continue
        for relative in repository.important_paths:
            if not (checkout / relative).exists():
                errors.append(f"Missing important path: {checkout / relative}")
    return errors


def config_dir(explicit: Path | None) -> Path:
    if explicit:
        return explicit.expanduser().resolve()
    try:
        output = run(["opencode", "debug", "paths"])
        for line in output.splitlines():
            key, separator, value = line.partition(" ")
            if key == "config" and separator:
                return Path(value.strip()).expanduser().resolve()
    except CLIError:
        pass
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base).expanduser().resolve() / "opencode"
    return Path.home() / ".config" / "opencode"


def render(template: Path, source_root: Path) -> str:
    source = source_root.as_posix()
    index = (source_root / ACTIVE_INDEX).as_posix()
    repository_root = ROOT.as_posix()
    return (
        template.read_text(encoding="utf-8")
        .replace("{{SOURCE_ROOT}}", source)
        .replace("{{REPO_ROOT}}", repository_root)
        .replace("{{INDEX_PATH}}", index)
        .replace("{{ACTIVE_INDEX}}", ACTIVE_INDEX)
        .replace("{{CANDIDATE_INDEX}}", CANDIDATE_INDEX)
        .replace("{{UPDATE_REPORT}}", UPDATE_REPORT)
        .replace("{{STATE_FILE}}", STATE_FILE)
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def metadata_path(destination: Path) -> Path:
    return destination / INSTALL_METADATA


def read_metadata(destination: Path) -> dict[str, Any]:
    path = metadata_path(destination)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise CLIError(f"Invalid installation metadata: {path}") from error


def install_agents(source_root: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    old = read_metadata(destination)
    old_files: dict[str, str] = old.get("agents", old.get("files", {}))
    rendered = {
        template.stem.removesuffix(".md"): render(template, source_root)
        for template in sorted(TEMPLATE_DIR.glob("*.md.in"))
    }
    for name, content in rendered.items():
        target = destination / f"{name}.md"
        if target.exists():
            current_hash = sha256_text(target.read_text(encoding="utf-8"))
            if name not in old_files:
                raise CLIError(f"Unmanaged agent already exists; refusing to overwrite: {target}")
            if current_hash != old_files[name]:
                raise CLIError(f"Installed agent was modified; refusing to overwrite: {target}")
    for name, content in rendered.items():
        target = destination / f"{name}.md"
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination, delete=False) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
        temporary_path.replace(target)
    metadata = {
        "source_root": str(source_root),
        "agents": {name: sha256_text(content) for name, content in rendered.items()},
        "commands": old.get("commands", {}),
    }
    write_atomic(metadata_path(destination), json.dumps(metadata, indent=2) + "\n")
    print(f"Installed {len(rendered)} agents into {destination}")


def install_commands(source_root: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    metadata_destination = destination.parent / "agents"
    old = read_metadata(metadata_destination)
    old_files: dict[str, str] = old.get("commands", {})
    rendered = {
        template.stem.removesuffix(".md"): render(template, source_root)
        for template in sorted((TEMPLATE_DIR.parent / "commands").glob("*.md.in"))
    }
    for name, content in rendered.items():
        target = destination / f"{name}.md"
        if target.exists():
            current_hash = sha256_text(target.read_text(encoding="utf-8"))
            if name not in old_files:
                raise CLIError(f"Unmanaged command already exists; refusing to overwrite: {target}")
            if current_hash != old_files[name]:
                raise CLIError(f"Installed command was modified; refusing to overwrite: {target}")
    for name, content in rendered.items():
        write_atomic(destination / f"{name}.md", content)
    metadata = {
        "source_root": str(source_root),
        "agents": old.get("agents", old.get("files", {})),
        "commands": {name: sha256_text(content) for name, content in rendered.items()},
    }
    write_atomic(metadata_path(metadata_destination), json.dumps(metadata, indent=2) + "\n")
    print(f"Installed {len(rendered)} commands into {destination}")


def remove_agents(destination: Path) -> None:
    metadata = read_metadata(destination)
    files: dict[str, str] = {
        **metadata.get("agents", metadata.get("files", {})),
        **{f"command:{name}": digest for name, digest in metadata.get("commands", {}).items()},
    }
    if not files:
        raise CLIError(f"No managed installation found in {destination}")
    for name, expected in files.items():
        command = name.startswith("command:")
        actual_name = name.removeprefix("command:")
        target = destination.parent / "commands" / f"{actual_name}.md" if command else destination / f"{actual_name}.md"
        if not target.is_file() or sha256_text(target.read_text(encoding="utf-8")) != expected:
            raise CLIError(f"Managed agent was modified or removed; refusing to uninstall: {target}")
    for name in files:
        command = name.startswith("command:")
        actual_name = name.removeprefix("command:")
        target = destination.parent / "commands" / f"{actual_name}.md" if command else destination / f"{actual_name}.md"
        target.unlink()
    metadata_path(destination).unlink()
    print(f"Removed managed agents from {destination}")


def prepare_sources(source_root: Path) -> None:
    ensure_git()
    source_root.mkdir(parents=True, exist_ok=True)
    for repository in load_repositories():
        clone_repository(source_root, repository)
    install_guide(source_root)


def command_install(args: argparse.Namespace) -> None:
    source_root = args.source_root.resolve()
    prepare_sources(source_root)
    generate_index(source_root)
    write_atomic(source_root / CANDIDATE_INDEX, (source_root / ACTIVE_INDEX).read_bytes())
    write_atomic(source_root / STATE_FILE, json.dumps({"revisions": current_revisions(source_root), "seeded": True}, indent=2) + "\n")
    errors = validate_navigation(source_root, source_root / ACTIVE_INDEX)
    if errors:
        raise CLIError("Validation failed:\n- " + "\n- ".join(errors))
    config = config_dir(args.config_dir)
    install_agents(source_root, config / "agents")
    install_commands(source_root, config / "commands")
    print("Installation complete. Restart OpenCode to load the agents.")


def prepare_update(source_root: Path) -> dict[str, tuple[str, str, list[str]]]:
    if not source_root.is_dir():
        raise CLIError(f"Missing source root: {source_root}. Run install first.")
    repositories = load_repositories()
    for repository in repositories:
        checkout = checkout_path(source_root, repository)
        if not (checkout / ".git").exists():
            raise CLIError(f"Missing checkout: {checkout}. Run install first.")
        ensure_clean(checkout)
        ensure_expected_remote(checkout, repository.url)
        current_branch = git(checkout, "branch", "--show-current")
        if current_branch != repository.branch:
            raise CLIError(f"{checkout} is on branch {current_branch!r}; expected {repository.branch!r}")
    for repository in repositories:
        checkout = checkout_path(source_root, repository)
        run(["git", "-C", str(checkout), "fetch", "--prune", "origin", repository.branch], capture=False)

    state = read_state(source_root)
    audited_revisions: dict[str, str] = state.get("revisions", {})
    revisions: dict[str, tuple[str, str, list[str]]] = {}
    for repository in repositories:
        before, after, changed = update_repository(source_root, repository, fetch=False)
        audit_from = audited_revisions.get(repository.name, before)
        if audit_from != before:
            changed = git(checkout_path(source_root, repository), "diff", "--name-status", audit_from, after).splitlines()
        revisions[repository.name] = (audit_from, after, changed)
    install_guide(source_root)
    report = write_update_report(source_root, revisions)
    generate_index(source_root, revisions, source_root / CANDIDATE_INDEX)
    print(f"Prepared update report: {report}")
    print(f"Prepared navigation candidate: {source_root / CANDIDATE_INDEX}")
    return revisions


def command_prepare_update(args: argparse.Namespace) -> None:
    prepare_update(args.source_root.resolve())


def command_finalize_update(args: argparse.Namespace) -> None:
    source_root = args.source_root.resolve()
    candidate = source_root / CANDIDATE_INDEX
    errors = validate_navigation(source_root, candidate)
    if errors:
        raise CLIError("Validation failed:\n- " + "\n- ".join(errors))
    active = source_root / ACTIVE_INDEX
    active.replace(active.with_name(f".{active.name}.previous")) if active.exists() else None
    candidate.replace(active)
    write_atomic(source_root / CANDIDATE_INDEX, active.read_bytes())
    state = read_state(source_root)
    state["revisions"] = current_revisions(source_root)
    state["last_successful_update"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    write_atomic(source_root / STATE_FILE, json.dumps(state, indent=2) + "\n")
    config = config_dir(args.config_dir)
    install_agents(source_root, config / "agents")
    install_commands(source_root, config / "commands")
    previous = active.with_name(f".{active.name}.previous")
    if previous.exists():
        previous.unlink()
    print("Navigation candidate validated and promoted. Restart OpenCode if installed definitions changed.")


def command_update(args: argparse.Namespace) -> None:
    prepare_update(args.source_root.resolve())
    print("Run the /update-intellij-research command to review and finalize the navigation candidate.")


def command_validate(args: argparse.Namespace) -> None:
    source_root = args.source_root.resolve()
    errors = validate_navigation(source_root, source_root / ACTIVE_INDEX)
    if errors:
        raise CLIError("Validation failed:\n- " + "\n- ".join(errors))
    print(f"Validated source mirror: {args.source_root.resolve()}")


def command_uninstall(args: argparse.Namespace) -> None:
    remove_agents(config_dir(args.config_dir) / "agents")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Manage IntelliJ source checkouts and OpenCode research agents.")
    result.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT, help="Directory containing source clones")
    result.add_argument("--config-dir", type=Path, help="OpenCode config directory override")
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("install", help="Clone sources, validate, and install agents")
    commands.add_parser("prepare-update", help="Fetch sources and create a report plus navigation candidate")
    commands.add_parser("finalize-update", help="Validate and atomically promote the navigation candidate")
    commands.add_parser("update-agent", help="Compatibility alias for prepare-update")
    commands.add_parser("validate", help="Validate source checkouts and important paths")
    commands.add_parser("uninstall", help="Remove agents installed by this repository")
    return result


def main() -> None:
    args = parser().parse_args()
    try:
        {
            "install": command_install,
            "prepare-update": command_prepare_update,
            "finalize-update": command_finalize_update,
            "update-agent": command_update,
            "validate": command_validate,
            "uninstall": command_uninstall,
        }[args.command](args)
    except CLIError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
