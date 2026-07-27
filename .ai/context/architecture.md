# 架构与目录说明

> 接入后请完善 `[CUSTOMIZE]` 部分，让 AI 理解代码组织。

## 分层结构

```
src/main/java/com/[CUSTOMIZE: 公司]/[CUSTOMIZE: 项目]/
├── controller/     # HTTP 接口（薄层，禁业务逻辑）
├── service/        # 业务编排 + 事务
│   └── impl/
├── mapper/         # 数据持久化（MyBatis）
├── entity/         # 数据库表映射
├── dto/            # 接口入参 / 出参
│   ├── req/
│   └── resp/
├── config/         # 配置类
└── common/         # 通用：异常、返回包装、枚举、常量
```

## 关键约束

- Controller → Service → Mapper 单向依赖，禁止反向调用或跨层调用。
- 跨层数据用 DTO / Entity 隔离（见 `rules/coding.md`）。
- [CUSTOMIZE: 本项目特有的架构约束，如是否多模块、是否有 RPC / MQ 入口]
