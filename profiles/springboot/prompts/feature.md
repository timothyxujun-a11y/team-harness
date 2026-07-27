# Prompt 模板 — 新需求开发

> 把需求贴在下方，按四步推进。AI 应严格遵循 `.ai/rules`。

## 需求

[CUSTOMIZE: 粘贴需求描述 / PRD 片段]

## 执行步骤

### 1. 需求分析
- 拆解为可验证的子目标。
- 列出影响范围（哪些类 / 表 / 接口）。
- 识别歧义点，有歧义先向我确认。

### 2. 技术设计
- 分层落点（Controller / Service / Mapper / DTO / Entity）。
- 接口契约（路径、入参、出参、异常码）。
- 数据库变更（DDL 先输出 SQL 待审）。

### 3. 代码实现
- 按 `rules/coding.md` 分层：Controller 薄、Service 厚。
- DTO 与 Entity 隔离；统一返回结构；统一异常处理。
- 只改必要范围。

### 4. 测试生成
- 按 `rules/test.md` 为核心 Service 生成 JUnit 5 + Mockito 单测。
- 覆盖正常 / 异常 / 边界。
- 改完执行 `mvn test` 确认通过。
