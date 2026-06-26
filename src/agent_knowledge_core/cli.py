#!/usr/bin/env python3
"""Lightweight agent skill and memory router.

The core intentionally uses only the Python standard library plus Git.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


MARKER = ".agent-knowledge-source.json"


class AkError(RuntimeError):
    pass


class Repo:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.manifest = self.root / "manifests" / "skills.json"
        self.lockfile = self.root / "manifests" / "skills.lock.json"
        self.local = self.root / "local"
        self.device = self.local / "device.json"
        self.generated = self.local / "generated"
        self.vendor = self.root / "skills" / "vendor"

    def rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root))
        except ValueError:
            return str(path)


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=False)
        f.write("\n")
    tmp.replace(path)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def expand_path(value: str) -> Path:
    if "%USERPROFILE%" in value and "USERPROFILE" not in os.environ:
        home = os.environ.get("HOME")
        if home:
            value = value.replace("%USERPROFILE%", home)
    return Path(os.path.expandvars(os.path.expanduser(value)))


def run(args: List[str], cwd: Optional[Path] = None, check: bool = True, quiet: bool = False) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and proc.returncode != 0:
        msg = proc.stderr.strip() or proc.stdout.strip()
        raise AkError("%s failed: %s" % (" ".join(args), msg))
    if not quiet and proc.stdout.strip():
        print(proc.stdout.rstrip())
    return proc


def source_to_url(source: str) -> str:
    if source.startswith("github:"):
        return "https://github.com/%s.git" % source[len("github:") :]
    if source.startswith("https://") or source.startswith("git@"):
        return source
    raise AkError("unsupported source %r" % source)


def manifest(repo: Repo) -> Dict[str, Any]:
    data = load_json(repo.manifest, {"version": 1, "skills": []})
    data.setdefault("version", 1)
    data.setdefault("skills", [])
    return data


def lockfile(repo: Repo) -> Dict[str, Any]:
    data = load_json(repo.lockfile, {"version": 1, "locked": {}})
    data.setdefault("version", 1)
    data.setdefault("locked", {})
    return data


def current_profile_name(repo: Repo) -> str:
    env = os.environ.get("AGENT_KNOWLEDGE_PROFILE")
    if env:
        return env
    profile = load_json(repo.device, {}).get("profile")
    if profile:
        return profile
    raise AkError("no profile selected; run: ak-core init --profile example-mac")


def profile_path(repo: Repo, name: str) -> Path:
    return repo.root / "profiles" / ("%s.json" % name)


def load_profile(repo: Repo, name: Optional[str] = None) -> Dict[str, Any]:
    if name is None:
        name = current_profile_name(repo)
    path = profile_path(repo, name)
    if not path.exists():
        raise AkError("profile not found: %s" % path)
    data = load_json(path, {})
    data.setdefault("profile", name)
    data.setdefault("include_groups", [])
    data.setdefault("exclude_groups", [])
    data.setdefault("agent_targets", {})
    data.setdefault("memory_roots", [])
    return data


def selected_skills(repo: Repo, profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    include = set(profile.get("include_groups", []))
    exclude = set(profile.get("exclude_groups", []))
    selected = []
    for item in manifest(repo).get("skills", []):
        groups = set(item.get("groups", []))
        if include and not (groups & include):
            continue
        if groups & exclude:
            continue
        selected.append(item)
    return selected


def skill_path(repo: Repo, item: Dict[str, Any]) -> Path:
    if item.get("kind") == "owned":
        return repo.root / item["path"]
    if item.get("kind") == "external":
        return repo.vendor / item["name"]
    raise AkError("unknown skill kind for %s" % item.get("name"))


def skill_file(repo: Repo, item: Dict[str, Any]) -> Path:
    return skill_path(repo, item) / "SKILL.md"


def parse_frontmatter(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    data: Dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def short(text: str, limit: int = 140) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def generated_filename(profile_name: str, agent: str, target: Dict[str, Any]) -> str:
    route_name = Path(target.get("route_file", "")).name
    suffix = route_name if route_name else "ROUTER.md"
    return "%s.%s.%s" % (profile_name, agent, suffix)


def generated_route(repo: Repo, profile: Dict[str, Any], agent: str, skills: List[Dict[str, Any]]) -> str:
    profile_name = profile.get("profile", "unknown")
    lines = [
        "# Agent Knowledge Router - %s" % profile_name,
        "",
        "This file is generated by agent-knowledge-core.",
        "It is a route index, not the full knowledge base.",
        "",
        "## Selected Skills",
        "",
        "| Skill | Kind | Groups | Source | Description |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in skills:
        if agent not in item.get("agents", []):
            continue
        fm = parse_frontmatter(skill_file(repo, item))
        desc = item.get("description") or fm.get("description") or ""
        source = repo.rel(skill_path(repo, item)) if skill_path(repo, item).exists() else "(not fetched)"
        groups = ", ".join(item.get("groups", []))
        lines.append("| `%s` | %s | %s | `%s` | %s |" % (item["name"], item.get("kind", ""), groups, source, short(desc)))

    lines.extend(["", "## Memory Index", "", "- `%s`" % str(repo.root / "memory" / "MEMORY.md"), "", "## Memory Roots", ""])
    for root in profile.get("memory_roots", []):
        lines.append("- `%s`" % str(repo.root / root))
    lines.extend(
        [
            "",
            "## Rules",
            "",
            "- Load full skill instructions only when the task matches the skill.",
            "- Treat external skills as dependencies tracked by `manifests/skills.lock.json`.",
            "- Do not sync generated agent memory directories into this repository.",
            "",
        ]
    )
    return "\n".join(lines)


def write_generated(repo: Repo, profile: Dict[str, Any]) -> Dict[str, Path]:
    skills = selected_skills(repo, profile)
    profile_name = profile.get("profile", "unknown")
    paths = {}
    for agent, target in profile.get("agent_targets", {}).items():
        paths[agent] = repo.generated / generated_filename(profile_name, agent, target)
    for agent, path in paths.items():
        atomic_write(path, generated_route(repo, profile, agent, skills))
    return paths


def update_marker_block(path: Path, block_id: str, content: str, dry_run: bool = False) -> Tuple[bool, str]:
    start = "<!-- agent-knowledge:%s:start -->" % block_id
    end = "<!-- agent-knowledge:%s:end -->" % block_id
    block = "%s\n%s\n%s\n" % (start, content.rstrip(), end)
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if (start in old) != (end in old):
        raise AkError("%s has an incomplete agent-knowledge marker block" % path)
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end) + r"\n?", re.S)
    if pattern.search(old):
        new = pattern.sub(block, old)
    else:
        sep = "" if old.endswith("\n") or not old else "\n"
        new = old + sep + "\n" + block
    if new == old:
        return (False, "unchanged")
    if dry_run:
        diff = difflib.unified_diff(old.splitlines(), new.splitlines(), fromfile=str(path), tofile=str(path) + " (new)", lineterm="")
        return (True, "\n".join(diff))
    if path.exists():
        shutil.copy2(str(path), str(path.with_suffix(path.suffix + ".bak-agent-knowledge")))
    atomic_write(path, new)
    return (True, "updated")


def install_one(repo: Repo, item: Dict[str, Any], agent: str, target_dir: Path, strategy: str, force: bool) -> Tuple[str, str]:
    src = skill_path(repo, item)
    if not (src / "SKILL.md").exists():
        return ("missing", "%s: run `ak-core fetch --name %s` first" % (item["name"], item["name"]))
    target_dir.mkdir(parents=True, exist_ok=True)
    dst = target_dir / item["name"]
    marker = dst / MARKER
    if dst.exists() or dst.is_symlink():
        if dst.is_symlink():
            try:
                if dst.resolve() == src.resolve():
                    return ("ok", "%s already linked for %s" % (item["name"], agent))
            except FileNotFoundError:
                pass
            if not force:
                return ("skip", "%s exists as unmanaged symlink for %s" % (item["name"], agent))
            dst.unlink()
        elif marker.exists() or force:
            if dst.is_dir():
                shutil.rmtree(str(dst))
            else:
                dst.unlink()
        else:
            return ("skip", "%s exists as unmanaged directory for %s" % (item["name"], agent))
    if strategy == "symlink":
        os.symlink(str(src), str(dst), target_is_directory=True)
    elif strategy == "copy":
        shutil.copytree(str(src), str(dst), ignore=shutil.ignore_patterns(".git"))
        save_json(marker, {"managed_by": "agent-knowledge-core", "name": item["name"], "kind": item.get("kind"), "installed_at": now_iso(), "source_path": str(src)})
    else:
        raise AkError("unknown install strategy: %s" % strategy)
    return ("installed", "%s installed for %s via %s" % (item["name"], agent, strategy))


def clone_repo(url: str, ref: str, dest: Path) -> None:
    proc = run(["git", "clone", "--depth", "1", "--branch", ref, url, str(dest)], check=False, quiet=True)
    if proc.returncode == 0:
        return
    run(["git", "clone", "--filter=blob:none", url, str(dest)], quiet=True)
    run(["git", "checkout", ref], cwd=dest, quiet=True)


def rev_parse(repo: Path, spec: str) -> str:
    return run(["git", "rev-parse", spec], cwd=repo, quiet=True).stdout.strip()


def fetch_external(repo: Repo, names: Optional[List[str]] = None) -> List[str]:
    wanted = set(names or [])
    items = [item for item in manifest(repo).get("skills", []) if item.get("kind") == "external" and (not wanted or item.get("name") in wanted)]
    if wanted:
        found = {item["name"] for item in items}
        missing = sorted(wanted - found)
        if missing:
            raise AkError("unknown external skill(s): %s" % ", ".join(missing))
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault((item["source"], item.get("ref", "main")), []).append(item)
    lock = lockfile(repo)
    locked = lock.setdefault("locked", {})
    messages = []
    repo.vendor.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ak-fetch-") as td:
        tmp_root = Path(td)
        for (source, ref), group in grouped.items():
            url = source_to_url(source)
            clone = tmp_root / re.sub(r"[^A-Za-z0-9_.-]+", "_", source + "_" + ref)
            clone_repo(url, ref, clone)
            commit = rev_parse(clone, "HEAD")
            for item in group:
                subdir = item["subdir"].strip("/")
                src = clone / subdir
                if not (src / "SKILL.md").exists():
                    raise AkError("%s does not contain SKILL.md at %s" % (item["name"], subdir))
                dst = repo.vendor / item["name"]
                if dst.exists() or dst.is_symlink():
                    if dst.is_dir() and not dst.is_symlink():
                        shutil.rmtree(str(dst))
                    else:
                        dst.unlink()
                shutil.copytree(str(src), str(dst), ignore=shutil.ignore_patterns(".git"))
                locked[item["name"]] = {
                    "source": source,
                    "subdir": subdir,
                    "ref": ref,
                    "resolved_commit": commit,
                    "tree_sha": rev_parse(clone, "HEAD:%s" % subdir),
                    "fetched_at": now_iso(),
                }
                messages.append("%s fetched at %s" % (item["name"], commit[:12]))
    save_json(repo.lockfile, lock)
    return messages


def iter_text_files(root: Path) -> Iterable[Path]:
    ignored = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv", "dist", "build", "local"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ignored and not d.endswith(".egg-info")]
        for filename in filenames:
            path = Path(dirpath) / filename
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".zip", ".gz", ".tar"}:
                continue
            yield path


def privacy_findings(root: Path, extra_terms: List[str]) -> List[str]:
    checks = [
        ("absolute user home", re.compile(r"/Users/[A-Za-z0-9_.-]+")),
        ("private ipv4-like address", re.compile(r"\b(?:10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b")),
        ("token-like assignment", re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[^'\"\s]{8,}")),
    ]
    for term in extra_terms:
        checks.append(("custom term %r" % term, re.compile(re.escape(term), re.I)))
    findings = []
    for path in iter_text_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            for label, pattern in checks:
                if pattern.search(line):
                    rel = path.relative_to(root)
                    findings.append("%s:%d: %s: %s" % (rel, line_no, label, line.strip()))
    return findings


def validate_manifest(repo: Repo) -> List[str]:
    errors: List[str] = []
    data = manifest(repo)
    names = set()
    for idx, item in enumerate(data.get("skills", [])):
        name = item.get("name")
        if not name:
            errors.append("skill #%d missing name" % idx)
            continue
        if name in names:
            errors.append("duplicate skill name: %s" % name)
        names.add(name)
        kind = item.get("kind")
        if kind not in ("owned", "external"):
            errors.append("%s has invalid kind %r" % (name, kind))
        if not item.get("groups"):
            errors.append("%s has no groups" % name)
        if not item.get("agents"):
            errors.append("%s has no agents" % name)
        if kind == "owned" and not (repo.root / item.get("path", "") / "SKILL.md").exists():
            errors.append("%s owned path missing SKILL.md" % name)
        if kind == "external":
            for key in ("source", "subdir", "ref"):
                if not item.get(key):
                    errors.append("%s external missing %s" % (name, key))
    return errors


def validate_profiles(repo: Repo) -> List[str]:
    errors: List[str] = []
    for path in (repo.root / "profiles").glob("*.json"):
        data = load_json(path, {})
        if not data.get("profile"):
            errors.append("%s missing profile" % repo.rel(path))
        if not data.get("agent_targets"):
            errors.append("%s missing agent_targets" % repo.rel(path))
        for root in data.get("memory_roots", []):
            if not (repo.root / root).exists():
                errors.append("%s references missing memory root %s" % (repo.rel(path), root))
    return errors


def personal_template_files() -> Dict[str, str]:
    return {
        "README.md": "# My Agent Knowledge\n\nThis repository stores scoped skills and memory for local coding agents.\n\n## Quick Start\n\n```bash\nak-core init --profile example-mac\nak-core validate\nak-core generate\nak-core install --inject-routes --dry-run\n```\n",
        ".gitignore": "local/device.json\nlocal/generated/\nlocal/reports/\nskills/vendor/\n__pycache__/\n*.pyc\n",
        "manifests/skills.json": json.dumps({"version": 1, "skills": [{"name": "example-skill", "kind": "owned", "path": "skills/owned/example-skill", "groups": ["common", "mac"], "agents": ["codex", "claude-code"], "description": "Example skill for demonstrating agent-knowledge-core."}]}, indent=2) + "\n",
        "manifests/skills.lock.json": json.dumps({"version": 1, "locked": {}}, indent=2) + "\n",
        "profiles/example-mac.json": json.dumps({"profile": "example-mac", "include_groups": ["common", "mac"], "exclude_groups": ["work-private", "personal-private"], "install_strategy": "symlink", "agent_targets": {"codex": {"skills_dir": "~/.codex/skills", "route_file": "~/.codex/AGENTS.md"}, "claude-code": {"skills_dir": "~/.claude/skills", "route_file": "~/.claude/CLAUDE.md"}}, "memory_roots": ["memory/common"]}, indent=2) + "\n",
        "memory/MEMORY.md": "# Memory Index\n\nRead this file first, then follow only the memory roots selected by the active profile.\n\n## Common\n\n- [Example preference](common/example_preference.md)\n",
        "memory/common/README.md": "# Common Memory\n\nUse this folder for long-lived context that is safe across all selected devices and agents.\n",
        "memory/common/example_preference.md": "---\nmetadata:\n  node_type: memory\n  type: preference\n  status: active\n---\n\n# Example Preference\n\nPrefer small, auditable changes and source-backed answers.\n",
        "skills/owned/README.md": "# Owned Skills\n\nPut skills you maintain here. Each skill directory must contain a `SKILL.md` file.\n",
        "skills/owned/example-skill/SKILL.md": "---\nname: example-skill\ndescription: Example skill for demonstrating agent-knowledge-core.\n---\n\n# Example Skill\n\nUse this skill only for demonstration. Replace it with a real workflow in your private knowledge repository.\n",
    }


def team_template_files() -> Dict[str, str]:
    today = _dt.date.today().isoformat()
    skills = {
        "version": 1,
        "skills": [
            {
                "name": "team-runbook",
                "kind": "owned",
                "path": "skills/owned/team-runbook",
                "groups": ["team"],
                "agents": ["codex", "claude-code"],
                "description": "Small-team runbook skill for reviewed operational workflows.",
            }
        ],
    }
    base_agent_targets = {
        "codex": {"skills_dir": "~/.codex/skills", "route_file": "~/.codex/AGENTS.md"},
        "claude-code": {"skills_dir": "~/.claude/skills", "route_file": "~/.claude/CLAUDE.md"},
    }
    team_mac = {
        "profile": "team-mac",
        "include_groups": ["team", "common", "mac"],
        "exclude_groups": ["personal"],
        "install_strategy": "symlink",
        "agent_targets": base_agent_targets,
        "memory_roots": ["memory/team", "memory/projects"],
    }
    team_linux = {
        "profile": "team-linux",
        "include_groups": ["team", "common", "linux"],
        "exclude_groups": ["personal"],
        "install_strategy": "symlink",
        "agent_targets": base_agent_targets,
        "memory_roots": ["memory/team", "memory/projects"],
    }
    return {
        "README.md": "# Team Agent Knowledge\n\nA lightweight shared knowledge repository for a small team.\n\n## Quick Start\n\n```bash\nak-core init --profile team-mac\nak-core validate\nak-core install --inject-routes --dry-run\n```\n\nUse pull requests for memory and skill changes. Keep personal notes in a separate repository.\n",
        ".gitignore": "local/device.json\nlocal/generated/\nlocal/reports/\nskills/vendor/\n__pycache__/\n*.pyc\n",
        "manifests/skills.json": json.dumps(skills, indent=2) + "\n",
        "manifests/skills.lock.json": json.dumps({"version": 1, "locked": {}}, indent=2) + "\n",
        "profiles/team-mac.json": json.dumps(team_mac, indent=2) + "\n",
        "profiles/team-linux.json": json.dumps(team_linux, indent=2) + "\n",
        "memory/MEMORY.md": "# Memory Index\n\nRead this file first, then follow only the memory roots selected by the active profile.\n\n## Team\n\n- [Team conventions](team/conventions.md)\n\n## Projects\n\n- [Example project](projects/example.md)\n",
        "memory/team/README.md": "# Team Memory\n\nShared conventions and runbooks that apply to the whole team.\n",
        "memory/team/conventions.md": "---\nmetadata:\n  owner: team\n  status: active\n  last_verified: %s\n---\n\n# Team Conventions\n\nPrefer small, auditable changes. Put reusable workflows in skills and project-specific evidence in `memory/projects/`.\n" % today,
        "memory/projects/README.md": "# Project Memory\n\nUse this folder for reviewed project context that more than one teammate needs.\n",
        "memory/projects/example.md": "---\nmetadata:\n  owner: team\n  status: active\n  last_verified: %s\n---\n\n# Example Project\n\nReplace this file with a short project overview, validation commands, and links to reviewed runbooks.\n" % today,
        "skills/owned/README.md": "# Team-Owned Skills\n\nPut reviewed team-maintained skills here. Each skill directory must contain a `SKILL.md` file.\n",
        "skills/owned/team-runbook/SKILL.md": "---\nname: team-runbook\ndescription: Small-team runbook skill for reviewed operational workflows.\n---\n\n# Team Runbook\n\nUse this skill when a teammate asks for a reviewed team workflow. Read the relevant memory index first, keep actions auditable, and do not use secrets from memory files.\n",
        "docs/team.md": "# Team Notes\n\nThis repository is intentionally small. Use Git pull requests for review, `ak-core validate` for structure checks, and `ak-core privacy-scan` as a backstop before merging.\n",
    }


def write_template_repo(path: Path, template: str = "personal") -> None:
    if path.exists() and any(path.iterdir()):
        raise AkError("%s already exists and is not empty" % path)
    path.mkdir(parents=True, exist_ok=True)
    if template == "personal":
        files = personal_template_files()
    elif template == "team":
        files = team_template_files()
    else:
        raise AkError("unknown template: %s" % template)
    for rel_path, content in files.items():
        atomic_write(path / rel_path, content)


def cmd_new(args: argparse.Namespace) -> None:
    write_template_repo(Path(args.path), args.template)
    print("created %s from %s template" % (args.path, args.template))


def cmd_init(args: argparse.Namespace) -> None:
    repo = Repo(Path(args.repo_root))
    if not args.profile:
        raise AkError("choose a profile explicitly, for example: --profile example-mac")
    if not profile_path(repo, args.profile).exists():
        raise AkError("profile does not exist: %s" % args.profile)
    repo.local.mkdir(parents=True, exist_ok=True)
    save_json(repo.device, {"profile": args.profile, "created_at": now_iso(), "host": platform.node(), "os": platform.platform()})
    print("profile set to %s in %s" % (args.profile, repo.rel(repo.device)))


def cmd_validate(args: argparse.Namespace) -> None:
    repo = Repo(Path(args.repo_root))
    errors = validate_manifest(repo) + validate_profiles(repo)
    if errors:
        for err in errors:
            print("ERROR: %s" % err, file=sys.stderr)
        raise SystemExit(1)
    if not args.quiet:
        print("OK")


def cmd_generate(args: argparse.Namespace) -> None:
    repo = Repo(Path(args.repo_root))
    profile = load_profile(repo, args.profile)
    paths = write_generated(repo, profile)
    for agent, path in paths.items():
        print("%s: %s" % (agent, repo.rel(path)))


def cmd_fetch(args: argparse.Namespace) -> None:
    repo = Repo(Path(args.repo_root))
    names = args.name
    if args.selected:
        profile = load_profile(repo, args.profile)
        names = (names or []) + [item["name"] for item in selected_skills(repo, profile) if item.get("kind") == "external"]
        if not names:
            print("nothing to fetch")
            return
    messages = fetch_external(repo, names)
    for msg in messages:
        print(msg)
    if not messages:
        print("nothing to fetch")


def cmd_install(args: argparse.Namespace) -> None:
    repo = Repo(Path(args.repo_root))
    profile = load_profile(repo, args.profile)
    paths = write_generated(repo, profile)
    agents = args.agent or list(profile.get("agent_targets", {}).keys())
    selected = selected_skills(repo, profile)
    strategy = args.strategy or profile.get("install_strategy", "copy" if os.name == "nt" else "symlink")
    for agent in agents:
        target = profile.get("agent_targets", {}).get(agent, {})
        skills_dir = target.get("skills_dir")
        if not skills_dir:
            print("skip %s: no skills_dir in profile" % agent)
            continue
        target_dir = expand_path(skills_dir)
        for item in selected:
            if agent not in item.get("agents", []):
                continue
            if args.dry_run:
                status, msg = ("dry-run", "%s would be installed for %s into %s" % (item["name"], agent, target_dir))
            else:
                status, msg = install_one(repo, item, agent, target_dir, strategy, args.force)
            print("[%s] %s" % (status, msg))
        if args.inject_routes and target.get("route_file"):
            route_path = expand_path(target["route_file"])
            generated = paths.get(agent)
            if generated:
                content = "Shared agent-knowledge router for profile `%s`:\n\n%s\n" % (profile.get("profile"), generated.read_text(encoding="utf-8").rstrip())
                changed, detail = update_marker_block(route_path, "router", content, dry_run=args.dry_run)
                if args.dry_run:
                    print("[route:dry-run] %s" % route_path)
                    if detail:
                        print(detail)
                elif changed:
                    print("[route] updated %s" % route_path)
                else:
                    print("[route] unchanged %s" % route_path)
    print("generated routes are under %s" % repo.rel(repo.generated))


def cmd_privacy_scan(args: argparse.Namespace) -> None:
    findings = privacy_findings(Path(args.repo_root), args.term or [])
    if findings:
        for finding in findings:
            print(finding)
        raise SystemExit(1)
    print("OK: no privacy findings")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ak-core")
    p.add_argument("--repo-root", default=".", help="agent-knowledge repository root; defaults to cwd")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("new", help="create an example agent-knowledge repository")
    s.add_argument("--template", choices=["personal", "team"], default="personal")
    s.add_argument("path")
    s.set_defaults(func=cmd_new)

    s = sub.add_parser("init", help="bind this device to a profile")
    s.add_argument("--profile", required=True)
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("validate")
    s.add_argument("--quiet", action="store_true")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("generate")
    s.add_argument("--profile")
    s.set_defaults(func=cmd_generate)

    s = sub.add_parser("fetch")
    s.add_argument("--name", action="append")
    s.add_argument("--selected", action="store_true", help="fetch external skills selected by the current profile")
    s.add_argument("--profile")
    s.set_defaults(func=cmd_fetch)

    s = sub.add_parser("install")
    s.add_argument("--profile")
    s.add_argument("--agent", action="append", help="agent id, e.g. claude-code or codex")
    s.add_argument("--strategy", choices=["symlink", "copy"])
    s.add_argument("--force", action="store_true")
    s.add_argument("--inject-routes", action="store_true")
    s.add_argument("--dry-run", action="store_true", help="preview route injection without writing route files")
    s.set_defaults(func=cmd_install)

    s = sub.add_parser("privacy-scan", help="scan the repository for common private-information patterns")
    s.add_argument("--term", action="append", help="extra literal term to flag; repeatable")
    s.set_defaults(func=cmd_privacy_scan)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except AkError as exc:
        print("ak-core: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
