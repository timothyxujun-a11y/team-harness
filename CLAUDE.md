<!-- 由 Team Harness v1.0.0 生成；更新规则请编辑 .ai/ 后重新执行 ./harness init -->
<!-- 本文件为 Claude Code 入口，会被自动加载。请勿手改，重新 init 即可刷新。 -->

# team-harness

Team Harness 规范源与接入工具仓库（轻量 AI 工程框架）

> Profile：`springboot` · Java 17 · 构建：Maven · Harness v1.0.0

## AI 开发必读

本项目已接入 **Team Harness**。开发前**必须**先加载 `.ai/` 下的规范：

| 类别 | 路径 | 要点 |
|------|------|------|
| 编码规范 | `.ai/rules/coding.md` | 分层职责、DTO 隔离、禁止硬编码、最小改动 |
| API 规范 | `.ai/rules/api.md` | REST、参数校验、统一返回、异常码 |
| 数据库规范 | `.ai/rules/database.md` | 索引、禁止 `SELECT *`、深分页、DDL 审核 |
| 异常处理 | `.ai/rules/exception.md` | 全局异常处理器、业务异常、事务回滚 |
| 安全规范 | `.ai/rules/security.md` | 禁止硬编码密钥、参数校验、脱敏、SQL 注入 |
| 测试规范 | `.ai/rules/test.md` | JUnit 5 + Mockito、不启动容器、三覆盖维度 |
| 项目上下文 | `.ai/context/` | 项目背景、架构、模块（理解需求时先读） |

执行任务时，对照 `.ai/prompts/` 选对应 Prompt 模板：`feature`（新需求）/ `bugfix`（修 Bug）/ `review`（代码审查）/ `unittest`（单测）/ `document`（文档）。

## 目录约定

```
controller/（接口层·薄） → service/（业务层） → mapper/（持久层）
entity/（表映射）  ⇄  dto/（接口出入参）   严格隔离
```

详见 `.ai/context/architecture.md`。

## 常用命令

```bash
mvn clean compile -DskipTests            # 编译（不跑测试）
mvn test                                  # 全量测试
mvn test -Dtest=XxxServiceTest            # 指定测试类
mvn test -Dtest=XxxServiceTest#shouldXxx  # 指定方法
```

> 改完代码先编译 + 跑受影响测试，通过后再报告。

## 禁止事项

1. ❌ 禁止编造不存在的接口、类、方法、配置
2. ❌ Controller 禁止编写业务逻辑
3. ❌ 禁止直接返回 Entity 到接口层
4. ❌ 禁止硬编码密码 / Token / 密钥 / 异常字符串
5. ❌ 禁止 `SELECT *`、深分页 `LIMIT offset, n`
6. ❌ 单元测试禁止启动 Spring 容器
7. ❌ DDL 变更必须先输出 SQL 供人工审核

## 提交规范

Conventional Commits：`<type>(<scope>): <中文描述>`，type ∈ `feat / fix / docs / refactor / test / chore`。
