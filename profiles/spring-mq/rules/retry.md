# 重试与死信处理

## MQ-RETRY-001: 必须配置合理的重试次数与退避策略

Consumer 必须显式配置最大重试次数（建议不超过 5 次），并采用指数退避策略。禁止使用无限重试导致消息积压。

### 错误示例

```java
// 错误：未配置重试次数，使用默认值（RocketMQ 默认 16 次）
@RocketMQMessageListener(
    consumerGroup = "order-service-consumer-group",
    topic = "order-topic"
)
public class OrderConsumer implements RocketMQListener<OrderMessage> {
    // ...
}
```

```yaml
# 错误：未配置重试相关参数
rocketmq:
  consumer:
    group: order-service-consumer-group
    topic: order-topic
```

### 正确示例（RocketMQ 注解方式）

```java
// 正确：显式配置最大重试次数
@RocketMQMessageListener(
    consumerGroup = "order-service-consumer-group",
    topic = "order-topic",
    maxReconsumeTimes = 5  // 最大重试 5 次
)
public class OrderConsumer implements RocketMQListener<OrderMessage> {

    @Override
    public void onMessage(OrderMessage message) {
        try {
            orderService.createOrder(message);
        } catch (BusinessException e) {
            // 业务异常不重试
            log.error("业务异常, 不重试, orderId={}", message.getOrderId(), e);
            return;
        } catch (Exception e) {
            // 系统异常触发重试
            log.error("系统异常, 将重试, orderId={}", message.getOrderId(), e);
            throw new RuntimeException(e);  // 抛出异常触发 MQ 重试
        }
    }
}
```

### 正确示例（Spring Retry 指数退避）

```java
@Service
public class OrderService {

    /**
     * 使用 Spring Retry 实现指数退避重试
     */
    @Retryable(
        value = {TransientException.class},
        maxAttempts = 3,
        backoff = @Backoff(delay = 1000, multiplier = 2.0, maxDelay = 10000)
    )
    public void createOrder(OrderMessage message) {
        // delay=1s, multiplier=2 → 间隔: 1s, 2s, 4s
        orderRepository.save(message);
    }

    /**
     * 重试耗尽后的兜底处理
     */
    @Recover
    public void recover(TransientException e, OrderMessage message) {
        log.error("重试耗尽, 发送死信, orderId={}", message.getOrderId(), e);
        deadLetterService.sendToDlq(message, e);
    }
}
```

### 检查要点

- 最大重试次数建议不超过 5 次
- 退避策略推荐指数退避（如 1s → 2s → 4s → 8s → 16s）
- 业务异常不应触发重试，系统异常才触发
- 重试次数耗尽后必须进入死信队列
- 配置可在 `application.yml` 或注解中设置

---

## MQ-RETRY-002: 必须实现死信队列监控与告警

系统必须对死信队列（DLQ）实现监控与告警机制，死信消息需提供人工介入处理入口或自动补偿流程。

### 错误示例

```java
// 错误：重试耗尽后丢弃消息，无任何监控
@Override
public void onMessage(OrderMessage message) {
    try {
        orderService.createOrder(message);
    } catch (Exception e) {
        log.error("处理失败, 丢弃消息", e);
        // 消息被丢弃，无死信处理
    }
}
```

### 正确示例

```java
// 死信消息处理器
@Component
@Slf4j
public class DeadLetterMessageHandler {

    @Autowired
    private DeadLetterMessageRepository dlqRepository;

    @Autowired
    private AlertService alertService;

    /**
     * 处理死信消息：持久化 + 告警
     */
    public void handleDeadLetter(String topic, String msgId, Object message, Throwable cause) {
        // 1. 持久化死信消息到数据库
        DeadLetterMessage dlq = new DeadLetterMessage();
        dlq.setTopic(topic);
        dlq.setMsgId(msgId);
        dlq.setMessageBody(JSON.toJSONString(message));
        dlq.setErrorCause(cause.getMessage());
        dlq.setStatus("PENDING");
        dlq.setCreateTime(LocalDateTime.now());
        dlqRepository.save(dlq);

        // 2. 发送告警
        alertService.sendAlert(String.format(
            "MQ死信告警: topic=%s, msgId=%s, 错误=%s",
            topic, msgId, cause.getMessage()
        ));

        log.error("死信消息已记录, topic={}, msgId={}", topic, msgId, cause);
    }
}

// Consumer 中在重试耗尽后调用死信处理
@RocketMQMessageListener(
    consumerGroup = "order-service-consumer-group",
    topic = "order-topic",
    maxReconsumeTimes = 5
)
public class OrderConsumer implements RocketMQListener<OrderMessage> {

    @Autowired
    private DeadLetterMessageHandler deadLetterHandler;

    @Override
    public void onMessage(OrderMessage message) {
        try {
            orderService.createOrder(message);
        } catch (BusinessException e) {
            log.error("业务异常, 直接进入死信, orderId={}", message.getOrderId(), e);
            deadLetterHandler.handleDeadLetter("order-topic", message.getMsgId(), message, e);
        } catch (Exception e) {
            log.error("系统异常, 触发重试, orderId={}", message.getOrderId(), e);
            throw new RuntimeException(e);
        }
    }
}
```

### 检查要点

- 死信消息必须持久化存储（数据库 / 文件），不能仅靠日志
- 死信产生时必须触发告警（钉钉/企业微信/邮件等）
- 需提供死信消息查询与重放的管理界面或 API
- 建议实现定时扫描死信表，对可自动补偿的消息进行重试
- RocketMQ 死信 Topic 命名规则：`%DLQ%{consumerGroup}`
