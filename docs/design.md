# Design

Chinese: [zh-CN/design.md](zh-CN/design.md)

## Goals

- Share scoped skills and memory across multiple coding agents.
- Fit individuals and small teams of about ten people.
- Keep the storage model inspectable: ordinary files, Git, and Python stdlib.
- Make profile boundaries explicit.
- Install skills into native agent locations while keeping memory routed by
  reference.
- Preserve provenance for external skills.

## Non-Goals

- No database.
- No daemon.
- No vector index.
- No web UI.
- No custom permission system.
- No automatic semantic merge.
- No automatic upgrade of external skills.

## Small-Team Principle

Prefer plain files, Git review, and explicit routes. Add no service, database,
daemon, UI, policy engine, or merge system until a real workflow breaks without
it.

## Layers

### Skills

Owned skills live under:

```text
skills/owned/<name>/SKILL.md
```

External skills are declared in:

```text
manifests/skills.json
```

They are fetched into:

```text
skills/vendor/<name>
```

The vendor directory is generated cache and should not be committed.

### Memory

Memory is curated Markdown, not a symlink to any agent's generated memory
directory. Profiles select allowed roots such as:

```text
memory/common
memory/work
memory/personal
```

Agents should read `memory/MEMORY.md` first, then follow only the roots selected
by the active profile.

Frontmatter is intentionally flexible. Keep only the fields that help humans
maintain the file, such as `owner`, `status`, and `last_verified`.

### Profiles

Profiles select skills by groups:

```json
{
  "include_groups": ["common", "mac"],
  "exclude_groups": ["work-private"],
  "memory_roots": ["memory/common"]
}
```

Profiles also define agent targets:

```json
{
  "agent_targets": {
    "codex": {
      "skills_dir": "~/.codex/skills",
      "route_file": "~/.codex/AGENTS.md"
    }
  }
}
```

### Router Blocks

`ak-core install --inject-routes` writes a managed marker block:

```text
<!-- agent-knowledge:router:start -->
...
<!-- agent-knowledge:router:end -->
```

If only one marker is present, the command stops and asks for manual repair.
