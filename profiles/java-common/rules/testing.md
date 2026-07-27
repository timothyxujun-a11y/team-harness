# 单元测试规范

> **适用规则**: JAVA-TEST-001, JAVA-TEST-002, JAVA-TEST-003, JAVA-TEST-004

---

## JAVA-TEST-001: 测试框架使用 JUnit 4 + Mockito + AssertJ

### 规则说明

单元测试固定使用 **JUnit 4 + Mockito + AssertJ** 技术栈。禁止使用 JUnit 5 或 TestNG。

### Maven 依赖

```xml
<dependencies>
    <!-- JUnit 4 -->
    <dependency>
        <groupId>junit</groupId>
        <artifactId>junit</artifactId>
        <version>4.13.2</version>
        <scope>test</scope>
    </dependency>

    <!-- Mockito -->
    <dependency>
        <groupId>org.mockito</groupId>
        <artifactId>mockito-core</artifactId>
        <version>4.11.0</version>
        <scope>test</scope>
    </dependency>

    <!-- AssertJ -->
    <dependency>
        <groupId>org.assertj</groupId>
        <artifactId>assertj-core</artifactId>
        <version>3.24.2</version>
        <scope>test</scope>
    </dependency>
</dependencies>
```

### 基本测试结构

```java
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.MockitoJUnitRunner;
import static org.mockito.Mockito.*;
import static org.assertj.core.api.Assertions.*;

@RunWith(MockitoJUnitRunner.class)
public class UserServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private EmailService emailService;

    @InjectMocks
    private UserService userService;

    @Before
    public void setUp() {
        // 公共初始化
    }

    @Test
    public void shouldReturnUserWhenUserIdExists() {
        // 测试逻辑
    }
}
```

### 禁止使用的框架

```java
// 禁止：JUnit 5
import org.junit.jupiter.api.Test;           // JUnit 5
import org.junit.jupiter.api.BeforeEach;     // JUnit 5
import org.junit.jupiter.api.extension.ExtendWith;  // JUnit 5

// 禁止：TestNG
import org.testng.annotations.Test;

// 禁止：使用 given().willReturn()（应使用 when().thenReturn()）
import static org.mockito.BDDMockito.given;  // 不推荐使用 BDDMockito
```

---

## JAVA-TEST-002: 禁止单元测试启动 Spring 容器

### 规则说明

**单元测试禁止启动 Spring 容器**。所有依赖通过 Mockito Mock 注入，不依赖 Spring Bean 容器。

### 禁止使用的注解

```java
// 禁止：以下注解会启动 Spring 容器
@RunWith(SpringRunner.class)                  // 启动 Spring 测试上下文
@SpringBootTest                               // 启动完整 Spring Boot 应用上下文
@ContextConfiguration                         // 加载 Spring 配置
@WebMvcTest                                   // 启动 Spring MVC 上下文
@DataJpaTest                                  // 启动 JPA 上下文
@Import                                       // 导入 Spring 配置类
@AutoConfigureMockMvc                         // 自动配置 MockMvc
```

### 正确做法：纯 Mock 测试

```java
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.MockitoJUnitRunner;

import static org.mockito.Mockito.*;
import static org.assertj.core.api.Assertions.*;

// 正确：使用 MockitoJUnitRunner，不启动 Spring
@RunWith(MockitoJUnitRunner.class)
public class OrderServiceTest {

    @Mock
    private OrderRepository orderRepository;

    @Mock
    private PaymentGateway paymentGateway;

    @InjectMocks
    private OrderService orderService;

    @Test
    public void shouldCreateOrderWhenInputValid() {
        // Arrange
        OrderRequest request = new OrderRequest(1L, "PROD-001", 2);
        Order savedOrder = new Order(100L, 1L, "PROD-001", 2);
        when(orderRepository.save(any(Order.class))).thenReturn(savedOrder);
        when(paymentGateway.charge(anyLong(), any(BigDecimal.class))).thenReturn(true);

        // Act
        Order result = orderService.createOrder(request);

        // Assert
        assertThat(result.getId()).isEqualTo(100L);
        assertThat(result.getQuantity()).isEqualTo(2);
        verify(orderRepository).save(any(Order.class));
        verify(paymentGateway).charge(eq(1L), any(BigDecimal.class));
    }
}
```

### 错误示例

```java
// 错误：启动了 Spring 容器
@RunWith(SpringRunner.class)
@SpringBootTest
public class OrderServiceTest {

    @Autowired
    private OrderService orderService;

    @Test
    public void testCreateOrder() {
        // 这不是单元测试，是集成测试
    }
}

// 错误：使用 @ContextConfiguration
@RunWith(SpringRunner.class)
@ContextConfiguration(classes = AppConfig.class)
public class OrderServiceTest {
    // ...
}
```

### 设计原则

- 单元测试应该**快速**——毫秒级执行
- 不依赖外部资源（数据库、网络、Spring 容器）
- 依赖通过 `@Mock` 注入，被测类通过 `@InjectMocks` 创建
- 集成测试应放在独立的测试目录或使用独立 Profile

---

## JAVA-TEST-003: AAA 结构与测试命名规范

### 规则说明

测试方法使用 **Arrange-Act-Assert** 三段式结构，方法命名采用 `should期望行为When条件` 格式，使用 `when().thenReturn()` 进行 Mock。

### AAA 结构

```java
@Test
public void shouldReturnUserWhenUserIdExists() {
    // Arrange - 准备测试数据
    Long userId = 1L;
    User mockUser = new User(userId, "张三", "zhangsan@example.com");
    when(userRepository.findById(userId)).thenReturn(mockUser);

    // Act - 执行被测方法
    User result = userService.getUserById(userId);

    // Assert - 验证结果
    assertThat(result).isNotNull();
    assertThat(result.getId()).isEqualTo(userId);
    assertThat(result.getName()).isEqualTo("张三");
    verify(userRepository).findById(userId);
}
```

### 测试方法命名

格式：`should{期望行为}When{条件}`

```java
// 正确：命名清晰表达意图
shouldReturnUserWhenUserIdExists()
shouldThrowExceptionWhenUserNotFound()
shouldReturnEmptyListWhenNoOrders()
shouldRetryWhenFirstCallFails()
shouldNotChargeWhenPaymentIsPending()
shouldReturnTrueWhenPasswordMeetsPolicy()
shouldConvertToDTOWhenEntityIsValid()
```

```java
// 错误：命名不清晰
testGetUser()            // 不表达意图
test1()                  // 无意义
getUserTest()            // 不是测试场景
shouldWork()             // 过于模糊
```

### Mock 使用规范：when().thenReturn()

```java
// 正确：使用 when().thenReturn()
@Test
public void shouldReturnOrderWhenOrderIdExists() {
    // Arrange
    when(orderRepository.findById(100L)).thenReturn(testOrder);

    // Act
    Order result = orderService.getOrder(100L);

    // Assert
    assertThat(result).isEqualTo(testOrder);
}

// 正确：Mock 异常抛出
@Test
public void shouldThrowExceptionWhenRepositoryFails() {
    // Arrange
    when(userRepository.findById(1L))
        .thenThrow(new RuntimeException("DB连接失败"));

    // Act & Assert
    assertThatThrownBy(() -> userService.getUserById(1L))
        .isInstanceOf(BusinessException.class)
        .hasMessageContaining("DB连接失败");
}

// 正确：Mock void 方法
@Test
public void shouldSendEmailWhenOrderCompleted() {
    // Arrange
    doNothing().when(emailService).send(anyString(), anyString());

    // Act
    orderService.completeOrder(100L);

    // Assert
    verify(emailService).send(eq("customer@example.com"), contains("订单完成"));
}
```

```java
// 错误：使用 BDDMockito 的 given().willReturn()
import static org.mockito.BDDMockito.given;

given(userRepository.findById(1L)).willReturn(mockUser);  // 禁止使用
```

### 完整示例

```java
@RunWith(MockitoJUnitRunner.class)
public class PaymentServiceTest {

    @Mock
    private PaymentGateway paymentGateway;

    @Mock
    private OrderRepository orderRepository;

    @InjectMocks
    private PaymentService paymentService;

    @Test
    public void shouldReturnTrueWhenPaymentSucceeds() {
        // Arrange
        Long orderId = 100L;
        BigDecimal amount = new BigDecimal("99.99");
        Order order = new Order(orderId, amount);
        when(orderRepository.findById(orderId)).thenReturn(order);
        when(paymentGateway.charge(orderId, amount)).thenReturn(true);

        // Act
        boolean result = paymentService.processPayment(orderId);

        // Assert
        assertThat(result).isTrue();
        verify(orderRepository).findById(orderId);
        verify(paymentGateway).charge(orderId, amount);
    }

    @Test
    public void shouldThrowExceptionWhenOrderNotFound() {
        // Arrange
        Long orderId = 999L;
        when(orderRepository.findById(orderId)).thenReturn(null);

        // Act & Assert
        assertThatThrownBy(() -> paymentService.processPayment(orderId))
            .isInstanceOf(OrderNotFoundException.class)
            .hasMessageContaining("999");

        verify(paymentGateway, never()).charge(anyLong(), any(BigDecimal.class));
    }

    @Test
    public void shouldReturnFalseWhenPaymentGatewayDeclines() {
        // Arrange
        Long orderId = 100L;
        BigDecimal amount = new BigDecimal("99.99");
        Order order = new Order(orderId, amount);
        when(orderRepository.findById(orderId)).thenReturn(order);
        when(paymentGateway.charge(orderId, amount)).thenReturn(false);

        // Act
        boolean result = paymentService.processPayment(orderId);

        // Assert
        assertThat(result).isFalse();
    }
}
```

---

## JAVA-TEST-004: 测试最小化运行与覆盖率要求

### 规则说明

只运行改动的测试类，使用 `@RunWith(MockitoJUnitRunner.class)`，核心逻辑行覆盖率不低于 80%。

### 最小化运行测试

开发阶段只运行改动的测试类，避免全量运行浪费时间：

```bash
# 运行单个测试类
mvn test -Dtest=UserServiceTest

# 运行单个测试方法
mvn test -Dtest=UserServiceTest#shouldReturnUserWhenUserIdExists

# 运行匹配模式的测试类
mvn test -Dtest="*ServiceTest"

# 运行指定模块的测试
mvn test -pl user-service -Dtest=UserServiceTest
```

### 使用 MockitoJUnitRunner

```java
// 正确：使用 MockitoJUnitRunner，不需要 Spring 容器
@RunWith(MockitoJUnitRunner.class)
public class UserServiceTest {
    // 测试在毫秒级完成
}

// 错误：使用 SpringRunner 导致启动慢
// @RunWith(SpringRunner.class)
```

### 覆盖率要求

| 代码类型 | 行覆盖率要求 | 说明 |
|---------|------------|------|
| 核心业务逻辑 | >= 80% | Service 层核心方法 |
| 工具类 | >= 90% | 公共工具方法 |
| Controller 层 | >= 60% | 参数校验、路由 |
| DTO / Entity | 不要求 | getter/setter 无需测试 |

### JaCoCo 配置

```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.11</version>
    <executions>
        <execution>
            <goals>
                <goal>prepare-agent</goal>
            </goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>test</phase>
            <goals>
                <goal>report</goal>
            </goals>
        </execution>
        <execution>
            <id>check</id>
            <goals>
                <goal>check</goal>
            </goals>
            <configuration>
                <rules>
                    <rule>
                        <element>BUNDLE</element>
                        <limits>
                            <limit>
                                <counter>LINE</counter>
                                <value>COVEREDRATIO</value>
                                <minimum>0.80</minimum>
                            </limit>
                        </limits>
                    </rule>
                </rules>
            </configuration>
        </execution>
    </executions>
</plugin>
```

### 测试原则

- **快速**：每个测试方法应在 100ms 内完成
- **独立**：测试之间不应有依赖，每个测试可独立运行
- **可重复**：多次运行结果一致，不依赖环境状态
- **最小化**：开发阶段只运行改动相关的测试，提交前运行全量测试
- **Mock 验证**：使用 `verify()` 确认依赖被正确调用
- **断言充分**：使用 AssertJ 链式断言，覆盖正常和异常路径

```java
// 正确：充分断言，使用 AssertJ 链式风格
@Test
public void shouldReturnUserDTOWhenUserExists() {
    when(userRepository.findById(1L)).thenReturn(new User(1L, "张三", "zhangsan@example.com"));

    UserDTO dto = userService.getUserDTO(1L);

    assertThat(dto)
        .isNotNull()
        .satisfies(d -> {
            assertThat(d.getId()).isEqualTo(1L);
            assertThat(d.getName()).isEqualTo("张三");
            assertThat(d.getEmail()).isEqualTo("zhangsan@example.com");
        });
}
```
