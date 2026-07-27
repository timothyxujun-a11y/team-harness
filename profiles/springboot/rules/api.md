# API 规范

> 来源：Team Harness V1.0 PRD §6.1。AI 生成接口必须满足。

## 1. REST 规范

- 资源用名词复数：`GET /orders`、`POST /orders`、`GET /orders/{id}`。
- HTTP 方法语义：GET 查询、POST 新增、PUT 全量更新、PATCH 部分更新、DELETE 删除。
- 统一版本前缀：`/api/v1/...`。
- 命名风格全项目统一（kebab-case 或 camelCase），禁止混用。

## 2. 参数校验（强制）

- 入参 DTO 使用 JSR-303 注解：`@NotNull` / `@NotBlank` / `@Size` / `@Pattern` / `@Min` / `@Max`。
- Controller 方法形参加 `@Valid`。
- 校验失败由全局异常处理器统一兜底（见 `exception.md`），不手写 if-else 逐个返回。

## 3. 统一返回结构（强制）

所有接口返回统一包装：

```json
{ "code": "0", "message": "success", "data": { } }
```

- `code`：业务码，成功为 `"0"`（或 `"200"`），其余为业务异常码。
- 禁止裸返回 Entity，也禁止无包装的散字段。

## 4. 异常码体系

- 成功码与业务异常码集中定义在枚举（如 `ResultCode`），禁止散落字符串字面量。
- 异常码分段：HTTP 层 / 业务层 / 第三方依赖层，分段清晰可辨。
