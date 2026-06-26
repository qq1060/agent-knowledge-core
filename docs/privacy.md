# Privacy

Chinese: [zh-CN/privacy.md](zh-CN/privacy.md)

`agent-knowledge-core` is intended to be public. A repository containing real
memory and owned skills is often private.

Do not publish a knowledge repository without reviewing it for:

- real names, email addresses, usernames, and home paths
- company names, internal hostnames, private IPs, and service URLs
- model names, artifact paths, dataset paths, and benchmark results that are not
  meant to be public
- API keys, tokens, passwords, cookies, and credentials
- project evidence that was useful to an agent but should not become public

Run the built-in scan before publishing:

```bash
ak-core privacy-scan --term your-company --term internal-hostname
```

The scan flags common patterns such as absolute local home paths, private IP
ranges, and token-like assignments. It is not a substitute for manual review.

## Recommended Split

Use two repositories:

```text
agent-knowledge-core/     public framework and CLI
agent-knowledge-private/  private skills, memory, profiles, and lockfiles
```

The private repository can use `ak-core` as a CLI dependency while keeping all
personal or company-specific content out of the public project.
