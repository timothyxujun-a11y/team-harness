# Git 工作流规则

> 规则 ID: CORE-GIT-001 ~ CORE-GIT-002

## CORE-GIT-001: 代码变更应具备可追踪性 (warning)

### Commit Message 格式

采用 Conventional Commits 格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type**:
- `feat`: 新功能
- `fix`: 缺陷修复
- `refactor`: 重构（不改变行为）
- `test`: 测试相关
- `docs`: 文档
- `chore`: 构建/工具/配置
- `perf`: 性能优化

**示例**:
```
feat(tax): 新增税金计算服务

- 实现 TaxCalculator 基础计算逻辑
- 新增税率配置加载

Closes #123
```

### 分支命名

- 功能分支: `feature/描述`
- 修复分支: `fix/描述`
- 重构分支: `refactor/描述`

## CORE-GIT-002: 高风险操作必须人工确认 (error)

以下操作必须经过人工确认后才能执行：

1. **数据库变更**：DDL 语句（CREATE/ALTER/DROP TABLE）
2. **配置变更**：生产环境配置修改
3. **文件删除**：删除已有源代码文件
4. **依赖变更**：修改 pom.xml 的依赖版本
5. **安全配置**：修改权限、认证、加密相关配置
6. **主分支操作**：直接向 main/master 推送

AI 在执行上述操作前，必须：
1. 说明操作内容和影响范围。
2. 等待用户明确确认（"是" / "确认" / "继续"）。
3. 未获得确认时不得执行。
