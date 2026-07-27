# Controller 分层规范

> 规则：HTTP-ARCH-001 / HTTP-ARCH-002 / HTTP-ARCH-003 | 严重级别：error

## 概述

Controller 层是 HTTP API 的入口层，必须严格遵守职责边界，不得越权处理业务逻辑或直接访问数据层。

## 规则详情

### 1. Controller 职责边界

Controller 层的唯一职责是：

1. 接收请求参数
2. 对参数进行基础校验（`@Valid`）
3. 调用 Service 层方法
4. 封装并返回统一响应结果

Controller 不得：

- 编写业务判断逻辑（如 if-else 业务流程分支）
- 进行数据转换加工（应委托给 Service 或 Converter）
- 直接进行跨服务调用（应通过 Service 调用 Feign/RPC 客户端）

#### 反例

```java
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    @Autowired
    private OrderMapper orderMapper;  // 违反分层：不应该直接注入 Mapper

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @PostMapping
    public Result<OrderVO> create(@RequestBody @Valid CreateOrderRequest request) {
        // 违反：Controller 编写了业务逻辑
        BigDecimal totalAmount = request.getItems().stream()
                .map(item -> item.getPrice().multiply(BigDecimal.valueOf(item.getQuantity())))
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        if (totalAmount.compareTo(new BigDecimal("1000")) > 0) {
            totalAmount = totalAmount.multiply(new BigDecimal("0.9")); // 业务折扣逻辑
        }

        // 违反：Controller 直接操作数据库
        Order order = new Order();
        order.setUserId(getCurrentUserId());
        order.setTotalAmount(totalAmount);
        orderMapper.insert(order);

        return Result.success(OrderConverter.INSTANCE.toVO(order));
    }
}
```

#### 正例

```java
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    @Autowired
    private OrderService orderService;

    @PostMapping
    public Result<OrderVO> create(@RequestBody @Valid CreateOrderRequest request) {
        OrderVO orderVO = orderService.createOrder(request);
        return Result.success(orderVO);
    }
}
```

### 2. 禁止 Controller 直接访问数据库

Controller 不得依赖以下组件：

- `*Mapper` / `*Repository` / `*DAO`（数据访问层）
- `JdbcTemplate` / `NamedParameterJdbcTemplate`
- `EntityManager` / `Session`（JPA/Hibernate）
- `RedisTemplate` / `MongoTemplate` 等直接数据操作组件

所有数据访问必须通过 Service 层完成。

```java
// 错误：Controller 直接注入 Repository
@Autowired
private UserRepository userRepository;

// 正确：通过 Service 层访问
@Autowired
private UserService userService;
```

### 3. 注解规范

每个 Controller 类必须满足：

- 使用 `@RestController` 注解（而非 `@Controller` + `@ResponseBody`）
- 使用 `@RequestMapping` 定义类级别路径前缀

```java
// 正确
@RestController
@RequestMapping("/api/users")
public class UserController {
    // ...
}

// 错误：缺少 RequestMapping 前缀会导致路径管理混乱
@RestController
public class UserController {
    @GetMapping("/api/users")  // 重复的全路径不利于维护
    // ...
}
```

### 4. 方法的 HTTP 方法注解

推荐使用组合注解：

| HTTP 方法 | 推荐注解 | 说明 |
|-----------|----------|------|
| GET | `@GetMapping` | 查询资源 |
| POST | `@PostMapping` | 创建资源 |
| PUT | `@PutMapping` | 全量更新 |
| PATCH | `@PatchMapping` | 部分更新 |
| DELETE | `@DeleteMapping` | 删除资源 |

### 4. Controller 内部方法拆分

当 Controller 中需要复用参数解析、权限校验等逻辑时，应提取为私有方法，而非将逻辑下沉到 Service 层中本该属于 Controller 层的职责：

```java
@RestController
@RequestMapping("/api/products")
public class ProductController {

    @Autowired
    private ProductService productService;

    @GetMapping("/{id}")
    public Result<ProductVO> getById(@PathVariable Long id) {
        checkPermission(id);  // 权限校验属于 Controller 层
        ProductVO vo = productService.getById(id);
        return Result.success(vo);
    }

    private void checkPermission(Long productId) {
        // 权限校验逻辑
    }
}
```

### 4. 参数绑定

Controller 方法参数绑定推荐方式：

```java
// 路径参数
@GetMapping("/{id}")
public Result<UserVO> getUser(@PathVariable Long id) { ... }

// 查询参数（简单参数）
@GetMapping
public Result<PageResult<UserVO>> list(@RequestParam String keyword,
                                        @RequestParam(defaultValue = "1") Integer page,
                                        @RequestParam(defaultValue = "20") Integer size) { ... }

// 请求体（复杂对象）
@PostMapping
public Result<UserVO> create(@RequestBody @Valid CreateUserRequest request) { ... }

// 表单参数（不推荐，除非文件上传等场景）
@PostMapping("/avatar")
public Result<String> uploadAvatar(@RequestParam("file") MultipartFile file) { ... }
```

## 检查清单

- [ ] Controller 是否只做参数接收、校验、Service 调用、结果返回？
- [ ] Controller 是否没有直接注入 Mapper/Repository/DAO？
- [ ] Controller 是否使用了 `@RestController` + `@RequestMapping`？
- [ ] Controller 中的业务逻辑是否已委托给 Service？
- [ ] 接口方法是否使用了正确的 HTTP 方法注解？
