---
description: 读取暂存区改动，生成 Conventional Commit 消息，经确认后提交。
---

# /commit 命令

分析暂存区改动，生成符合 Conventional Commits 规范的提交消息，经用户确认后提交。

## 执行步骤

1. **检查暂存区**：
   - 执行 `git diff --cached --stat` 查看暂存区文件列表
   - 如果暂存区为空，提示用户先 `git add` 并退出

2. **分析改动内容**：
   - 执行 `git diff --cached` 获取完整 diff
   - 分析改动类型：新增功能 / 修复 Bug / 重构 / 测试 / 文档 / 杂项
   - 分析影响范围：确定 scope（模块名）

3. **生成 Commit 消息**：
   按 Conventional Commits 格式生成：

   ```
   <type>(<scope>): <中文描述>
   ```

   type 选择规则：
   - 新增功能或接口 → `feat`
   - 修复 Bug → `fix`
   - 文档变更 → `docs`
   - 代码重构（不改行为）→ `refactor`
   - 新增/修改测试 → `test`
   - 构建/配置/依赖 → `chore`

   scope 从改动的包路径或模块名推断。

4. **用户确认**：
   - 展示生成的 commit 消息
   - 询问用户是否确认，或需要修改
   - 用户确认后执行 `git commit`

5. **提交后**：
   - 执行 `git log -1` 显示提交结果
   - 提示用户可以 `git push`

## 示例

```
> /commit

分析暂存区改动...
- order-service/src/main/java/.../OrderController.java (新增 1 个接口)
- order-service/src/main/java/.../OrderService.java (新增 1 个方法)
- order-service/src/test/java/.../OrderServiceTest.java (新增 2 个测试)

建议的 commit 消息：
  feat(order): 新增根据外部订单号查询订单详情接口

确认提交？(y/n/edit)
```

## 注意事项

- commit 描述使用中文
- 一行不超过 72 字符
- 如果改动跨多个模块，scope 用 `*` 或省略
- 不自动 push，需要用户手动执行
