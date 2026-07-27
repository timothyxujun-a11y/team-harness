# 旧版兼容性

## LEGACY-COMPAT-001: 测试框架必须使用 JUnit 4

遗留项目必须使用 JUnit 4（`junit:junit:4.x`）作为测试框架，禁止引入 JUnit 5（`org.junit.jupiter`），确保与旧版 Maven Surefire/Failsafe 插件兼容。

### 错误示例

```xml
<!-- 错误：使用 JUnit 5 依赖 -->
<dependency>
    <groupId>org.junit.jupiter</groupId>
    <artifactId>junit-jupiter</artifactId>
    <version>5.9.2</version>
    <scope>test</scope>
</dependency>
```

```java
// 错误：使用 JUnit 5 注解
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import static org.junit.jupiter.api.Assertions.assertEquals;

class OrderServiceTest {

    @BeforeEach
    void setUp() {
        // ...
    }

    @Test
    void testCreateOrder() {
        assertEquals(1, result.size());
    }
}
```

### 正确示例

```xml
<!-- 正确：使用 JUnit 4 依赖 -->
<dependency>
    <groupId>junit</groupId>
    <artifactId>junit</artifactId>
    <version>4.13.2</version>
    <scope>test</scope>
</dependency>
```

```java
// 正确：使用 JUnit 4 注解
import org.junit.Test;
import org.junit.Before;
import static org.junit.Assert.assertEquals;

public class OrderServiceTest {

    @Before
    public void setUp() {
        // ...
    }

    @Test
    public void testCreateOrder() {
        assertEquals(1, result.size());
    }
}
```

### JUnit 4 vs JUnit 5 对照表

| 特性 | JUnit 4 | JUnit 5 |
|------|---------|---------|
| 包名 | `org.junit` | `org.junit.jupiter.api` |
| 测试注解 | `@Test` | `@Test` |
| 前置方法 | `@Before` | `@BeforeEach` |
| 后置方法 | `@After` | `@AfterEach` |
| 类前置 | `@BeforeClass` | `@BeforeAll` |
| 断言 | `org.junit.Assert.*` | `org.junit.jupiter.api.Assertions.*` |
| 测试类 | 无强制要求（但建议 public） | 无强制要求 |
| 测试方法 | 必须 `public` | 可省略 `public` |

### 检查要点

- `pom.xml` 中测试依赖必须为 `junit:junit:4.x`，禁止 `org.junit.jupiter`
- 测试类 import 必须使用 `org.junit.Test`、`org.junit.Before` 等 JUnit 4 包
- 测试方法必须为 `public void`
- 断言方法使用 `org.junit.Assert.*`
- 若使用 Mockito，推荐 `mockito-core:2.x` 版本（兼容 JUnit 4）

---

## LEGACY-COMPAT-002: Maven 插件版本必须兼容 Java 8 和旧版 Maven

Maven 编译插件、Surefire 等插件版本必须选择兼容 JDK 8 的版本，禁止使用仅支持 JDK 11+ 的插件版本。`maven-compiler-plugin` 不超过 3.8.1。

### 兼容版本参考

| 插件 | 兼容 JDK 8 的最高版本 | 说明 |
|------|----------------------|------|
| `maven-compiler-plugin` | 3.8.1 | 3.8.1+ 需要 JDK 11+ 运行 |
| `maven-surefire-plugin` | 3.0.0-M9 | 3.0.0+ 部分版本需要 JDK 11+ |
| `maven-failsafe-plugin` | 3.0.0-M9 | 同 Surefire |
| `maven-jar-plugin` | 3.2.0 | 3.2.2+ 需要 JDK 11+ |
| `maven-shade-plugin` | 3.2.4 | 3.3.0+ 需要 JDK 11+ |
| `maven-source-plugin` | 3.2.1 | 3.3.0+ 需要 JDK 11+ |

### 错误示例

```xml
<!-- 错误：使用不兼容 JDK 8 的插件版本 -->
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-compiler-plugin</artifactId>
    <version>3.11.0</version>  <!-- 需要 JDK 11+ -->
    <configuration>
        <release>8</release>   <!-- release 标签需要 JDK 9+ -->
    </configuration>
</plugin>
```

### 正确示例

```xml
<build>
    <plugins>
        <!-- 编译插件：3.8.1 兼容 JDK 8 -->
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-compiler-plugin</artifactId>
            <version>3.8.1</version>
            <configuration>
                <source>1.8</source>
                <target>1.8</target>
                <encoding>UTF-8</encoding>
                <!-- 禁止使用 <release> 标签，该标签需要 JDK 9+ -->
            </configuration>
        </plugin>

        <!-- Surefire 测试插件 -->
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-surefire-plugin</artifactId>
            <version>3.0.0-M9</version>
        </plugin>

        <!-- 打包插件 -->
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-jar-plugin</artifactId>
            <version>3.2.0</version>
        </plugin>

        <!-- Shade 插件 -->
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-shade-plugin</artifactId>
            <version>3.2.4</version>
        </plugin>
    </plugins>
</build>
```

### 检查要点

- `maven-compiler-plugin` 版本不超过 3.8.1
- 编译配置使用 `<source>1.8</source>` 和 `<target>1.8</target>`，禁止使用 `<release>` 标签
- 所有 Maven 插件版本需验证在 JDK 8 环境下可正常运行
- 新增插件依赖时需检查其最低 JDK 要求
- CI 环境必须使用 JDK 8 构建，确保兼容性
- `pom.xml` 中 `maven.compiler.source` / `maven.compiler.target` 属性应设为 `1.8`
