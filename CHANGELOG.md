# 更新日志

本文件记录 Team Harness 版本变更，遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## v1.0.0（2026-07-27）

按《Team Harness AI 工程统一使用平台 V1.0 PRD》全新重构为轻量框架。

### 新增
- 纯 Bash CLI `./harness init`（零依赖，替代原 Python + venv 方案，接入不再需要 Python）
- `.ai/` 标准结构：`rules/` + `context/` + `prompts/` + `version.yaml`
- `profiles/springboot` 模板源：编码 / API / 数据库 / 异常 / 安全 / 测试 6 类规则 + 项目上下文骨架 + 5 个 Prompt 模板
- `templates/CLAUDE.md.tpl` 入口文件模板（Claude Code）
- 接入即生成 `CLAUDE.md`，Claude Code 自动加载规范

> 本期仅支持 Claude Code；Codex（`AGENTS.md`）等其他智能体接入后续提供。

### 移除（相对旧版 v2.x，回归 V1.0 精简范围）
- Python CLI（`scripts/harness_py/`）与 venv bootstrap
- Core / Profile / Overlay 三层规则体系、JSON Schema、按需加载选择器
- 版本锁 / 升级 / 回滚 / 迁移命令
- CI 强制门禁（9 Gate）、Git Hook（pre-commit / pre-push）
- 4 个示例项目、`sync.sh`、44 个 Python 测试

> 旧版实现可在 git 历史中检索（`v2.1.0` 及之前 commit）。
