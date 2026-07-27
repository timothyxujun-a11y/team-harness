# 响应格式规范

> 规则：HTTP-RESP-001 / HTTP-RESP-002 | 严重级别：error

## 概述

所有 API 必须使用统一的响应体结构，确保前端和下游服务能以一致的方式处理所有接口的返回值。

## 规则详情

### 1. 统一响应体结构（HTTP-RESP-001）

所有 Controller 方法的返回值必须用 `Result<T>` 包装。

#### 统一响应体定义

```java
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Result<T> {

    /** 业务状态码 */
    private Integer code;

    /** 提示信息 */
    private String message;

    /** 响应数据 */
    private T data;

    /** 时间戳 */
    private Long timestamp;

    // ========== 成功响应 ==========
    public static <T> Result<T> success() {
        return new Result<>(200, "操作成功", null, System.currentTimeMillis());
    }

    public static <T> Result<T> success(T data) {
        return new Result<>(200, "操作成功", data, System.currentTimeMillis());
    }

    public static <T> Result<T> success(String message, T data) {
        return new Result<>(200, message, data, System.currentTimeMillis());
    }

    // ========== 失败响应 ==========
    public static <T> Result<T> fail(Integer code, String message) {
        return new Result<>(code, message, null, System.currentTimeMillis());
    }

    public static <T> Result<T> fail(ErrorCode errorCode) {
        return new Result<>(errorCode.getCode(), errorCode.getMessage(), null, System.currentTimeMillis());
    }

    public static <T> Result<T> fail(ErrorCode errorCode, String detail) {
        return new Result<>(errorCode.getCode(),
                errorCode.getMessage() + ": " + detail, null, System.currentTimeMillis());
    }
}
```

#### Controller 使用示例

```java
@RestController
@RequestMapping("/api/users")
public class UserController {

    @GetMapping("/{id}")
    public Result<UserVO> getById(@PathVariable Long id) {
        UserVO vo = userService.getById(id);
        return Result.success(vo);
    }

    @GetMapping
    public Result<PageResult<UserVO>> list(@RequestParam Integer page,
                                            @RequestParam Integer size) {
        PageResult<UserVO> result = userService.list(page, size);
        return Result.success(result);
    }
}
```

#### 实际响应 JSON 示例

```json
// 成功响应
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "id": 1,
    "username": "zhangsan",
    "email": "zhangsan@example.com"
  },
  "timestamp": 1700000000000
}

// 失败响应
{
  "code": 40001,
  "message": "用户不存在: id=999",
  "data": null,
  "timestamp": 1700000000000
}
```

### 2. 错误码体系（HTTP-RESP-002）

#### 错误码设计规范

错误码采用 **5 位整数**，分段设计：

| 范围 | 含义 | 说明 |
|------|------|------|
| 200 | 成功 | 操作成功 |
| 4xxxx | 客户端错误 | 参数错误、权限不足、资源不存在等 |
| 5xxxx | 服务端错误 | 系统异常、数据库错误、第三方服务异常等 |

#### 错误码枚举定义

```java
public enum ErrorCode {

    // ===== 通用错误（40000 ~ 40099）=====
    SUCCESS(200, "操作成功"),
    PARAM_ERROR(40001, "参数校验失败"),
    UNAUTHORIZED(40002, "未登录或登录已过期"),
    FORBIDDEN(40003, "无权限访问"),
    NOT_FOUND(40004, "资源不存在"),
    METHOD_NOT_ALLOWED(40005, "不支持的请求方法"),
    RATE_LIMIT(40006, "请求过于频繁"),

    // ===== 用户模块（40100 ~ 40199）=====
    USER_NOT_FOUND(40100, "用户不存在"),
    USERNAME_EXISTS(40101, "用户名已存在"),
    MOBILE_EXISTS(40102, "手机号已注册"),
    PASSWORD_ERROR(40103, "用户名或密码错误"),
    ACCOUNT_LOCKED(40104, "账号已被锁定"),

    // ===== 订单模块（40200 ~ 40299）=====
    ORDER_NOT_FOUND(40200, "订单不存在"),
    ORDER_STATUS_ERROR(40201, "订单状态不允许当前操作"),
    ORDER_STOCK_INSUFFICIENT(40202, "库存不足"),

    // ===== 系统错误（50000 ~ 59999）=====
    SYSTEM_ERROR(50000, "系统繁忙，请稍后重试"),
    DB_ERROR(50001, "数据库异常"),
    RPC_ERROR(50002, "远程服务调用失败"),
    FILE_UPLOAD_ERROR(50003, "文件上传失败");

    private final Integer code;
    private final String message;

    ErrorCode(Integer code, String message) {
        this.code = code;
        this.message = message;
    }

    public Integer getCode() { return code; }
    public String getMessage() { return message; }
}
```

#### 使用方式

```java
// Service 层抛出业务异常
public UserVO getById(Long id) {
    User user = userMapper.selectById(id);
    if (user == null) {
        throw new BusinessException(ErrorCode.USER_NOT_FOUND, "id=" + id);
    }
    return UserConverter.INSTANCE.toVO(user);
}

// 业务异常定义
public class BusinessException extends RuntimeException {
    private final ErrorCode errorCode;

    public BusinessException(ErrorCode errorCode) {
        super(errorCode.getMessage());
        this.errorCode = errorCode;
    }

    public BusinessException(ErrorCode errorCode, String detail) {
        super(errorCode.getMessage() + ": " + detail);
        this.errorCode = errorCode;
    }

    public ErrorCode getErrorCode() { return errorCode; }
}

// 全局异常处理器
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BusinessException.class)
    public Result<Void> handleBusinessException(BusinessException ex) {
        return Result.fail(ex.getErrorCode().getCode(), ex.getMessage());
    }
}
```

### 3. 分页响应格式

所有列表查询接口必须返回标准分页格式。

#### 分页响应体定义

```java
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PageResult<T> {

    /** 当前页码 */
    private Integer page;

    /** 每页大小 */
    private Integer size;

    /** 总记录数 */
    private Long total;

    /** 总页数 */
    private Integer totalPages;

    /** 数据列表 */
    private List<T> records;

    public static <T> PageResult<T> of(Integer page, Integer size, Long total, List<T> records) {
        int totalPages = (int) Math.ceil((double) total / size);
        return new PageResult<>(page, size, total, totalPages, records);
    }
}
```

#### Controller 使用

```java
@GetMapping
public Result<PageResult<UserVO>> list(@RequestParam(defaultValue = "1") Integer page,
                                        @RequestParam(defaultValue = "20") Integer size,
                                        @RequestParam(required = false) String keyword) {
    PageResult<UserVO> result = userService.search(keyword, page, size);
    return Result.success(result);
}
```

#### 分页响应 JSON 示例

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {
    "page": 1,
    "size": 20,
    "total": 156,
    "totalPages": 8,
    "records": [
      { "id": 1, "username": "zhangsan", "email": "zhangsan@example.com" },
      { "id": 2, "username": "lisi", "email": "lisi@example.com" }
    ]
  },
  "timestamp": 1700000000000
}
```

## 检查清单

- [ ] 所有 Controller 方法返回值是否使用 `Result<T>` 包装？
- [ ] 是否建立了统一的错误码枚举 `ErrorCode`？
- [ ] 错误码是否按模块分段管理？
- [ ] 是否定义了 `BusinessException` 并配合全局异常处理器？
- [ ] 分页接口是否使用 `PageResult<T>` 包装列表数据？
- [ ] 响应体是否包含了 `timestamp` 字段？
