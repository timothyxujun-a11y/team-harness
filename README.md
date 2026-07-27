# Team Harness — 轻量级 AI 工程接入框架 V1

为微服务项目提供标准化的 AI 使用能力：**项目规范 → Team Harness → AI 工具 → 标准化研发输出**。

> 纯 Bash，零依赖。一条命令 `./harness init` 完成 AI 规范接入，**不需要 Python / Node / 任何前置环境**。

## 它解决什么问题

| 痛点 | Harness 的解法 |
|------|----------------|
| AI 缺项目上下文 | `.ai/context/` 项目背景 / 架构 / 模块 |
| 规范整体加载、相关性差 | `.ai/rules/INDEX.md` 路由表，AI 按任务 / 文件**按需选读** |
| Prompt 质量依赖个人经验 | `.ai/prompts/` 新需求 / Bug / Review / 单测 / 文档模板 |
| 复杂任务无标准流程 | `.claude/skills/` 多步骤 Skill：`new-service`、`new-api` |
| AI 决策无记录、难回溯 | `.ai/log/changes.md` 操作日志（日志即 Markdown） |
| 研发规范约束不了 AI | `.ai/rules/` 编码 / API / 数据库 / 异常 / 安全 / 测试 |
| 团队经验难复用 | 规范集中托管本仓库，统一分发 |

## 支持的 AI 工具

- **Claude Code** → 生成 `CLAUDE.md`

> 其他智能体（Codex 等）接入后续支持，本期仅提供 Claude Code。

## 架构

```
本仓库（team-harness）= 规范源 + 接入工具
├── harness                       # 纯 Bash CLI（零依赖）
├── profiles/springboot/          # Spring Boot 规则模板源
│   ├── rules/  + INDEX.md        # 6 类规则 + 路由表（按任务选读）
│   ├── context/                  # project / architecture / module（骨架）
│   ├── prompts/                  # feature / bugfix / review / unittest / document
│   ├── skills/                   # new-service / new-api（多步骤流程）
│   └── log/changes.md            # AI 操作日志模板
├── templates/CLAUDE.md.tpl       # Claude Code 入口模板
└── git-hooks/pre-commit          # 可选极简 pre-commit

业务项目接入后（harness init 生成）
├── .ai/
│   ├── version.yaml              # 版本 + profile 锁定
│   ├── rules/  (含 INDEX.md)     # 团队规范 + 按需路由
│   ├── context/                  # 项目上下文（人工填写，不被覆盖）
│   ├── prompts/                  # Prompt 模板
│   └── log/changes.md            # AI 操作日志
├── CLAUDE.md                     # Claude Code 入口
└── .claude/skills/               # new-service / new-api
```

## 快速开始

```bash
# 1. 把本仓库 clone 到团队公共位置
git clone <repo-url> team-harness

# 2. 在业务项目根目录执行 init
cd my-service
../team-harness/harness init --name my-service --java-version 17

# 3. 本地自检
../team-harness/harness check
```

接入后：
1. 编辑 `.ai/context/project.md` 填写项目背景
2. 用 Claude Code 打开项目，AI 按 `INDEX.md` 按需加载规范

## 命令一览

| 命令 | 作用 |
|------|------|
| `init` | 接入：生成 `.ai/`、`CLAUDE.md`、分发 Skill |
| `check` | 本地自检：`.ai` 完整性 + `[CUSTOMIZE]` 占位残留 |
| `rules` | 打印规则路由表 `INDEX.md`（按任务选读规则） |
| `log [--init]` | 查看 / 初始化 AI 操作日志 |
| `hooks --install` | 安装可选极简 pre-commit（`--uninstall` 卸载） |
| `version` | 版本信息 |

## 按需加载规则（INDEX）

规则不再整体加载。`.ai/rules/INDEX.md` 是一张路由表：改 Controller 读 `coding+api+exception`，写 SQL 读 `coding+database+security`……AI 先读极小的 INDEX，只加载相关规则。`harness rules` 随时查看。

## 标准流程 Skill

把"复杂任务"固化成带 Checklist 的多步骤流程，随 `init` 分发到 `.claude/skills/`，Claude Code 自动识别：

- **`new-service`**：新增微服务（脚手架 → 分层 → 异常基线 → 切片 → 测试 → 自检 → 日志）
- **`new-api`**：新增 REST 接口（契约 → 分层 → 异常 → 单测 → 自检 → 日志）

## 质量回路（轻量）

V1 聚焦研发阶段，**不内置 CI 强制门禁**（编译 / 测试 / 覆盖率 / 漂移 / 敏感信息扫描等留给各项目 CI 自行接 `harness check`）。本地提供：

- `harness check`：零依赖自检（结构完整 + 占位残留）
- `harness hooks --install`：可选极简 pre-commit，仅拦"还有 `[CUSTOMIZE]` 未填就提交"，默认不装，`--no-verify` 可跳过

## AI 操作日志

`.ai/log/changes.md` 是一张 Markdown 表，AI 每次任务结束追加一条（任务 / 关键决策 / 改动文件 / 测试 / review）。团队据此回溯与改进规范。`harness log` 查看，`harness log --init` 初始化。

## 版本管理

`.ai/version.yaml` 锁定接入版本与 profile：

```yaml
version: 1.1.0
profile: springboot
```

升级 Harness 后重新 `./harness init`，自动刷新 `rules/`、`prompts/`、`skills/` 与版本号；`context/` 与 `log/changes.md` 保留你的填写不被覆盖。

## 前置条件

- Bash（macOS / Linux 自带；Windows 用 Git Bash / WSL）
- Git、Claude Code
- 业务项目本身：Java 8+ / Maven 3.6+

> 不需要 Python，不需要 Node，不需要安装任何依赖。

## 设计原则

1. **轻量零依赖**：纯 Bash + Markdown，一条命令接入。
2. **规范即文件**：规则、路由、流程、日志都是 Markdown，AI 直接读，无运行时。
3. **公共与本地隔离**：`rules/prompts/skills` 跟随团队更新；`context`、`log` 是项目私有，不被覆盖。

## 版本

见 [CHANGELOG.md](CHANGELOG.md)，当前 **v1.1.0**。完整需求见 [PRD](Team_Harness_AI工程统一使用平台_V1.0_PRD.md)。
