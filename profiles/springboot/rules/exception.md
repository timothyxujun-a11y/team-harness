# 异常处理规范

> 来源：Team Harness V1.0 PRD §6.1。统一异常处理为强制项。

## 1. 全局异常处理器（强制）

- 使用 `@RestControllerAdvice` + `@ExceptionHandler` 统一捕获。
- 至少覆盖三类：业务异常、参数校验异常、未捕获异常（兜底）。
- 兜底异常不得把堆栈 / SQL / 内部信息返回前端，统一友好提示 + 服务端记录日志。

## 2. 自定义业务异常

- 定义统一基类 `BusinessException(ResultCode)`（或等价设计）。
- 业务错误抛业务异常，禁止 `throw new RuntimeException("xxx")` 散抛字符串。
- 异常只用于异常路径，禁止用异常控制正常流程。

## 3. 异常码

- 异常码与文案集中在 `ResultCode` 枚举（见 `api.md`），不在代码里硬编码异常字符串。

## 4. 事务与异常

- `@Transactional` 默认只回滚 `RuntimeException`；需回滚受检异常时显式 `rollbackFor`。
- 事务方法内不得吞异常（`catch` 后既不抛出也不手动标记回滚）。
