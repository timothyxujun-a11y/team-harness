# ============================================================
# Harness Quality Gates — CI 强制质量门禁
# ============================================================
# 由 Team Harness 自动生成
# 版本: {{ harness_version }}
# ============================================================

name: Harness Quality Gates

on:
  pull_request:
    branches: [main, master]
  push:
    branches: [main, master]

jobs:
  harness-check:
    runs-on: ubuntu-latest
    name: Harness Quality Gates

    steps:
      - name: 检出代码
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: 设置 Java {{ java_version }}
        uses: actions/setup-java@v4
        with:
          java-version: "{{ java_version }}"
          distribution: temurin
          cache: maven

      - name: 设置 Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.x"

      - name: 安装 Python 依赖
        run: pip install pyyaml

      # Gate 1: Doctor
      - name: [GATE-001] Harness Doctor
        run: ./scripts/harness doctor --ci

      # Gate 2: 生成漂移检查
      - name: [GATE-002] 生成文件漂移检查
        run: ./scripts/harness render --check

      # Gate 3: 规则一致性
      - name: [GATE-003] 规则一致性检查
        run: ./scripts/harness rules check

      # Gate 4: 上下文预算
      - name: [GATE-004] 上下文预算检查
        run: ./scripts/harness doctor --context-only --ci

      # Gate 5: Maven 编译
      - name: [GATE-005] Maven 编译
        run: {{ compile_command }}

      # Gate 6: 自动化测试
      - name: [GATE-006] 单元测试
        run: {{ test_command }}

      # Gate 7: 增量覆盖率
      - name: [GATE-007] 增量覆盖率
        run: |
          mvn jacoco:report -q
          pip install diff-cover
          diff-cover jacoco.xml --compare-branch={{ diff_base_branch }} --fail-under={{ diff_coverage_threshold }}
        continue-on-error: false

      # Gate 8: 未完成配置检查
      - name: [GATE-008] 未完成配置检查
        run: |
          if grep -rq "TODO-HARNESS\|FIXME-HARNESS" --include="*.yaml" --include="*.yml" --include="*.md" --include="*.json" . ; then
            echo "::error ::发现未完成的 Harness 配置标记"
            exit 1
          fi

      # Gate 9: 敏感信息扫描
      - name: [GATE-009] 敏感信息扫描
        run: |
          echo "检查明文敏感信息..."
          PATTERNS="password\s*=|token\s*=|secret\s*=|apiKey\s*=|private_key|BEGIN RSA|BEGIN PRIVATE"
          FOUND=false
          for pattern in $PATTERNS; do
            if git diff --name-only HEAD~1 | xargs grep -r "$pattern" --include="*.java" --include="*.yml" --include="*.yaml" --include="*.properties" 2>/dev/null; then
              FOUND=true
            fi
          done
          if [ "$FOUND" = true ]; then
            echo "::warning ::检测到可能的敏感信息"
          fi

      - name: Harness Report
        if: always()
        run: |
          echo "========================================"
          echo "  Harness Quality Report"
          echo "========================================"
          echo "  Harness: {{ harness_version }}"
          echo "  Project: {{ project_name }}"
          echo "  Java: {{ java_version }}"
          echo "========================================"
