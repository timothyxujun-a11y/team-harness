# Producer 封装规范

## MQ-PROD-001: Producer 发送必须封装统一的发送服务

禁止在业务代码中直接注入 `RocketMQTemplate`/`KafkaTemplate` 发送消息，必须通过统一的 `MqProducerService` 封装层发送，以便统一处理日志、Trace 和异常。

### 错误示例

```java
// 错误：业务代码直接注入 Template 发送消息
@Service
public class OrderService {

    @Autowired
    private RocketMQTemplate rocketMQTemplate;  // 禁止直接使用

    public void createOrder(OrderRequest request) {
        OrderMessage message = new OrderMessage(request.getOrderId(), "CREATED");
        // 直接调用，缺少统一日志和异常处理
        rocketMQTemplate.convertAndSend("order-topic", message);
    }
}
```

### 正确示例

```java
// 统一封装的消息发送服务
@Service
@Slf4j
public class MqProducerService {

    @Autowired
    private RocketMQTemplate rocketMQTemplate;

    /**
     * 同步发送消息
     */
    public <T> SendResult syncSend(String topic, String tag, T message) {
        String destination = StringUtils.isBlank(tag) ? topic : topic + ":" + tag;
        try {
            SendResult result = rocketMQTemplate.syncSend(destination, message);
            log.info("消息发送成功, topic={}, msgId={}, status={}",
                topic, result.getMsgId(), result.getSendStatus());
            return result;
        } catch (Exception e) {
            log.error("消息发送失败, topic={}, message={}", topic, message, e);
            throw new MqSendException("消息发送失败: " + topic, e);
        }
    }

    /**
     * 异步发送消息
     */
    public <T> void asyncSend(String topic, String tag, T message, SendCallback callback) {
        String destination = StringUtils.isBlank(tag) ? topic : topic + ":" + tag;
        rocketMQTemplate.asyncSend(destination, message, callback);
    }
}

// 业务代码通过封装层发送
@Service
public class OrderService {

    @Autowired
    private MqProducerService mqProducerService;

    public void createOrder(OrderRequest request) {
        OrderMessage message = new OrderMessage(request.getOrderId(), "CREATED");
        mqProducerService.syncSend("order-topic", "create", message);
    }
}
```

### 检查要点

- 业务代码中不应直接出现 `RocketMQTemplate` 或 `KafkaTemplate` 的注入
- 封装层必须包含日志记录（发送前/发送后/异常）
- 封装层应支持同步发送、异步发送、延迟发送等模式
- 建议在封装层集成 Trace ID 传递

---

## MQ-PROD-002: Producer 同步发送必须设置超时与重试次数

同步发送消息时必须显式设置 `timeout` 和 `retryTimes`，禁止使用默认超时值。异步发送必须提供回调处理失败场景。

### 错误示例

```java
// 错误：使用默认超时和重试次数
@Service
public class MqProducerService {

    @Autowired
    private RocketMQTemplate rocketMQTemplate;

    public void sendOrder(OrderMessage message) {
        // 未设置超时和重试次数
        rocketMQTemplate.convertAndSend("order-topic", message);
    }
}
```

### 正确示例

```java
// 正确：显式设置超时和重试次数
@Service
@Slf4j
public class MqProducerService {

    @Autowired
    private RocketMQTemplate rocketMQTemplate;

    private static final long SEND_TIMEOUT_MS = 3000L;
    private static final int RETRY_TIMES = 2;

    /**
     * 同步发送（带超时和重试）
     */
    public <T> SendResult syncSend(String topic, T message) {
        Message<T> mqMessage = MessageBuilder.withPayload(message).build();
        try {
            SendResult result = rocketMQTemplate.syncSend(
                topic,
                mqMessage,
                SEND_TIMEOUT_MS,
                RETRY_TIMES
            );
            log.info("消息发送成功, topic={}, msgId={}", topic, result.getMsgId());
            return result;
        } catch (Exception e) {
            log.error("消息发送失败, topic={}", topic, e);
            throw new MqSendException("消息发送失败", e);
        }
    }

    /**
     * 异步发送（带回调）
     */
    public <T> void asyncSend(String topic, T message) {
        Message<T> mqMessage = MessageBuilder.withPayload(message).build();
        rocketMQTemplate.asyncSend(topic, mqMessage, new SendCallback() {
            @Override
            public void onSuccess(SendResult sendResult) {
                log.info("异步消息发送成功, topic={}, msgId={}", topic, sendResult.getMsgId());
            }

            @Override
            public void onException(Throwable e) {
                log.error("异步消息发送失败, topic={}", topic, e);
                // 失败补偿：写入本地消息表，由定时任务重试
                localMessageService.saveForRetry(topic, message, e);
            }
        }, SEND_TIMEOUT_MS, RETRY_TIMES);
    }
}
```

### 检查要点

- 同步发送必须显式设置 timeout（建议 3000ms）
- 同步发送必须显式设置 retryTimes（建议 2 次）
- 异步发送必须实现 `SendCallback`，处理 `onSuccess` 和 `onException`
- 异步发送失败时应有补偿机制（如本地消息表 + 定时重试）
