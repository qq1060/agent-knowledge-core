# agent-knowledge-core

Chinese: [README.zh-CN.md](README.zh-CN.md)

`agent-knowledge-core` is a lightweight, Git-native router for sharing scoped
skills and long-term memory across coding agents. It is designed for individuals
and small teams of about ten people who want shared agent context without
running any infrastructure.

It provides the public, reusable mechanics behind an agent knowledge repository:

- profile-scoped skill and memory routing
- owned and external skill manifests
- lockfile-backed external skill fetching
- generated router blocks for agent global files
- conservative skill installation by symlink or copy
- a small privacy scan for obvious private-information leaks

It does not provide a cloud memory service, daemon, database, vector store, or
semantic merge engine. Your knowledge remains ordinary files in a repository you
control.

The guiding rule is Occam's razor: prefer plain files, Git review, and explicit
routes until a real small-team workflow breaks without more machinery.

## Quick Start

Create a private knowledge repository from the example template:

```bash
ak-core new ~/agent-knowledge
cd ~/agent-knowledge
ak-core init --profile example-mac
ak-core validate
ak-core generate
ak-core install --inject-routes --dry-run
```

Create a small-team knowledge repository:

```bash
ak-core new --template team ./agent-knowledge-team
cd ./agent-knowledge-team
ak-core init --profile team-mac
ak-core validate
ak-core install --inject-routes --dry-run
```

Install skills and inject the router when the dry run looks correct:

```bash
ak-core install --inject-routes
```

## Repository Concepts

- **Profile**: A machine or context, such as `work-mac` or `home-windows`.
- **Groups**: Tags used to select skills for a profile.
- **Owned skill**: A skill maintained in your knowledge repository.
- **External skill**: A skill fetched from another Git repository and pinned in
  `manifests/skills.lock.json`.
- **Memory roots**: Directories the active profile permits agents to read.
- **Router block**: A generated index inserted into an agent's global file, such
  as `AGENTS.md` or `CLAUDE.md`.

## Commands

| Command | Purpose |
| --- | --- |
| `ak-core new <path>` | Create an example knowledge repository. |
| `ak-core new --template team <path>` | Create a small-team knowledge repository. |
| `ak-core init --profile <name>` | Bind the current device to a profile. |
| `ak-core validate` | Validate manifests and profile files. |
| `ak-core fetch --name <skill>` | Fetch an external skill into `skills/vendor/`. |
| `ak-core fetch --selected` | Fetch external skills selected by the active profile. |
| `ak-core generate` | Generate router files into `local/generated/`. |
| `ak-core install` | Install selected skills into configured agent skill dirs. |
| `ak-core install --inject-routes` | Install skills and update agent global router blocks. |
| `ak-core privacy-scan` | Scan for common private-information patterns. |

Use `--repo-root <path>` from outside a knowledge repository.

## Safety Model

Generated and machine-local state should not be committed:

```text
local/device.json
local/generated/
local/reports/
skills/vendor/
```

External skills are reproducible from `manifests/skills.json` and
`manifests/skills.lock.json`. Owned skills and curated memory are the durable
source of truth.

Before publishing a knowledge repository, run:

```bash
ak-core privacy-scan --term your-company --term internal-hostname
```

The scan is intentionally conservative and cannot prove that a repository is
safe to publish. Treat it as a backstop, then review manually.

## Small Teams

For a small team, keep the repository boring:

- Use Git hosting permissions instead of a custom permission system.
- Use pull requests instead of a custom review UI.
- Use `ak-core validate` and `ak-core privacy-scan` in CI.
- Keep personal notes in a separate personal repository.

See [docs/team.md](docs/team.md) and [docs/security.md](docs/security.md).
