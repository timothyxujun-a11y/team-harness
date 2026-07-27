# 项目架构说明 — hybrid-service-example

## 技术选型

| 维度 | 选型 | 版本 |
|------|------|------|
| 语言 | Java | 11 |
| 框架 | Spring Boot | 2.7.x |
| 消息队列 | RocketMQ | 5.x（Client 2.7.x） |
| 构建工具 | Maven | 3.6+ |
| ORM | MyBatis-Plus | 3.5.x |
| 缓存 | Redis (Lettuce) | Spring Data Redis 2.7.x |
| 对象映射 | MapStruct | 1.5.x |
| 测试框架 | JUnit 4 + Mockito + AssertJ | — |
| 覆盖率 | JaCoCo + diff-cover | 0.8.x |
| 链路追踪 | 自定义 AOP + MDC | — |

## 包结构

```
com.example.tax
├── controller/                        # HTTP 入口层
│   ├── TaxCalculateController.java             # 税金计算接口
│   └── TaxRateController.java                  # 税率配置接口
├── rocket/                            # MQ 入口层
│   ├── consumer/
│   │   └── TaxCalculateRequestConsumer.java    # 税金计算请求消费者
│   └── producer/
│       ├── TaxCalculateResultProducer.java     # 税金计算结果生产者
│       └── TaxRateChangeProducer.java          # 税率变更通知生产者
├── service/                           # 业务逻辑层
│   ├── calculate/
│   │   ├── ITaxCalculateService.java           # 税金计算接口
│   │   └── impl/
│   │       └── TaxCalculateServiceImpl.java    # 税金计算实现
│   ├── rate/
│   │   ├── ITaxRateService.java                # 税率查询/管理接口
│   │   └── impl/
│   │       └── TaxRateServiceImpl.java         # 税率查询/管理实现
│   ├── message/
│   │   ├── ITaxMessageService.java             # MQ 消息处理接口
│   │   └── impl/
│   │       └── TaxMessageServiceImpl.java      # MQ 消息处理实现
│   └── idempotent/
│       └── IdempotentService.java              # 幂等服务
├── mapper/                            # 数据访问层
│   ├── TaxRateMapper.java
│   ├── TaxRateHistoryMapper.java
│   └── MsgIdempotentMapper.java
├── entity/                            # 数据库实体
│   ├── TaxRate.java
│   ├── TaxRateHistory.java
│   └── MsgIdempotent.java
├── dto/                               # 数据传输对象
│   ├── calculate/
│   │   ├── TaxCalculateRequestDTO.java         # HTTP 计算请求
│   │   ├── TaxCalculateResultVO.java           # HTTP 计算结果
│   │   └── TaxCalculateMessageDTO.java         # MQ 计算消息体
│   ├── rate/
│   │   ├── TaxRateQueryDTO.java
│   │   ├── TaxRateUpdateDTO.java
│   │   └── TaxRateVO.java
│   └── enums/
│       ├── TaxTypeEnum.java
│       └── TaxpayerTypeEnum.java
├── convert/                           # 对象转换器
│   ├── TaxRateConvert.java
│   └── TaxCalculateConvert.java
├── config/                            # 配置类
│   ├── RocketMQConfig.java
│   ├── RedisConfig.java
│   ├── RocketMQProperties.java
│   └── TaxProperties.java
├── trace/                             # 链路追踪
│   ├── TraceIdLog.java
│   └── LogTraceIdAspect.java
├── common/                            # 通用组件
│   ├── exception/
│   │   ├── BusinessException.java
│   │   └── GlobalExceptionHandler.java
│   ├── response/
│   │   └── ApiResponse.java
│   └── constant/
│       ├── MqConstant.java
│       └── TaxConstant.java
└── Application.java                   # 启动类
```

## 双入口架构

### HTTP 同步流程

```
HTTP 请求
    │
    ▼
Controller（参数接收 + 校验）
    │
    ▼
TaxCalculateService.calculate()    ← 共用 Service
    │
    ├── TaxRateService.getRate()   ← 查询税率（Redis 优先）
    │       │
    │       ├── Redis 命中 ──► 返回
    │       └── Redis 未命中 ──► DB 查询 ──► 回写 Redis
    │
    ▼
计算税金（BigDecimal 精度）
    │
    ▼
返回 ApiResponse<TaxCalculateResultVO>
```

### MQ 异步流程

```
MQ 消息到达
    │
    ▼
TaxCalculateRequestConsumer（反序列化 + 校验）
    │  @TraceIdLog
    ▼
TaxMessageService.handleCalculateRequest()    ← 共用 Service
    │
    ├── IdempotentService.check()             ← 幂等检查
    │
    ├── TaxCalculateService.calculate()       ← 复用同一计算逻辑
    │       │
    │       └── TaxRateService.getRate()
    │
    ▼
TaxCalculateResultProducer.send()             ← 发送结果消息
    │
    ▼
IdempotentService.mark()                      ← 标记已处理
```

### 共用 Service 设计

HTTP 和 MQ 两个入口共用 `TaxCalculateService` 和 `TaxRateService`，避免逻辑重复：

```
controller ──► TaxCalculateService ◄── rocket.consumer
                      │
                      └──► TaxRateService
                              │
                              └──► Redis / Mapper
```

## 缓存架构

### Redis Key 设计

| Key | 用途 | TTL | 示例 |
|-----|------|-----|------|
| `tax:rate:{taxType}:{region}:{category}:{taxpayerType}` | 税率缓存 | 1h | `tax:rate:VAT:110000:ELECTRONICS:GENERAL` |
| `idempotent:{topic}:{msgKey}` | 消息幂等 | 72h | `idempotent:tax-calculate-request:abc123` |
| `tax:rate:lock:{region}:{category}` | 税率更新分布式锁 | 30s | `tax:rate:lock:110000:ELECTRONICS` |

### 缓存一致性

1. 税率变更时先更新 DB，再删除 Redis 缓存（Cache-Aside 模式）
2. 删除缓存失败时记录日志并重试（最多 3 次）
3. 缓存击穿保护：DB 查询返回 null 时写入空值标记（TTL 5min），防止穿透

## 链路追踪

- HTTP 入口：通过 Spring Interceptor 注入 traceId 到 MDC
- MQ 入口：通过 `@TraceIdLog` AOP 注入 traceId（继承消息中的 traceId 或生成新的）
- 全链路：logback pattern 含 `%X{traceId}`，Producer 发送消息时携带 traceId 字段

## 配置管理

| 配置类型 | 管理方式 |
|----------|----------|
| MQ 参数 | `RocketMQProperties` + `@ConfigurationProperties` |
| Redis 参数 | `application.yml` + 环境变量 |
| 业务参数（缓存 TTL、重试次数等） | `TaxProperties` + `@ConfigurationProperties` |
| 税率默认值 | `TaxConstant` 常量类 |
| 敏感信息 | 环境变量 / 配置中心 |

## 测试架构

```
src/test/java/com/example/tax
├── service/
│   ├── calculate/
│   │   └── TaxCalculateServiceImplTest.java    # 核心计算逻辑单测
│   ├── rate/
│   │   └── TaxRateServiceImplTest.java         # 税率查询/缓存单测
│   └── message/
│       └── TaxMessageServiceImplTest.java      # MQ 消息处理单测
├── controller/
│   └── TaxCalculateControllerTest.java          # MockMvc 测试
└── rocket/
    └── consumer/
        └── TaxCalculateRequestConsumerTest.java # Consumer 薄层测试
```

- 税金计算逻辑为核心业务，**强制 TDD**（红-绿-重构）
- 所有测试为纯单元测试，禁止启动 Spring 容器
- 税金计算精度测试：覆盖边界值（0 元、极大金额、精度截断等）
- 增量覆盖率阈值：80%
