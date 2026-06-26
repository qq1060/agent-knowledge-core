# 设计说明

English: [../design.md](../design.md)

## 目标

- 在多个 coding agent 之间共享有边界的 skills 和 memory。
- 适合个人和约 10 人左右的小团队。
- 保持存储模型可检查：普通文件、Git、Python 标准库。
- 明确 profile 边界。
- 将 skills 安装到 agent 原生目录，同时通过引用路由 memory。
- 保留外部 skills 的来源和版本信息。

## 非目标

- 不引入数据库。
- 不运行 daemon。
- 不维护向量索引。
- 不提供 Web UI。
- 不实现自定义权限系统。
- 不自动做语义合并。
- 不自动升级外部 skills。

## 小团队原则

优先使用普通文件、Git review 和显式路由。除非真实流程已经离不开，否则不增加服务、
数据库、daemon、UI、策略引擎或合并系统。

## 分层

### Skills

自有 skills 放在：

```text
skills/owned/<name>/SKILL.md
```

外部 skills 在这里声明：

```text
manifests/skills.json
```

拉取后缓存到：

```text
skills/vendor/<name>
```

`skills/vendor/` 是可重建缓存，不应提交。

### Memory

Memory 是人工整理的 Markdown，不是任何 agent 自动生成 memory 目录的 symlink。
Profiles 选择允许读取的 roots，例如：

```text
memory/common
memory/work
memory/personal
```

Agent 应先读 `memory/MEMORY.md`，再只进入当前 profile 允许的 roots。

Frontmatter 有意保持灵活。只保留有助于人维护文件的字段，例如 `owner`、`status`、
`last_verified`。

### Profiles

Profiles 通过 groups 选择 skills：

```json
{
  "include_groups": ["common", "mac"],
  "exclude_groups": ["work-private"],
  "memory_roots": ["memory/common"]
}
```

Profiles 也定义 agent targets：

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

`ak-core install --inject-routes` 会写入托管 marker block：

```text
<!-- agent-knowledge:router:start -->
...
<!-- agent-knowledge:router:end -->
```

如果只发现 start 或 end 其中一个 marker，命令会停止并要求人工修复。
