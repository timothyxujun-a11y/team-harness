# 分布式锁

## JOB-LOCK-001: 分布式 Job 必须获取分布式锁防止重复执行

在多节点部署环境下，Job 执行前必须获取分布式锁（Redis/DB/ZooKeeper），确保同一时间只有一个节点执行任务。

### 错误示例

```java
// 错误：未加分布式锁，多节点同时执行导致数据重复处理
@XxlJob("orderSettlementJobHandler")
public void settleOrders() {
    // 多节点环境下可能并发执行，导致重复结算
    List<Order> orders = orderService.fetchUnsettledOrders();
    for (Order order : orders) {
        settlementService.settle(order);
    }
}
```

### 正确示例（Redisson 分布式锁）

```java
@XxlJob("orderSettlementJobHandler")
public void settleOrders() {
    String lockKey = "job:lock:order-settlement";
    RLock lock = redissonClient.getLock(lockKey);

    // 尝试获取锁，等待 0 秒（不等待），持有 30 分钟自动释放
    boolean acquired = false;
    try {
        acquired = lock.tryLock(0, 30, TimeUnit.MINUTES);
        if (!acquired) {
            log.info("未获取到分布式锁, 跳过执行, lockKey={}", lockKey);
            XxlJobHelper.handleSuccess("其他节点正在执行, 跳过");
            return;
        }

        log.info("获取分布式锁成功, 开始执行结算任务");
        List<Order> orders = orderService.fetchUnsettledOrders();
        for (Order order : orders) {
            settlementService.settle(order);
        }
        XxlJobHelper.handleSuccess("结算完成, 数量=" + orders.size());

    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
        log.error("获取锁被中断", e);
        XxlJobHelper.handleFail("获取锁被中断");
    } catch (Exception e) {
        log.error("结算任务执行失败", e);
        XxlJobHelper.handleFail("结算任务执行失败: " + e.getMessage());
    } finally {
        if (acquired && lock.isHeldByCurrentThread()) {
            lock.unlock();
            log.info("分布式锁已释放");
        }
    }
}
```

### 正确示例（数据库乐观锁方案）

```java
@XxlJob("orderSettlementJobHandler")
public void settleOrders() {
    // 通过数据库行锁抢占执行权
    JobLock lock = jobLockService.tryAcquire("order-settlement", getNodeId());
    if (lock == null) {
        log.info("未抢占到任务锁, 跳过执行");
        XxlJobHelper.handleSuccess("其他节点正在执行, 跳过");
        return;
    }

    try {
        List<Order> orders = orderService.fetchUnsettledOrders();
        for (Order order : orders) {
            settlementService.settle(order);
        }
    } finally {
        jobLockService.release(lock);
    }
}
```

### 检查要点

- 多节点部署的 Job 必须使用分布式锁
- 锁的 key 命名需有语义（如 `job:lock:{job-name}`）
- 获取锁失败时应正常返回，不抛异常
- finally 块中必须释放锁，且释放前检查是否持有锁
- 推荐使用 Redisson（Redis）或数据库方案

---

## JOB-LOCK-002: 分布式锁必须设置合理的超时与自动续期

分布式锁必须设置过期时间防止死锁，且在任务执行时间较长时启用锁续期（Watchdog）机制，避免锁过期导致并发执行。

### 错误示例

```java
// 错误：锁未设置过期时间，节点宕机后锁永不释放
RLock lock = redissonClient.getLock("job:lock:order-settlement");
lock.lock();  // 无过期时间，死锁风险
try {
    settleOrders();
} finally {
    lock.unlock();
}
```

```java
// 错误：锁过期时间太短，任务未完成锁已释放，其他节点并发执行
RLock lock = redissonClient.getLock("job:lock:order-settlement");
lock.lock(10, TimeUnit.SECONDS);  // 仅 10 秒，但任务需要 5 分钟
try {
    settleOrders();
} finally {
    lock.unlock();
}
```

### 正确示例

```java
@XxlJob("orderSettlementJobHandler")
public void settleOrders() {
    String lockKey = "job:lock:order-settlement";
    RLock lock = redissonClient.getLock(lockKey);

    try {
        // 方式一：使用 Redisson Watchdog 自动续期（推荐）
        // lock.lock() 会触发 Watchdog，默认每 10 秒续期到 30 秒
        boolean acquired = lock.tryLock(0, -1, TimeUnit.SECONDS);
        if (!acquired) {
            log.info("未获取到锁, 跳过执行");
            return;
        }

        // 方式二：手动设置足够长的过期时间（需预估任务最大执行时间）
        // boolean acquired = lock.tryLock(0, 30, TimeUnit.MINUTES);

        settleOrdersInternal();

    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
    } finally {
        if (lock.isHeldByCurrentThread()) {
            lock.unlock();
        }
    }
}
```

### 检查要点

- 锁必须设置过期时间（TTL），禁止使用无过期时间的 `lock()`
- 推荐使用 Redisson Watchdog 自动续期机制（`tryLock(0, -1, SECONDS)`）
- 若手动设置 TTL，需预估任务最大执行时间并留有余量
- 释放锁前必须检查 `isHeldByCurrentThread()`，避免释放非本线程持有的锁
- Watchdog 依赖 Redisson 实例的 `lockWatchdogTimeout` 配置（默认 30 秒）
