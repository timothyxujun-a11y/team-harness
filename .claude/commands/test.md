---
description: 按改动范围运行相关测试。无参数时运行全量测试。
---

# /test 命令

根据当前代码改动，识别受影响的测试类并执行。

## 执行步骤

1. **检测构建工具**：检查项目根目录
   - 有 `pom.xml` → Maven（优先使用 `./mvnw`）
   - 有 `build.gradle` 或 `build.gradle.kts` → Gradle（优先使用 `./gradlew`）

2. **识别改动范围**：
   - 执行 `git diff --name-only` 获取改动的文件列表
   - 从改动的 Java 文件中提取类名
   - 为每个改动的类找到对应的测试类（`XxxTest`）

3. **执行测试**：

   **如果传入了参数**（如 `/test OrderServiceTest`）：
   - Maven: `mvn test -Dtest=参数值`
   - Gradle: `./gradlew test --tests "*参数值*"`

   **如果未传入参数**：
   - 有改动的测试类：逐个执行
     - Maven: `mvn test -Dtest=Test1,Test2`
     - Gradle: `./gradlew test --tests "*Test1*" --tests "*Test2*"`
   - 无改动的测试类：运行全量测试
     - Maven: `mvn test`
     - Gradle: `./gradlew test`

4. **输出结果**：
   - 测试总数 / 通过数 / 失败数
   - 失败测试的详细信息（类名、方法名、失败原因）
   - 如有失败，分析原因并给出修复建议

## 注意事项

- 测试执行超时上限 5 分钟，超时则终止并报告
- 如果编译失败，先报告编译错误，不执行测试
- 中文输出结果
