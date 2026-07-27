<!-- 由 Team Harness v{{harness_version}} 生成；更新规则请编辑 .ai/ 后重新执行 ./harness init -->
<!-- 本文件为 Claude Code 入口，会被自动加载。请勿手改，重新 init 即可刷新。 -->

# {{project_name}}

{{project_description}}

> Profile：`{{profile}}` · Java {{java_version}} · 构建：Maven · Harness v{{harness_version}}

## AI 开发必读

本项目已接入 **Team Harness**。开发前**必须**：

1. **按需加载规则**：先读 `.ai/rules/INDEX.md`，按当前任务 / 改动文件**选择**要加载的规则，不要整体加载六份规则。
2. **理解上下文**：需求不清时先读 `.ai/context/`（项目背景 / 架构 / 模块）。
3. **复用标准流程**：复杂任务优先用 Skill —— `new-service`（新增微服务）、`new-api`（新增接口）；常规任务对照 `.ai/prompts/` 选 Prompt 模板（`feature` / `bugfix` / `review` / `unittest` / `document`）。

规则一览（路由详见 `INDEX.md`）：`coding` · `api` · `database` · `exception` · `security` · `test`。

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

## AI 操作日志（强制）

每次任务结束**必须**在 `.ai/log/changes.md` 顶部追加一条：日期 / 任务 / 关键决策 / 改动文件 / 是否跑测试 / 是否过 review。团队据此回溯与改进规范，不得省略。
