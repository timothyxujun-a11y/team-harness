# 参数校验规范

> 规则：HTTP-VAL-001 / HTTP-VAL-002 | 严重级别：error / warning

## 概述

所有 Controller 入参必须进行校验，推荐使用 JSR-303 Bean Validation 标准注解。特殊校验逻辑应封装为自定义校验注解，保持代码可维护性。

## 规则详情

### 1. 使用 JSR-303 注解校验

在 DTO / Request 对象上使用标准校验注解，通过 `@Valid` 或 `@Validated` 触发校验。

#### 常用校验注解

| 注解 | 说明 | 示例 |
|------|------|------|
| `@NotNull` | 值不能为 null | `@NotNull(message = "ID 不能为空")` |
| `@NotEmpty` | 字符串/集合不能为 null 且不能为空 | `@NotEmpty(message = "名称不能为空")` |
| `@NotBlank` | 字符串不能为 null 且去除空格后不能为空 | `@NotBlank(message = "用户名不能为空")` |
| `@Size` | 字符串/集合大小范围 | `@Size(min = 1, max = 100, message = "...")` |
| `@Min` / `@Max` | 数值最小/最大值 | `@Min(value = 1, message = "页码最小为 1")` |
| `@Email` | 邮箱格式 | `@Email(message = "邮箱格式不正确")` |
| `@Pattern` | 正则匹配 | `@Pattern(regexp = "^1[3-9]\\d{9}$")` |
| `@Positive` / `@Negative` | 正数/负数 | `@Positive(message = "金额必须为正数")` |
| `@Range` | 数值范围（Hibernate Validator） | `@Range(min = 0, max = 150, message = "...")` |

#### 正例

```java
// Request DTO
@Data
public class CreateUserRequest {

    @NotBlank(message = "用户名不能为空")
    @Size(min = 2, max = 20, message = "用户名长度需在 2-20 之间")
    private String username;

    @NotBlank(message = "手机号不能为空")
    @Pattern(regexp = "^1[3-9]\\d{9}$", message = "手机号格式不正确")
    private String mobile;

    @Email(message = "邮箱格式不正确")
    private String email;

    @NotNull(message = "年龄不能为空")
    @Range(min = 0, max = 150, message = "年龄需在 0-150 之间")
    private Integer age;
}
```

```java
// Controller 使用 @Valid 触发校验
@RestController
@RequestMapping("/api/users")
public class UserController {

    @PostMapping
    public Result<UserVO> create(@RequestBody @Valid CreateUserRequest request) {
        UserVO vo = userService.createUser(request);
        return Result.success(vo);
    }
}
```

#### 分组校验

当同一 DTO 在不同场景下需要不同校验规则时，使用分组校验：

```java
// 定义分组接口
public interface CreateGroup {}
public interface UpdateGroup {}

@Data
public class UserRequest {

    @NotNull(message = "ID 不能为空", groups = UpdateGroup.class)
    private Long id;

    @NotBlank(message = "用户名不能为空", groups = {CreateGroup.class, UpdateGroup.class})
    @Size(min = 2, max = 20, groups = {CreateGroup.class, UpdateGroup.class})
    private String username;
}

// Controller
@PostMapping
public Result<UserVO> create(@RequestBody @Validated(CreateGroup.class) UserRequest request) { ... }

@PutMapping("/{id}")
public Result<UserVO> update(@RequestBody @Validated(UpdateGroup.class) UserRequest request) { ... }
```

### 2. 统一异常处理

校验失败时，Spring 会抛出 `MethodArgumentNotValidException`。必须使用全局异常处理器统一处理，返回友好提示：

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Result<Void> handleValidationException(MethodArgumentNotValidException ex) {
        String message = ex.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining("; "));
        return Result.fail(ErrorCode.PARAM_ERROR.getCode(), message);
    }
}
```

### 3. 自定义校验注解（HTTP-VAL-002）

当 JSR-303 内置注解无法满足需求时，应在 `common` 模块封装自定义校验注解。

#### 示例：枚举值校验

```java
// 1. 定义注解
@Target({ElementType.FIELD})
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = EnumValueValidator.class)
@Documented
public @interface EnumValue {

    String message() default "枚举值不合法";

    Class<?>[] groups() default {};

    Class<? extends Payload>[] payload() default {};

    Class<? extends Enum<?>> enumClass();

    String fieldName() default "code";
}
```

```java
// 2. 实现校验器
public class EnumValueValidator implements ConstraintValidator<EnumValue, Object> {

    private Set<Object> validValues = new HashSet<>();

    @Override
    public void initialize(EnumValue constraintAnnotation) {
        Class<? extends Enum<?>> enumClass = constraintAnnotation.enumClass();
        String fieldName = constraintAnnotation.fieldName();
        try {
            Method getter = enumClass.getMethod("get" +
                    Character.toUpperCase(fieldName.charAt(0)) + fieldName.substring(1));
            for (Enum<?> enumConstant : enumClass.getEnumConstants()) {
                validValues.add(getter.invoke(enumConstant));
            }
        } catch (Exception e) {
            throw new RuntimeException("枚举校验器初始化失败", e);
        }
    }

    @Override
    public boolean isValid(Object value, ConstraintValidatorContext context) {
        return value == null || validValues.contains(value);
    }
}
```

```java
// 3. 使用自定义注解
@Data
public class CreateOrderRequest {

    @EnumValue(enumClass = OrderStatusEnum.class, fieldName = "code",
               message = "订单状态不合法")
    private String status;
}
```

#### 示例：手机号校验（项目级通用注解）

```java
@Target({ElementType.FIELD})
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = MobileValidator.class)
@Documented
public @interface Mobile {

    String message() default "手机号格式不正确";

    Class<?>[] groups() default {};

    Class<? extends Payload>[] payload() default {};
}

public class MobileValidator implements ConstraintValidator<Mobile, String> {

    private static final Pattern MOBILE_PATTERN = Pattern.compile("^1[3-9]\\d{9}$");

    @Override
    public boolean isValid(String value, ConstraintValidatorContext context) {
        if (value == null || value.isEmpty()) {
            return true; // @NotBlank 单独处理非空
        }
        return MOBILE_PATTERN.matcher(value).matches();
    }
}
```

## 检查清单

- [ ] 所有 Controller 入参是否使用了 `@Valid` 或 `@Validated`？
- [ ] DTO/Request 对象的字段是否添加了对应的校验注解？
- [ ] 校验注解的 `message` 属性是否提供了友好的中文提示？
- [ ] 是否配置了全局异常处理器处理 `MethodArgumentNotValidException`？
- [ ] 项目级通用校验逻辑是否已封装为自定义注解？
- [ ] 不同场景的校验是否使用了分组校验隔离？
