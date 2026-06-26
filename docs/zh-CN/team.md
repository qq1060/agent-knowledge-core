# 小团队指南

English: [../team.md](../team.md)

本指南面向约 10 人左右、希望共享 agent 上下文但不想运行服务的小团队。

## 适用场景

当团队希望共享这些内容时，可以使用 `agent-knowledge-core`：

- 仓库约定
- review checklist
- 事故 runbook
- benchmark 或验证流程
- 应该跨 chat 保留的项目上下文
- 对多名成员有用的 agent skills

不要把它当成工单系统、secret store、数据库、wiki 替代品或自动 memory 合并器。

## 开始使用

创建团队仓：

```bash
ak-core new --template team ./agent-knowledge-team
cd ./agent-knowledge-team
ak-core init --profile team-mac
ak-core validate
ak-core install --inject-routes --dry-run
```

确认 dry run 内容无误后：

```bash
ak-core install --inject-routes
```

## 推荐结构

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

个人笔记放在单独的个人知识仓。团队仓只放团队明确同意共享的上下文。

## 适合放入团队仓的内容

- 稳定的团队约定。
- 多人会复用的工作流。
- 有 owner 和近期验证日期的项目上下文。
- 队友可安全复用的排障步骤。
- 公开或团队认可的第三方 skill 引用。

## 不适合放入团队仓的内容

- Tokens、passwords、cookies 或 private keys。
- 客户数据或未脱敏日志。
- 个人本机路径。
- 只对某一台机器或某一个人成立的事实。
- 大型生成态 memory dump。
- 团队无人愿意维护的结论。

## 最小 Review 规则

使用 pull request。一个有用的 review 会问：

- 这条内容是否应该进入团队仓？
- 内容是否仍然准确？
- 是否有人负责清理过期事实？
- 是否包含 secrets、本地路径或客户数据？
- `ak-core validate` 是否通过？
- `ak-core privacy-scan` 搭配团队 denylist terms 是否通过？

示例：

```bash
ak-core privacy-scan --term your-company --term internal-domain
```

## 最小 Frontmatter

只在有助于维护时使用 frontmatter：

```yaml
metadata:
  owner: infra
  status: active
  last_verified: YYYY-MM-DD
```

推荐 status：

- `active`
- `stale`
- `archived`

Frontmatter 有意保持灵活。不要在团队真正需要之前建立大型分类体系。

## CI

小团队通常只需要：

```bash
ak-core validate
ak-core privacy-scan --term your-company --term internal-domain
```

把公司名、内部域名、服务前缀或其他不应出现在仓库里的值加入自定义 terms。
