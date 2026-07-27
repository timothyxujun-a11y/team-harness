# Consumer 入口规范

## MQ-CONS-001: Consumer 必须显式声明消费组与 Topic

所有消息消费者必须通过 `@RocketMQMessageListener` 或 `@KafkaListener` 显式指定 `consumerGroup` 和 `topic`，禁止使用通配符订阅生产环境 Topic。

### 错误示例

```java
// 错误：未指定 consumerGroup，使用通配符订阅
@RocketMQMessageListener(topic = "*")
public class OrderConsumer implements RocketMQListener<OrderMessage> {
    @Override
    public void onMessage(OrderMessage message) {
        processOrder(message);
    }
}
```

### 正确示例

```java
// 正确：显式声明 consumerGroup 和 topic
@RocketMQMessageListener(
    consumerGroup = "order-service-consumer-group",
    topic = "order-topic",
    consumeMode = ConsumeMode.CONCURRENTLY
)
public class OrderConsumer implements RocketMQListener<OrderMessage> {
    @Override
    public void onMessage(OrderMessage message) {
        processOrder(message);
    }
}
```

Kafka 示例：

```java
// 正确：显式声明 groupId 和 topic
@KafkaListener(
    groupId = "order-service-group",
    topics = "order-topic"
)
public void handleOrder(OrderMessage message) {
    processOrder(message);
}
```

### 检查要点

- `consumerGroup` / `groupId` 不能为空，命名格式建议为 `{服务名}-consumer-group`
- `topic` 不能使用通配符 `*` 或 `#`
- 每个 Consumer 类只订阅一个 Topic，避免职责混乱

---

## MQ-CONS-002: Consumer 消费逻辑必须捕获异常并返回状态

Consumer 消费方法内部必须 try-catch 业务异常，根据业务语义返回 `ConsumeConcurrentlyStatus` 或 `Acknowledgment`，禁止异常直接向上抛出导致无限重试。

### 错误示例

```java
// 错误：未捕获异常，异常直接抛出导致无限重试
@RocketMQMessageListener(
    consumerGroup = "order-service-consumer-group",
    topic = "order-topic"
)
public class OrderConsumer implements RocketMQListener<OrderMessage> {
    @Override
    public void onMessage(OrderMessage message) {
        // 异常直接抛出，MQ 框架会无限重试
        orderService.createOrder(message);
    }
}
```

### 正确示例

```java
@RocketMQMessageListener(
    consumerGroup = "order-service-consumer-group",
    topic = "order-topic"
)
public class OrderConsumer implements RocketMQListener<OrderMessage> {
    @Override
    public void onMessage(OrderMessage message) {
        try {
            orderService.createOrder(message);
        } catch (BusinessException e) {
            // 业务异常，记录日志后消费成功，避免无限重试
            log.error("订单处理业务异常, orderId={}", message.getOrderId(), e);
            // 发送到死信队列或记录到补偿表
            deadLetterService.sendToDlq(message, e);
        } catch (Exception e) {
            // 系统异常，记录日志后消费成功，由死信机制兜底
            log.error("订单处理系统异常, orderId={}", message.getOrderId(), e);
            deadLetterService.sendToDlq(message, e);
        }
    }
}
```

### 检查要点

- 消费方法体内必须有 try-catch 块
- 业务异常（BusinessException）不应触发 MQ 重试，应直接消费成功并记录
- 系统异常（如网络超时）可返回 RECONSUME_LATER 触发有限次重试
- 所有异常路径都必须有日志记录

---

## MQ-CONS-003: Consumer 必须设置合理的并发消费线程数

Consumer 必须显式配置 `consumeThreadMin`/`consumeThreadMax` 或 `concurrency` 属性，禁止使用默认值在生产环境运行。

### 错误示例

```java
// 错误：未配置并发线程数，使用框架默认值
@RocketMQMessageListener(
    consumerGroup = "order-service-consumer-group",
    topic = "order-topic"
)
public class OrderConsumer implements RocketMQListener<OrderMessage> {
    // ...
}
```

### 正确示例

```java
// 正确：显式配置并发消费线程数
@RocketMQMessageListener(
    consumerGroup = "order-service-consumer-group",
    topic = "order-topic",
    consumeThreadMin = 2,
    consumeThreadMax = 4
)
public class OrderConsumer implements RocketMQListener<OrderMessage> {
    // ...
}
```

### 检查要点

- 并发线程数需根据下游服务承受能力设定，不建议超过 10
- IO 密集型任务可适当增大，CPU 密集型任务应减小
- 线程数配置需与下游数据库连接池 / 线程池匹配，避免资源耗尽
