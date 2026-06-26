# 安全说明

English: [../security.md](../security.md)

`agent-knowledge-core` 的安全模型保持简单。它不实现权限、角色或策略服务。请使用
Git hosting 的访问控制和 pull request review。

## 默认规则

- core 项目保持公开和通用。
- 真实团队 memory 和团队自有 skills 默认放在私有仓，除非团队明确 review 后决定公开。
- 不提交 `local/` 或 `skills/vendor/` 这类生成目录。
- 不在 memory 文件或 skill 指令里保存 secrets。

## 轻量检查

合并前运行：

```bash
ak-core validate
ak-core privacy-scan --term your-company --term internal-domain
```

隐私扫描会捕捉常见本地路径、类似私有 IP 的值、类似 token 的赋值，以及团队提供的
denylist terms。它是兜底，不是保证。

## 团队仓边界

适合团队共享：

- review 过的 runbooks
- coding 和 review 约定
- 可复现的验证命令
- 带 owner 和最后验证日期的项目笔记
- 不包含凭据或个人本地假设的 skills

不要放入：

- secrets
- 客户数据
- 未脱敏日志
- 个人笔记
- 只适用于某个人机器的设置细节
- 原始生成态 agent memory

如果某个事实只对某个人或某台机器成立，放在个人仓；或者明确标注为容易过期的项目证据。
