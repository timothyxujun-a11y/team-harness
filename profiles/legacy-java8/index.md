# Legacy Java 8 编码规范

## 概述

本 Profile 定义了 Java 8 遗留项目的编码规范，核心目标是限制使用 Java 9+ 语法与 API，确保代码在 JDK 8 环境下可正常编译运行。

适用于无法升级到 Java 11/17/21 的遗留项目，涵盖语法限制和旧版兼容性两个维度。

## 依赖

- `java-common` — Java 通用编码规范

## 规则总览

| 规则 ID | 标题 | 严重级别 | 规则文件 |
|---------|------|----------|----------|
| LEGACY-SYN-001 | 禁止使用 Java 9+ 集合工厂方法 | error | rules/syntax.md |
| LEGACY-SYN-002 | 禁止使用 var 关键字 | error | rules/syntax.md |
| LEGACY-SYN-003 | 禁止使用 Java 9+ Stream API 方法 | error | rules/syntax.md |
| LEGACY-COMPAT-001 | 测试框架必须使用 JUnit 4 | error | rules/compatibility.md |
| LEGACY-COMPAT-002 | Maven 插件版本必须兼容 Java 8 和旧版 Maven | error | rules/compatibility.md |

## 适用场景

- 新功能开发（feature-development）
- 代码重构（refactor）
- 代码评审（code-review）
