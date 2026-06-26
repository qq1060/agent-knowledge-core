# agent-knowledge-core

English: [README.md](README.md)

`agent-knowledge-core` 是一个轻量的 Git-native 路由器，用来在不同 coding agent
之间共享有边界的 skills 和长期上下文。它面向个人和约 10 人左右的小团队：希望共享
agent 上下文，但不想运行任何额外基础设施。

它提供 agent knowledge 仓库背后的通用机制：

- 按 profile 路由 skill 和 memory
- 管理自有 skill 和外部 skill manifest
- 用 lockfile 记录外部 skill 的来源和版本
- 生成可注入 agent 全局文件的 router block
- 以 symlink 或 copy 的方式保守安装 skill
- 提供一个轻量隐私扫描，拦截明显的私有信息泄漏

它不提供云端 memory 服务、daemon、数据库、向量库或语义合并引擎。知识仍然是你
控制的仓库里的普通文件。

指导原则是奥卡姆剃刀：优先使用普通文件、Git review 和显式路由；只有当真实的小团队
流程缺少某个机制就转不动时，才增加更多东西。

## 快速开始

创建个人知识仓：

```bash
ak-core new ~/agent-knowledge
cd ~/agent-knowledge
ak-core init --profile example-mac
ak-core validate
ak-core generate
ak-core install --inject-routes --dry-run
```

创建小团队知识仓：

```bash
ak-core new --template team ./agent-knowledge-team
cd ./agent-knowledge-team
ak-core init --profile team-mac
ak-core validate
ak-core install --inject-routes --dry-run
```

确认 dry run 内容无误后安装 skill 并注入路由：

```bash
ak-core install --inject-routes
```

## 核心概念

- **Profile**：一台机器或一个使用场景，例如 `work-mac`、`home-windows`。
- **Groups**：用于为 profile 选择 skill 的标签。
- **Owned skill**：由你或团队维护在知识仓中的 skill。
- **External skill**：从其他 Git 仓库拉取并记录在 `manifests/skills.lock.json` 中的 skill。
- **Memory roots**：当前 profile 允许 agent 读取的 memory 目录。
- **Router block**：注入到 agent 全局文件里的生成索引，例如 `AGENTS.md` 或 `CLAUDE.md`。

## 命令

| 命令 | 用途 |
| --- | --- |
| `ak-core new <path>` | 创建示例个人知识仓。 |
| `ak-core new --template team <path>` | 创建小团队知识仓。 |
| `ak-core init --profile <name>` | 将当前设备绑定到某个 profile。 |
| `ak-core validate` | 校验 manifests 和 profiles。 |
| `ak-core fetch --name <skill>` | 拉取外部 skill 到 `skills/vendor/`。 |
| `ak-core fetch --selected` | 拉取当前 profile 选中的外部 skills。 |
| `ak-core generate` | 生成 router 文件到 `local/generated/`。 |
| `ak-core install` | 安装选中的 skills 到 agent skill 目录。 |
| `ak-core install --inject-routes` | 安装 skills 并更新 agent 全局 router block。 |
| `ak-core privacy-scan` | 扫描常见私有信息模式。 |

从知识仓目录外运行时，可以使用 `--repo-root <path>`。

## 安全模型

生成态和机器本地状态不应提交：

```text
local/device.json
local/generated/
local/reports/
skills/vendor/
```

外部 skills 可以从 `manifests/skills.json` 和 `manifests/skills.lock.json` 重建。
自有 skills 和人工整理的 memory 才是长期事实来源。

发布知识仓前运行：

```bash
ak-core privacy-scan --term your-company --term internal-hostname
```

其中 `your-company` 和 `internal-hostname` 是占位符，请替换为团队自己的敏感词。

扫描只是保守的兜底，不能证明仓库一定安全。发布前仍需要人工 review。

## 小团队

小团队应该让仓库保持朴素：

- 用 Git hosting 权限，不做自定义权限系统。
- 用 pull request，不做自定义 review UI。
- 在 CI 里跑 `ak-core validate` 和 `ak-core privacy-scan`。
- 个人笔记放在单独的个人知识仓。

更多说明见 [docs/zh-CN/team.md](docs/zh-CN/team.md) 和
[docs/zh-CN/security.md](docs/zh-CN/security.md)。
