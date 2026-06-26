# 隐私说明

English: [../privacy.md](../privacy.md)

`agent-knowledge-core` 适合公开。包含真实 memory 和 owned skills 的知识仓通常应该是私有的。

发布知识仓前，请检查是否包含：

- 真实姓名、邮箱、用户名和 home 路径
- 公司名、内部 hostnames、私有 IP 和服务 URL
- 不应公开的模型名、artifact 路径、dataset 路径和 benchmark 结果
- API keys、tokens、passwords、cookies 和凭据
- 曾对 agent 有用、但不应公开的项目证据

发布前运行内置扫描：

```bash
ak-core privacy-scan --term your-company --term internal-hostname
```

扫描会标记常见本地 home 路径、私有 IP 范围和类似 token 的赋值。它不能替代人工 review。

## 推荐拆分

使用两个仓库：

```text
agent-knowledge-core/     公开框架和 CLI
agent-knowledge-private/  私有 skills、memory、profiles 和 lockfiles
```

私有仓可以依赖 `ak-core` CLI，同时让个人或公司特定内容留在公开项目之外。
