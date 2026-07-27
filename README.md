# Team Harness — 仓库级 AI 工程化系统

将 Claude Code 的项目规则从「一份大 CLAUDE.md」升级为**分层、按需加载、可版本化、可验证**的 Harness：团队公共规则、技术类型规则、项目本地规则三层分离；规则按任务/文件/Diff 动态选择；每个业务项目锁定明确版本；本地 Git Hook 快速反馈 + CI 不可绕过的正式门禁。

> 适用于 Java + Spring Boot + Maven 微服务（HTTP / MQ / Job / Java8 存量）。

## 前置条件

- Python 3.7+（CLI 运行；首次自动 bootstrap venv 并安装 pyyaml）
- Java 8+/Maven 3.6+（业务项目编译测试；优先 Maven Wrapper）
- Git、Claude Code

## 架构概览

**Harness 主仓库**（本仓库）提供规则源与工具：

```
team-harness/
├── core/              # Core：适用全部项目的强制基础规则
├── profiles/          # Profile：java-common / spring-http / spring-mq / spring-job / legacy-java8
├── templates/         # CLAUDE.md / settings.json / CI workflow / profile-index 模板
├── schemas/           # config / lock / profile / rules JSON Schema
├── scripts/harness    # 统一 CLI 入口（Python）
├── git-hooks/         # pre-commit(编译) / pre-push(增量覆盖率)
└── examples/          # 4 个示例项目（http / mq / hybrid / legacy-java8）
```

**业务项目接入后**（由 `harness init` + `render` 生成）：

```
business-service/
├── CLAUDE.md               # 自动生成，最小常驻上下文（≤2000 Token）
├── CLAUDE.local.md         # 项目本地规则（不被覆盖）
├── .harness/
│   ├── config.yaml         # 项目配置（Profile/构建/预算）
│   ├── lock.yaml           # 版本锁（harness 版本 + Profile checksum）
│   ├── managed-files.json  # 受管文件清单 + SHA256
│   └── local/              # 项目本地规则（business/architecture/...）
├── docs/harness/           # 生成的规则索引（按需加载第二层）
└── .claude/{agents,settings.json}   # 分发的 Agent 与权限
```

## 快速开始

```bash
# 1. 在业务项目根目录初始化（生成 .harness/config.yaml）
./scripts/harness init --name my-service --java-version 17 --profiles java-common,spring-http

# 2. 编辑 .harness/config.yaml 填写项目描述，然后生成受管文件
./scripts/harness render

# 3. 自检
./scripts/harness doctor
```

## CLI 命令参考

```bash
./scripts/harness <command>
```

| 命令 | 作用 |
|------|------|
| `init` | 初始化项目，生成 `.harness/config.yaml` |
| `render` | 生成受管文件（CLAUDE.md / settings / workflow / agents / 索引） |
| `render --check` | 检查生成文件是否漂移（不修改，CI 用） |
| `render --diff` | 输出实际与预期差异 |
| `doctor` | 自检（12 类检查：环境/配置/版本/规则/上下文/CI/Hook/安全） |
| `doctor --json` | JSON 输出（CI 集成） |
| `doctor --fix` | 自动修复（生成缺失文件、装 Hook；不改业务代码） |
| `rules select --task <t> --files <f>` | 按任务/文件选择规则（输出 JSON，含选择原因与 Token 估算） |
| `rules check` | 规则一致性检查（重复 ID / 缺失文件 / Token 估算） |
| `version` | 版本与锁文件信息 |
| `upgrade --check` | 检查升级影响 |
| `upgrade --to <ver> --source <path>` | 本地校验升级到指定版本 |
| `rollback` | 回滚到上一个版本 |
| `install-hooks` | 安装 Git Hook（`--uninstall` 卸载） |
| `migrate` | v1 → v2 迁移（识别 `[CUSTOMIZE]`、备份、生成新结构） |

## 分层规则

- **Core**（`core/`）：适用全部项目的强制基础规则（AI 行为、安全、Git 工作流、质量门禁）。不可被 Profile/Overlay 降级。
- **Profile**（`profiles/`）：按技术类型。`java-common`（通用）、`spring-http`（Controller/DTO/OpenAPI）、`spring-mq`（Consumer/幂等/重试）、`spring-job`（分布式锁/批处理）、`legacy-java8`（语法限制/JUnit4）。
- **Project Overlay**（`.harness/local/`）：仅本项目。补充规则，不可覆盖 Core 强制规则。

合并顺序：`Core → Profile 依赖 → 显式 Profile → Project Overlay`。

## 按需加载（HR-003）

CLAUDE.md 只保留最小常驻上下文。详细规则三层加载：常驻 → 规则索引 → 详细规则。

```bash
# 修改 Controller 时，只选 HTTP 相关规则（不加载 MQ/Job）
./scripts/harness rules select --task code-review \
  --files src/main/java/com/x/controller/TaxController.java
```

输出含 `matchedProfiles`、`selectedRules`（每条带规则 ID、路径、原因、Token 估算）。超过 `codeReview` 预算（默认 ≤15 规则 / ≤8000 Token）按优先级截断。

## 版本管理（HR-004）

每个业务项目通过 `.harness/lock.yaml` 锁定 Harness 版本（语义化版本），**不得默认追踪 main**。

```bash
./scripts/harness version                    # 查看当前版本与锁
./scripts/harness upgrade --to 2.1.0 --source /path/to/team-harness   # 本地校验升级
./scripts/harness rollback                   # 回滚到上一版本
```

升级流程：解析本地 source → 校验 commit + Profile checksum → 临时渲染 → 原子替换 → 更新嵌套锁文件 → Doctor。

## CI 强制门禁（HR-005）

`.github/workflows/harness-check.yml`（由 render 生成）执行 9 个 Gate：

| Gate | 检查 |
|------|------|
| GATE-001 | Doctor 自检 |
| GATE-002 | 生成文件漂移 |
| GATE-003 | 规则一致性 |
| GATE-004 | 上下文预算 |
| GATE-005 | Maven 编译 |
| GATE-006 | 自动化测试 |
| GATE-007 | 增量覆盖率（diff-cover > 阈值） |
| GATE-008 | 未完成配置（`[CUSTOMIZE]`/TODO-HARNESS/示例包名） |
| GATE-009 | 敏感信息扫描（命中阻断合并） |

本地 Git Hook（pre-commit 编译、pre-push 增量覆盖率）可 `--no-verify` 跳过；CI 不可绕过。

## 迁移指南（v1 → v2）

v1 的 `[CUSTOMIZE]` 占位 + `sync.sh` 已废弃，改用 `config.yaml` + `harness` CLI。

```bash
# 在 v1 项目根目录
./scripts/harness migrate
```

迁移会：识别旧 `[CUSTOMIZE]` → 提取项目名/描述到 `config.yaml` → 推荐 Profile → 备份旧文件到 `.harness/backups/<时间戳>/` → 生成 Local 骨架与受管文件 → 自检。幂等（已是 v2 则提示）。

## 示例项目

`examples/` 下 4 个 harness 接入示例（HTTP / MQ / 混合 / Java8 存量），演示不同 Profile 组合、本地规则结构与规则命中：

```bash
cd examples/http-service
./scripts/harness render --check       # 无漂移
./scripts/harness doctor               # 自检
./scripts/harness rules select --task code-review --files src/main/java/x/controller/UserController.java
```

## 设计原则

1. **最小常驻上下文**：CLAUDE.md 只放总纲，完整规则按需加载。
2. **单一规则源**：规则只在 `rules.yaml` 定义一次，Agent/规范/CI 共享。
3. **公共与本地隔离**：Harness 管理的文件可重新生成；项目本地文件不被覆盖。
4. **本地反馈与正式门禁分离**：Git Hook 可跳过，CI 不可绕过。
5. **版本可控**：业务项目锁定明确版本，不默认追踪 main。

## 自动化测试

```bash
PYTHONPATH=scripts python -m unittest discover -s tests   # 44 个测试
```

## 版本

见 [CHANGELOG.md](CHANGELOG.md)。当前 **v2.1.0**。
