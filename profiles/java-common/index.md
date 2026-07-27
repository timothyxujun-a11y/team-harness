# Java 通用编码规范 - 规则索引

> **Profile**: java-common v1.0.0
> **适用语言**: Java (8/11/17/21)
> **构建工具**: Maven

---

## 命名规范 (JAVA-CODE)

| 规则 ID | 严重级别 | 标题 | 文件路径 |
|---------|---------|------|---------|
| JAVA-CODE-001 | error | 类命名使用 PascalCase | rules/naming.md |
| JAVA-CODE-002 | error | 方法命名使用 camelCase | rules/naming.md |
| JAVA-CODE-003 | error | 常量与包命名规范 | rules/naming.md |

## 异常处理 (JAVA-EXC)

| 规则 ID | 严重级别 | 标题 | 文件路径 |
|---------|---------|------|---------|
| JAVA-EXC-001 | error | 自定义业务异常继承 RuntimeException | rules/exception.md |
| JAVA-EXC-002 | error | 禁止捕获异常后忽略 | rules/exception.md |
| JAVA-EXC-003 | error | 异常信息必须包含上下文与 Controller 统一处理 | rules/exception.md |

## 日志规范 (JAVA-LOG)

| 规则 ID | 严重级别 | 标题 | 文件路径 |
|---------|---------|------|---------|
| JAVA-LOG-001 | error | 使用 SLF4J + Logback 日志框架 | rules/logging.md |
| JAVA-LOG-002 | warn | 日志级别使用规范 | rules/logging.md |
| JAVA-LOG-003 | error | 敏感信息不得记录日志 | rules/logging.md |

## 单元测试 (JAVA-TEST)

| 规则 ID | 严重级别 | 标题 | 文件路径 |
|---------|---------|------|---------|
| JAVA-TEST-001 | error | 测试框架使用 JUnit 4 + Mockito + AssertJ | rules/testing.md |
| JAVA-TEST-002 | error | 禁止单元测试启动 Spring 容器 | rules/testing.md |
| JAVA-TEST-003 | error | AAA 结构与测试命名规范 | rules/testing.md |
| JAVA-TEST-004 | warn | 测试最小化运行与覆盖率要求 | rules/testing.md |

---

**规则总数**: 13 条
- `error` 级别: 11 条
- `warn` 级别: 2 条
