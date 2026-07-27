# http-service-example 本地规则

> 本文件为项目级 AI 协作规则，与 `.harness/local/` 下的业务说明和架构文档配合使用。
> AI 助手在本项目中工作时应优先遵循本文件。

## 项目身份

- **项目名称**: http-service-example
- **模块/职责**: 用户管理与订单查询 HTTP API 服务
- **技术栈**: Java 17 + Spring Boot 3.x + Maven
- **基础包名**: `com.example.http`

## 业务领域

### 用户服务（UserService）

- 提供用户注册、查询、更新、停用等 CRUD 接口
- 用户状态枚举：`ACTIVE`（活跃）、`INACTIVE`（停用）、`DELETED`（已删除）
- 注册时需校验用户名唯一性和手机号格式
- 用户停用后不可登录，但保留历史数据

### 订单服务（OrderService）

- 提供订单列表查询、订单详情查询接口
- 订单状态枚举：`PENDING`（待支付）、`PAID`（已支付）、`SHIPPED`（已发货）、`COMPLETED`（已完成）、`CANCELLED`（已取消）
- 订单列表支持分页查询，默认每页 20 条
- 订单详情包含订单基本信息、商品明细、物流信息

### API 版本化策略

- URL 路径版本化：`/api/v1/users`、`/api/v2/users`
- 当前默认版本为 v1，新版本通过新增 Controller 实现，旧版本保持向后兼容
- 版本废弃时在响应头添加 `Deprecation: true` 和 `Sunset` 头
- 同一接口最多保留 2 个版本，旧版本在下线前至少保留 3 个月过渡期

## 分层架构

```
controller（HTTP 入口） → service（业务逻辑） → mapper（数据访问）
                                                ↘ entity（数据模型）
```

### Controller 层

- 统一响应体格式：`{ "code": 0, "message": "success", "data": ... }`
- 参数校验使用 `@Valid` + Bean Validation 注解
- Controller 仅做参数接收、校验、调用 Service、组装响应，**禁止编写业务逻辑**
- RESTful 风格：资源名用复数（`/users`、`/orders`），动作用 HTTP 方法表达

### Service 层

- 接口命名 `I*Service`，实现 `*ServiceImpl`
- 多表写入必加 `@Transactional`；纯查询标 `@Transactional(readOnly = true)`
- Service 间调用避免循环依赖，必要时通过事件机制解耦

### DTO 命名约定

- 入参：`*DTO`（如 `UserCreateDTO`、`OrderQueryDTO`）
- 出参：`*VO`（如 `UserVO`、`OrderDetailVO`）
- Entity 与 DTO 转换优先使用 MapStruct

## 构建与验证

```bash
./mvnw clean compile -DskipTests    # 编译
./mvnw test                          # 全量测试
./mvnw test -Dtest=UserServiceTest   # 指定测试类
./mvnw clean package -DskipTests     # 打包
```

> 每次代码修改完成后，必须执行编译验证，失败则停止并报告。

## AI 行为补充

1. 新增接口时先确认 API 版本，优先复用已有版本
2. 修改 Entity 时需同步检查 DTO 和 VO 是否受影响
3. 订单查询涉及多表 JOIN，优先在 Mapper XML 中编写 SQL，禁止在 Service 中拼接 SQL
4. 用户敏感信息（手机号、身份证号）在 VO 中必须脱敏输出
