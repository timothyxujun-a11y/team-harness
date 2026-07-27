# mq-service-example 本地规则

> 本文件为项目级 AI 协作规则，与 `.harness/local/` 下的业务说明和架构文档配合使用。
> AI 助手在本项目中工作时应优先遵循本文件。

## 项目身份

- **项目名称**: mq-service-example
- **模块/职责**: 订单状态变更异步通知服务
- **技术栈**: Java 8 + Spring Boot 2.x + RocketMQ + Maven
- **基础包名**: `com.example.mq`

## 业务领域

### RocketMQ 消息处理

- 消费订单状态变更消息（Topic: `order-status-change`），处理订单支付、发货、完成等状态变更通知
- 消费消息后执行：更新本地订单缓存、发送通知（短信/Push）、触发下游业务流程
- Producer 发送消息到 `notification-send` Topic，通知下游通道下发

### 消息幂等策略

- **幂等 key**：`topic + msgKey`（msgKey 为订单号 + 状态 + 时间戳的哈希）
- **去重机制**：消费前查询 Redis 幂等表（`idempotent:{topic}:{msgKey}`，TTL 24h），存在则跳过
- **兜底**：Redis 不可用时降级查 DB 幂等表（`msg_idempotent` 表，唯一索引 `topic + msg_key`）
- **事务消息**：涉及本地事务 + 消息发送的场景使用 RocketMQ 事务消息，确保最终一致性

### 重试配置

| 参数 | 值 | 说明 |
|------|----|------|
| 最大重试次数 | 5 | 超过后进入死信队列 |
| 重试间隔 | 指数退避 | 1s → 5s → 10s → 30s → 1min |
| 消费超时 | 30s | 单条消息最长处理时间 |
| 死信处理 | 人工介入 | 死信队列告警 + Dashboard 查看 |
| 并发消费线程数 | 20 | 根据 MQ 积压动态调整 |

### 异常分类

| 类型 | 处理方式 | 示例 |
|------|----------|------|
| 可重试异常 | 抛出，触发 MQ 自动重试 | DB 死锁、下游超时、网络抖动 |
| 不可重试异常 | catch + WARN 日志 + 丢弃 | 参数校验失败、消息格式错误、业务状态非法 |
| 死信 | 超过最大重试次数后自动进入死信队列 | 持续失败的消息 |

## 分层架构

```
rocket（MQ 消费入口） → service（业务逻辑） → mapper（数据访问）
                        ↘ entity（数据模型）
                        ↘ producer（消息发送）
```

### Consumer 层

- 使用 `@RocketMQMessageListener` 注解声明消费者
- Consumer 仅做消息反序列化、参数校验、调用 Service，**禁止编写业务逻辑**
- 每个 Consumer 方法必须标注 `@TraceIdLog`，注入 traceId 到 MDC

### Producer 层

- 封装 `RocketMQTemplate`，统一发送入口
- 发送消息时设置 `msgKey`（幂等 key）和 `tags`（业务标签）
- 发送失败按语义处理：可重试异常抛出由上游重试，不可重试异常落库补偿

## 构建与验证

```bash
./mvnw clean compile -DskipTests    # 编译
./mvnw test                          # 全量测试
./mvnw test -Dtest=OrderMessageServiceTest   # 指定测试类
./mvnw clean package -DskipTests     # 打包
```

## Java 8 限制

本项目运行在 Java 8 环境，**禁止使用以下 Java 9+ 特性**：

- `var` 关键字（Java 10+）
- `Record` 类（Java 14+）
- `switch` 表达式（Java 14+）
- `Text Block` 文本块（Java 15+）
- `Stream.toList()`（Java 16+）
- `Optional.orElseThrow()` 无参版本（Java 10+）
- `List.of()` / `Map.of()` 工厂方法（Java 9+）

使用 `Collections.singletonList()` / `Collections.unmodifiableList()` 等替代。

## AI 行为补充

1. 新增 Consumer 时必须配置幂等策略，不可遗漏
2. 修改消息体结构时需检查 Schema 兼容性（只增不删，字段加默认值）
3. Producer 发送消息必须设置 traceId 传递，保持全链路追踪
4. 涉及事务消息时，本地事务和消息发送必须保证最终一致性
