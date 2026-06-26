# 迁移说明

English: [../migration.md](../migration.md)

本指南说明如何从现有私有 agent-knowledge 仓中抽取公开 core。

1. 为 `agent-knowledge-core` 创建新的公开仓库。
2. 将可复用代码移入 Python 包，确保私有 memory 和 owned skills 不进入公开仓。
3. 用示例 profiles 替换真实 profiles。
4. 用示例 manifest 条目替换真实 manifest。
5. 不提交生成态：

```text
local/device.json
local/generated/
local/reports/
skills/vendor/
```

6. 运行校验和隐私检查：

```bash
ak-core validate
ak-core generate
ak-core privacy-scan --term company-name --term internal-host
```

7. 发布前人工 review 整个仓库。

私有仓应该继续持有：

- 真实 memory 文件
- 真实 owned skills
- 机器特定 profiles
- 你实际使用的外部 skills lockfile
- 符合你工作流的 sync scripts
