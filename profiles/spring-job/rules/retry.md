# 失败重试与断点续跑

## JOB-RETRY-001: Job 失败必须支持重试并保留执行上下文

Job 执行失败时必须支持自动重试（建议 3 次），重试时需保留执行上下文（已处理进度），避免数据不一致。重试耗尽后需触发告警。

### 错误示例

```java
// 错误：失败后无重试机制，直接结束
@XxlJob("reportGenerateJobHandler")
public void generateReports() {
    List<Report> reports = reportService.fetchPendingReports();
    for (Report report : reports) {
        reportService.generate(report);  // 任何一条失败，整个 Job 直接异常退出
    }
}
```

### 正确示例

```java
@XxlJob("reportGenerateJobHandler")
public void generateReports() {
    int maxRetry = 3;
    int batchSize = 100;
    long lastId = 0L;

    // 读取上次执行进度，支持断点续跑
    JobProgress progress = jobProgressService.getProgress("report-generate");
    if (progress != null && "RUNNING".equals(progress.getStatus())) {
        lastId = progress.getLastProcessedId();
        log.info("从断点续跑, lastId={}", lastId);
    }

    while (true) {
        List<Report> reports = reportMapper.selectByIdAfter(lastId, batchSize);
        if (reports.isEmpty()) {
            jobProgressService.markCompleted("report-generate");
            break;
        }

        for (Report report : reports) {
            int retryCount = 0;
            boolean success = false;

            // 单条数据重试
            while (retryCount < maxRetry && !success) {
                try {
                    reportService.generate(report);
                    success = true;
                } catch (Exception e) {
                    retryCount++;
                    log.warn("报表生成失败, reportId={}, 重试 {}/{}",
                        report.getId(), retryCount, maxRetry, e);
                    if (retryCount >= maxRetry) {
                        // 重试耗尽，记录失败项并告警
                        jobFailureService.recordFailure(
                            "report-generate", report.getId(), e.getMessage());
                        alertService.sendAlert(String.format(
                            "报表生成失败(重试耗尽), reportId=%d, 错误=%s",
                            report.getId(), e.getMessage()));
                    } else {
                        // 指数退避等待
                        sleepWithBackoff(retryCount);
                    }
                }
            }
        }

        // 更新进度
        lastId = reports.get(reports.size() - 1).getId();
        jobProgressService.saveProgress("report-generate", lastId, 0);
    }

    XxlJobHelper.handleSuccess("报表生成任务完成");
}

/**
 * 指数退避等待
 */
private void sleepWithBackoff(int retryCount) {
    long delay = (long) Math.pow(2, retryCount) * 1000;  // 2s, 4s, 8s
    try {
        Thread.sleep(delay);
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
    }
}
```

### 正确示例（整体 Job 级别重试 + XXL-JOB 重试配置）

```java
// 在 XXL-JOB 调度中心配置重试次数（如 3 次）
// Job 代码中处理重试逻辑

@XxlJob("reportGenerateJobHandler")
public void generateReports() {
    try {
        generateReportsInternal();
        XxlJobHelper.handleSuccess("报表生成任务完成");
    } catch (Exception e) {
        log.error("报表生成任务失败, 等待调度框架重试", e);
        // 抛出异常，XXL-JOB 调度中心会根据配置自动重试
        // 重试时从持久化进度恢复，不会从头开始
        throw e;
    }
}

private void generateReportsInternal() {
    JobProgress progress = jobProgressService.getProgress("report-generate");
    long lastId = (progress != null) ? progress.getLastProcessedId() : 0L;

    while (true) {
        List<Report> reports = reportMapper.selectByIdAfter(lastId, 100);
        if (reports.isEmpty()) {
            jobProgressService.markCompleted("report-generate");
            return;
        }

        for (Report report : reports) {
            reportService.generate(report);  // 单条失败则抛出异常触发整体重试
        }

        lastId = reports.get(reports.size() - 1).getId();
        jobProgressService.saveProgress("report-generate", lastId, 0);
    }
}
```

### 检查要点

- Job 必须支持失败重试，重试次数建议 3 次
- 重试需采用指数退避策略（如 2s → 4s → 8s）
- 重试时必须从持久化进度恢复，不能从头开始
- 重试耗尽后必须触发告警（钉钉/企业微信/邮件）
- 失败的数据项应单独记录，不阻塞整体流程
- 可结合 XXL-JOB 调度中心的「任务重试次数」配置实现框架级重试
