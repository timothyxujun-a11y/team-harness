# Claude Code 项目约定总纲

> **按需加载地图**：本文件仅放总纲（常驻上下文）。详细规范按需查阅，勿默认全量加载：
> - 分层 / 命名 / 异常 / 日志 / 测试细则 → `docs/conventions.md`
> - 历史设计文档（已完成） → `docs/superpowers/specs/archive/`

## 项目身份

- **项目名称**: [CUSTOMIZE: 填写项目名，如 order-service]
- **模块/职责**: [CUSTOMIZE: 填写业务简介，如 订单交易核心服务]
- **技术栈**: Java + Spring Boot（版本从构建文件读取，不硬编码）

## 构建工具

本项目使用 **Maven** 作为构建工具，使用 `./mvnw`（若存在）否则 `mvn`。Java 版本和 Spring Boot 版本从 `pom.xml` 中读取，不硬编码。

## 包结构约定

```
src/main/java/[BASE_PACKAGE]/
├── controller/     # REST API 层：参数校验、请求/响应封装
├── service/        # 业务逻辑层：核心逻辑、事务管理
├── repository/     # 数据访问层：MyBatis Mapper / JPA Repository
├── domain/         # 领域模型：实体、值对象、领域事件
├── dto/            # 数据传输对象：接收 XxxDTO / 返回 XxxVO
├── config/         # 配置类：Spring 配置、Bean 定义
├── handler/        # 全局处理器：异常处理、拦截器
└── util/           # 工具类：纯静态方法，无业务逻辑
```

### 分层依赖方向（硬性红线）

```
controller → service → domain
                  ↘ repository（持久化抽象）
```

- **禁止跨层反向依赖**：controller 不能被 service 引用，service 不能被 repository 引用
- **禁止跨层直连**：controller 不能直接调用 repository（必须经过 service）
- **domain 层不依赖任何上层**：实体类不引用 controller/service/repository

## 加一个功能的完整步骤

当需要新增一个功能（如"根据外部订单号查询订单详情"）时，按以下顺序操作：

1. **domain**：在 `domain/` 下新增或修改实体类、值对象
2. **repository**：在 `repository/` 下定义数据访问接口（Mapper 接口 / JPA 方法签名）
3. **service 测试（红）**：先为核心 service 方法写失败的单元测试（JUnit 4 + Mockito，mock repository），运行确认失败
4. **service 实现（绿→重构）**：实现业务方法（事务管理 + 异常处理）让测试通过，再重构
5. **controller**：在 `controller/` 下新增 REST 端点（仅参数校验 + 调 service），补 controller 单测（mock service）
6. **code-review**：开发完成、单测全绿后，调用 `code-reviewer` 子 agent（`/review`）审查，处理「必须修复」项

> 详细规范见 `docs/conventions.md`

## 验证命令清单

### 验证命令

```bash
# 编译（不跑测试）
mvn clean compile -DskipTests

# 运行所有测试
mvn test

# 运行特定测试类
mvn test -Dtest=OrderServiceTest

# 运行特定测试方法
mvn test -Dtest=OrderServiceTest#shouldReturnOrderWhenIdExists

# 打包（跳过测试）
mvn clean package -DskipTests
```

> **每次代码修改完成后，Claude Code 应自动执行编译验证，失败则停止并报告错误。**

## 测试约定

- **框架**：JUnit 4 + Mockito + AssertJ
- **结构**：AAA（Arrange-Act-Assert），每个测试方法三段式
- **命名**：`should期望行为When条件`，如 `shouldReturnOrderWhenIdExists`
- **最小化运行**：所有单测禁止启动 Spring 容器（不使用 `@SpringBootTest`、`@RunWith(SpringRunner.class)` 等注解），通过 Mock 隔离依赖
- **覆盖率目标**：核心 service 方法必须有单测
- **Mock 策略**：service 层测试 mock repository；controller 层测试 mock service
- **TDD（测试先行）**：Service/Domain 核心逻辑必须红→绿→重构；Controller 补单测但不强制 TDD；Repository 因禁启 Spring 容器不纳入

详细测试规范见 `docs/conventions.md` 第 5 节。

## 提交规范

使用 **Conventional Commits**：

```
<type>(<scope>): <description>
```

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
8. **核心逻辑走 TDD**：新增/修改 Service、Domain 核心逻辑时遵循红-绿-重构——先写失败的单元测试并确认失败，再写最小实现使其通过，最后重构
9. **开发后必过 code-review**：开发完成且单测通过后，必须调用 `code-reviewer` 子 agent（`/review`）审查改动，「必须修复」项处理完毕前不得报告任务完成

## codegraph 代码图谱（可选增强）

<!-- codegraph:start -->
本项目可选接入 [codegraph](https://github.com/colbymchenry/codegraph)：本地优先的代码知识图谱 MCP server，全支持 Java + Spring 路由（`@GetMapping` 等），把逐文件 grep/Read 探索压缩成一次调用。

- **主 agent 无需关注本段**：MCP server 连接时自动下发使用指引
- **子 agent（code-reviewer/test-writer）与非 MCP 场景**：当存在 `.codegraph/` 索引时，优先用 `codegraph_explore`（CLI 等价 `codegraph explore`）回答「X 是怎么工作的」、调用链（X 如何到达 Y）、改动影响面
- **一次调用即返回**相关符号源码 + 调用路径 + 影响半径，返回的源码视为已读，**不要再用 grep/Read 复核**
- **编辑后留意**响应中的 ⚠️ staleness banner，对 pending 文件直接 `Read` 取最新内容
- **无索引时**（未 `codegraph init`）回退内置 grep/Read；建索引是人工决定，不要自作主张初始化

接入步骤见 README「接入 codegraph」章节。
<!-- codegraph:end -->

## grill-me 需求拷问（可选）

<!-- grill-me:start -->
在 SDD 的需求阶段（生成需求文档前），可用 `/grill-me`（或直接说「grill 一下这个需求」）对计划/设计做一次一问的拷问式打磨：沿决策树逐分支理清，每个问题带推荐答案，事实自己查、决策才问你，达成共识后再进 Plan/实施。
<!-- grill-me:end -->

> 来源：[Matt Pocock · mattpocock/skills](https://github.com/mattpocock/skills)（MIT）

## 当前进行中的需求

请查看 `.claude/plans/` 目录下的活跃需求文档。已完成的需求归档至 `.claude/plans/archive/`。
