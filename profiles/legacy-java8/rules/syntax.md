# Java 8 语法限制

## LEGACY-SYN-001: 禁止使用 Java 9+ 集合工厂方法

禁止使用 `List.of()`、`Map.of()`、`Set.of()` 等 Java 9+ 集合工厂方法，必须使用 `Collections.unmodifiableList()` 或 `Arrays.asList()` 等 Java 8 兼容写法。

### 禁止使用的 API

| API | 引入版本 |
|-----|----------|
| `List.of(...)` | Java 9 |
| `Set.of(...)` | Java 9 |
| `Map.of(...)` | Java 9 |
| `Map.entry(k, v)` | Java 9 |
| `List.copyOf()` | Java 10 |
| `Set.copyOf()` | Java 10 |
| `Map.copyOf()` | Java 10 |

### 错误示例

```java
// 错误：使用 Java 9+ 集合工厂方法，Java 8 下编译失败
List<String> names = List.of("Alice", "Bob", "Charlie");
Set<Integer> ids = Set.of(1, 2, 3);
Map<String, Integer> config = Map.of(
    "timeout", 3000,
    "retry", 3
);
```

### 正确示例

```java
// 不可变 List
List<String> names = Collections.unmodifiableList(
    Arrays.asList("Alice", "Bob", "Charlie")
);

// 不可变 Set
Set<Integer> ids = Collections.unmodifiableSet(
    new HashSet<>(Arrays.asList(1, 2, 3))
);

// 不可变 Map
Map<String, Integer> config = new HashMap<>();
config.put("timeout", 3000);
config.put("retry", 3);
Map<String, Integer> unmodifiableConfig = Collections.unmodifiableMap(config);

// 使用 Guava（如项目已依赖）
List<String> names = ImmutableList.of("Alice", "Bob", "Charlie");
Set<Integer> ids = ImmutableSet.of(1, 2, 3);
Map<String, Integer> config = ImmutableMap.of(
    "timeout", 3000,
    "retry", 3
);
```

### 检查要点

- 代码中不应出现 `List.of()`、`Set.of()`、`Map.of()` 调用
- 需要不可变集合时使用 `Collections.unmodifiableXxx()` 包装
- 可使用 Guava 的 `ImmutableList`/`ImmutableSet`/`ImmutableMap`（如项目已有依赖）
- `Arrays.asList()` 返回的是固定大小的 List，不支持 add/remove

---

## LEGACY-SYN-002: 禁止使用 var 关键字

禁止使用 Java 10+ 引入的 `var` 局部变量类型推断关键字，必须显式声明变量类型。

### 错误示例

```java
// 错误：使用 var 关键字，Java 8 下编译失败
var names = new ArrayList<String>();
var config = loadConfig();
var result = service.process(request);
var stream = list.stream().filter(x -> x > 0);
```

### 正确示例

```java
// 正确：显式声明变量类型
List<String> names = new ArrayList<>();
Map<String, Object> config = loadConfig();
ProcessResult result = service.process(request);
IntStream stream = list.stream().filter(x -> x > 0).mapToInt(Integer::intValue);
```

### 检查要点

- 代码中不应出现 `var` 关键字作为局部变量类型声明
- 所有局部变量必须显式声明类型
- 注意区分：`var` 在 Java 8 中不是关键字，但作为类型名使用会编译失败
- lambda 表达式参数类型推断不受此规则限制（如 `(x, y) -> x + y` 仍可使用）

---

## LEGACY-SYN-003: 禁止使用 Java 9+ Stream API 方法

禁止使用 `Stream.takeWhile()`、`dropWhile()`、`ofNullable()` 等 Java 9+ 新增方法，必须使用 Java 8 兼容的 Stream API 实现等价逻辑。

### 禁止使用的 Stream 方法

| 方法 | 引入版本 | 等价 Java 8 实现 |
|------|----------|------------------|
| `Stream.takeWhile(predicate)` | Java 9 | 遍历 + break 或使用第三方库 |
| `Stream.dropWhile(predicate)` | Java 9 | 遍历 + 标志位或使用第三方库 |
| `Stream.ofNullable(value)` | Java 9 | `Stream.of(value).filter(Objects::nonNull)` 或 `Optional` |
| `IntStream.takeWhile()` | Java 9 | 同上 |
| `Stream.iterate(seed, next, hasNext)` | Java 9 | 使用 `IntStream.range` 或手动循环 |

### 错误示例

```java
// 错误：使用 Java 9+ Stream 方法
List<Integer> result = list.stream()
    .takeWhile(x -> x < 10)   // Java 9+
    .collect(Collectors.toList());

List<Integer> result2 = list.stream()
    .dropWhile(x -> x < 5)    // Java 9+
    .collect(Collectors.toList());

Stream<String> stream = Stream.ofNullable(maybeNull);  // Java 9+
```

### 正确示例

```java
// takeWhile 等价实现：取满足条件的前缀元素
List<Integer> result = new ArrayList<>();
for (Integer x : list) {
    if (x < 10) {
        result.add(x);
    } else {
        break;  // 遇到不满足条件的元素即停止
    }
}

// dropWhile 等价实现：跳过满足条件的前缀元素
List<Integer> result2 = new ArrayList<>();
boolean dropping = true;
for (Integer x : list) {
    if (dropping && x < 5) {
        continue;  // 跳过前缀
    }
    dropping = false;
    result2.add(x);
}

// ofNullable 等价实现
Stream<String> stream = maybeNull != null
    ? Stream.of(maybeNull)
    : Stream.empty();

// 或者使用 Optional
Stream<String> stream = Optional.ofNullable(maybeNull)
    .map(Stream::of)
    .orElse(Stream.empty());

// takeWhile 使用 StreamEx（如项目已依赖 streamex 库）
List<Integer> result = StreamEx.of(list)
    .takeWhile(x -> x < 10)
    .toList();
```

### 检查要点

- 代码中不应出现 `takeWhile`、`dropWhile`、`ofNullable` 方法调用
- 如需类似功能，使用 for 循环 + break/continue 手动实现
- 可使用第三方库 StreamEx / Guava 提供的等价方法
- Code Review 时需特别注意 Stream 链式调用中是否混入 Java 9+ 方法
