---
description: 评审当前 git diff 中的代码改动，对照团队规范检查问题。
---

# /review 命令

调用 `code-reviewer` agent 评审当前代码改动。

## 执行步骤

1. **获取改动范围**：
   - 执行 `git diff` 获取未暂存改动
   - 执行 `git diff --cached` 获取已暂存改动
   - 如果没有任何改动，提示用户并退出

2. **调用 code-reviewer agent**：
   将改动内容传递给 `code-reviewer` agent，按照其定义的审查维度进行检查：
   - 架构合规性
   - 代码风格
   - 异常处理
   - 测试覆盖
   - 安全检查

3. **输出审查报告**：
   按 code-reviewer agent 的输出格式呈现结果，包含：
   - 必须修复项（附修改建议）
   - 建议修改项（附修改建议）
   - 通过项
   - 总结

## 使用方式

- `/review` — 评审当前所有未提交的改动
- `/review 文件路径` — 评审指定文件的改动

## 注意事项

- 审查标准以 `docs/conventions.md` 为准
- 只审查改动的代码行，不审查未改动的代码
- 中文输出
