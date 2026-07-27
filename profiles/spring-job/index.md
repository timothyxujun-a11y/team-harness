# Spring Job 开发规范

## 概述

本 Profile 定义了 Spring 项目中定时任务（Job）的开发规范，覆盖 Job 入口、分布式锁、批处理、失败重试与断点续跑四个维度。

适用于使用 Spring Boot + XXL-JOB/ElasticJob 的 Java 项目，兼容 Java 8/11/17/21。

## 依赖

- `java-common` — Java 通用编码规范

## 规则总览

| 规则 ID | 标题 | 严重级别 | 规则文件 |
|---------|------|----------|----------|
| JOB-ENTRY-001 | Job 必须使用统一调度框架而非原生 @Scheduled | error | rules/job-entry.md |
| JOB-ENTRY-002 | Job 执行入口必须记录执行日志与执行结果 | error | rules/job-entry.md |
| JOB-LOCK-001 | 分布式 Job 必须获取分布式锁防止重复执行 | error | rules/distributed-lock.md |
| JOB-LOCK-002 | 分布式锁必须设置合理的超时与自动续期 | error | rules/distributed-lock.md |
| JOB-BATCH-001 | 批量处理必须分页执行，禁止一次性加载全量数据 | error | rules/batch.md |
| JOB-BATCH-002 | 批处理必须记录处理进度，支持断点续跑 | error | rules/batch.md |
| JOB-RETRY-001 | Job 失败必须支持重试并保留执行上下文 | error | rules/retry.md |

## 适用场景

- 新功能开发（feature-development）
- 代码重构（refactor）
- 代码评审（code-review）
