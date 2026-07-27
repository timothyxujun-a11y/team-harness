# 安全规则

> 规则 ID: CORE-SEC-001 ~ CORE-SEC-002
> 严重级别: error（全部强制）

## CORE-SEC-001: 不得写入生产密钥和敏感信息

代码中不得硬编码以下内容：
- 数据库密码
- API Token / Access Key / Secret Key
- 私钥（RSA、ECDSA 等）
- JWT Secret
- 第三方服务凭证
- 生产环境连接信息

**正确做法**：
- 使用环境变量或配置中心注入。
- 使用 `@Value("${app.secret}")` 而非字面量。
- 敏感配置放在 `application-{env}.yml` 中，且 `.yml` 不入库。

**违反示例**:
```java
// 错误：硬编码密码
private static final String DB_PASSWORD = "admin123";
```

## CORE-SEC-002: 不得执行高风险 Git 操作

AI 不得执行以下操作，除非用户明确要求并确认：
- `git push --force` / `git push -f`
- `git reset --hard`（特别是对已推送的提交）
- `git rebase` 已推送的提交
- `rm -rf` 递归删除
- 修改 `.git/config`
- 删除分支
- 修改 Git Hook

**允许的操作**：
- `git add` / `git commit` / `git push`（非 force）
- `git status` / `git diff` / `git log`
- `git branch` / `git checkout`（创建和切换分支）
- `git merge`（非主分支）

**需要确认的操作**：
- 修改 `main` / `master` 分支
- 数据库 DDL 变更
- 删除已有文件
- 修改安全相关配置
