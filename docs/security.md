# Security

Chinese: [zh-CN/security.md](zh-CN/security.md)

`agent-knowledge-core` keeps security simple. It does not implement permissions,
roles, or a policy service. Use your Git host for access control and pull
request review.

## Defaults

- Keep the core project public and generic.
- Keep real team memory and team-owned skills in a private repository unless the
  team has explicitly reviewed them for publication.
- Do not commit generated directories such as `local/` or `skills/vendor/`.
- Do not store secrets in memory files or skill instructions.

## Lightweight Checks

Run these before merging changes:

```bash
ak-core validate
ak-core privacy-scan --term your-company --term internal-domain
```

The privacy scan catches common local paths, private IP-like values, token-like
assignments, and team-provided denylist terms. It is a backstop, not a guarantee.

## Team Repository Boundaries

Good team-shared content:

- reviewed runbooks
- coding and review conventions
- reproducible validation commands
- project notes with an owner and last verification date
- skills that do not contain credentials or private local assumptions

Keep out:

- secrets
- customer data
- unredacted logs
- personal notes
- one-person machine setup details
- raw generated agent memory

If a fact is true only on one person or one machine, keep it personal or mark it
clearly as stale-prone project evidence.
