---
name: new-service
description: 新增一个微服务模块的标准多步骤流程。当需要从零创建一个新服务/模块（脚手架、分层骨架、统一返回与异常、配置、测试基线、自检）时使用。
---

# Skill：新增微服务

把"新增一个微服务"固化为标准多步骤流程，确保每个新服务都符合团队规范（`.ai/rules`）。

## 触发场景
- "新增一个 xxx 微服务 / 模块"
- "搭一个新服务的骨架"

## 标准步骤

1. **确认边界**
   - 服务名、包名（`com.<公司>.<服务>`）、Java 版本、端口、依赖中间件（DB / MQ / Cache）。
   - 对外协议：HTTP / MQ 入口 / 定时任务。

2. **脚手架（按 `.ai/context/architecture.md` 分层）**
   - `pom.xml`（Spring Boot + Maven，版本统一）。
   - 包结构：`controller / service/impl / mapper / entity / dto/{req,resp} / config / common`。
   - 主启动类 + `application.yml`（dev / test / prod 环境隔离）。

3. **通用基线（按 `rules/exception.md`、`rules/api.md`）**
   - 统一返回 `Result<T>` + `ResultCode` 枚举。
   - `BusinessException` + `@RestControllerAdvice` 全局异常处理器。

4. **第一个垂直切片**
   - 一个最简接口走通 Controller → Service → Mapper → Entity → DTO，验证分层与异常链路。

5. **测试基线（按 `rules/test.md`）**
   - 为切片里的 Service 补 JUnit 5 + Mockito 单测（不启动容器）。

6. **自检**
   - 运行 `harness check`：确认 `.ai` 完整、无 `[CUSTOMIZE]` 残留。
   - 编译 + `mvn test` 通过。

7. **记录日志**
   - 在 `.ai/log/changes.md` 顶部追加一条（关键决策：分层 / 版本 / 中间件）。

## 交付 Checklist
- [ ] 分层目录齐全，Controller 无业务逻辑
- [ ] 统一返回 + 全局异常就位
- [ ] DTO / Entity 隔离
- [ ] 至少一个端到端切片 + 单测通过
- [ ] `harness check` 无 WARN
- [ ] `.ai/log/changes.md` 已记录
