# 项目架构说明 — mq-service-example

## 技术选型

| 维度 | 选型 | 版本 |
|------|------|------|
| 语言 | Java | 8 |
| 框架 | Spring Boot | 2.7.x |
| 消息队列 | RocketMQ | 5.x（Client 2.7.x） |
| 构建工具 | Maven | 3.6+ |
| ORM | MyBatis-Plus | 3.5.x |
| 缓存 | Redis (Lettuce) | Spring Data Redis 2.7.x |
| 测试框架 | JUnit 4 + Mockito + AssertJ | — |
| 覆盖率 | JaCoCo + diff-cover | 0.8.x |
| 链路追踪 | 自定义 AOP + MDC | — |

## 包结构

```
com.example.mq
├── rocket/                         # RocketMQ 消费入口层
│   ├── consumer/
│   │   ├── OrderStatusConsumer.java         # 订单状态变更消费者
│   │   └── NotificationConsumer.java         # 通知发送消费者
│   └── producer/
│       ├── OrderMessageProducer.java         # 订单消息生产者
│       └── NotificationProducer.java         # 通知消息生产者
├── service/                        # 业务逻辑层
│   ├── order/
│   │   ├── IOrderMessageService.java         # 订单消息处理接口
│   │   └── impl/
│   │       └── OrderMessageServiceImpl.java  # 订单消息处理实现
│   ├── notification/
│   │   ├── INotificationService.java
│   │   └── impl/
│   │       └── NotificationServiceImpl.java
│   └── idempotent/
│       ├── IdempotentService.java            # 幂等服务
│       └── impl/
│           └── IdempotentServiceImpl.java
├── mapper/                         # 数据访问层
│   ├── OrderCacheMapper.java
│   ├── MsgIdempotentMapper.java
│   └── NotificationLogMapper.java
├── entity/                         # 数据库实体
│   ├── OrderCache.java
│   ├── MsgIdempotent.java
│   └── NotificationLog.java
├── dto/                            # 消息载荷与传输对象
│   ├── OrderStatusChangeDTO.java             # 订单状态变更消息体
│   ├── NotificationSendDTO.java              # 通知发送消息体
│   └── OrderStatusEnum.java
├── config/                         # 配置类
│   ├── RocketMQConfig.java                   # RocketMQ 配置
│   ├── RedisConfig.java
│   └── RocketMQProperties.java               # MQ 配置属性
├── trace/                          # 链路追踪（独立包）
│   ├── TraceIdLog.java                       # @TraceIdLog 注解
│   ├── LogTraceIdAspect.java                 # AOP 切面
│   └── TraceUtils.java
├── common/                         # 通用组件
│   ├── exception/
│   │   ├── BusinessException.java
│   │   └── MessageRetryableException.java    # 可重试异常
│   ├── constant/
│   │   └── MqConstant.java                   # Topic/Group 常量
│   └── response/
│       └── MessageResult.java                # 消息处理结果
└── Application.java                # 启动类
```

## 分层依赖方向

```
rocket（MQ 入口） → service → mapper → entity
                       │
                       ├── idempotent（幂等检查）
                       └── trace（链路追踪，AOP 横切）
```

**禁止反向依赖**：mapper 不得引用 service，entity 不得引用上层。

## RocketMQ 集成

### Consumer 配置

```java
@RocketMQMessageListener(
    topic = MqConstant.TOPIC_ORDER_STATUS_CHANGE,
    consumerGroup = MqConstant.CG_ORDER_STATUS,
    selectorExpression = "PAID || SHIPPED || COMPLETED || CANCELLED",
    consumeMode = ConsumeMode.CONCURRENTLY,
    consumeThreadMax = 20,
    consumeTimeout = 30000L
)
public class OrderStatusConsumer implements RocketMQListener<String> {

    @Override
    @TraceIdLog
    public void onMessage(String message) {
        // 1. 反序列化
        OrderStatusChangeDTO dto = JSON.parseObject(message, OrderStatusChangeDTO.class);
        // 2. 参数校验
        validate(dto);
        // 3. 调用 Service（薄层，无业务逻辑）
        orderMessageService.handleStatusChange(dto);
    }
}
```

### Producer 封装

```java
@Component
public class NotificationProducer {

    public void send(NotificationSendDTO dto) {
        Message<String> msg = MessageBuilder
            .withPayload(JSON.toJSONString(dto))
            .setHeader(Keys.KEYS, dto.buildMsgKey())
            .setHeader(MessageConst.PROPERTY_TAGS, dto.getTag())
            .build();
        rocketMQTemplate.syncSend(MqConstant.TOPIC_NOTIFICATION_SEND, msg);
    }
}
```

## 链路追踪

### traceId 传递机制

```
MQ 入口（Consumer）
    │ @TraceIdLog 注解
    ▼
LogTraceIdAspect（@Around）
    │ 生成或继承消息中的 traceId
    │ MDC.put("traceId", traceId)
    ▼
Service / Mapper / Producer
    │ log 中自动携带 traceId（logback pattern: %X{traceId}）
    ▼
Producer 发送下游消息
    │ 消息体中携带 traceId 字段
    ▼
下游 Consumer 继承同一 traceId
```

## 配置管理

| 配置类型 | 管理方式 | 示例 |
|----------|----------|------|
| MQ 参数（Topic/Group/NameServer） | `RocketMQProperties` + `@ConfigurationProperties` | `rocketmq.name-server=...` |
| 消费参数（线程数/超时/重试） | `RocketMQProperties` | `rocketmq.consumer.consume-thread-max=20` |
| Redis 参数 | `application.yml` + 环境变量 | `spring.redis.host=...` |
| 敏感信息（AccessKey/SecretKey） | 环境变量 / 配置中心 | 禁止写入代码和配置文件 |
| 业务参数（幂等 TTL 等） | `@ConfigurationProperties` | `mq.idempotent.ttl=86400` |

## 测试架构

```
src/test/java/com/example/mq
├── service/
│   ├── order/
│   │   └── OrderMessageServiceImplTest.java   # 纯单测，Mock Mapper + IdempotentService
│   └── idempotent/
│       └── IdempotentServiceImplTest.java      # 纯单测，Mock Redis + Mapper
├── rocket/
│   └── consumer/
│       └── OrderStatusConsumerTest.java        # Mock Service，验证薄层逻辑
└── rocket/
    └── producer/
        └── NotificationProducerTest.java       # Mock RocketMQTemplate
```

- 所有测试为纯单元测试，**禁止启动 Spring 容器**
- Consumer 测试仅验证：消息反序列化、参数校验、Service 调用
- Service 测试 Mock Mapper 和 IdempotentService，验证业务逻辑和异常处理
- 增量覆盖率阈值：80%
