# 编码规范详细文档

> 本文档被 `CLAUDE.md` 引用，是 AI 和团队开发者共同遵守的详细规范。
> **面向消息驱动项目**（入口为 MQ 消费者，无 HTTP Controller）。修改本文件等同于修改团队契约，需经 Code Review。
> 文中以本项目（`com.yl.track.bus`，rabbit/rocket 入口）为例。

---

## 0. 开发工作流（TDD + 分层顺序）

新增/修改一个功能时，按以下顺序，核心逻辑走 TDD 红-绿-重构：

1. **entity**：在 `entity/` 下新增/修改数据库实体（对应表结构）
2. **mapper**：在 `mapper/` 下定义 MyBatis Mapper 接口 + `resources/mapper/*.xml`
3. **service 测试（红）**：先为核心 service/impl 方法写失败的单元测试（JUnit 4 + Mockito，mock mapper），确认失败
4. **service 实现（绿→重构）**：实现业务方法（事务 + 异常）让测试通过，再重构
5. **消息入口**：在 `rabbit/`（Ops\*Receiver）或 `rocket/`（\*Consumer）新增消费者，仅做消息解析 + 调 service（**薄层，禁业务逻辑**）
6. **code-review**：开发完成、单测全绿后，调用 `code-reviewer` 子 agent（`/review`）审查，处理「必须修复」项

> 各层职责见 §1，测试细则见 §5。

---

## 1. 分层架构职责

```
rabbit/rocket（消息入口） → service → mapper（持久化）
                          ↘ entity（数据模型）
```

### 1.1 消息入口层（`rabbit/` `rocket/`）

| 维度 | 规则 |
|------|------|
| 职责 | 消息接收、反序列化、参数校验、调用 service |
| 技术 | rabbit：Spring Cloud Stream（`@EnableBinding` + `@StreamListener`，channel 集中在 `XxxStreamInterface`）；rocket：`@RocketMQMessageListener` + `RocketMQListener<String>` |
| 链路 | 入口方法必须标 `@TraceIdLog`（见 §4.2） |
| 异常 | 按 §3 分类处理（可重试抛出 / 不可重试捕获） |
| **禁止** | **编写聚合/业务逻辑**（反例：`OpsArrivalScanReceiver.onMessage` 写整段聚合）—— 业务必须下沉到 service |

### 1.2 Service 层（`service/` 接口 + `service/impl/` 实现）

| 维度 | 规则 |
|------|------|
| 命名 | 接口 `I*Service`（`IOmsOrderService`），实现 `*ServiceImpl`（`OmsOrderServiceImpl`） |
| 职责 | 核心业务逻辑、调用 mapper、调用下游 MQ、事务管理 |
| 事务 | **条件强制**：多表/多数据源写入必加 `@Transactional`；纯查询标 `readOnly=true`；单消息单条写入可不加 |
| 异常 | 捕获外部调用异常并转换（见 §3） |
| **禁止** | 直接操作 `HttpServletRequest`；service 里散落 `@Value`（见 §6） |

### 1.3 数据访问层（`mapper/`）

| 维度 | 规则 |
|------|------|
| 技术 | MyBatis + MyBatis-Plus，`@Mapper` 接口 + `resources/mapper/*.xml` |
| 命名 | `XxxMapper`（`OmsOrderMapper`） |
| SQL | XML 中参数化查询 `#{}`，**禁止字符串拼接 `${}`**（SQL 注入） |
| **禁止** | 业务判断逻辑、调用 service |

### 1.4 实体层（`entity/`）

| 维度 | 规则 |
|------|------|
| 职责 | 数据库实体，对应表结构，纯 POJO（贫血模型） |
| 注解 | `@TableName`（MyBatis-Plus）；字段 `@TableField` 等 |
| Lombok | `@Data` 或 `@Getter/@Setter`，显式标注 |
| **禁止** | 业务方法；引用 service/mapper/入口层 |

> 无独立 `domain/` 层；值对象/领域事件按需放 `entity/` 或 `dto/`。

### 1.5 DTO 层（`dto/`）

| 维度 | 规则 |
|------|------|
| 用途 | 消息载荷、service 间传输、下游 MQ 发送体 |
| 命名 | **后缀必须与所在包一致**：`dto/` 下只能 `*DTO`（入参）/ `*VO`（出参）；`entity/` 下只能 `*Entity` |
| 转换 | 优先 MapStruct；消息驱动/小项目可手写 converter（`XxxConverter.toEntity(...)`）集中放 `convert/` 包，**禁止散落 setter** |
| 反例 | `dto/ArrivalScanEntity`（应为 `ArrivalScanDTO`）—— 命名与包冲突，待治理 |

### 1.6 其他层

- **`enums/`**：状态码、类型枚举（`*Enum`，枚举值 `ALL_CAPS`）
- **`config/`**：Spring 配置、Bean 定义（MQ 模板、序列化、ID 生成）
- **`base/`**：常量（**禁 interface 放常量**，强制 `final class XxxConstant` + `private` 构造；MQ Topic 名等）
- **`utils/`**：纯静态工具（`DateTimeUtils` 等）
- **`trace/`**（独立，与业务包并行）：链路追踪（见 §4.2）

---

## 2. 命名规范

| 类型 | 规则 | 示例 |
|------|------|------|
| 类名 | UpperCamelCase | `OmsOrderService`、`OpsArrivalScanReceiver` |
| 接口/实现 | `I*Service` / `*ServiceImpl` | `IOmsOrderService` / `OmsOrderServiceImpl` |
| 方法/变量 | lowerCamelCase | `getOrderById`、`traceId` |
| 常量 | ALL_CAPS + 下划线 | `MAX_RETRY_COUNT`、`DEFAULT_PAGE_SIZE` |
| 常量类 | **`final class` + `private` 构造**（禁 interface 常量） | `final class Constant { private Constant() {} ... }` |
| 枚举 | `*Enum`，值 ALL_CAPS | `OrderStatusEnum.PENDING_PAYMENT` |
| 包名 | 全小写，按业务域 | `com.yl.track.bus.service` |
| 数据库表 | snake_case | `trace_push`、`oms_order` |
| 数据库字段 | snake_case | `create_time`、`waybill_no` |

---

## 3. 异常处理（MQ 场景）

消息驱动项目无 HTTP 响应，异常策略围绕 **MQ 重试**：

### 3.1 两类异常

| 类型 | 处理 | 示例 |
|------|------|------|
| **可重试异常**（瞬时） | 直接抛出，触发 MQ 重试 | DB 死锁、下游超时、网络抖动 |
| **不可重试异常**（业务/毒消息） | `catch` + WARN 日志 + 丢弃或转死信，**避免无限重试** | 参数校验失败、消息格式错误、业务状态非法 |

### 3.2 规则

1. **禁裸 `throw new RuntimeException`**（反例：项目中 10 处 RocketMQ 发送失败直接 throw）—— 用具体异常或自定义业务异常
2. 自定义业务异常（`BusinessException`）携带错误码 + 上下文，便于排障
3. 外部调用（DB / RPC / HTTP / 下游 MQ）必须 try-catch 并转换为「可重试/不可重试」
4. 不吞异常：catch 块必须有日志（含 traceId）或重新抛出
5. MQ 发送失败：按语义决定重试抛出或落库补偿，**禁止静默丢失**

---

## 4. 日志规范

### 4.1 基础

| 场景 | 级别 | 要求 |
|------|------|------|
| 方法入口/出口 | DEBUG | 入参/返回值（敏感信息脱敏） |
| 业务异常（不可重试） | WARN | 错误码 + 业务上下文 + traceId |
| 系统异常（可重试） | ERROR | 完整堆栈 + traceId |
| 外部调用 | INFO | 调用目标、耗时、结果状态 |

规则：
1. SLF4J（`@Slf4j`），禁 `System.out.println`
2. 占位符 `{}`，禁字符串拼接
3. ERROR 必须含异常对象：`log.error("msg", e)`
4. 敏感信息（密码/Token/身份证号）脱敏

### 4.2 链路追踪 traceId（核心，消息驱动项目排障生命线）

1. 所有 MQ 入口方法（Receiver/Consumer）标注 `@TraceIdLog`（或等价切面），通过 **MDC** 注入 traceId
2. `logback-spring.xml` 的 pattern 必须含 `%X{traceId}`
3. 一个消息处理**全链路**（入口 → service → mapper → 下游 MQ 发送）共用同一 traceId
4. 设施在 `trace/` 包：`LogTraceIdAspect`（`@Around` AOP）、`@TraceIdLog` 注解、`TraceUtils`

---

## 5. 测试规范

### 5.1 框架与依赖

- JUnit 4（`@Test`、`@Before`、`@RunWith`）
- Mockito（`@Mock`、`@InjectMocks`、`@RunWith(MockitoJUnitRunner.class)`、`when().thenReturn()`）
- AssertJ（`assertThat(actual).isEqualTo(expected)`）

### 5.2 强制要求

1. **项目必须存在 `src/test/` 目录**（即使空骨架），避免「引了依赖却零测试」
2. **核心 service/impl 方法必须有单测**
3. **禁启 Spring 容器**：纯单测，Mock 隔离依赖。禁 `@SpringBootTest`、`@RunWith(SpringRunner.class)`、`@ContextConfiguration`
4. **增量代码单测覆盖率 > 80%**（见 §5.4）

### 5.3 命名与结构（AAA）

```java
@RunWith(MockitoJUnitRunner.class)
public class OmsOrderServiceImplTest {

    @Mock
    private OmsOrderMapper omsOrderMapper;

    @InjectMocks
    private OmsOrderServiceImpl omsOrderService;

    @Test
    public void shouldReturnOrderWhenIdExists() {
        // Arrange
        OmsOrder order = new OmsOrder();
        order.setId(1L);
        when(omsOrderMapper.selectById(1L)).thenReturn(order);

        // Act
        OmsOrder result = omsOrderService.getById(1L);

        // Assert
        assertThat(result.getId()).isEqualTo(1L);
    }
}
```

- 命名：`should期望行为When条件`（`shouldReturnOrderWhenIdExists`）
- 三段式：Arrange / Act / Assert，用注释分隔
- 单个测试方法不超过 30 行

### 5.4 增量覆盖率 > 80%

- **工具**：JaCoCo（全量报表）+ diff-cover（增量卡阈值）
- **口径**：增量**行覆盖**（本次 diff 的新增/修改行）；存量代码不强求
- **校验**：pre-push hook 跑 `mvn -DskipTests=false test` → `jacoco.xml` → `diff-cover --fail-under=80`（接入见 README「增量覆盖率」）
- 从 0 起步友好：只要求新写的代码有测试

### 5.5 TDD 范围（按层）

- **service/impl + converter + utils**：强制 TDD（红-绿-重构）
- **消息入口（Receiver/Consumer）**：补单测（mock service），不强制 TDD
- **mapper**：因禁启 Spring 容器，不纳入（数据访问正确性靠后续集成测试）

> 禁「先写实现再补测试」—— 测试后置不算 TDD。

---

## 6. 配置管理

| 类型 | 规则 |
|------|------|
| 业务参数（topic/group/阈值/开关） | **强制** `@ConfigurationProperties` + `xxxProperties.java` |
| 基础设施 Bean 装配参数（zkUrl 等） | 允许 `@Value`，但必须在 `@Configuration` 配置类内集中使用 |
| MQ 配置（topic/nameServer/accessKey） | `${}` 占位 + 配置中心 |
| **禁止** | service 层散落 `@Value` |
| 敏感信息 | 环境变量 / 配置中心注入，不写配置文件 |
| 默认值 | 关键配置提供合理默认值作降级 |

> 反例：`IdGeneratorConfig` 用散落 `@Value` 且无 Properties 类 —— 业务参数应迁移到 `xxxProperties`。
