# Spring MQ 开发规范

## 概述

本 Profile 定义了 Spring 项目中消息队列（RocketMQ / Kafka）的开发规范，覆盖 Consumer 入口、Producer 封装、消息幂等、重试与死信处理、消息 Schema 兼容性五个维度。

适用于使用 Spring Boot + RocketMQ/Kafka 的 Java 项目，兼容 Java 8/11/17/21。

## 依赖

- `java-common` — Java 通用编码规范

## 规则总览

| 规则 ID | 标题 | 严重级别 | 规则文件 |
|---------|------|----------|----------|
| MQ-CONS-001 | Consumer 必须显式声明消费组与 Topic | error | rules/consumer.md |
| MQ-CONS-002 | Consumer 消费逻辑必须捕获异常并返回状态 | error | rules/consumer.md |
| MQ-CONS-003 | Consumer 必须设置合理的并发消费线程数 | warning | rules/consumer.md |
| MQ-PROD-001 | Producer 发送必须封装统一的发送服务 | error | rules/producer.md |
| MQ-PROD-002 | Producer 同步发送必须设置超时与重试次数 | error | rules/producer.md |
| MQ-IDEMP-001 | Consumer 必须实现幂等性校验 | error | rules/idempotency.md |
| MQ-IDEMP-002 | 幂等键必须使用业务唯一标识而非 msgId | warning | rules/idempotency.md |
| MQ-RETRY-001 | 必须配置合理的重试次数与退避策略 | error | rules/retry.md |
| MQ-RETRY-002 | 必须实现死信队列监控与告警 | error | rules/retry.md |
| MQ-SCHEMA-001 | 消息体 Schema 变更必须保持向后兼容 | error | rules/schema.md |

## 适用场景

- 新功能开发（feature-development）
- 代码重构（refactor）
- 代码评审（code-review）
