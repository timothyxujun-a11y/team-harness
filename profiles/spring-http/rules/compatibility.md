# API 兼容性规范

> 规则：HTTP-COMPAT-001 / HTTP-COMPAT-002 | 严重级别：error / warning

## 概述

API 兼容性是微服务架构中的核心约束。任何对已发布 API 的不兼容修改都可能导致下游调用方故障，必须在设计阶段就充分考虑向后兼容性。

## 规则详情

### 1. 不得删除已有 API 端点（HTTP-COMPAT-001）

已对外发布的 API 端点（接口路径 + HTTP 方法）不得删除。如需废弃，必须遵循以下流程：

1. 标记为 `@Deprecated` 并在文档中声明替代接口
2. 设置废弃截止日期（至少保留一个大版本周期）
3. 在废弃期内，旧接口调用时应记录告警日志
4. 确认所有调用方完成迁移后方可移除

```java
// 正确：标记废弃，指向新接口
@Deprecated
@GetMapping("/v1/users/{id}")
@Operation(summary = "获取用户详情（已废弃）", deprecated = true,
           description = "请使用 GET /api/v2/users/{id} 替代，本接口将在 v3.0 移除")
public Result<UserV1VO> getUserV1(@PathVariable Long id) {
    log.warn("检测到废弃接口调用: GET /v1/users/{}", id);
    UserVO vo = userService.getById(id);
    return Result.success(UserConverter.toV1(vo));
}

// 新版本接口
@GetMapping("/v2/users/{id}")
@Operation(summary = "获取用户详情")
public Result<UserVO> getUserV2(@PathVariable Long id) {
    return Result.success(userService.getById(id));
}
```

### 2. 不得修改已有字段含义（HTTP-COMPAT-001）

已发布的响应字段不得修改：

- 字段名称不得重命名
- 字段类型不得变更（如 `Integer` 改为 `String`）
- 字段含义不得改变（如 `price` 从元改为分）

```java
// 错误：修改已有字段类型
// v1:
@Data
public class UserV1VO {
    private Integer age;  // 整型年龄
}

// v2（错误）:
@Data
public class UserV2VO {
    private String age;  // 改为字符串，下游反序列化会崩溃
}

// 正确：新增字段而非修改旧字段
@Data
public class UserV2VO {
    private Integer age;       // 保留旧字段，保证兼容
    private String ageRange;   // 新增字段提供新信息
}
```

### 3. 新增字段必须有默认值（HTTP-COMPAT-002）

响应对象新增字段时，必须提供合理的默认值：

```java
@Data
public class UserVO {

    private Long id;
    private String username;

    // 新增字段，要有默认值
    private String nickname = "";                    // 字符串默认空串

    private Integer gender = 0;                       // 数值默认 0（表示未设置）

    private Boolean isVip = false;                    // 布尔默认 false

    private List<String> tags = Collections.emptyList();  // 集合默认空列表

    private UserExtVO ext = new UserExtVO();          // 嵌套对象默认实例
}
```

请求对象新增可选字段时，使用 `@RequestParam(required = false)` 并提供 `defaultValue`：

```java
@GetMapping
public Result<PageResult<UserVO>> list(
        @RequestParam(defaultValue = "1") Integer page,
        @RequestParam(defaultValue = "20") Integer size,
        @RequestParam(required = false) String keyword,  // 新增可选的查询参数
        @RequestParam(required = false, defaultValue = "0") Integer gender  // 新筛选条件
) {
    return Result.success(userService.search(page, size, keyword, gender));
}
```

### 4. 版本化 API 管理（HTTP-COMPAT-002）

当需要发布不兼容变更时，应使用版本化 API 管理。推荐策略：

#### 策略一：URL 路径版本（推荐）

```java
@RestController
@RequestMapping("/api/v1/users")
public class UserV1Controller {
    @GetMapping("/{id}")
    public Result<UserV1VO> getById(@PathVariable Long id) { ... }
}

@RestController
@RequestMapping("/api/v2/users")
public class UserV2Controller {
    @GetMapping("/{id}")
    public Result<UserV2VO> getById(@PathVariable Long id) { ... }
}
```

#### 策略二：请求头版本

```java
@GetMapping("/{id}")
public Result<?> getById(@PathVariable Long id,
                          @RequestHeader(value = "API-Version", defaultValue = "1") String version) {
    if ("2".equals(version)) {
        return Result.success(userService.getByIdV2(id));
    }
    return Result.success(userService.getByIdV1(id));
}
```

> 推荐使用策略一（URL 路径版本），更直观且易于网关路由管理。

### 5. 请求参数兼容性

```java
// 错误：已有必填参数改为选填，行为语义改变
// v1: @RequestParam Integer status    （必填）
// v2: @RequestParam(required = false) Integer status  （选填，语义不同）

// 正确：保持原参数不变，新增可选参数
// v1:
@GetMapping
public Result<List<OrderVO>> list(@RequestParam Integer status) { ... }

// v2: 保留原参数，新增可选参数
@GetMapping
public Result<PageResult<OrderVO>> list(@RequestParam Integer status,
                                         @RequestParam(defaultValue = "1") Integer page,
                                         @RequestParam(defaultValue = "20") Integer size) { ... }
```

## 兼容性变更矩阵

| 变更类型 | 是否兼容 | 处理方式 |
|----------|----------|----------|
| 新增接口 | 兼容 | 直接添加 |
| 新增可选请求参数 | 兼容 | 使用 `required = false` |
| 新增可选响应字段 | 兼容 | 提供默认值 |
| 删除接口 | 不兼容 | 标记 `@Deprecated`，等待迁移 |
| 删除请求参数 | 不兼容 | 使用新版本接口 |
| 修改字段类型 | 不兼容 | 使用新版本接口 |
| 修改字段含义 | 不兼容 | 新增字段替代 |
| 修改 HTTP 方法 | 不兼容 | 新增接口 |
| 修改响应状态码 | 不兼容 | 使用新版本 |
| 修改错误码含义 | 不兼容 | 新增错误码 |

## 检查清单

- [ ] 本次变更是否删除了任何已有 API 端点？
- [ ] 是否修改了已有响应字段的名称、类型或含义？
- [ ] 新增的响应字段是否提供了合理的默认值？
- [ ] 新增的可选请求参数是否使用了 `required = false`？
- [ ] 不兼容变更是否通过版本化 API 实现？
- [ ] 废弃接口是否添加了 `@Deprecated` 注解和文档说明？
- [ ] 废弃接口是否记录了告警日志？
