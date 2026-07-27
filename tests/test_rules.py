#!/usr/bin/env python3
"""测试 harness_py.rules 模块"""

import unittest
import sys
import os
import tempfile
import json

# 确保可以导入 harness_py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from harness_py import utils
from harness_py.rules import RuleSelector, check_consistency


def _write_core_rules(root, rules_yaml_text):
    """在临时项目根下创建 core/rules.yaml。"""
    core_dir = os.path.join(root, "core")
    os.makedirs(core_dir, exist_ok=True)
    with open(os.path.join(core_dir, "rules.yaml"), "w") as f:
        f.write(rules_yaml_text)


# 不启用任何 Profile，仅使用 Core 规则，避免依赖解析副作用
_EMPTY_PROFILES_CONFIG = {"profiles": []}


class RuleSelectorTest(unittest.TestCase):
    """RuleSelector 选择逻辑测试用例。"""

    def test_rule_selector_select_by_path(self):
        """按文件路径选择规则。"""
        yaml_text = """
rules:
  - id: PATH-001
    title: Controller 规则
    severity: info
    enforced: false
    selectors:
      paths:
        include:
          - "**/controller/**/*.java"
    context:
      priority: medium
      estimatedTokens: 200
  - id: PATH-002
    title: Service 规则
    severity: info
    enforced: false
    selectors:
      paths:
        include:
          - "**/service/**/*.java"
    context:
      priority: medium
      estimatedTokens: 200
"""
        with tempfile.TemporaryDirectory() as tmp:
            _write_core_rules(tmp, yaml_text)
            selector = RuleSelector(tmp, _EMPTY_PROFILES_CONFIG)

            result = selector.select(
                files=["src/main/java/com/example/controller/OrderController.java"]
            )
            ids = [r["id"] for r in result["selectedRules"]]

            self.assertIn("PATH-001", ids)
            self.assertNotIn("PATH-002", ids)

    def test_rule_selector_select_by_task(self):
        """按任务类型选择规则。"""
        yaml_text = """
rules:
  - id: TASK-001
    title: 代码评审规则
    severity: info
    enforced: false
    selectors:
      tasks:
        - code-review
    context:
      priority: medium
      estimatedTokens: 100
  - id: TASK-002
    title: 特性开发规则
    severity: info
    enforced: false
    selectors:
      tasks:
        - feature-development
    context:
      priority: medium
      estimatedTokens: 100
"""
        with tempfile.TemporaryDirectory() as tmp:
            _write_core_rules(tmp, yaml_text)
            selector = RuleSelector(tmp, _EMPTY_PROFILES_CONFIG)

            result = selector.select(task="code-review")
            ids = [r["id"] for r in result["selectedRules"]]

            self.assertIn("TASK-001", ids)
            self.assertNotIn("TASK-002", ids)

    def test_rule_selector_budget_truncation(self):
        """预算截断：max_rules 限制返回数量。"""
        yaml_text = """
rules:
  - id: BUDGET-001
    title: 规则一
    severity: info
    enforced: false
    context:
      priority: low
      estimatedTokens: 100
  - id: BUDGET-002
    title: 规则二
    severity: info
    enforced: false
    context:
      priority: low
      estimatedTokens: 100
  - id: BUDGET-003
    title: 规则三
    severity: info
    enforced: false
    context:
      priority: low
      estimatedTokens: 100
"""
        with tempfile.TemporaryDirectory() as tmp:
            _write_core_rules(tmp, yaml_text)
            selector = RuleSelector(tmp, _EMPTY_PROFILES_CONFIG)

            result = selector.select(max_rules=2)
            self.assertEqual(len(result["selectedRules"]), 2)

    def test_rule_selector_priority_sort(self):
        """按优先级排序：high 排在 low 之前。"""
        yaml_text = """
rules:
  - id: PRIO-LOW
    title: 低优先级
    severity: info
    enforced: false
    context:
      priority: low
      estimatedTokens: 100
  - id: PRIO-HIGH
    title: 高优先级
    severity: error
    enforced: true
    context:
      priority: high
      estimatedTokens: 100
  - id: PRIO-MED
    title: 中优先级
    severity: info
    enforced: false
    context:
      priority: medium
      estimatedTokens: 100
"""
        with tempfile.TemporaryDirectory() as tmp:
            _write_core_rules(tmp, yaml_text)
            selector = RuleSelector(tmp, _EMPTY_PROFILES_CONFIG)

            result = selector.select()
            ids = [r["id"] for r in result["selectedRules"]]

            # high → medium → low
            self.assertEqual(ids[0], "PRIO-HIGH")
            self.assertEqual(ids[1], "PRIO-MED")
            self.assertEqual(ids[2], "PRIO-LOW")


class CheckConsistencyTest(unittest.TestCase):
    """check_consistency 一致性检查测试用例。"""

    def test_check_consistency_duplicate_ids(self):
        """重复 ID 检测。"""
        yaml_text = """
rules:
  - id: DUP-001
    title: 重复规则 A
    severity: info
    enforced: false
    context:
      priority: low
      estimatedTokens: 100
  - id: DUP-001
    title: 重复规则 B
    severity: info
    enforced: false
    context:
      priority: low
      estimatedTokens: 100
"""
        with tempfile.TemporaryDirectory() as tmp:
            _write_core_rules(tmp, yaml_text)
            passed, issues = check_consistency(tmp, _EMPTY_PROFILES_CONFIG)

            self.assertFalse(passed)
            joined = "\n".join(issues)
            self.assertIn("重复规则 ID", joined)
            self.assertIn("DUP-001", joined)

    def test_check_consistency_missing_files(self):
        """缺失文件检测：content.path 指向不存在的文件。"""
        yaml_text = """
rules:
  - id: MISSING-001
    title: 指向缺失文件
    severity: info
    enforced: false
    content:
      path: rules/nonexistent.md
    context:
      priority: low
      estimatedTokens: 100
"""
        with tempfile.TemporaryDirectory() as tmp:
            _write_core_rules(tmp, yaml_text)
            passed, issues = check_consistency(tmp, _EMPTY_PROFILES_CONFIG)

            self.assertFalse(passed)
            joined = "\n".join(issues)
            self.assertIn("规则文件缺失", joined)
            self.assertIn("MISSING-001", joined)


if __name__ == '__main__':
    unittest.main()
