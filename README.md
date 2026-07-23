# Team AI Engineering Kit - Claude Code 工程化方案

一套可复用的 Claude Code AI 工程化"外壳"，通过 `sync.sh` 脚本一键同步到团队现有 Java/Spring Boot 项目，全员获得一致、安全、高效的 AI 协作体验。

## 前置条件

- Java 8+（或项目实际使用的版本）
- Maven 3.6+
- Claude Code 已安装并可用
- Git

## 目录结构

```
harness-project/
├── README.md                          # 本文件：方案总览 + 适配指南
├── CLAUDE.md                          # 【核心】约定总纲（AI 首先读取）
├── docs/
│   ├── conventions.md                 # 详细编码规范（CLAUDE.md 引用）
│   └── superpowers/specs/             # 设计文档
├── .claude/
│   ├── settings.json                  # 权限 allow/deny 配置
│   ├── agents/
│   │   ├── code-reviewer.md           # 子 agent：代码审查
│   │   └── test-writer.md             # 子 agent：编写单测
│   ├── commands/
│   │   ├── test.md                    # /test：按改动范围跑测试
│   │   ├── review.md                  # /review：评审当前改动
│   │   └── commit.md                  # /commit：生成 Conventional Commit
│   └── plans/                         # 需求文档（Plan 模式产物）
│       └── archive/                   # 已完成需求归档
├── scripts/
│   ├── sync.sh                        # 从 team-harness 仓库同步配置
│   └── install-git-hooks.sh           # 一键安装 git pre-commit hook
└── git-hooks/
    └── pre-commit                     # 提交前 Checkstyle 静态检查
```

## 如何适配到真实项目

### 方式一：脚本同步（推荐）

在目标 Java 项目根目录执行一行命令即可拉取最新配置：

```bash
# 首次使用：一键 bootstrap（下载并运行 sync.sh）
curl -fsSL https://raw.githubusercontent.com/timothyxujun-a11y/team-harness/main/scripts/sync.sh | bash
```

首次执行后，`sync.sh` 会复制到 `scripts/sync.sh`，后续直接运行：

```bash
# 检查有哪些更新（不实际修改）
./scripts/sync.sh --check

# 同步最新配置（交互式确认覆盖已修改的文件）
./scripts/sync.sh

# 同步并自动安装 git hooks
./scripts/sync.sh --hooks

# 强制覆盖所有文件（不推荐，会丢失已填写的 [CUSTOMIZE] 值）
./scripts/sync.sh --force
```

同步完成后：

```bash
# 1. 填写 [CUSTOMIZE] 占位
grep -rn '[CUSTOMIZE' .

# 2. 提交一次验证 pre-commit 生效
git add .
git commit -m "chore: 接入团队 AI 工程化规范"
```

> **sync.sh 智能保护**：如果本地文件已填写 `[CUSTOMIZE]`（不再包含占位符），同步时会询问确认后才覆盖，避免丢失项目定制内容。

### 方式二：按需挑选

如果项目已有 `.claude/` 目录或 `CLAUDE.md`，按需合并：

1. **合并 `CLAUDE.md`**：把约定章节并入现有文件
2. **合并 `.claude/settings.json`**：把 allow/deny 列表合并到现有配置
3. **新增 agents**：复制需要的 agent 文件到 `.claude/agents/`
4. **新增 commands**：复制需要的命令文件到 `.claude/commands/`

## [CUSTOMIZE] 占位清单

适配时需要填写的占位项：

| 文件 | 占位 | 说明 |
|------|------|------|
| `CLAUDE.md` | `[CUSTOMIZE: 项目名]` | 如 `order-service` |
| `CLAUDE.md` | `[CUSTOMIZE: 业务简介]` | 如 `订单交易核心服务` |
| `CLAUDE.md` | `[CUSTOMIZE: 业务术语表链接]` | 团队 wiki 链接 |
| `CLAUDE.md` | `[CUSTOMIZE: 接口设计规范链接]` | 团队 wiki 链接 |
| `CLAUDE.md` | `[CUSTOMIZE: 架构设计文档链接]` | 团队 wiki 链接 |
| `.claude/settings.json` | `[CUSTOMIZE: JDK 路径]` | 或留空使用系统默认 |

## 常用命令速查

### Claude Code 命令

| 命令 | 作用 |
|------|------|
| `/test` | 按改动范围运行相关测试 |
| `/test OrderServiceTest` | 运行指定测试类 |
| `/review` | 评审当前代码改动 |
| `/commit` | 生成 Conventional Commit 消息并提交 |

### 构建命令（Maven）

```bash
mvn clean compile -DskipTests    # 编译
mvn test                          # 全量测试
mvn test -Dtest=OrderServiceTest  # 指定测试类
mvn clean package -DskipTests     # 打包
```

### Git Hooks

```bash
./scripts/install-git-hooks.sh     # 安装 pre-commit hook
git commit --no-verify             # 跳过检查（不推荐）
rm -f .git/hooks/pre-commit        # 卸载 hook
```

## 工作流：规范驱动开发（SDD）

### 完整流程（半天以上工作量）

```
1. 生成需求文档
   → 在 Claude Code 中描述需求，生成 .claude/plans/feat-xxx/requirements.md

2. 人工审核
   → 逐项检查 requirements.md，确认 AI 理解正确

3. 生成任务清单并执行
   → 让 AI 生成 task.md，然后逐步实施
   → 每个任务完成后自动编译验证

4. 代码审查
   → 执行 /review，按报告修复问题

5. 提交
   → 执行 /commit，生成规范提交消息

6. 归档
   → mv .claude/plans/feat-xxx .claude/plans/archive/
```

### 快速流程（半天以内工作量）

```
1. 在 Claude Code 中直接描述需求
2. AI 遵守 CLAUDE.md 和 docs/conventions.md 编写代码
3. 修改后自动编译验证
4. 执行 /review 审查
5. 执行 /commit 提交
```

## 设计原则

1. **流水的工具，铁打的规范**：规范写在文件里，不依赖某个 AI 工具的特定功能
2. **AI 在约束下工作**：通过 rules、settings.json、git hooks 三层约束
3. **改动最小化**：sync.sh 一键同步，适配只需填占位
4. **不绑死技术栈**：Maven 适配，Java 版本从构建文件读取
5. **不含格式化**：本期不集成 Spotless/google-java-format，只做静态检查

## 版本

- v1.3.0 (2026-07-23)：前置条件改为 Java 8+；测试框架改为 JUnit 4；强制单测禁止启动 Spring 容器
- v1.2.0 (2026-07-23)：构建工具固定为 Maven，移除 Gradle 支持
- v1.1.0 (2026-07-23)：新增 `sync.sh` 脚本同步方式，支持 `--check`/`--force`/`--hooks`
- v1.0.0 (2026-07-23)：初始版本，11 个交付文件
