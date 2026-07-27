# 消息 Schema 兼容性

## MQ-SCHEMA-001: 消息体 Schema 变更必须保持向后兼容

消息体（POJO/JSON）字段变更必须保持向后兼容——新增字段需提供默认值，禁止删除或重命名已有字段。推荐使用 Schema Registry 管理消息版本。

### 向后兼容原则

| 变更类型 | 是否允许 | 说明 |
|----------|----------|------|
| 新增字段（有默认值） | 允许 | 旧消费者反序列化时使用默认值 |
| 新增字段（无默认值） | 禁止 | 旧消费者反序列化会报错 |
| 删除已有字段 | 禁止 | 旧 Producer 发送的消息新 Consumer 无法解析 |
| 重命名字段 | 禁止 | 等同于删除+新增，破坏兼容性 |
| 修改字段类型 | 禁止 | 反序列化类型不匹配 |
| 新增可选字段 | 允许 | 使用包装类型或提供默认值 |

### 错误示例

```java
// 错误：删除已有字段，破坏向后兼容
public class OrderMessage {
    private String orderId;
    // 删除了 orderStatus 字段 —— 旧 Producer 发送的消息包含此字段，新 Consumer 无法解析
    private BigDecimal amount;
}

// 错误：重命名字段
public class OrderMessage {
    private String orderId;
    private String orderState;  // 原 orderStatus 重命名为 orderState，旧消息无法映射
    private BigDecimal amount;
}

// 错误：新增字段无默认值
public class OrderMessage {
    private String orderId;
    private String orderStatus;
    private BigDecimal amount;
    private String userId;  // 新增字段无默认值，旧消息反序列化后为 null，可能 NPE
}
```

### 正确示例

```java
// 正确：向后兼容的消息体定义
public class OrderMessage {

    private String orderId;
    private String orderStatus;
    private BigDecimal amount;

    // 新增字段使用包装类型，提供默认值
    private String userId = "";
    private Integer sourceType = 0;
    private List<String> tags = Collections.emptyList();

    // 新增可选字段通过 @JsonInclude 控制序列化
    @JsonInclude(JsonInclude.Include.NON_NULL)
    private String promotionId;

    // getters and setters ...
}

// 正确：使用 Schema 版本号管理
public class OrderMessage {
    /** Schema 版本号 */
    private int version = 1;

    private String orderId;
    private String orderStatus;
    private BigDecimal amount;

    // V2 新增字段
    private String userId = "";

    // getters and setters ...
}
```

### 正确示例：Schema Registry（Avro）

```java
// 使用 Avro Schema 定义消息，通过 Schema Registry 管理版本
// schema: order-message-v1.avsc
{
  "type": "record",
  "name": "OrderMessage",
  "namespace": "com.company.mq",
  "fields": [
    {"name": "orderId", "type": "string"},
    {"name": "orderStatus", "type": "string"},
    {"name": "amount", "type": {"type": "bytes", "logicalType": "decimal", "precision": 18, "scale": 2}},
    {"name": "userId", "type": "string", "default": ""}  // V2 新增，有默认值
  ]
}

// Producer 配置 Schema Registry
@Configuration
public class KafkaProducerConfig {

    @Bean
    public ProducerFactory<String, OrderMessage> producerFactory() {
        Map<String, Object> config = new HashMap<>();
        config.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        config.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        config.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, KafkaAvroSerializer.class);
        config.put("schema.registry.url", schemaRegistryUrl);
        // 自动注册 Schema（生产环境建议关闭，手动注册）
        config.put("auto.register.schemas", false);
        return new DefaultKafkaProducerFactory<>(config);
    }
}
```

### 检查要点

- 新增字段必须提供默认值或使用包装类型（Integer/Long/String 等）
- 禁止删除或重命名已有字段
- 禁止修改已有字段的数据类型
- 建议在消息体中维护 `version` 字段，便于 Consumer 做版本适配
- 生产环境推荐使用 Schema Registry（Confluent / Apicurio）管理 Schema 演进
- Schema 变更需在 Code Review 中重点审查
