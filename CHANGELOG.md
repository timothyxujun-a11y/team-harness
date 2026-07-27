# Changelog

本文件记录 Team Harness 的所有版本变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## 2.0.0 — 2026-07-27

### Added

- **HR-001**：Core、Profile、Project Overlay 三层分层架构。
  - Core 强制基础规则（AI 行为、安全、Git 工作流、质量门禁）。
  - 5 个 Profile：`java-common`、`spring-http`、`spring-mq`、`spring-job`、`legacy-java8`。
  - Profile 依赖、冲突检测、合并顺序。
- **HR-002**：项目定制分离与生成机制。
  - `.harness/config.yaml` 项目配置。
  - 自动生成最小化 `CLAUDE.md`（≤200 行、≤8KB、≤2000 Token）。
  - 受管文件清单（`managed-files.json`）+ SHA256 校验。
  - `render`、`render --check`、`render --diff` 命令。
  - 原子更新（临时目录 → 校验 → 替换）。
- **HR-003**：规则按需加载与上下文预算。
  - 规则选择器（Profile / 文件路径 / 注解 / 任务类型 / Git Diff）。
  - 三层加载：常驻上下文 → 规则索引 → 详细规则。
  - 上下文预算（maxFiles / maxRules / maxTokens）+ 优先级截断。
  - `rules select` 命令输出 JSON 选择结果。
- **HR-004**：Harness 版本锁定与升级机制。
  - `.harness/lock.yaml` 锁文件（版本 + Commit + Profile 校验和）。
  - `version`、`upgrade --check`、`upgrade --to`、`rollback` 命令。
  - 语义化版本 + canary/stable 发布渠道。
  - 升级中断条件 + 原子升级流程。
- **HR-005**：CI 强制质量门禁。
  - GitHub Actions workflow 模板（9 个 Gate）。
  - Doctor、生成漂移、规则一致性、上下文预算、编译、测试、增量覆盖率、未完成配置、敏感信息扫描。
  - error/warning/info 门禁等级。
- **HR-006**：Agent、规范和 CI 规则一致性。
  - 统一 `rules.yaml` 单一规则源。
  - 规则编号体系（CORE-/JAVA-/HTTP-/MQ-/JOB-）。
  - Agent 改为动态规则选择，不内嵌完整规则。
  - 规则例外（ruleOverrides）+ 过期检测。
- **HR-007**：Harness Doctor 自检能力。
  - 12 类检查（DOC-001 ~ DOC-012）。
  - `doctor`、`doctor --verbose`、`doctor --json`、`doctor --ci`、`doctor --fix`。
  - JSON 输出可用于 CI 集成。
- 统一 CLI 工具 `./scripts/harness`（9 个子命令）。
- 旧版本迁移工具 `migrate`（v1 → v2 自动迁移 + 备份 + 报告）。
- 4 个示例项目：HTTP、MQ、混合、Java 8 存量。
- 4 个 JSON Schema：config、lock、profile、rules。
- 自动化测试套件。

### Changed

- `CLAUDE.md` 从手工编辑改为自动生成（最小常驻上下文）。
- 规则从分散在多个文件改为统一 `rules.yaml` 管理。
- Agent 从内嵌完整规则改为动态规则选择。
- Git Hook 定位为本地快速反馈，CI 为正式门禁。
- 项目接入从 `sync.sh` 拷贝改为 `harness init` 生成。

### Breaking Changes

- v1 的 `[CUSTOMIZE]` 占位符机制废弃，改用 `.harness/config.yaml` + `CLAUDE.local.md`。
- v1 的 `sync.sh` 被 `harness` CLI 替代。
- v1 的 `docs/conventions.md` 拆分为 Core + Profile 规则文件。

### Migration

- 运行 `./scripts/harness migrate` 从 v1 自动迁移到 v2。
- 迁移前自动备份到 `.harness/backups/`。
- 旧文件中的 `[CUSTOMIZE]` 值提取到 `.harness/config.yaml`。
- 项目特殊规则迁移到 `.harness/local/` 目录。

---

## 1.x — 2026-07-23

### Added

- 初始版本：CLAUDE.md + docs/conventions.md + .claude/ 配置 + sync.sh。
- Maven 固定构建工具。
- JUnit 4 + Mockito + AssertJ 测试框架。
- Git pre-commit hook（Checkstyle 静态检查）。
