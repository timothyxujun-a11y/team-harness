# 规则路由（按任务选读，避免整体加载）

> 开始任务前先读本表，**只读相关规则**，不要一次性读完所有规则文件。
> 不确定时按「编码 → API → 数据库 → 异常 → 安全 → 测试」顺序全读。

## 按任务类型

| 你在做… | 必读规则 | 选读 |
|--------|----------|------|
| 新增 / 修改 Controller、REST 接口 | coding, api, exception | security |
| 写 SQL / DDL / Mapper / `*.xml` | coding, database, security | - |
| 写 Service 业务逻辑 / 事务 | coding, exception, test | - |
| 写或改单元测试 | test | coding |
| 涉及密钥 / 权限 / 外部入参 | security | - |
| 修 Bug | `prompts/bugfix` + 对应规则 | - |
| 代码审查 | `prompts/review` + 全部规则 | - |
| 新增微服务 | Skill `new-service` + 全部规则 | - |
| 新增接口 | Skill `new-api` + coding, api, exception, test | - |

## 按改动文件路径速查

| 文件路径 | 加载规则 |
|----------|----------|
| `**/controller/**` | coding + api + exception |
| `**/service/**` | coding + exception + test |
| `**/mapper/**`、`**/resources/mapper/**/*.xml` | coding + database |
| `**/*Test.java` | test |
| 涉及配置 / 密钥 / 鉴权 | security |

## 规则文件清单

- `coding.md` — 分层职责、DTO 隔离、禁止硬编码、最小改动
- `api.md` — REST、参数校验、统一返回、异常码
- `database.md` — 索引、禁止 `SELECT *`、深分页、DDL 审核
- `exception.md` — 全局异常处理器、业务异常、事务回滚
- `security.md` — 禁止硬编码密钥、参数校验、脱敏、SQL 注入
- `test.md` — JUnit 5 + Mockito、不启动容器、三覆盖维度
