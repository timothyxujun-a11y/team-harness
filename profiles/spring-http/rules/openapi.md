# OpenAPI 文档规范

> 规则：HTTP-DOC-001 | 严重级别：warning

## 概述

所有 API 接口必须添加 OpenAPI 文档注解，确保能通过 Swagger UI 或 Knife4j 自动生成可交互的 API 文档，方便前后端联调和接口管理。

## 规则详情

### 1. 依赖配置

#### Spring Boot 2.x（SpringDoc）

```xml
<dependency>
    <groupId>org.springdoc</groupId>
    <artifactId>springdoc-openapi-ui</artifactId>
    <version>1.7.0</version>
</dependency>
```

```yaml
# application.yml
springdoc:
  api-docs:
    path: /v3/api-docs
  swagger-ui:
    path: /swagger-ui.html
  group-configs:
    - group: default
      paths-to-match: /**
```

#### Spring Boot 3.x（SpringDoc）

```xml
<dependency>
    <groupId>org.springdoc</groupId>
    <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
    <version>2.3.0</version>
</dependency>
```

#### Knife4j 增强（可选）

```xml
<dependency>
    <groupId>com.github.xiaoymin</groupId>
    <artifactId>knife4j-openapi3-spring-boot-starter</artifactId>
    <version>4.4.0</version>
</dependency>
```

### 2. 配置类

```java
@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("用户服务 API 文档")
                        .description("用户服务 RESTful API 接口文档")
                        .version("1.0.0")
                        .contact(new Contact()
                                .name("开发团队")
                                .email("dev@company.com")))
                .externalDocs(new ExternalDocumentation()
                        .description("Wiki 文档")
                        .url("https://wiki.company.com"));
    }
}
```

### 3. Controller 注解

每个 Controller 类和方法都必须添加 Swagger 注解：

```java
@RestController
@RequestMapping("/api/users")
@Tag(name = "用户管理", description = "用户信息的增删改查接口")
public class UserController {

    @Operation(summary = "获取用户详情", description = "根据用户 ID 查询用户详细信息")
    @Parameters({
            @Parameter(name = "id", description = "用户 ID", required = true, example = "1")
    })
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "查询成功",
                    content = @Content(schema = @Schema(implementation = UserVO.class))),
            @ApiResponse(responseCode = "40004", description = "用户不存在")
    })
    @GetMapping("/{id}")
    public Result<UserVO> getById(@PathVariable Long id) {
        UserVO vo = userService.getById(id);
        return Result.success(vo);
    }

    @Operation(summary = "分页查询用户列表", description = "根据关键词分页搜索用户")
    @GetMapping
    public Result<PageResult<UserVO>> list(
            @Parameter(description = "搜索关键词（用户名/手机号）", example = "zhang")
            @RequestParam(required = false) String keyword,
            @Parameter(description = "页码（从 1 开始）", example = "1")
            @RequestParam(defaultValue = "1") Integer page,
            @Parameter(description = "每页大小", example = "20")
            @RequestParam(defaultValue = "20") Integer size
    ) {
        PageResult<UserVO> result = userService.search(keyword, page, size);
        return Result.success(result);
    }

    @Operation(summary = "创建用户", description = "新建用户，用户名和手机号不可重复")
    @PostMapping
    public Result<UserVO> create(
            @RequestBody @Valid CreateUserRequest request) {
        UserVO vo = userService.createUser(request);
        return Result.success(vo);
    }
}
```

### 4. DTO 字段注解

```java
@Data
@Schema(description = "创建用户请求参数")
public class CreateUserRequest {

    @Schema(description = "用户名", required = true, example = "zhangsan",
            minLength = 2, maxLength = 20)
    @NotBlank(message = "用户名不能为空")
    @Size(min = 2, max = 20)
    private String username;

    @Schema(description = "手机号", required = true, example = "13800138000")
    @NotBlank(message = "手机号不能为空")
    @Pattern(regexp = "^1[3-9]\\d{9}$")
    private String mobile;

    @Schema(description = "邮箱", example = "zhangsan@example.com")
    @Email
    private String email;

    @Schema(description = "年龄", example = "25", minimum = "0", maximum = "150")
    @Range(min = 0, max = 150)
    private Integer age;

    @Schema(description = "性别（0-未知 1-男 2-女）", example = "1",
            allowableValues = {"0", "1", "2"})
    private Integer gender;
}
```

```java
@Data
@Schema(description = "用户信息响应")
public class UserVO {

    @Schema(description = "用户 ID", example = "1")
    private Long id;

    @Schema(description = "用户名", example = "zhangsan")
    private String username;

    @Schema(description = "手机号", example = "13800138000")
    private String mobile;

    @Schema(description = "邮箱", example = "zhangsan@example.com")
    private String email;

    @Schema(description = "年龄", example = "25")
    private Integer age;

    @Schema(description = "创建时间", example = "2024-01-01 12:00:00")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime createTime;
}
```

### 5. 枚举字段注解

对于枚举类型字段，使用 `@Schema` 明确标注可选值：

```java
@Data
@Schema(description = "订单请求参数")
public class CreateOrderRequest {

    @Schema(description = "支付方式", example = "WECHAT",
            allowableValues = {"WECHAT", "ALIPAY", "BANK_CARD", "BALANCE"})
    @NotNull(message = "支付方式不能为空")
    private PayMethodEnum payMethod;
}
```

### 6. 通用参数处理

对于分页参数等通用参数，可定义通用接口避免重复注解：

```java
@Schema(description = "分页查询参数")
public interface PageParam {

    @Schema(description = "页码（从 1 开始）", example = "1")
    @RequestParam(defaultValue = "1")
    @Positive(message = "页码最小为 1")
    Integer getPage();

    @Schema(description = "每页大小", example = "20")
    @RequestParam(defaultValue = "20")
    @Positive(message = "每页大小最小为 1")
    @Max(value = 100, message = "每页大小最大为 100")
    Integer getSize();
}
```

### 7. 权限控制注解

对需要认证的接口添加安全注解：

```java
@Operation(
    summary = "删除用户",
    description = "管理员删除指定用户",
    security = @SecurityRequirement(name = "BearerAuth")
)
@DeleteMapping("/{id}")
@PreAuthorize("hasRole('ADMIN')")
public Result<Void> delete(@PathVariable Long id) {
    userService.delete(id);
    return Result.success();
}
```

### 8. 访问文档

配置完成后可通过以下地址访问：

| 组件 | 访问地址 |
|------|----------|
| Swagger UI（SpringDoc） | `http://localhost:8080/swagger-ui.html` |
| Knife4j UI | `http://localhost:8080/doc.html` |
| OpenAPI JSON | `http://localhost:8080/v3/api-docs` |

## 检查清单

- [ ] 是否引入了 SpringDoc 或 Knife4j 依赖？
- [ ] Controller 类是否添加了 `@Tag` 注解？
- [ ] Controller 方法是否添加了 `@Operation` 注解？
- [ ] 路径参数是否添加了 `@Parameter` 注解？
- [ ] DTO 类是否添加了 `@Schema(description = "...")` 注解？
- [ ] DTO 字段是否添加了对应的描述和示例？
- [ ] 接口返回类型是否标注了 `@ApiResponse`？
- [ ] 枚举字段是否标注了 `allowableValues`？
- [ ] `/doc.html` 或 `/swagger-ui.html` 是否可正常访问并展示文档？
