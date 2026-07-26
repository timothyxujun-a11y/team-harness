# 团队级 Java/Spring Boot · Claude Code AI 工程化方案（可复用文件包）

- 状态：已实现（实现见 README，当前 v1.4）
- 日期：2026-07-23（初稿）
- 交付形态：可复用文件包（拷入现有项目根目录后按需适配）
- 技术栈：Java 8+ / Spring Boot / Maven
- AI 工具：Claude Code
- 方案深度：标准层

> ⚠️ 本文为设计初稿（v1.0），保留用于追溯设计意图。最终实现已演进，**以 README.md 为准**。与初稿的主要差异：
> - 测试框架：JUnit 5 → **JUnit 4**（见 CLAUDE.md / docs/conventions.md 第 5 节）
> - 构建工具：Maven/Gradle 双支持 → **仅 Maven**
> - 新增 `config/checkstyle.xml` 规则模板，让 pre-commit 的静态检查名副其实（仍不含格式化）

---

## 1. 背景与目标

把一套 Claude Code AI 工程化"外壳"做成**可复用文件包**，拷进团队现有 Java/Spring Boot 项目后，全员获得一致、安全、高效的 AI 协作体验。

### 目标
- **统一约定**：AI 明确知道代码放哪、怎么命名、怎么测、怎么提交
- **流程闭环**：理解 → 实现 → 测试 → 评审 → 提交，用 commands / agents 固化成可调用动作
- **安全收口**：`.claude/settings.json` 用权限 allow/deny 避免破坏性操作
- **可复用**：参数化 + Java/Spring Boot 版本从构建文件读取，不绑定单一项目

### 非目标（本期明确不含）
- ❌ **不做任何格式化**：不集成 Spotless / google-java-format、不做编辑后自动格式化、不做提交前格式化检查
- ❌ 不含项目级 skills、MCP 配置、onboarding 文档、独立工作流规范文档（属"完整层"）
- ❌ 不是代码脚手架，不含业务代码 / DB / 安全组件 / Application 主类

---

## 2. 交付物形态

一个自包含目录。两种落地方式：
1. 整体拷入真实项目根目录（与已有 `.claude/`、`CLAUDE.md` 合并）
2. 按需挑选文件合并

拷入后：填写 `[CUSTOMIZE]` 占位 → 运行 `scripts/install-git-hooks.sh` → 即生效。`README.md` 给出逐步适配说明。

---

## 3. 目录结构

```
harness-project/
├── README.md                  # 方案总览 + 如何拷贝/适配进真实项目
├── CLAUDE.md                  # 【核心】约定总纲（参数化，默认 Java/Spring Boot）
├── docs/
│   └── conventions.md         # 详细编码规范（分层/命名/异常/日志/测试），CLAUDE.md 引用
├── .claude/
│   ├── settings.json          # 权限 allow/deny + 环境变量（不含 hooks）
│   ├── agents/
│   │   ├── code-reviewer.md   # 子 agent：对照约定评审 diff
│   │   └── test-writer.md     # 子 agent：JUnit 4 + Mockito 写单测
│   └── commands/
│       ├── test.md            # /test：按改动范围跑测试
│       ├── review.md          # /review：评审当前改动
│       └── commit.md          # /commit：生成 Conventional Commit
├── scripts/
│   └── install-git-hooks.sh   # 一键安装 git pre-commit hook
└── git-hooks/
    └── pre-commit             # 提交前 Checkstyle 静态检查（Maven）
```

共 11 个交付文件。

---

## 4. 组件详述

### 4.1 CLAUDE.md（约定总纲，最关键）
参数化、带 Java/Spring Boot 默认值，包含：
- **项目身份与技术栈声明**：含 `[CUSTOMIZE]` 占位（项目名、模块、业务简介）
- **构建工具**：Maven（`./mvnw` 优先）；Java/Spring Boot 版本从 `pom.xml` 读取，不硬编码
- **包结构约定 + 分层依赖方向**：`web → service → domain`，`repository` 为持久化抽象；禁止跨层反向依赖
- **加一个功能的完整步骤**：domain → repository → service → controller → 单测
- **验证命令清单**：编译 / 测试 /（检测到的构建工具对应命令）
- **测试约定**：JUnit 4 + Mockito + AssertJ；AAA 结构；命名 `shouldXxxWhenYyy`；纯单元测试优先
- **提交规范**：Conventional Commits（`feat:`/`fix:`/...）；中文回复偏好
- **AI 行为规范**：改完先跑测试再报告；遵循现有代码模式；改动最小化；不编造 API；遇不确定先问

### 4.2 .claude/settings.json
- `permissions.allow`：构建/测试命令（`mvn`、`./mvnw`、`gradle`、`./gradlew`）、git 只读（`git status`、`git diff`、`git log`）、`grep`/`find`/`ls`/`cat`
- `permissions.deny`：`rm -rf`、`git push --force`、`git push -f`、删库删表语句（`DROP`/`DELETE FROM`）、覆盖性写入仓库关键文件
- `env`：必要环境变量占位（按需）
- **不含任何 hooks**（格式化 hook 已按要求移除）

### 4.3 agents/
- **code-reviewer**：对照 `docs/conventions.md` 与现有代码模式评审 `git diff`，输出结构化问题（correctness / style / test-coverage），中文，给出可执行修改建议
- **test-writer**：为指定类/方法生成 JUnit 4 + Mockito + AssertJ 单测，符合命名与 AAA 约定，优先纯单元测试

### 4.4 commands/
- **/test**：分析当前改动涉及的类 → 跑相关测试；无参数时跑全量
- **/review**：调用 `code-reviewer` agent 评审当前 `git diff`
- **/commit**：读取暂存区改动 → 生成 Conventional Commit 消息 → 经用户确认后提交

### 4.5 git pre-commit hook + 安装脚本
- **pre-commit**：提交前跑 Checkstyle 静态规则检查（Maven：`checkstyle:check`，规则集为 `config/checkstyle.xml`）；项目未配置 checkstyle 插件时**优雅降级为编译检查**（`mvn compile`）；不合规拒绝提交。**只检查不改代码**（非格式化）
- **install-git-hooks.sh**：把 `git-hooks/pre-commit` 安装到项目 `.git/hooks/` 并赋可执行权限

### 4.6 docs/conventions.md
CLAUDE.md 引用的详细规范，避免主文件过长：分层职责、命名、异常处理、日志、测试细则。

### 4.7 README.md
方案总览 + 前置条件 + 拷贝/适配步骤 + 占位清单 + 常用命令速查。

---

## 5. 默认与约定

| 项 | 处理 |
|---|---|
| 构建工具 | Maven（v1.2 起移除 Gradle 支持） |
| Java / Spring Boot 版本 | 不硬编码，从项目构建文件读取 |
| 输出语言 | 中文（遵循全局偏好） |
| 格式化 | **完全不含** |
| 提交前检查 | Checkstyle 静态规则（可降级为编译检查） |

---

## 6. 适配指南（拷入真实项目后）

1. 合并 `CLAUDE.md`（若已有，则把约定章节并入）
2. 合并 `.claude/`（settings.json 的 allow/deny 与现有合并；agents/commands 新增）
3. 填写 CLAUDE.md 中所有 `[CUSTOMIZE]` 占位
4. 运行 `scripts/install-git-hooks.sh`
5. 提交一次验证 pre-commit 生效

---

## 7. 验收标准

- [ ] 11 个文件齐备，内容自洽、无相互矛盾
- [ ] CLAUDE.md 可被 AI 直接遵循，占位清晰
- [ ] `settings.json` JSON 合法，权限 allow/deny 合理
- [ ] `agents/*.md` 与 `commands/*.md` frontmatter 合法、可被 Claude Code 识别
- [ ] `pre-commit` 与 `install-git-hooks.sh` 对 Maven 适配、可执行
- [ ] 全文**无任何格式化**相关内容（Spotless/google-java-format/编辑后格式化 hook）
- [ ] 所有面向用户的说明为中文

---

## 8. 后续可选扩展（不在本期）

- 完整层：项目级 skills、MCP 配置、onboarding 文档、独立工作流规范、权限安全策略文档
- 若团队需要格式化：可后续追加 Spotless（本期按需求不做）
