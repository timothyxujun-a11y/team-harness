# 测试规范

> 来源：Team Harness V1.0 PRD §6.6。测试框架：JUnit 5 + Mockito。

## 1. 覆盖维度（强制）

每个被测方法至少覆盖：
- **正常流程**：主路径返回正确结果。
- **异常分支**：业务异常 / 依赖抛错被正确处理。
- **边界值**：`null`、`0`、临界值、空集合 / 单元素集合。

## 2. 单元测试原则

- 单元测试**不得启动 Spring 容器**（禁止 `@SpringBootTest`），依赖一律用 Mockito mock。
- 一个测试方法只验证一个行为，用 `@DisplayName` 描述用例意图。
- 方法名表达意图：`shouldReturnXxxWhenYyy` / `shouldThrowXxxWhenYyy`。
- 不依赖测试执行顺序，不依赖共享可变状态。

## 3. Mock

- 用 `@Mock` 构造依赖、`@InjectMocks` 注入被测对象（或显式构造）。
- `verify` 关键交互；断言结果，不断言实现细节。

## 4. 常用命令

```bash
mvn test -Dtest=OrderServiceTest                # 指定类
mvn test -Dtest=OrderServiceTest#shouldReturnX  # 指定方法
```

## 5. AI 生成测试时

- 优先为核心 Service / Domain 逻辑生成测试。
- 不为 getter / setter / 纯数据 DTO 生成无意义测试。
