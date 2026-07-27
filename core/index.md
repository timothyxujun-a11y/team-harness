# Core 规则索引

> 适用于全部项目的强制基础规则。Core 不包含任何业务系统特定内容。

## 规则主题

| 规则 ID | 严重级别 | 标题 | 文件 |
|---------|---------|------|------|
| CORE-AI-001 | error | 不得编造不存在的接口、类或配置 | rules/ai-behavior.md |
| CORE-AI-002 | error | 修改代码前必须理解需求 | rules/ai-behavior.md |
| CORE-AI-003 | error | 只修改完成当前任务所需的范围 | rules/ai-behavior.md |
| CORE-AI-004 | error | 修改后应执行必要的编译和测试 | rules/ai-behavior.md |
| CORE-AI-005 | error | AI 生成内容必须接受人工评审 | rules/ai-behavior.md |
| CORE-SEC-001 | error | 不得写入生产密钥和敏感信息 | rules/security.md |
| CORE-SEC-002 | error | 不得执行高风险 Git 操作 | rules/security.md |
| CORE-GIT-001 | warning | 代码变更应具备可追踪性 | rules/git-workflow.md |
| CORE-GIT-002 | error | 高风险操作必须人工确认 | rules/git-workflow.md |
| CORE-QUAL-001 | error | 变更后必须通过质量检查 | rules/quality-gates.md |

## 加载说明

- Core 规则在所有任务中默认加载。
- `enforced: true` 的规则不可被项目例外降级。
- Core 不包含具体公司包名、业务域、MQ 中间件、Controller 结构、ORM 框架或测试版本。
