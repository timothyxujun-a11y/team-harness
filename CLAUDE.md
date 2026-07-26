# Claude Code 项目约定总纲

> **按需加载地图**：本文件仅放总纲（常驻上下文）。所有编码细则按需查阅 `docs/conventions.md`：
> 分层职责 / 命名 / 异常 / 日志 / 测试 / 配置管理 / 开发工作流（TDD）
> - 历史设计文档（已完成） → `docs/superpowers/specs/archive/`

## 项目身份

- **项目名称**: [CUSTOMIZE: 填写项目名，如 order-service]
- **模块/职责**: [CUSTOMIZE: 填写业务简介，如 订单交易核心服务]
- **技术栈**: Java + Spring Boot（版本从构建文件读取，不硬编码）

## 构建工具

本项目使用 **Maven**，优先 `./mvnw`（若存在）否则 `mvn`。Java 与 Spring Boot 版本从 `pom.xml` 读取，不硬编码。

## 验证命令清单

```bash
mvn clean compile -DskipTests                                  # 编译（不跑测试）
mvn test                                                        # 全量测试
mvn test -Dtest=OrderServiceTest                                # 指定测试类
mvn test -Dtest=OrderServiceTest#shouldReturnOrderWhenIdExists  # 指定方法
mvn clean package -DskipTests                                   # 打包（跳过测试）
```

> **每次代码修改完成后，Claude Code 应自动执行编译验证，失败则停止并报告错误。**

## 提交规范

使用 **Conventional Commits**：`<type>(<scope>): <description>`

- **type**: `feat` / `fix` / `docs` / `refactor` / `test` / `chore`
- **scope**: 模块名（如 `order`、`user`、`config`）
- **description**: 中文简短描述

示例：

```
feat(order): 新增根据外部订单号查询订单详情接口
fix(payment): 修复支付回调超时未更新订单状态的问题
test(user): 补充 UserService 核心方法单元测试
```

## AI 行为规范

1. **改完先跑测试再报告**：每次代码修改后，先执行编译和受影响的测试，通过后再向用户报告完成
2. **遵循现有代码模式**：新增代码必须与同包/同类中已有代码的风格保持一致
3. **改动最小化**：只改必要的行，不做顺手重构；如需重构，单独提出并经用户确认
4. **不编造 API**：不使用项目中不存在的类/方法/依赖；如需引入新依赖，先告知用户并获得确认
5. **遇不确定先问**：对需求理解有歧义、对现有代码行为不确定时，先提问而非猜测
6. **中文回复**：所有回复、注释、commit message 描述使用中文
7. **安全红线**：禁止硬编码密钥/密码/Token；涉及 DDL 变更必须先输出 SQL 供人工审核
8. **核心逻辑走 TDD**：新增/修改 Service、Domain 核心逻辑时遵循红-绿-重构（细则见 `docs/conventions.md` 开发工作流）
9. **开发后必过 code-review**：开发完成且单测通过后，必须调用 `code-reviewer` 子 agent（`/review`）审查改动，「必须修复」项处理完毕前不得报告任务完成

## grill-me 需求拷问（可选）

<!-- grill-me:start -->
在 SDD 的需求阶段（生成需求文档前），可用 `/grill-me`（或直接说「grill 一下这个需求」）对计划/设计做一次一问的拷问式打磨：沿决策树逐分支理清，每个问题带推荐答案，事实自己查、决策才问你，达成共识后再进 Plan/实施。
<!-- grill-me:end -->

> 来源：[Matt Pocock · mattpocock/skills](https://github.com/mattpocock/skills)（MIT）

## 当前进行中的需求

请查看 `.claude/plans/` 目录下的活跃需求文档。已完成的需求归档至 `.claude/plans/archive/`。
