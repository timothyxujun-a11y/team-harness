# Changelog

本文件记录 Team Harness 的所有版本变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## 2.1.0 — 2026-07-27

本次版本修复 2.0.0 的端到端阻塞缺陷，并补全需求文档（HR-001~HR-007）声称但实际缺失的能力，使第一阶段真正可用。44 个自动化测试全绿（含端到端）。

### Added

- **hooks 模块**：`harness install-hooks` 安装/卸载 Git Hook，含版本戳校验与幂等（`--uninstall`）。
- **migrate 模块**：`harness migrate` 自动 v1→v2 迁移（识别 `[CUSTOMIZE]`、备份、生成 config/local、迁移报告），幂等。
- **upgrade 本地校验模式**：`harness upgrade --to <ver> --source <path>` 从本地 source 校验 commit + Profile checksum，临时渲染、原子替换、更新锁文件。
- **锁文件嵌套结构**：对齐 `harness-lock.schema.json`（`harness.{version,repository,ref,commit}` + `profiles.{name}.{version,checksum}` + `generated` + `previousVersion.lockContent`）。
- **Agent 动态规则选择（HR-006）**：`code-reviewer`/`test-writer` 不再内嵌规则正文，改为调用 `rules select` 按需加载，报告引用规则 ID。
- **Agent 分发**：render 将 harness 管理的 Agent 拷贝到业务项目 `.claude/agents/`。
- **rules select 上下文预算**：按 `codeReview`/`taskRules` 预算段截断（优先 error/Core/高优先级）。
- **local/index.yaml 统一为 sections 结构**（需求 §11.10）+ `protected-files.md`。
- **端到端测试套件**：`test_render/version/hooks/migrate/doctor/cli/e2e`，覆盖 19→44。

### Fixed

- 入口脚本 `PYTHONPATH` 在 `set -u` 下崩溃（干净环境所有命令不可用）。
- `resolve_profiles` 在 render/rules 三处调用签名错配。
- `get_build_commands` 参数语义与取 key 错误（`compile` vs `compileCommand`）。
- `find_project_root` 用 `.git` 导致 examples 子项目根错位；解耦 harness 安装源根与业务项目根。
- `doctor._doc007` 取错字段（应为 `content.path`）致规则文件缺失检测失效。
- `doctor._auto_fix` DOC-001 写 JSON 存为 `.yaml`。
- `doctor` 强制 `.git` 依赖；DOC-001/DOC-003 误报。
- `java-common/rules.yaml` 两处 `severity: warn`（违反 schema enum）。
- `JAVA-TEST-*` 规则未匹配 `test-generation` 任务与源文件路径。
- `version.do_upgrade` 假升级（不下载不校验）。
- CI GATE-009 敏感信息扫描只告警不阻断（违反 §13.6）。

### Changed

- `get_core_dir`/`get_profiles_dir`/`get_templates_dir` 解耦：局部优先、harness 源根回退。
- DOC-010 检测 Hook 是否为当前版本（非仅文件存在）。
- Agent 报告格式强制引用规则 ID。

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
