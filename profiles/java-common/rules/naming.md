# 命名规范

> **适用规则**: JAVA-CODE-001, JAVA-CODE-002, JAVA-CODE-003

---

## JAVA-CODE-001: 类命名使用 PascalCase

### 规则说明

所有类、接口、枚举、注解类型必须使用 **PascalCase**（大驼峰）命名法。名称应为名词或名词短语，准确表达类型含义。

### 命名要求

| 类型 | 命名格式 | 示例 |
|------|---------|------|
| 普通类 | PascalCase | `UserService`, `OrderProcessor` |
| 接口 | PascalCase | `Repository`, `PaymentGateway` |
| 枚举 | PascalCase | `OrderStatus`, `PaymentType` |
| 注解 | PascalCase | `@AuditLog`, `@Retryable` |
| 抽象类 | Abstract + PascalCase | `AbstractRepository`, `AbstractBaseEntity` |
| 异常类 | 名称 + Exception | `BusinessException`, `InvalidParameterException` |
| 测试类 | 被测类名 + Test | `UserServiceTest`, `OrderProcessorTest` |

### 正确示例

```java
// 正确：PascalCase，名词短语
public class UserAccountService { }

public interface OrderRepository { }

public enum OrderStatus {
    PENDING, PAID, SHIPPED, DELIVERED
}

public abstract class AbstractBaseEntity { }

public class BusinessException extends RuntimeException { }
```

### 错误示例

```java
// 错误：使用了下划线
public class User_Account_Service { }

// 错误：首字母小写
public class userService { }

// 错命：缩写不清晰
public class UsrSvc { }
```

---

## JAVA-CODE-002: 方法命名使用 camelCase

### 规则说明

方法名使用 **camelCase**（小驼峰）命名法，应以动词开头，准确表达方法行为意图。

### 命名前缀约定

| 场景 | 前缀 | 示例 |
|------|------|------|
| 查询 | get/find/query | `getUserById`, `findActiveOrders`, `queryByName` |
| 判断 | is/has/can/should | `isValid`, `hasPermission`, `canAccess` |
| 操作 | save/update/delete/create | `createOrder`, `updateUser`, `deleteById` |
| 转换 | to/convert/transform | `toString`, `convertToDTO`, `transformEntity` |
| 校验 | validate/check/verify | `validateInput`, `checkPermission` |

### 正确示例

```java
public class UserService {

    // 正确：动词开头，camelCase
    public User getUserById(Long id) { }

    public boolean isValid(User user) { }

    public void updatePassword(Long userId, String newPassword) { }

    public UserDTO convertToDTO(User entity) { }

    public void validateCreateRequest(CreateUserRequest request) { }
}
```

### 错误示例

```java
// 错误：使用了下划线
public User get_user_by_id(Long id) { }

// 错误：不是动词开头
public User id(Long id) { }

// 错误：PascalCase 用于方法
public User GetUserById(Long id) { }
```

---

## JAVA-CODE-003: 常量与包命名规范

### 规则说明

常量使用 **UPPER_SNAKE_CASE**（全大写下划线分隔），包名全小写不使用下划线，测试类以 `Test` 结尾。

### 常量命名

```java
public class Constants {

    // 正确：UPPER_SNAKE_CASE
    public static final int MAX_RETRY_COUNT = 3;
    public static final String DEFAULT_CHARSET = "UTF-8";
    public static final long CACHE_EXPIRE_SECONDS = 3600L;

    // 错误：camelCase 用于常量
    // public static final int maxRetryCount = 3;
}
```

### 包命名

```java
// 正确：全小写，不使用下划线或大写字母
package com.company.project.user.service;
package com.company.project.order.controller;

// 错误：使用了下划线
// package com.company.project.user_service;

// 错误：使用了大写
// package com.company.project.UserService;
```

### 测试类命名

```java
// 正确：被测类名 + Test
public class UserServiceTest { }
public class OrderProcessorTest { }

// 错误：缺少 Test 后缀
// public class UserServiceTests { }  // 注意：本规范使用 Test 而非 Tests
// public class UserServiceSpec { }
```
