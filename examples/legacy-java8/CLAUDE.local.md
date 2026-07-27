# legacy-java8-example 本地规则

> 本文件为项目级 AI 协作规则，与 `.harness/local/` 下的业务说明和架构文档配合使用。
> AI 助手在本项目中工作时应优先遵循本文件。

## 项目身份

- **项目名称**: legacy-java8-example
- **模块/职责**: 日终对账与报表生成定时任务服务
- **技术栈**: Java 8 + Spring Boot 2.3.x + Quartz + Maven
- **基础包名**: `com.example.job`

## 业务领域

### Quartz 调度

- 使用 Quartz Scheduler 管理所有定时任务，支持 Cron 表达式和 SimpleTrigger
- Job 存储方式：JDBC JobStore（集群模式），确保任务在集群中不重复执行
- 调度配置通过 `application.yml` 管理，支持动态启停任务
- 每个 Job 执行前记录执行日志（开始时间、参数、机器），执行后更新状态和耗时

### 分布式锁

- **Redis 分布式锁**：任务执行前获取锁，确保集群中只有一个节点执行
- 锁 Key：`job:lock:{jobName}:{jobGroup}`，TTL 略大于任务预估最大执行时间
- 获取锁失败时跳过执行并记录 INFO 日志（非异常）
- 锁释放：任务执行完成后主动释放（Lua 脚本确保原子性），TTL 作为兜底

### 批处理策略

- 大数据量任务采用分页处理，每页 500 条，避免内存溢出
- 处理过程中记录进度（已处理条数 / 总条数），支持断点续跑
- 单条数据处理失败不中断整批，记录错误日志后继续处理下一条
- 批次完成后汇总成功/失败数量，发送执行报告

### JUnit 4 测试

- 测试框架固定为 JUnit 4（`@Test`、`@Before`、`@RunWith`）
- 使用 Mockito（`@Mock`、`@InjectMocks`、`@RunWith(MockitoJUnitRunner.class)`）隔离依赖
- 断言使用 AssertJ（`assertThat(...).isEqualTo(...)`）
- **禁止使用 JUnit 5**（`@BeforeEach`、`@ExtendWith` 等）
- **禁止启动 Spring 容器**（无 `@SpringBootTest`、`@RunWith(SpringRunner.class)`）

## 定时任务清单

| 任务名称 | Cron 表达式 | 说明 | 超时时间 |
|----------|------------|------|----------|
| 日终对账 | `0 0 23 * * ?` | 每天 23:00 执行，对账当日交易数据 | 2h |
| 报表生成 | `0 30 0 * * ?` | 每天 00:30 执行，生成日报表 | 1h |
| 周报汇总 | `0 0 2 ? * MON` | 每周一 02:00 执行，汇总周报 | 3h |
| 月结归档 | `0 0 3 1 * ?` | 每月 1 日 03:00 执行，月结归档 | 4h |
| 数据清理 | `0 0 4 * * ?` | 每天 04:00 执行，清理过期数据 | 30min |

## 分层架构

```
job（Quartz Job 入口） → service（业务逻辑） → mapper（数据访问）
                          ↘ report（报表生成）
```

### Job 层

- 实现 `QuartzJobBean`，仅做参数解析、调用 Service、异常兜底
- Job 类必须标注 `@TraceIdLog`，注入 traceId
- Job 类**禁止编写业务逻辑**，仅作为调度入口

### Service 层

- 接口命名 `I*Service`，实现 `*ServiceImpl`
- 对账逻辑和报表生成逻辑集中在 Service 层
- 批处理方法需支持分页参数（`pageNum`、`pageSize`）

## 构建与验证

```bash
./mvnw clean compile -DskipTests    # 编译
./mvnw test                          # 全量测试
./mvnw test -Dtest=ReconcileServiceTest   # 指定测试类
./mvnw clean package -DskipTests     # 打包
```

## Java 8 限制

本项目运行在 Java 8 环境，**禁止使用以下 Java 9+ 特性**：

- `var` 关键字（Java 10+）
- `Record` 类（Java 14+）
- `switch` 表达式（Java 14+）
- `Text Block` 文本块（Java 15+）
- `Stream.toList()`（Java 16+）
- `List.of()` / `Map.of()` 工厂方法（Java 9+）
- `Optional.isEmpty()`（Java 11+，使用 `!optional.isPresent()` 替代）

使用 `Collections.singletonList()` / `Collections.unmodifiableList()` 等替代。

## AI 行为补充

1. 新增定时任务时必须配置分布式锁，确保集群安全
2. 批处理任务必须实现分页处理和断点续跑能力
3. 对账差异超过阈值（默认 0.01%）时必须告警并暂停后续流程
4. 报表生成涉及大数据量查询时，优先使用游标查询（MyBatis Cursor）避免 OOM
5. 修改 Job 调度时间时需评估对下游系统的影响
