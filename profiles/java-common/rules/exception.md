# 异常处理规范

> **适用规则**: JAVA-EXC-001, JAVA-EXC-002, JAVA-EXC-003

---

## JAVA-EXC-001: 自定义业务异常继承 RuntimeException

### 规则说明

自定义业务异常应继承 **RuntimeException**（非受检异常），而非 Exception（受检异常）。避免在方法签名上强制声明 `throws`，减少不必要的方法签名耦合。

### 正确示例

```java
// 正确：继承 RuntimeException
public class BusinessException extends RuntimeException {

    private String errorCode;

    public BusinessException(String errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
    }

    public BusinessException(String errorCode, String message, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
    }

    public String getErrorCode() {
        return errorCode;
    }
}

// 正确：不同业务场景可以分层继承
public class UserNotFoundException extends BusinessException {

    public UserNotFoundException(Long userId) {
        super("USER_NOT_FOUND", "用户不存在, userId=" + userId);
    }
}
```

### 错误示例

```java
// 错误：继承 Exception，强制调用方声明 throws
public class BusinessException extends Exception {
    public BusinessException(String message) {
        super(message);
    }
}

// 错误：方法签名被迫声明 throws，传播成本高
public User getUser(Long id) throws BusinessException {
    // ...
}
```

### 设计原则

- 业务异常统一继承 `RuntimeException`
- 按业务域细分异常类型，如 `UserNotFoundException`、`InsufficientBalanceException`
- 异常构造器应支持传入 `cause`，保留原始异常链
- 每个异常携带错误码 `errorCode`，便于前端/日志定位

---

## JAVA-EXC-002: 禁止捕获异常后忽略

### 规则说明

**不得**在 `catch` 块中空处理或仅打印日志后继续执行。捕获异常后必须进行合理处理：恢复、重试、重新抛出或转换为业务异常。

### 正确示例

```java
// 正确：转换为业务异常重新抛出
try {
    String result = externalApi.call();
} catch (IOException e) {
    throw new BusinessException("API_CALL_FAILED", "调用外部接口失败", e);
}

// 正确：有恢复逻辑
try {
    value = Integer.parseInt(str);
} catch (NumberFormatException e) {
    value = 0;
    log.warn("数值解析失败, 使用默认值, input={}", str);
}

// 正确：重试逻辑
int retry = 0;
while (retry < MAX_RETRY) {
    try {
        return doOperation();
    } catch (TemporaryException e) {
        retry++;
        if (retry >= MAX_RETRY) {
            throw new BusinessException("OPERATION_FAILED", "操作重试失败", e);
        }
    }
}
```

### 错误示例

```java
// 错误：捕获后空处理（吞掉异常）
try {
    doSomething();
} catch (Exception e) {
    // 什么都不做
}

// 错误：仅打印堆栈，不处理
try {
    doSomething();
} catch (Exception e) {
    e.printStackTrace();
}

// 错误：仅记录日志，不恢复也不抛出
try {
    doSomething();
} catch (Exception e) {
    log.error("error", e);
    // 继续往下执行，可能导致后续逻辑出错
}
```

---

## JAVA-EXC-003: 异常信息必须包含上下文与 Controller 统一处理

### 规则说明

异常消息必须包含**业务上下文信息**（如 ID、参数值等），便于问题定位。Controller 层应使用 `@ControllerAdvice` + `@ExceptionHandler` 进行统一异常处理。

### 异常信息包含上下文

```java
// 正确：包含上下文信息
public User getUserById(Long userId) {
    User user = userRepository.findById(userId);
    if (user == null) {
        throw new UserNotFoundException(userId);
    }
    return user;
}

// BusinessException 的 message 应包含关键参数
throw new BusinessException(
    "ORDER_STATUS_ERROR",
    String.format("订单状态非法, orderId=%d, currentStatus=%s, expectedStatus=%s",
        orderId, currentStatus, expectedStatus)
);
```

```java
// 错误：异常信息没有上下文
throw new BusinessException("ERROR", "操作失败");

// 错误：异常信息过于笼统
throw new RuntimeException("something wrong");
```

### Controller 统一异常处理

```java
@ControllerAdvice
public class GlobalExceptionHandler {

    // 处理业务异常
    @ExceptionHandler(BusinessException.class)
    @ResponseBody
    public ResponseEntity<ErrorResponse> handleBusinessException(BusinessException e) {
        log.warn("业务异常: code={}, message={}", e.getErrorCode(), e.getMessage());
        ErrorResponse response = new ErrorResponse(e.getErrorCode(), e.getMessage());
        return ResponseEntity.badRequest().body(response);
    }

    // 处理参数校验异常
    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseBody
    public ResponseEntity<ErrorResponse> handleValidationException(MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
            .map(fe -> fe.getField() + ": " + fe.getDefaultMessage())
            .collect(Collectors.joining(", "));
        log.warn("参数校验失败: {}", message);
        ErrorResponse response = new ErrorResponse("VALIDATION_ERROR", message);
        return ResponseEntity.badRequest().body(response);
    }

    // 兜底处理未知异常
    @ExceptionHandler(Exception.class)
    @ResponseBody
    public ResponseEntity<ErrorResponse> handleException(Exception e) {
        log.error("系统异常", e);
        ErrorResponse response = new ErrorResponse("SYSTEM_ERROR", "系统繁忙，请稍后重试");
        return ResponseEntity.internalServerError().body(response);
    }
}
```

### 统一响应结构

```java
public class ErrorResponse {

    private String code;
    private String message;
    private long timestamp;

    // 构造器、getter、setter
}
```

### 设计原则

- 业务异常信息必须包含关键参数（ID、状态值等），便于日志排查
- `@ControllerAdvice` 统一捕获，Controller 方法不应出现 `try-catch` 处理业务异常
- 对外返回友好错误信息，不暴露堆栈信息
- 未知异常统一兜底，返回通用提示
