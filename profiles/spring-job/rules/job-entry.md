# Job 入口规范

## JOB-ENTRY-001: Job 必须使用统一调度框架而非原生 @Scheduled

定时任务必须使用 XXL-JOB / ElasticJob 等分布式调度框架，禁止在生产环境使用 Spring 原生 `@Scheduled` 注解（无法动态调度、无执行日志、无失败告警）。

### 错误示例

```java
// 错误：使用 @Scheduled，无法动态调度、无执行日志、无失败告警
@Component
public class OrderSyncJob {

    @Scheduled(cron = "0 0 2 * * ?")
    public void syncOrders() {
        orderService.syncOrdersFromExternal();
    }
}
```

### 正确示例（XXL-JOB）

```java
// 正确：使用 XXL-JOB 统一调度框架
@Component
@Slf4j
public class OrderSyncJob {

    @Autowired
    private OrderService orderService;

    @XxlJob("orderSyncJobHandler")
    public void syncOrders() {
        log.info("订单同步任务开始执行");
        try {
            int count = orderService.syncOrdersFromExternal();
            log.info("订单同步任务执行完成, 同步数量={}", count);
        } catch (Exception e) {
            log.error("订单同步任务执行失败", e);
            throw e;  // 抛出异常，XXL-JOB 会记录失败状态并触发告警
        }
    }
}
```

### 正确示例（ElasticJob）

```java
// 正确：使用 ElasticJob 分布式调度
@Component
public class OrderSyncJob implements SimpleJob {

    @Autowired
    private OrderService orderService;

    @Override
    public void execute(ShardingContext shardingContext) {
        int shardIndex = shardingContext.getShardingItem();
        int shardTotal = shardingContext.getShardingTotalCount();
        log.info("订单同步任务开始, 分片: {}/{}", shardIndex, shardTotal);

        orderService.syncOrdersByShard(shardIndex, shardTotal);
    }
}
```

### 检查要点

- 生产环境禁止使用 `@Scheduled` 注解
- Job 必须通过 XXL-JOB / ElasticJob 等调度框架注册
- Job handler 命名需有语义（如 `orderSyncJobHandler`）
- 单个 Job 类只负责一个业务任务，禁止一个类中堆叠多个不相关 Job

---

## JOB-ENTRY-002: Job 执行入口必须记录执行日志与执行结果

Job 执行方法必须记录开始时间、结束时间、处理数据量、成功/失败数量等关键指标，并通过调度框架返回执行结果。

### 错误示例

```java
// 错误：无执行日志，无结果记录
@XxlJob("orderSyncJobHandler")
public void syncOrders() {
    orderService.syncOrdersFromExternal();
    // 无日志、无执行结果返回
}
```

### 正确示例

```java
@XxlJob("orderSyncJobHandler")
public void syncOrders() {
    long startTime = System.currentTimeMillis();
    log.info("订单同步任务开始执行, startTime={}", startTime);

    int total = 0;
    int success = 0;
    int failed = 0;

    try {
        List<Order> orders = orderService.fetchPendingOrders();
        total = orders.size();

        for (Order order : orders) {
            try {
                orderService.syncSingleOrder(order);
                success++;
            } catch (Exception e) {
                failed++;
                log.error("订单同步失败, orderId={}", order.getId(), e);
            }
        }

        long endTime = System.currentTimeMillis();
        long duration = endTime - startTime;

        log.info("订单同步任务执行完成, 总数={}, 成功={}, 失败={}, 耗时={}ms",
            total, success, failed, duration);

        // 通过 XXL-JOB 返回执行结果
        XxlJobHelper.handleSuccess(
            String.format("总数:%d, 成功:%d, 失败:%d, 耗时:%dms", total, success, failed, duration)
        );

    } catch (Exception e) {
        long endTime = System.currentTimeMillis();
        log.error("订单同步任务执行异常, 耗时={}ms", endTime - startTime, e);
        XxlJobHelper.handleFail("任务执行异常: " + e.getMessage());
    }
}
```

### 检查要点

- Job 执行入口必须记录开始时间、结束时间、耗时
- 必须记录处理数据总量、成功数、失败数
- 执行结果通过调度框架 API 返回（如 `XxlJobHelper.handleSuccess/handleFail`）
- 异常必须捕获并记录，不能静默吞掉
- 日志级别：正常流程用 INFO，异常用 ERROR
