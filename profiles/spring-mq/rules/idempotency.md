# 消息幂等

## MQ-IDEMP-001: Consumer 必须实现幂等性校验

所有 Consumer 必须在业务处理前基于消息唯一 ID（msgId / 业务唯一键）进行幂等校验，防止重复消费。幂等存储推荐使用 Redis SETNX 或数据库唯一索引。

### 错误示例

```java
// 错误：未做幂等校验，重复消费会导致重复创建订单
@RocketMQMessageListener(
    consumerGroup = "order-service-consumer-group",
    topic = "order-topic"
)
public class OrderConsumer implements RocketMQListener<OrderMessage> {
    @Override
    public void onMessage(OrderMessage message) {
        // 直接处理，无幂等校验
        orderService.createOrder(message);
    }
}
```

### 正确示例（Redis 方案）

```java
@RocketMQMessageListener(
    consumerGroup = "order-service-consumer-group",
    topic = "order-topic"
)
public class OrderConsumer implements RocketMQListener<OrderMessage> {

    @Autowired
    private StringRedisTemplate redisTemplate;

    @Autowired
    private OrderService orderService;

    private static final String IDEMPOTENT_KEY_PREFIX = "mq:idempotent:";
    private static final long IDEMPOTENT_EXPIRE_HOURS = 24L;

    @Override
    public void onMessage(OrderMessage message) {
        String idempotentKey = IDEMPOTENT_KEY_PREFIX + message.getOrderId();
        // SETNX 原子操作，设置成功说明是首次消费
        Boolean isFirst = redisTemplate.opsForValue()
            .setIfAbsent(idempotentKey, "1", IDEMPOTENT_EXPIRE_HOURS, TimeUnit.HOURS);

        if (Boolean.FALSE.equals(isFirst)) {
            // 已消费过，跳过
            log.info("消息已消费, 跳过处理, orderId={}", message.getOrderId());
            return;
        }

        try {
            orderService.createOrder(message);
        } catch (Exception e) {
            // 处理失败，删除幂等键以便重试
            redisTemplate.delete(idempotentKey);
            throw e;
        }
    }
}
```

### 正确示例（数据库唯一索引方案）

```java
@RocketMQMessageListener(
    consumerGroup = "order-service-consumer-group",
    topic = "order-topic"
)
public class OrderConsumer implements RocketMQListener<OrderMessage> {

    @Autowired
    private MessageConsumeLogService consumeLogService;

    @Autowired
    private OrderService orderService;

    @Override
    public void onMessage(OrderMessage message) {
        // 通过数据库唯一索引保证幂等
        try {
            consumeLogService.recordConsume(message.getMsgId(), "order-topic");
        } catch (DuplicateKeyException e) {
            log.info("消息已消费, 跳过处理, msgId={}", message.getMsgId());
            return;
        }
        orderService.createOrder(message);
    }
}
```

### 检查要点

- 每个 Consumer 都必须有幂等校验逻辑
- 幂等键需设置合理的过期时间（建议 24 小时）
- 业务处理失败时需回滚幂等状态，允许重试
- 推荐方案：Redis SETNX（高性能场景）/ 数据库唯一索引（强一致场景）

---

## MQ-IDEMP-002: 幂等键必须使用业务唯一标识而非 msgId

幂等校验的键应优先使用业务唯一标识（如订单号+操作类型），而非 MQ 中间件生成的 msgId，因为 msgId 在极端情况下可能重复。

### 错误示例

```java
// 错误：使用 msgId 作为幂等键
String idempotentKey = "mq:idempotent:" + message.getMsgId();
```

### 正确示例

```java
// 正确：使用业务唯一标识作为幂等键
String idempotentKey = "mq:idempotent:order:" + message.getOrderId();

// 对于多操作类型的消息，组合业务标识
String idempotentKey = "mq:idempotent:order:" + message.getOrderId()
    + ":" + message.getOperationType();
```

### 检查要点

- 幂等键应由业务领域唯一标识组成（如订单号、支付流水号）
- 多操作场景需组合「业务ID + 操作类型」
- 幂等键应具有明确的命名前缀，便于排查和清理
- msgId 可作为辅助日志，但不应作为幂等去重的唯一依据
