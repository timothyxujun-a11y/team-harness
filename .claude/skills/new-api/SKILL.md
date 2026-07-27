---
name: new-api
description: 新增一个 REST 接口的标准多步骤流程。当需要在已有服务里加一个 HTTP 接口（契约、分层实现、异常、单测、自检）时使用。
---

# Skill：新增 REST 接口

## 触发场景
- "新增一个 xxx 接口"
- "加一个查询 / 创建 / 更新的 API"

## 标准步骤（先查 `rules/INDEX.md`：coding + api + exception + test）

1. **契约定义**
   - 路径（REST 名词复数）、HTTP 方法、入参 DTO（JSR-303 校验注解）、出参 DTO、异常码。

2. **分层实现**
   - `controller/`：薄层，`@Valid` 校验 + 调 Service + 组装 `Result`。
   - `service/impl/`：业务编排 + 事务（`@Transactional` 注意 `rollbackFor`）。
   - `mapper/` + `*.xml`：参数化 SQL，禁 `select *`，注意深分页。
   - `dto/req`、`dto/resp`：与 Entity 隔离。

3. **异常与返回**
   - 业务错误抛 `BusinessException(ResultCode)`，由全局处理器兜底。
   - 成功返回统一 `Result.ok(data)`。

4. **单元测试（`rules/test.md`）**
   - Service 层：JUnit 5 + Mockito，覆盖正常 / 异常 / 边界，不启动容器。
   - 方法命名 `shouldXxxWhenYyy`，`@DisplayName` 中文描述。

5. **自检**
   - `mvn test -Dtest=<目标测试类>` 通过。
   - 对照 `rules/INDEX.md` 确认相关规则已遵循。
   - `harness check`。

6. **记录日志**
   - `.ai/log/changes.md` 追加一条（接口、关键决策、改动文件、测试 / review 状态）。

## 交付 Checklist
- [ ] 入参校验注解齐全
- [ ] Controller 无业务逻辑
- [ ] 统一返回 + 业务异常
- [ ] DTO / Entity 隔离
- [ ] SQL 无 `select *`、无深分页风险
- [ ] 单测覆盖三维度且通过
- [ ] `.ai/log/changes.md` 已记录
