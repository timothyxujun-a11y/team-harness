# 编码规范详细文档

> 本文档被 `CLAUDE.md` 引用，是 AI 和团队开发者共同遵守的详细规范。
> 修改本文件等同于修改团队契约，需经 Code Review。

---

## 1. 分层架构职责

### 1.1 Controller 层

| 维度 | 规则 |
|------|------|
| 职责 | 参数校验、请求/响应封装、调用 Service |
| 禁止 | 编写业务逻辑、直接调用 Repository、直接操作数据库 |
| 注解 | `@RestController`、`@RequestMapping`、`@Validated`、Swagger `@Operation` |
| 返回值 | 统一使用 `Result<T>` 包装（含 code、msg、data） |
| 异常 | 不捕获业务异常（交给全局异常处理器）；只捕获并转换框架级异常 |

```java
// 正确示例
@RestController
@RequestMapping("/api/v1/orders")
@Tag(name = "订单管理")
public class OrderController {

    private final OrderService orderService;

    @GetMapping("/{id}")
    @Operation(summary = "根据ID查询订单")
    public Result<OrderDetailDTO> getOrder(@PathVariable Long id) {
        return Result.success(orderService.getOrderById(id));
    }
}
```

### 1.2 Service 层

| 维度 | 规则 |
|------|------|
| 职责 | 核心业务逻辑、事务管理、调用 Repository |
| 禁止 | 直接写 SQL、包含 HTTP 相关代码、直接操作 HttpServletRequest |
| 事务 | `@Transactional` 加在 Service 方法上， readOnly 标注查询方法 |
| 异常 | 捕获外部调用异常并转换为 `BusinessException` |

### 1.3 Repository 层

| 维度 | 规则 |
|------|------|
| 职责 | 数据访问，MyBatis Mapper 或 JPA Repository |
| 禁止 | 包含业务判断逻辑、调用 Service |
| 命名 | MyBatis: `XxxMapper`；JPA: `XxxRepository` |
| SQL | MyBatis XML 中使用参数化查询，禁止字符串拼接 SQL |

### 1.4 Domain 层

| 维度 | 规则 |
|------|------|
| 职责 | 实体类、值对象、领域事件 |
| 禁止 | 包含业务方法（贫血模型）或依赖上层 |
| 注解 | JPA 实体使用 `@Entity`；MyBatis 实体为纯 POJO |
| Lombok | 使用 `@Data` 或 `@Getter/@Setter`，显式标注 |

### 1.5 DTO 层

| 维度 | 规则 |
|------|------|
| 命名 | 请求：`XxxRequest`；响应：`XxxResponse`/`XxxDTO`；视图：`XxxVO` |
| 校验 | Request 使用 `@Valid` + JSR-303 注解（`@NotNull`、`@Size` 等） |
| 转换 | 使用 MapStruct 或手动转换，禁止直接暴露 Domain 实体 |

---

## 2. 命名规范

| 类型 | 规则 | 示例 |
|------|------|------|
| 类名 | UpperCamelCase | `OrderService`、`PaymentCallbackHandler` |
| 方法/变量 | lowerCamelCase | `getOrderById`、`orderTimeout` |
| 常量 | ALL_CAPS + 下划线 | `MAX_RETRY_COUNT`、`DEFAULT_PAGE_SIZE` |
| 包名 | 全小写，按业务域 | `com.company.order.service` |
| 枚举值 | ALL_CAPS + 下划线 | `OrderStatus.PENDING_PAYMENT` |
| 数据库表 | snake_case | `order_detail`、`payment_record` |
| 数据库字段 | snake_case | `create_time`、`user_id` |
| API 路径 | `/api/v{版本}/{资源名}/{操作}` | `/api/v1/orders/{id}/items` |

---

## 3. 异常处理

### 3.1 异常体系

```
RuntimeException
  └── BusinessException（自定义业务异常）
        ├── errorCode: ErrorCode 枚举
        └── message: 用户可读的错误描述
```

### 3.2 规则

1. **统一业务异常**：所有业务错误抛出 `BusinessException`，禁止直接抛 `RuntimeException`
2. **全局处理器**：使用 `@ControllerAdvice` 统一捕获并返回 `Result<Void>`
3. **错误码管理**：使用 `ErrorCode` 枚举，禁止魔法数字
4. **外部调用**：DB、RPC、HTTP 调用必须 try-catch 并转换为 `BusinessException`
5. **不吞异常**：catch 块中必须有日志记录或重新抛出

```java
// 正确示例
public OrderDTO getOrder(Long id) {
    try {
        Order order = orderMapper.selectById(id);
        if (order == null) {
            throw new BusinessException(ErrorCode.ORDER_NOT_FOUND);
        }
        return OrderConverter.toDTO(order);
    } catch (BusinessException e) {
        throw e;
    } catch (Exception e) {
        log.error("查询订单失败, id={}", id, e);
        throw new BusinessException(ErrorCode.SYSTEM_ERROR, e);
    }
}
```

---

## 4. 日志规范

| 场景 | 级别 | 要求 |
|------|------|------|
| 方法入口/出口 | DEBUG | 记录入参和返回值（敏感信息脱敏） |
| 业务异常 | WARN | 记录错误码和业务上下文 |
| 系统异常 | ERROR | 记录完整异常堆栈 |
| 外部调用 | INFO | 记录调用目标、耗时、结果状态 |

规则：
1. 使用 SLF4J（`@Slf4j`），不直接使用 `System.out.println`
2. 日志使用占位符 `{}`，不使用字符串拼接
3. ERROR 级别日志必须包含异常对象：`log.error("msg", e)`
4. 敏感信息（密码、Token、身份证号）脱敏后记录

---

## 5. 测试规范

### 5.1 框架与依赖

- JUnit 5（`@Test`、`@DisplayName`、`@Nested`）
- Mockito（`@Mock`、`@InjectMocks`、`when().thenReturn()`）
- AssertJ（`assertThat(actual).isEqualTo(expected)`）

### 5.2 命名与结构

```java
@DisplayName("订单服务测试")
class OrderServiceTest {

    @Nested
    @DisplayName("查询订单")
    class GetOrder {

        @Test
        @DisplayName("订单存在时返回订单详情")
        void shouldReturnOrderWhenIdExists() {
            // Arrange
            given(orderMapper.selectById(1L)).willReturn(testOrder());

            // Act
            OrderDTO result = orderService.getOrder(1L);

            // Assert
            assertThat(result.getId()).isEqualTo(1L);
            assertThat(result.getStatus()).isEqualTo(OrderStatus.PENDING_PAYMENT);
        }

        @Test
        @DisplayName("订单不存在时抛出业务异常")
        void shouldThrowWhenOrderNotFound() {
            // Arrange
            given(orderMapper.selectById(999L)).willReturn(null);

            // Act & Assert
            assertThatThrownBy(() -> orderService.getOrder(999L))
                    .isInstanceOf(BusinessException.class)
                    .hasMessageContaining("订单不存在");
        }
    }
}
```

### 5.3 规则

1. **AAA 结构**：每个测试方法分为 Arrange（准备）、Act（执行）、Assert（断言）三段，用注释分隔
2. **纯单元测试优先**：Service 层测试 mock Repository，不启动 Spring Context
3. **测试隔离**：每个测试方法独立，不依赖执行顺序，不共享可变状态
4. **边界覆盖**：正常路径 + 空值 + 边界值 + 异常路径
5. **不测试 getter/setter**：只测试包含逻辑的方法
6. **方法长度**：单个测试方法不超过 30 行

---

## 6. API 设计规范

1. **RESTful 风格**：资源用名词、操作用 HTTP 方法
2. **版本控制**：路径中携带版本号 `/api/v1/...`
3. **统一响应**：`Result<T>` 包装，含 `code`、`msg`、`data`
4. **Swagger 注解**：所有接口必须标注 `@Operation`、`@Parameter`
5. **分页参数**：统一使用 `pageNum`（从 1 开始）和 `pageSize`
6. **时间格式**：ISO 8601（`yyyy-MM-dd'T'HH:mm:ss.SSSZ`）

---

## 7. 配置管理

1. **禁止硬编码**：所有环境相关的配置（DB 连接、Redis 地址等）使用 `${}` 占位符
2. **Profile 隔离**：`application-dev.yml`、`application-test.yml`、`application-prod.yml`
3. **敏感信息**：密码、Token 通过环境变量或配置中心注入，不写入配置文件
4. **默认值**：关键配置项提供合理默认值作为降级方案
