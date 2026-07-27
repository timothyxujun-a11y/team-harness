# 业务说明 — mq-service-example

## 业务概述

本项目是一个基于 RocketMQ 的异步消息处理服务，核心职责是消费订单状态变更消息并执行后续通知流程。

---

## 消息流

```
订单服务 ──► RocketMQ (order-status-change)
                    │
                    ▼
            ┌───────────────┐
            │ OrderStatus   │  消费消息
            │ Consumer      │
            └───────┬───────┘
                    │
          ┌─────────┼─────────┐
          │         │         │
          ▼         ▼         ▼
    更新本地缓存  发送通知  触发下游
          │         │         │
          │         ▼         │
          │  RocketMQ          │
          │  (notification-send)
          │         │
          ▼         ▼
    ┌──────────┐  ┌──────────────┐
    │ DB 订单  │  │ 通知下游通道  │
    │ 缓存表   │  │ (短信/Push)   │
    └──────────┘  └──────────────┘
```

---

## 消息 Topic 与 Consumer Group

| Topic | Consumer Group | 说明 | Tags |
|-------|---------------|------|------|
| `order-status-change` | `order_status_cg` | 订单状态变更消息 | `PAID`、`SHIPPED`、`COMPLETED`、`CANCELLED` |
| `notification-send` | `notification_cg` | 通知发送消息 | `SMS`、`PUSH`、`EMAIL` |

### 消息体结构（order-status-change）

```json
{
  "orderId": "ORDER202607270001",
  "userId": "USER001",
  "oldStatus": "PENDING",
  "newStatus": "PAID",
  "eventTime": "2026-07-27T10:30:00.000+08:00",
  "traceId": "trace-abc-123",
  "extra": {
    "paymentMethod": "ALIPAY",
    "amount": 199.00
  }
}
```

### Schema 兼容性规则

1. 字段**只能新增**，不能删除或重命名
2. 新增字段必须有默认值（null 或空字符串）
3. 字段类型只能向后兼容（如 int → long 可以，long → int 不可以）
4. 消息体版本通过 `schemaVersion` 字段标识，当前为 `1`

---

## 消息幂等策略

### 幂等 Key 生成规则

```
msgKey = MD5(topic + ":" + orderId + ":" + newStatus + ":" + eventTime)
```

### 去重流程

```
消息到达
    │
    ▼
计算 msgKey
    │
    ▼
查询 Redis 幂等表（idempotent:{topic}:{msgKey}，TTL 24h）
    │
    ├── 存在 ──► 跳过，返回 CONSUME_SUCCESS
    │
    └── 不存在
        │
        ▼
    查询 DB 幂等表（msg_idempotent，唯一索引 topic + msg_key）
        │
        ├── 存在 ──► 跳过，返回 CONSUME_SUCCESS
        │
        └── 不存在
            │
            ▼
        执行业务逻辑
            │
            ▼
        写入 DB 幂等表 + Redis 幂等表
            │
            ▼
        返回 CONSUME_SUCCESS
```

### 降级策略

- **Redis 不可用**：降级为仅查 DB 幂等表（性能下降但保证正确性）
- **DB 不可用**：抛出可重试异常，触发 MQ 重试
- **Redis + DB 均不可用**：抛出可重试异常，触发 MQ 重试

---

## 重试配置

### 消费重试

| 参数 | 值 | 说明 |
|------|----|------|
| 最大重试次数 | 5 | 超过后进入死信队列 |
| 重试间隔 | 指数退避 | 1s → 5s → 10s → 30s → 1min |
| 消费超时 | 30s | 单条消息最长处理时间 |
| 并发消费线程数 | 20 | 根据 MQ 积压动态调整 |
| 拉取批次大小 | 32 | 每次从 Broker 拉取的消息数 |

### 重试异常分类

| 异常类型 | 是否重试 | 处理方式 |
|----------|----------|----------|
| DB 死锁 | 是 | 抛出，触发 MQ 自动重试 |
| 下游 RPC 超时 | 是 | 抛出，触发 MQ 自动重试 |
| 网络抖动 | 是 | 抛出，触发 MQ 自动重试 |
| 参数校验失败 | 否 | catch + WARN 日志 + 丢弃 |
| 消息格式错误 | 否 | catch + WARN 日志 + 丢弃 |
| 业务状态非法 | 否 | catch + WARN 日志 + 丢弃 |
| 空指针等代码 Bug | 否 | catch + ERROR 日志 + 丢弃（需修复代码） |

---

## 死信队列处理

### 死信队列配置

- 死信 Topic：`%DLQ%order_status_cg`
- 死信 Consumer Group：`DLQ_order_status_cg`

### 死信处理流程

```
消息超过最大重试次数
    │
    ▼
自动进入死信队列
    │
    ▼
告警系统检测到死信消息 → 发送钉钉/邮件告警
    │
    ▼
人工排查根因
    │
    ├── 可修复（如数据修复后重放）──► 从死信队列重放消息
    │
    └── 不可修复（如毒消息）──► 标记并归档，避免再次消费
```

---

## 事务消息

### 适用场景

涉及「本地事务 + 消息发送」的场景使用 RocketMQ 事务消息，确保最终一致性。

### 事务消息流程

```
Producer 发送半消息（half message）
    │
    ▼
RocketMQ 存储半消息（消费者不可见）
    │
    ▼
执行本地事务
    │
    ├── 成功 ──► 提交半消息（消费者可见）
    │
    ├── 失败 ──► 回滚半消息（删除）
    │
    └── 超时/未知 ──► RocketMQ 回查本地事务状态
                        │
                        ├── 事务已提交 ──► 提交半消息
                        └── 事务未提交 ──► 回滚半消息
```

### 事务回查

- 回查超时：60s 后开始回查
- 回查次数：最多 5 次
- 回查实现：`TransactionListener` 接口，根据本地事务表状态返回 `COMMIT` / `ROLLBACK` / `UNKNOWN`
