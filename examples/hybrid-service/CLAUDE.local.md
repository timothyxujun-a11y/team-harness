# hybrid-service-example 本地规则

> 本文件为项目级 AI 协作规则，与 `.harness/local/` 下的业务说明和架构文档配合使用。
> AI 助手在本项目中工作时应优先遵循本文件。

## 项目身份

- **项目名称**: hybrid-service-example
- **模块/职责**: 税金计算服务，同步 HTTP API + 异步 MQ 消息处理
- **技术栈**: Java 11 + Spring Boot 2.7.x + RocketMQ + Maven
- **基础包名**: `com.example.tax`

## 业务领域

### 税金计算

- 支持增值税（VAT）、消费税、附加税等多种税种计算
- 根据商品类目、交易金额、纳税人身份（一般纳税人/小规模纳税人）计算应纳税额
- 税率可配置，支持按地区、行业、商品类目维度配置不同税率

### 税率配置

- 税率数据存储在 DB 中，Redis 缓存热数据（TTL 1h）
- 税率变更通过 HTTP 接口触发，变更后异步推送通知到下游服务
- 税率生效时间支持立即生效和定时生效两种模式
- 税率查询支持按地区编码 + 商品类目编码精确匹配

### MQ 异步通知

- **消费**：接收订单服务发送的税金计算请求消息（Topic: `tax-calculate-request`），异步计算税金后回写结果
- **发送**：税金计算完成后发送通知消息（Topic: `tax-calculate-result`），通知订单服务更新订单税金
- 税率变更后发送广播消息（Topic: `tax-rate-change`），通知所有下游服务刷新本地缓存

## 双入口架构

```
controller（HTTP 同步入口）──► TaxCalculateService ──► TaxRateService
                                                        │
rocket（MQ 异步入口）──────► TaxMessageService  ───────┘
                                                    │
                                              mapper（数据访问）
```

### HTTP API（同步）

- `POST /api/v1/tax/calculate`：同步计算税金，返回计算结果
- `GET /api/v1/tax/rate`：查询税率配置
- `POST /api/v1/tax/rate`：更新税率配置（触发缓存刷新 + MQ 通知）
- HTTP 入口仅做参数接收、校验、调用 Service、组装响应

### MQ 消息（异步）

- Consumer：消费税金计算请求，异步计算后发送结果消息
- Producer：发送税金计算结果消息和税率变更通知消息
- Consumer 仅做消息反序列化、调用 Service，**禁止编写业务逻辑**

## 构建与验证

```bash
./mvnw clean compile -DskipTests    # 编译
./mvnw test                          # 全量测试
./mvnw test -Dtest=TaxCalculateServiceTest   # 指定测试类
./mvnw clean package -DskipTests     # 打包
```

## Java 11 限制

本项目运行在 Java 11 环境，**禁止使用以下 Java 12+ 特性**：

- `switch` 表达式（Java 14+，预览版 Java 12）
- `Record` 类（Java 14+）
- `Text Block` 文本块（Java 15+）
- `var` 关键字可用于局部变量类型推断（Java 11 支持，允许使用）
- `Stream.toList()`（Java 16+，使用 `Collectors.toList()` 替代）

## AI 行为补充

1. 修改税率配置逻辑时必须同步更新 Redis 缓存，并发送 MQ 通知
2. 税金计算精度必须使用 `BigDecimal`，**禁止使用 `double` / `float`**
3. HTTP 和 MQ 两个入口共用同一套 Service，避免逻辑重复
4. 税率查询优先走 Redis 缓存，缓存未命中再查 DB 并回写缓存
5. MQ 消费者必须实现幂等策略，避免重复计算
