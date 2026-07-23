# Claude Code 项目约定总纲

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
├── dto/            # 数据传输对象：Request/Response VO
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
2. **repository**：在 `repository/` 下新增数据访问方法（Mapper 接口 + XML 或 JPA 方法）
3. **service**：在 `service/` 下新增业务方法，包含事务管理和异常处理
4. **controller**：在 `controller/` 下新增 REST 端点，仅做参数校验和调用 service
5. **单测**：为核心 service 方法编写单元测试（JUnit 4 + Mockito）

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

## 团队知识库参考

- [CUSTOMIZE: 业务术语表链接]
- [CUSTOMIZE: 接口设计规范链接]
- [CUSTOMIZE: 架构设计文档链接]

## 当前进行中的需求

请查看 `.claude/plans/` 目录下的活跃需求文档。已完成的需求归档至 `.claude/plans/archive/`。
