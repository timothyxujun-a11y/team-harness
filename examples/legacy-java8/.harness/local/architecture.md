# 项目架构说明 — legacy-java8-example

## 技术选型

| 维度 | 选型 | 版本 |
|------|------|------|
| 语言 | Java | 8 |
| 框架 | Spring Boot | 2.3.x |
| 任务调度 | Quartz | 2.3.x |
| 构建工具 | Maven | 3.6+ |
| ORM | MyBatis-Plus | 3.5.x |
| 缓存 | Redis (Lettuce) | Spring Data Redis 2.3.x |
| Excel 处理 | Apache POI | 5.2.x（SXSSF 流式写入） |
| 测试框架 | JUnit 4 + Mockito + AssertJ | — |
| 覆盖率 | JaCoCo + diff-cover | 0.8.x |
| 链路追踪 | 自定义 AOP + MDC | — |

## 包结构

```
com.example.job
├── job/                              # Quartz Job 入口层
│   ├── ReconcileJob.java                      # 日终对账任务
│   ├── ReportJob.java                         # 报表生成任务
│   ├── WeeklyReportJob.java                   # 周报汇总任务
│   ├── MonthlyArchiveJob.java                 # 月结归档任务
│   └── DataCleanupJob.java                    # 数据清理任务
├── service/                          # 业务逻辑层
│   ├── reconcile/
│   │   ├── IReconcileService.java             # 对账服务接口
│   │   └── impl/
│   │       └── ReconcileServiceImpl.java      # 对账服务实现
│   ├── report/
│   │   ├── IReportService.java                # 报表服务接口
│   │   └── impl/
│   │       └── ReportServiceImpl.java         # 报表服务实现
│   ├── archive/
│   │   ├── IArchiveService.java               # 归档服务接口
│   │   └── impl/
│   │       └── ArchiveServiceImpl.java        # 归档服务实现
│   ├── cleanup/
│   │   └── CleanupService.java                # 数据清理服务
│   └── progress/
│       └── JobProgressService.java            # 任务进度服务（断点续跑）
├── mapper/                           # 数据访问层
│   ├── TransactionMapper.java
│   ├── ReconcileDiffMapper.java
│   ├── JobExecutionLogMapper.java
│   ├── JobProgressMapper.java
│   └── ArchiveTransactionMapper.java
├── entity/                           # 数据库实体
│   ├── Transaction.java
│   ├── ReconcileDiff.java
│   ├── JobExecutionLog.java
│   ├── JobProgress.java
│   └── ReportMetadata.java
├── dto/                              # 数据传输对象
│   ├── ReconcileResultDTO.java
│   ├── ReportConfigDTO.java
│   └── JobExecutionParam.java
├── lock/                             # 分布式锁
│   ├── DistributedLockService.java             # Redis 分布式锁服务
│   └── LockResult.java
├── config/                           # 配置类
│   ├── QuartzConfig.java                       # Quartz 调度器配置
│   ├── RedisConfig.java
│   ├── QuartzProperties.java                   # Quartz 配置属性
│   └── JobProperties.java                      # 任务参数配置
├── trace/                            # 链路追踪
│   ├── TraceIdLog.java
│   └── LogTraceIdAspect.java
├── common/                           # 通用组件
│   ├── exception/
│   │   ├── BusinessException.java
│   │   └── JobExecutionException.java
│   ├── constant/
│   │   ├── JobConstant.java                    # 任务名称、锁 Key 常量
│   │   └── ReportConstant.java
│   └── alert/
│       └── AlertService.java                   # 告警通知服务
└── Application.java                  # 启动类
```

## 分层依赖方向

```
job（Quartz 入口） → service → mapper → entity
                       │
                       ├── lock（分布式锁）
                       ├── progress（断点续跑）
                       └── alert（告警通知）
```

**禁止反向依赖**：mapper 不得引用 service，entity 不得引用上层。

## Quartz 集群配置

### JDBC JobStore

```yaml
# application.yml
spring:
  quartz:
    job-store-type: jdbc
    properties:
      org.quartz.scheduler.instanceName: JobScheduler
      org.quartz.scheduler.instanceId: AUTO
      org.quartz.jobStore.isClustered: true
      org.quartz.jobStore.clusterCheckinInterval: 20000
      org.quartz.jobStore.tablePrefix: QRTZ_
      org.quartz.threadPool.threadCount: 10
      org.quartz.threadPool.threadPriority: 5
```

### 集群工作原理

```
节点 A                    节点 B                    节点 C
  │                         │                         │
  └─────── QRTZ_LOCKS ──────┴─────────────────────────┘
                     │
                     ▼
            数据库行锁（SELECT ... FOR UPDATE）
                     │
         ┌───────────┼───────────┐
         │           │           │
    节点 A 获取锁  节点 B 等待   节点 C 等待
         │
         ▼
    执行 Job
         │
         ▼
    释放锁
                     │
              节点 B/C 可获取下一个 Job
```

- 同一 Job 在集群中只有一个节点执行
- 节点故障时，其他节点自动接管（通过 `clusterCheckinInterval` 检测）
- Job 执行状态持久化到 DB，重启后可恢复

## 分布式锁

### Redis 锁实现

```
Job 执行前
    │
    ▼
DistributedLockService.tryLock(key, ttl)
    │
    ├── 获取成功（SET NX EX）
    │     │
    │     ▼
    │   执行 Job 逻辑
    │     │
    │     ├── 完成 ──► 释放锁（Lua 脚本：校验 value + DEL）
    │     │
    │     └── 异常 ──► finally 块释放锁
    │
    └── 获取失败
          │
          ▼
      记录 INFO 日志："其他节点正在执行，跳过"
          │
          ▼
      正常返回（不抛异常）
```

### 锁 Key 与 TTL

| Job | Lock Key | TTL |
|-----|----------|-----|
| 日终对账 | `job:lock:reconcile:daily` | 2.5h |
| 报表生成 | `job:lock:report:daily` | 1.5h |
| 周报汇总 | `job:lock:report:weekly` | 3.5h |
| 月结归档 | `job:lock:archive:monthly` | 4.5h |
| 数据清理 | `job:lock:cleanup:daily` | 35min |

## 配置管理

| 配置类型 | 管理方式 |
|----------|----------|
| Quartz 参数 | `QuartzProperties` + `@ConfigurationProperties` |
| 任务参数（超时、重试、阈值） | `JobProperties` + `@ConfigurationProperties` |
| Redis 参数 | `application.yml` + 环境变量 |
| 敏感信息 | 环境变量 / 配置中心 |
| 分页大小 | `JobConstant.DEFAULT_PAGE_SIZE = 500` |

## 测试架构

```
src/test/java/com/example/job
├── service/
│   ├── reconcile/
│   │   └── ReconcileServiceImplTest.java       # 对账逻辑单测（Mock Mapper）
│   ├── report/
│   │   └── ReportServiceImplTest.java           # 报表生成单测
│   └── archive/
│       └── ArchiveServiceImplTest.java          # 归档逻辑单测
├── lock/
│   └── DistributedLockServiceTest.java          # 分布式锁单测（Mock Redis）
└── job/
    └── ReconcileJobTest.java                     # Job 入口薄层测试（Mock Service）
```

### 测试规范

- 框架：JUnit 4 + Mockito + AssertJ
- 命名：`should期望行为When条件`（如 `shouldReturnDiffWhenLocalHasExtraRecord`）
- 结构：Arrange / Act / Assert 三段式
- **禁止启动 Spring 容器**（无 `@SpringBootTest`、`@RunWith(SpringRunner.class)`）
- 核心对账逻辑和归档逻辑**强制 TDD**
- 增量覆盖率阈值：80%

### 测试示例

```java
@RunWith(MockitoJUnitRunner.class)
public class ReconcileServiceImplTest {

    @Mock
    private TransactionMapper transactionMapper;

    @Mock
    private ReconcileDiffMapper reconcileDiffMapper;

    @InjectMocks
    private ReconcileServiceImpl reconcileService;

    @Test
    public void shouldRecordDiffWhenLocalAmountMismatch() {
        // Arrange
        Transaction local = new Transaction();
        local.setId(1L);
        local.setAmount(new BigDecimal("100.00"));
        local.setChannelTxnId("CH001");

        ChannelReceipt channel = new ChannelReceipt();
        channel.setTxnId("CH001");
        channel.setAmount(new BigDecimal("99.00"));

        when(transactionMapper.selectById(1L)).thenReturn(local);
        when(channelReceiptMapper.selectByTxnId("CH001")).thenReturn(channel);

        // Act
        ReconcileResultDTO result = reconcileService.reconcileSingle(local, channel);

        // Assert
        assertThat(result.isMatched()).isFalse();
        assertThat(result.getDiffType()).isEqualTo("AMOUNT_MISMATCH");
        assertThat(result.getDiffAmount()).isEqualByComparingTo("1.00");
    }
}
```
