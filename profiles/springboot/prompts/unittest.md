# Prompt 模板 — 单元测试生成

## 目标

[CUSTOMIZE: 指定类或方法，如「为 OrderServiceImpl#create 生成单测」]

## 要求

- 框架：JUnit 5 + Mockito，不启动 Spring 容器。
- 覆盖维度：正常流程 / 异常分支 / 边界值（见 `rules/test.md`）。
- 依赖用 `@Mock`，被测对象用 `@InjectMocks`（或显式构造）。
- 方法名：`shouldXxxWhenYyy`；用 `@DisplayName` 中文描述用例意图。

## 完成后

- 运行 `mvn test -Dtest=<目标测试类>` 确认通过。
- 不为 getter / setter / 纯数据 DTO 生成无意义测试。
