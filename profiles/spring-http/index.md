# Spring Boot HTTP API 服务规范

本 Profile 定义了 Spring Boot HTTP API 服务的编码规范与架构约束，适用于所有提供 RESTful API 的 Spring Boot 微服务。

## 快速索引

| 规则分组 | 规则 ID | 严重级别 | 说明 |
|----------|---------|----------|------|
| Controller 架构 | HTTP-ARCH-001 | error | Controller 职责边界——只负责参数接收、校验、调用 Service、返回结果 |
| Controller 架构 | HTTP-ARCH-002 | error | 禁止 Controller 直接访问数据库 |
| Controller 架构 | HTTP-ARCH-003 | error | `@RestController` + `@RequestMapping` 注解规范 |
| 参数校验 | HTTP-VAL-001 | error | JSR-303 参数校验注解 |
| 参数校验 | HTTP-VAL-002 | warning | 自定义校验注解封装 |
| 响应格式 | HTTP-RESP-001 | error | 统一响应体结构 |
| 响应格式 | HTTP-RESP-002 | error | 错误码体系与分页响应格式 |
| API 兼容性 | HTTP-COMPAT-001 | error | 禁止删除已有 API 端点和修改字段含义 |
| API 兼容性 | HTTP-COMPAT-002 | warning | 新增字段兼容与版本化管理 |
| OpenAPI 文档 | HTTP-DOC-001 | warning | 接口文档注解规范 |

## 规则详情

### Controller 架构 → [controller.md](rules/controller.md)

- Controller 只负责参数接收、校验、调用 Service、返回结果
- Controller 不得承载核心业务逻辑
- Controller 不得直接访问数据库（DAO/Repository）
- 统一使用 `@RestController` + `@RequestMapping` 注解

### 参数校验 → [validation.md](rules/validation.md)

- 使用 JSR-303 注解进行入参校验（`@Valid`、`@NotNull`、`@Size` 等）
- 特殊校验逻辑封装为自定义校验注解
- 校验失败统一返回参数错误码

### 响应格式 → [response.md](rules/response.md)

- 所有接口统一使用 `Result<T>` 包装响应
- 建立错误码枚举体系，区分系统异常与业务异常
- 分页接口返回标准分页结构

### API 兼容性 → [compatibility.md](rules/compatibility.md)

- 已发布的 API 端点不得删除，只能标记废弃
- 已有响应字段不得修改名称或含义
- 新增字段必须提供默认值
- 大版本变更使用 API 版本化管理

### OpenAPI 文档 → [openapi.md](rules/openapi.md)

- 必须使用 Swagger/Knife4j 注解
- Controller、接口方法、DTO 均需添加文档注解
- 确保 `/doc.html` 可正常访问和调试

## 适用场景

| 任务类型 | 是否生效 |
|----------|----------|
| 功能开发 (`feature-development`) | 是 |
| 重构 (`refactor`) | 是 |
| 代码审查 (`code-review`) | 是 |

## 依赖关系

本 Profile 依赖 `java-common` Profile，使用时需确保该 Profile 已加载。

## 兼容性

- 语言：Java
- Java 版本：8 / 11 / 17 / 21
- 构建工具：Maven
- 框架：Spring Boot 2.x / 3.x
- 冲突：无
