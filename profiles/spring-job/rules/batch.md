# 批处理

## JOB-BATCH-001: 批量处理必须分页执行，禁止一次性加载全量数据

Job 批量处理数据时必须分页/分批拉取，单批次数据量建议不超过 1000 条，禁止一次性加载全量数据到内存。

### 错误示例

```java
// 错误：一次性查询全量数据，数据量大时 OOM
@XxlJob("userPointCalcJobHandler")
public void calcUserPoints() {
    // 全量加载所有用户，百万级数据会导致 OOM
    List<User> allUsers = userMapper.selectAll();
    for (User user : allUsers) {
        pointService.calculatePoints(user);
    }
}
```

### 正确示例（分页处理）

```java
@XxlJob("userPointCalcJobHandler")
public void calcUserPoints() {
    int pageSize = 500;
    int pageNo = 1;
    int totalProcessed = 0;

    while (true) {
        // 分页查询
        List<User> users = userMapper.selectPage(pageNo, pageSize);
        if (users.isEmpty()) {
            break;
        }

        for (User user : users) {
            try {
                pointService.calculatePoints(user);
                totalProcessed++;
            } catch (Exception e) {
                log.error("积分计算失败, userId={}", user.getId(), e);
            }
        }

        log.info("已处理第 {} 页, 累计处理 {} 条", pageNo, totalProcessed);
        pageNo++;
    }

    log.info("积分计算任务完成, 总处理数量={}", totalProcessed);
    XxlJobHelper.handleSuccess("总处理数量: " + totalProcessed);
}
```

### 正确示例（游标/ID 增量处理，推荐）

```java
@XxlJob("userPointCalcJobHandler")
public void calcUserPoints() {
    int batchSize = 500;
    long lastId = 0L;
    int totalProcessed = 0;

    while (true) {
        // 基于 ID 增量查询，避免深分页性能问题
        List<User> users = userMapper.selectByIdAfter(lastId, batchSize);
        if (users.isEmpty()) {
            break;
        }

        for (User user : users) {
            try {
                pointService.calculatePoints(user);
                totalProcessed++;
            } catch (Exception e) {
                log.error("积分计算失败, userId={}", user.getId(), e);
            }
        }

        lastId = users.get(users.size() - 1).getId();
        log.info("已处理到 userId={}, 累计处理 {} 条", lastId, totalProcessed);
    }

    log.info("积分计算任务完成, 总处理数量={}", totalProcessed);
    XxlJobHelper.handleSuccess("总处理数量: " + totalProcessed);
}
```

### 检查要点

- 禁止 `selectAll()` / `findAll()` 等全量查询
- 单批次数据量建议 500~1000 条
- 推荐使用 ID 增量查询（`WHERE id > lastId ORDER BY id LIMIT batchSize`），避免深分页性能问题
- 每批次处理完后应记录进度日志

---

## JOB-BATCH-002: 批处理必须记录处理进度，支持断点续跑

批处理 Job 必须将处理进度（当前页码/最后处理的 ID）持久化，当 Job 中断后重启时能从断点继续执行，而非从头开始。

### 错误示例

```java
// 错误：每次执行都从头开始，中断后无法恢复
@XxlJob("dataMigrationJobHandler")
public void migrateData() {
    long lastId = 0L;  // 每次都从 0 开始
    int batchSize = 500;

    while (true) {
        List<Data> batch = dataMapper.selectByIdAfter(lastId, batchSize);
        if (batch.isEmpty()) break;

        for (Data data : batch) {
            migrationService.migrate(data);
        }
        lastId = batch.get(batch.size() - 1).getId();
    }
}
```

### 正确示例

```java
@XxlJob("dataMigrationJobHandler")
public void migrateData() {
    int batchSize = 500;

    // 1. 从持久化存储读取上次处理进度
    JobProgress progress = jobProgressService.getProgress("data-migration");
    long lastId = (progress != null) ? progress.getLastProcessedId() : 0L;
    log.info("数据迁移任务启动, 从 lastId={} 继续执行", lastId);

    int totalProcessed = 0;
    while (true) {
        List<Data> batch = dataMapper.selectByIdAfter(lastId, batchSize);
        if (batch.isEmpty()) {
            log.info("数据处理完成");
            // 清理进度记录
            jobProgressService.markCompleted("data-migration");
            break;
        }

        for (Data data : batch) {
            try {
                migrationService.migrate(data);
                totalProcessed++;
            } catch (Exception e) {
                log.error("数据迁移失败, dataId={}", data.getId(), e);
                // 记录失败项，不影响整体进度
                jobFailureService.recordFailure("data-migration", data.getId(), e.getMessage());
            }
        }

        // 2. 每批处理后更新进度
        lastId = batch.get(batch.size() - 1).getId();
        jobProgressService.saveProgress("data-migration", lastId, totalProcessed);
        log.info("已处理到 dataId={}, 累计处理 {} 条", lastId, totalProcessed);
    }

    XxlJobHelper.handleSuccess("迁移完成, 总处理数量: " + totalProcessed);
}
```

### 进度表设计

```sql
CREATE TABLE job_progress (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL UNIQUE COMMENT '任务名称',
    last_processed_id BIGINT DEFAULT 0 COMMENT '最后处理的 ID',
    processed_count INT DEFAULT 0 COMMENT '已处理数量',
    status VARCHAR(20) DEFAULT 'RUNNING' COMMENT '状态: RUNNING/COMPLETED/FAILED',
    last_execute_time DATETIME COMMENT '最后执行时间',
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### 检查要点

- 处理进度（lastId / pageNo）必须持久化到数据库或 Redis
- Job 启动时先读取上次进度，从断点继续
- 每批次处理完成后立即更新进度
- Job 完成后标记状态为 COMPLETED，下次执行可从头开始
- 失败的数据项应单独记录，不影响整体进度推进
