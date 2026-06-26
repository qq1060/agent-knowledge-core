# Small-Team Guide

Chinese: [zh-CN/team.md](zh-CN/team.md)

This guide is for teams of about ten people who want shared agent context
without operating a service.

## Fit

Use `agent-knowledge-core` when your team wants to share:

- repository conventions
- review checklists
- incident runbooks
- benchmark or validation workflows
- project context that should survive beyond one chat
- agent skills that are useful to more than one person

Do not use it as a ticket system, secret store, database, wiki replacement, or
automatic memory merger.

## Start

Create a team repository:

```bash
ak-core new --template team ./agent-knowledge-team
cd ./agent-knowledge-team
ak-core init --profile team-mac
ak-core validate
ak-core install --inject-routes --dry-run
```

When the dry run looks correct:

```bash
ak-core install --inject-routes
```

## Recommended Shape

```text
agent-knowledge-team/
  memory/
    MEMORY.md
    team/
      README.md
      conventions.md
    projects/
      example.md
  skills/
    owned/
      team-runbook/
        SKILL.md
    vendor/
  manifests/
    skills.json
    skills.lock.json
  profiles/
    team-mac.json
    team-linux.json
```

Keep personal notes in a separate personal knowledge repository. The team
repository should contain only context the team agrees to share.

## What Belongs Here

- Stable team conventions.
- Reusable workflows that more than one person runs.
- Project context with an owner and a recent verification date.
- Troubleshooting steps that are safe for teammates to reuse.
- Public or team-approved third-party skill references.

## What Does Not Belong Here

- Tokens, passwords, cookies, or private keys.
- Customer data or unredacted logs.
- Personal local paths.
- One-person machine facts.
- Large generated memory dumps.
- Claims that nobody on the team is willing to maintain.

## Minimal Review Rules

Use pull requests. A useful review asks:

- Does this belong in the team repository?
- Is the content still accurate?
- Is there an owner for stale-fact cleanup?
- Does it contain secrets, local paths, or customer data?
- Does `ak-core validate` pass?
- Does `ak-core privacy-scan` pass with the team's denylist terms?

Example:

```bash
ak-core privacy-scan --term your-company --term internal-domain
```

## Minimal Frontmatter

Use frontmatter only where it helps maintenance:

```yaml
metadata:
  owner: infra
  status: active
  last_verified: YYYY-MM-DD
```

Recommended status values:

- `active`
- `stale`
- `archived`

Frontmatter is intentionally flexible. Do not build a large taxonomy before the
team needs one.

## CI

A small team usually needs only:

```bash
ak-core validate
ak-core privacy-scan --term your-company --term internal-domain
```

Add custom terms for your company name, internal domains, service prefixes, or
other values that should not appear in the repository.
