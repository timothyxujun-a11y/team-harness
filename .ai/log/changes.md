# AI 操作日志

> 每次 AI 任务结束后，**必须**在下方表格顶部追加一条记录（最新的在最上）。
> 目的：让团队可回溯 AI 的决策与改动，持续改进 `.ai/` 规范。日志即文档，零运行时。

| 日期 | 任务 | 关键决策 | 改动文件 | 测试 | Review |
|------|------|----------|----------|------|--------|
| 2026-07-27 | v1.1.0 增强四项能力 | 用 INDEX 路由 + Skill + check + log 四个纯文件机制回应"整体加载/无流程/无门禁/无日志"质疑，坚持零依赖 | harness, rules/INDEX.md, skills/*, git-hooks/pre-commit, README, CHANGELOG | ⏭ Bash 工具无 mvn | ⏭ |
| YYYY-MM-DD | （一句话任务） | （做了什么取舍 / 为什么） | （主要文件） | ✅/⏭ `mvn test` | ✅/⏭ `/review` |

<!--
追加示例（删掉本注释后使用）：
| 2026-07-27 | 新增订单查询接口 | 用延迟关联分页避免深分页；DTO 与 Entity 隔离 | OrderController, OrderServiceImpl, OrderMapper.xml | ✅ OrderServiceTest | ✅ /review -->
