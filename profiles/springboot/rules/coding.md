# 编码规范（Coding）

> AI 生成代码必须遵守本规范。来源：Team Harness V1.0 PRD §6.1。

## 1. 分层职责（强制）

| 层 | 职责 | 禁止 |
|----|------|------|
| Controller | 接收参数、校验、调用 Service、组装返回 | ❌ 编写业务逻辑 |
| Service | 业务编排、事务控制 | ❌ 直接操作数据库细节、❌ 处理 HTTP 协议 |
| Mapper/Repository | 数据持久化 | ❌ 业务逻辑 |
| Entity | 数据库表映射 | ❌ 直接暴露到接口层 |
| DTO/VO | 接口入参 / 出参 | ❌ 与 Entity 混用 |

## 2. DTO 与 Entity 隔离（强制）

- 接口入参 / 出参必须使用 DTO/VO，禁止直接返回 Entity。
- Entity ↔ DTO 转换使用 MapStruct 或显式转换方法；禁止把可变 Entity 直接对外。

## 3. 禁止硬编码（强制）

- 字符串常量、魔法数字、URL、异常码必须定义为常量或枚举。
- 可变配置走 `application.yml` + `@Value` / `@ConfigurationProperties`。

## 4. 命名

- 类：`UpperCamelCase`；方法 / 变量：`lowerCamelCase`；常量：`UPPER_SNAKE_CASE`。
- 接口与实现：`XxxService` / `XxxServiceImpl`。
- 见名知意，禁止 `data1`、`tmp`、`a` 等无意义命名。

## 5. 最小改动（强制）

- 只修改完成当前任务所需的最小范围，不做顺手重构。
- 对现有行为不确定时先提问，不猜测、不臆造 API。

## 6. 其他

- 优先用 Stream / Optional 表达清晰意图；简单循环更易读时不必强转。
- 删除无用 import 与被注释掉的死代码。
