# Migration

Chinese: [zh-CN/migration.md](zh-CN/migration.md)

This guide describes how to extract a public core from an existing private
agent-knowledge repository.

1. Create a new public repository for `agent-knowledge-core`.
2. Move reusable code into a package, keeping private memory and owned skills
   out of the public repository.
3. Replace real profiles with examples.
4. Replace real manifests with example entries.
5. Keep generated state out of Git:

```text
local/device.json
local/generated/
local/reports/
skills/vendor/
```

6. Run validation and privacy checks:

```bash
ak-core validate
ak-core generate
ak-core privacy-scan --term company-name --term internal-host
```

7. Review the repository manually before publishing.

Your private repository should continue to own:

- real memory files
- real owned skills
- machine-specific profiles
- lockfiles for the exact external skills you consume
- sync scripts that match your workflow
