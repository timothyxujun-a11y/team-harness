# 日志规范

> **适用规则**: JAVA-LOG-001, JAVA-LOG-002, JAVA-LOG-003

---

## JAVA-LOG-001: 使用 SLF4J + Logback 日志框架

### 规则说明

必须使用 **SLF4J** 作为日志门面接口，**Logback** 作为日志实现。禁止使用 `System.out.println`、`java.util.logging` 或直接使用 Logback API。

### 正确用法

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class UserService {

    // 正确：使用 SLF4J Logger
    private static final Logger log = LoggerFactory.getLogger(UserService.class);

    public User getUser(Long id) {
        log.info("查询用户, id={}", id);
        User user = repository.findById(id);
        log.debug("查询结果, id={}, found={}", id, user != null);
        return user;
    }
}
```

### 使用 Lombok 简化

```java
import lombok.extern.slf4j.Slf4j;

// 正确：使用 Lombok @Slf4j 注解
@Slf4j
public class UserService {

    public User getUser(Long id) {
        log.info("查询用户, id={}", id);
        // ...
    }
}
```

### 错误示例

```java
// 错误：使用 System.out.println
System.out.println("用户ID: " + userId);

// 错误：直接使用 Logback API
import ch.qos.logback.classic.Logger;
Logger logger = (Logger) LoggerFactory.getLogger("UserService");

// 错误：使用 java.util.logging
import java.util.logging.Logger;
private static final Logger logger = Logger.getLogger("UserService");

// 错误：字符串拼接而非占位符
log.info("查询用户, id=" + id);  // 即使日志级别不输出也会执行字符串拼接
log.info("查询用户, id=" + id + ", name=" + name);  // 浪费性能
```

### Maven 依赖

```xml
<!-- SLF4J + Logback -->
<dependency>
    <groupId>org.slf4j</groupId>
    <artifactId>slf4j-api</artifactId>
    <version>2.0.9</version>
</dependency>
<dependency>
    <groupId>ch.qos.logback</groupId>
    <artifactId>logback-classic</artifactId>
    <version>1.4.14</version>
</dependency>

<!-- Lombok（可选） -->
<dependency>
    <groupId>org.projectlombok</groupId>
    <artifactId>lombok</artifactId>
    <scope>provided</scope>
</dependency>
```

### 日志占位符规则

- 使用 `{}` 占位符，而非字符串拼接
- 占位符数量应与参数数量一致
- 避免在占位符参数中使用复杂方法调用

```java
// 正确
log.info("创建订单, userId={}, productId={}, quantity={}", userId, productId, quantity);

// 错误：字符串拼接
log.info("创建订单, userId=" + userId + ", productId=" + productId);

// 注意：异常对象作为最后一个参数时不需要占位符
log.error("调用外部接口失败, url={}", url, exception);
```

---

## JAVA-LOG-002: 日志级别使用规范

### 规则说明

按场景正确使用 **DEBUG / INFO / WARN / ERROR** 四个级别，避免滥用。

### 级别使用指南

| 级别 | 适用场景 | 示例 |
|------|---------|------|
| **ERROR** | 影响业务流程的异常，需要立即关注 | 外部服务调用失败、数据库连接异常 |
| **WARN** | 可预见的业务异常或潜在风险 | 用户不存在、参数校验失败、重试操作 |
| **INFO** | 关键业务流程节点 | 订单创建成功、任务执行完成、定时任务启动 |
| **DEBUG** | 开发调试信息，生产环境默认关闭 | 方法入参/出参、中间状态、SQL 执行详情 |

### 正确示例

```java
public class OrderService {

    public Order createOrder(Long userId, List<OrderItem> items) {
        // INFO：关键业务节点
        log.info("开始创建订单, userId={}, itemCount={}", userId, items.size());

        // DEBUG：调试信息
        log.debug("订单明细: {}", items);

        try {
            Order order = repository.save(buildOrder(userId, items));
            // INFO：业务结果
            log.info("订单创建成功, orderId={}, totalAmount={}", order.getId(), order.getTotalAmount());
            return order;
        } catch (DataAccessException e) {
            // ERROR：系统级异常，影响业务
            log.error("订单创建失败, userId={}", userId, e);
            throw new BusinessException("ORDER_CREATE_FAILED", "订单创建失败", e);
        }
    }

    public User getUser(Long userId) {
        User user = repository.findById(userId);
        if (user == null) {
            // WARN：可预见的业务异常
            log.warn("用户不存在, userId={}", userId);
            throw new UserNotFoundException(userId);
        }
        return user;
    }
}
```

### 错误示例

```java
// 错误：用 ERROR 记录可预见的业务异常
log.error("用户不存在, userId={}", userId);  // 应使用 WARN

// 错误：用 INFO 记录高频调用的方法出入参
log.info("进入 getUser方法, id={}", id);  // 应使用 DEBUG

// 错误：用 WARN 记录正常流程
log.warn("订单创建完成, orderId={}", orderId);  // 应使用 INFO

// 错误：滥用 ERROR
log.error("字段为空");  // 应该使用参数校验而非日志
```

### 级别使用原则

- **ERROR** 仅用于系统级故障或不可恢复的异常
- **WARN** 用于可预见的业务异常，不影响系统稳定性
- **INFO** 用于记录关键业务流程，生产环境开启
- **DEBUG** 用于开发调试，生产环境默认关闭
- 避免在循环中输出日志，尤其是 INFO 和 ERROR

---

## JAVA-LOG-003: 敏感信息不得记录日志

### 规则说明

密码、Token、身份证号、银行卡号等敏感信息**不得以明文**记录到日志中。必须进行脱敏处理或不记录。

### 需要脱敏的字段

| 字段类型 | 脱敏方式 | 示例 |
|---------|---------|------|
| 密码 | 不记录 | - |
| Token / API Key | 截取前后各 4 位 | `abcd****xyz` |
| 身份证号 | 截取前 6 后 4 | `110101****1234` |
| 手机号 | 截取前 3 后 4 | `138****5678` |
| 银行卡号 | 截取后 4 位 | `************1234` |
| 邮箱 | 截取前 2 后 @ 后域名 | `ab****@example.com` |

### 正确示例

```java
public class UserService {

    public void login(String username, String password) {
        // 正确：不记录密码
        log.info("用户登录, username={}", username);
        // 错误：log.info("用户登录, username={}, password={}", username, password);

        try {
            authService.authenticate(username, password);
            log.info("登录成功, username={}", username);
        } catch (AuthenticationException e) {
            log.warn("登录失败, username={}", username);
        }
    }

    public void processPayment(String cardNumber, String cvv, BigDecimal amount) {
        // 正确：银行卡号脱敏，CVV 不记录
        log.info("处理支付, cardNumber={}, amount={}", maskBankCard(cardNumber), amount);
        // 错误：log.info("处理支付, cardNumber={}, cvv={}, amount={}", cardNumber, cvv, amount);
    }

    private String maskBankCard(String cardNumber) {
        if (cardNumber == null || cardNumber.length() < 8) {
            return "****";
        }
        String lastFour = cardNumber.substring(cardNumber.length() - 4);
        return "************" + lastFour;
    }
}
```

### 敏感信息场景

```java
// HTTP 请求日志：不记录 Authorization 头
log.info("API请求, method={}, uri={}, body={}", method, uri, maskSensitiveFields(body));

// 对象日志：使用 @ToString(exclude = ...) 排除敏感字段
@ToString(exclude = {"password", "salt"})
public class UserCredential {
    private String username;
    private String password;
    private String salt;
}

// 配置信息：不记录数据库密码
log.info("数据库配置, host={}, port={}, username={}", host, port, username);
// 错误：log.info("数据库配置, url={}, password={}", url, password);
```

### 设计原则

- 密码、CVV、私钥等**绝对不能**出现在任何级别的日志中
- Token、卡号、身份证等需脱敏后才能记录
- 使用 Lombok `@ToString(exclude=...)` 防止自动 toString 泄露敏感信息
- 日志框架的配置文件（logback.xml）中也要注意不输出完整请求体
