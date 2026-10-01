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
ROUTING_HEADING = "## Routing Guide"
CHECKOUTS_HEADING = "## Checkouts"
RESOLUTION_HEADING = "## Resolution"
MAX_ROUTING_GROWTH_LINES = 25
MAX_ROUTING_GROWTH_CHARACTERS = 4000
MAX_ROUTING_SHRINK_LINES = 10


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


def write_atomic(path: Path, content: str | bytes) -> None:
    if isinstance(content, str):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
    else:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, delete=False) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def checkout_section(source_root: Path) -> str:
    lines = [
        CHECKOUTS_HEADING,
        "",
        "| Repository | Branch | Revision |",
        "|---|---|---|",
    ]
    for repository in load_repositories():
        checkout = checkout_path(source_root, repository)
        if (checkout / ".git").exists():
            branch = git(checkout, "branch", "--show-current")
            revision = git(checkout, "rev-parse", "HEAD")
            lines.append(f"| `{repository.name}` | `{branch}` | `{revision[:12]}` |")
        else:
            lines.append(f"| `{repository.name}` | - | - |")
    return "\n".join(lines)


def generate_index(source_root: Path, destination: Path | None = None) -> Path:
    content = "\n".join([
        "# IntelliJ Research Navigation Index",
        "",
        "Use this validated local index as the primary navigation guide for the IntelliJ source mirror. Resolve paths relative to the mirror root.",
        "",
        f"Mirror root: `{source_root}`",
        "",
        ROUTING_HEADING,
        "",
        GUIDE.read_text(encoding="utf-8").strip(),
        "",
        checkout_section(source_root),
        "",
        RESOLUTION_HEADING,
        "",
        "Resolve paths in the routing guide relative to the directory containing this file.",
        "",
    ])
    index = destination or source_root / ACTIVE_INDEX
    write_atomic(index, content + "\n")
    return index


def replace_checkout_section(content: str, replacement: str) -> str:
    checkout_matches = list(re.finditer(rf"(?m)^{re.escape(CHECKOUTS_HEADING)}\s*$", content))
    resolution_matches = list(re.finditer(rf"(?m)^{re.escape(RESOLUTION_HEADING)}\s*$", content))
    if len(checkout_matches) != 1 or len(resolution_matches) != 1:
        raise CLIError("Active navigation index must contain exactly one Checkouts and Resolution section")
    checkout = checkout_matches[0]
    resolution = resolution_matches[0]
    if checkout.start() >= resolution.start():
        raise CLIError("Active navigation index has invalid section ordering")
    return content[:checkout.start()] + replacement.rstrip() + "\n\n" + content[resolution.start():]


def prepare_candidate_index(source_root: Path) -> Path:
    active = source_root / ACTIVE_INDEX
    if not active.is_file():
        raise CLIError(f"Missing active navigation index: {active}. Run install first.")
    content = replace_checkout_section(active.read_text(encoding="utf-8"), checkout_section(source_root))
    candidate = source_root / CANDIDATE_INDEX
    write_atomic(candidate, content)
    return candidate


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


def routing_content(content: str) -> str | None:
    routing_matches = list(re.finditer(rf"(?m)^{re.escape(ROUTING_HEADING)}\s*$", content))
    checkout_matches = list(re.finditer(rf"(?m)^{re.escape(CHECKOUTS_HEADING)}\s*$", content))
    if len(routing_matches) != 1 or len(checkout_matches) != 1:
        return None
    routing = routing_matches[0]
    checkout = checkout_matches[0]
    if routing.end() >= checkout.start():
        return None
    return content[routing.end():checkout.start()].strip()


def checkout_content(content: str) -> str | None:
    checkout_matches = list(re.finditer(rf"(?m)^{re.escape(CHECKOUTS_HEADING)}\s*$", content))
    resolution_matches = list(re.finditer(rf"(?m)^{re.escape(RESOLUTION_HEADING)}\s*$", content))
    if len(checkout_matches) != 1 or len(resolution_matches) != 1:
        return None
    checkout = checkout_matches[0]
    resolution = resolution_matches[0]
    if checkout.start() >= resolution.start():
        return None
    return content[checkout.start():resolution.start()].strip()


def navigation_content_errors(content: str) -> list[str]:
    errors: list[str] = []
    routing = routing_content(content)
    if routing is None:
        errors.append("Navigation index must contain one Routing Guide followed by one Checkouts section")
    elif not routing:
        errors.append("Navigation index Routing Guide must not be empty")
    if checkout_content(content) is None:
        errors.append("Navigation index must contain one Checkouts followed by one Resolution section")
    if re.search(r"(?mi)^#{1,6}\s+Changed Paths\s*$", content):
        errors.append("Navigation index contains maintenance-only Changed Paths")
    if re.search(r"(?m)^\s*-\s+`(?:[ACDMRTUXB?]{1,2}|[RC][0-9]+)\t", content):
        errors.append("Navigation index contains maintenance-only Git diff entries")
    if re.search(r"(?mi)^#\s+IntelliJ Research Update Report\s*$", content) or re.search(
        r"(?mi)^\s*-\s+(?:Previous revision|Current revision|Changed paths):", content
    ):
        errors.append("Navigation index contains maintenance-only update report metadata")
    return errors


def routing_growth_errors(active_content: str, candidate_content: str) -> list[str]:
    active_routing = routing_content(active_content)
    candidate_routing = routing_content(candidate_content)
    if active_routing is None or candidate_routing is None:
        return []
    active_lines = len(active_routing.splitlines())
    candidate_lines = len(candidate_routing.splitlines())
    allowed_lines = max(MAX_ROUTING_GROWTH_LINES, (active_lines + 3) // 4)
    allowed_characters = max(MAX_ROUTING_GROWTH_CHARACTERS, (len(active_routing) + 3) // 4)
    allowed_removed_lines = max(MAX_ROUTING_SHRINK_LINES, (active_lines + 3) // 4)
    errors: list[str] = []
    if candidate_lines - active_lines > allowed_lines:
        errors.append(
            f"Routing guide grew by {candidate_lines - active_lines} lines; maximum allowed growth is {allowed_lines}"
        )
    if len(candidate_routing) - len(active_routing) > allowed_characters:
        errors.append(
            "Routing guide grew by "
            f"{len(candidate_routing) - len(active_routing)} characters; maximum allowed growth is {allowed_characters}"
        )
    if active_lines - candidate_lines > allowed_removed_lines:
        errors.append(
            f"Routing guide shrank by {active_lines - candidate_lines} lines; maximum allowed reduction is {allowed_removed_lines}"
        )
    return errors


def validate_navigation(source_root: Path, navigation: Path, baseline: Path | None = None) -> list[str]:
    errors = validate(source_root)
    if not navigation.is_file():
        return [*errors, f"Missing navigation index: {navigation}"]
    content = navigation.read_text(encoding="utf-8")
    errors.extend(navigation_content_errors(content))
    actual_checkouts = checkout_content(content)
    if actual_checkouts is not None and actual_checkouts != checkout_section(source_root):
        errors.append("Navigation index checkout metadata does not match the current source repositories")
    if baseline is not None and baseline.is_file() and baseline != navigation:
        errors.extend(routing_growth_errors(baseline.read_text(encoding="utf-8"), content))
    known_repositories = {repository.name: repository for repository in load_repositories()}
    for token in re.findall(r"`([^`]+)`", content):
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
    active = source_root / ACTIVE_INDEX
    candidate = source_root / CANDIDATE_INDEX
    state = source_root / STATE_FILE
    if not active.exists():
        generate_index(source_root)
    else:
        refreshed = replace_checkout_section(active.read_text(encoding="utf-8"), checkout_section(source_root))
        if refreshed != active.read_text(encoding="utf-8"):
            write_atomic(active, refreshed)
    if not candidate.exists():
        write_atomic(candidate, active.read_bytes())
    if not state.exists():
        write_atomic(state, json.dumps({"revisions": current_revisions(source_root), "seeded": True}, indent=2) + "\n")
    errors = validate_navigation(source_root, active)
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
    candidate = prepare_candidate_index(source_root)
    print(f"Prepared update report: {report}")
    print(f"Prepared navigation candidate: {candidate}")
    return revisions


def command_prepare_update(args: argparse.Namespace) -> None:
    prepare_update(args.source_root.resolve())


def command_finalize_update(args: argparse.Namespace) -> None:
    source_root = args.source_root.resolve()
    candidate = source_root / CANDIDATE_INDEX
    errors = validate_navigation(source_root, candidate, source_root / ACTIVE_INDEX)
    if errors:
        raise CLIError("Validation failed:\n- " + "\n- ".join(errors))
    active = source_root / ACTIVE_INDEX
    state_path = source_root / STATE_FILE
    candidate_content = candidate.read_bytes()
    active_content = active.read_bytes() if active.exists() else None
    state_content = state_path.read_bytes() if state_path.exists() else None
    state = read_state(source_root)
    state["revisions"] = current_revisions(source_root)
    state["last_successful_update"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    updated_state = json.dumps(state, indent=2) + "\n"
    config = config_dir(args.config_dir)
    install_agents(source_root, config / "agents")
    install_commands(source_root, config / "commands")
    try:
        write_atomic(active, candidate_content)
        write_atomic(state_path, updated_state)
    except OSError:
        if active_content is None:
            active.unlink(missing_ok=True)
        else:
            write_atomic(active, active_content)
        if state_content is None:
            state_path.unlink(missing_ok=True)
        else:
            write_atomic(state_path, state_content)
        raise
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
