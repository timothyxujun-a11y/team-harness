# Team Harness — 轻量级 AI 工程接入框架 V1.0

为微服务项目提供标准化的 AI 使用能力：**项目规范 → Team Harness → AI 工具 → 标准化研发输出**。

> 纯 Bash，零依赖。一条命令 `./harness init` 完成 AI 规范接入，**不需要 Python / Node / 任何前置环境**。

## 它解决什么问题

| 痛点 | Harness 的解法 |
|------|----------------|
| AI 缺项目上下文 | `.ai/context/` 提供项目背景 / 架构 / 模块 |
| Prompt 质量依赖个人经验 | `.ai/prompts/` 提供新需求 / Bug / Review / 单测 / 文档模板 |
| 研发规范约束不了 AI | `.ai/rules/` 编码 / API / 数据库 / 异常 / 安全 / 测试规范 |
| 团队经验难复用 | 规范集中托管于本仓库，统一分发 |

## 支持的 AI 工具

- **Claude Code** → 生成 `CLAUDE.md`
- **Codex** → 生成 `AGENTS.md`

## 架构

```
本仓库（team-harness）= 规范源 + 接入工具
├── harness                 # 纯 Bash CLI（零依赖）
├── profiles/springboot/    # Spring Boot 规则模板源
│   ├── rules/              # coding / api / database / exception / security / test
│   ├── context/            # project / architecture / module（骨架）
│   └── prompts/            # feature / bugfix / review / unittest / document
└── templates/              # CLAUDE.md.tpl / AGENTS.md.tpl

业务项目接入后（harness init 生成）
├── .ai/
│   ├── version.yaml        # 版本 + profile 锁定
│   ├── rules/              # 团队规范
│   ├── context/            # 项目上下文（人工填写，不被覆盖）
│   └── prompts/            # Prompt 模板
├── CLAUDE.md               # Claude Code 入口
└── AGENTS.md               # Codex 入口
```

## 快速开始

```bash
# 1. 把本仓库 clone 到团队公共位置
git clone <repo-url> team-harness

# 2. 在业务项目根目录执行 init
cd my-service
../team-harness/harness init --name my-service --java-version 17
```

接入后：
1. 编辑 `.ai/context/project.md` 填写项目背景
2. 用 Claude Code / Codex 打开项目，AI 自动加载 `.ai` 规范

## harness init 流程（PRD §6.7）

```
检测项目类型 → 加载 Profile → 生成 .ai/ → 生成 CLAUDE.md → 生成 AGENTS.md → 完成
```

| 参数 | 作用 | 默认 |
|------|------|------|
| `--name` | 项目名 | 当前目录名 |
| `--profile` | Profile | `springboot`（MVP 唯一） |
| `--java-version` | Java 版本 | `17` |
| `--description` | 一句话描述 | 空 |

## 版本管理

`.ai/version.yaml` 锁定接入的 Harness 版本与 profile：

```yaml
version: 1.0.0
profile: springboot
```

升级 Harness 后重新执行 `./harness init`，自动刷新 `rules/`、`prompts/` 与版本号；`context/` 保留你的填写不被覆盖。

## 前置条件

- Bash（macOS / Linux 自带；Windows 用 Git Bash / WSL）
- Git、Claude Code 或 Codex
- 业务项目本身：Java 8+ / Maven 3.6+

> 不需要 Python，不需要 Node，不需要安装任何依赖。

## 设计原则

1. **轻量零依赖**：纯 Bash，一条命令接入。
2. **规范即文件**：规则是 Markdown，AI 直接读，无运行时。
3. **公共与本地隔离**：`rules/prompts` 跟随团队更新；`context` 是项目私有，不被覆盖。

## 版本

见 [CHANGELOG.md](CHANGELOG.md)，当前 **v1.0.0**。完整需求见 [PRD](Team_Harness_AI工程统一使用平台_V1.0_PRD.md)。
