# 项目架构说明 — http-service-example

## 技术选型

| 维度 | 选型 | 版本 |
|------|------|------|
| 语言 | Java | 17 |
| 框架 | Spring Boot | 3.x |
| 构建工具 | Maven | 3.9+ |
| ORM | MyBatis-Plus | 3.5.x |
| 对象映射 | MapStruct | 1.5.x |
| 参数校验 | Bean Validation | 3.0 (Jakarta Validation) |
| 测试框架 | JUnit 4 + Mockito + AssertJ | — |
| 覆盖率 | JaCoCo + diff-cover | 0.8.x |

## 包结构

```
com.example.http
├── controller/              # HTTP 入口层
│   ├── user/
│   │   ├── UserController.java          # 用户接口（v1）
│   │   └── UserV2Controller.java        # 用户接口（v2，如有）
│   └── order/
│       └── OrderController.java         # 订单接口
├── service/                 # 业务逻辑层
│   ├── user/
│   │   ├── IUserService.java            # 用户服务接口
│   │   └── impl/
│   │       └── UserServiceImpl.java     # 用户服务实现
│   └── order/
│       ├── IOrderService.java           # 订单服务接口
│       └── impl/
│           └── OrderServiceImpl.java    # 订单服务实现
├── mapper/                  # 数据访问层
│   ├── UserMapper.java
│   ├── OrderMapper.java
│   └── OrderItemMapper.java
├── entity/                  # 数据库实体
│   ├── User.java
│   ├── Order.java
│   └── OrderItem.java
├── dto/                     # 数据传输对象
│   ├── user/
│   │   ├── UserCreateDTO.java
│   │   ├── UserUpdateDTO.java
│   │   └── UserQueryDTO.java
│   └── order/
│       ├── OrderQueryDTO.java
│       └── OrderVO.java
├── convert/                 # 对象转换器（MapStruct）
│   ├── UserConvert.java
│   └── OrderConvert.java
├── enums/                   # 枚举
│   ├── UserStatusEnum.java
│   └── OrderStatusEnum.java
├── config/                  # 配置类
│   ├── WebMvcConfig.java
│   └── MybatisPlusConfig.java
├── common/                  # 通用组件
│   ├── response/
│   │   ├── ApiResponse.java            # 统一响应体
│   │   └── PageResult.java             # 分页响应体
│   ├── exception/
│   │   ├── BusinessException.java
│   │   └── GlobalExceptionHandler.java # 全局异常处理
│   └── constant/
│       └── ApiConstant.java
└── Application.java         # 启动类
```

## 分层依赖方向

```
controller → service → mapper → entity
     │           │
     │           └── convert（DTO ↔ Entity 转换）
     │
     └── dto（入参/出参）
```

**禁止反向依赖**：mapper 不得引用 service，entity 不得引用 service/mapper/controller。

## 关键设计决策

### 统一响应体

所有接口返回 `ApiResponse<T>`：

```java
public class ApiResponse<T> {
    private int code;        // 0=成功，非 0=错误码
    private String message;  // 提示信息
    private T data;          // 业务数据
}
```

### 全局异常处理

- `BusinessException`：业务异常，返回 HTTP 200 + 错误码
- `MethodArgumentNotValidException`：参数校验失败，返回 HTTP 400
- `Exception`：未知异常，返回 HTTP 500 + 通用错误信息

### 分页查询

- 使用 MyBatis-Plus `Page` 分页插件
- Controller 接收 `pageNum`（从 1 开始）和 `pageSize`
- Service 返回 `PageResult<T>`，包含 `total`、`pages`、`records`

### MapStruct 转换

- 每个 `convert/` 类为 MapStruct 接口（`@Mapper(componentModel = "spring")`）
- Entity → VO、DTO → Entity 的转换集中在 Convert 类
- **禁止**在 Service 中散落 setter 转换

## 测试架构

```
src/test/java/com/example/http
├── service/
│   ├── user/
│   │   └── UserServiceImplTest.java    # 纯单测，Mock Mapper
│   └── order/
│       └── OrderServiceImplTest.java
└── controller/
    └── user/
        └── UserControllerTest.java      # MockMvc 测试
```

- Service 层：JUnit 4 + Mockito，Mock Mapper 层，禁止启动 Spring 容器
- Controller 层：使用 `MockMvc` + `@WebMvcTest`，仅加载 Web 层
- 增量覆盖率阈值：80%（JaCoCo + diff-cover）

## 配置管理

| 配置类型 | 管理方式 |
|----------|----------|
| 业务参数（分页大小、超时时间等） | `@ConfigurationProperties` + `XxxProperties.java` |
| 数据库连接 | `application.yml` + 环境变量 |
| 敏感信息（密码、密钥） | 环境变量 / 配置中心，禁止写入代码 |
| 多环境配置 | `application-dev.yml` / `application-prod.yml` |
