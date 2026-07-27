#!/usr/bin/env python3
"""测试 harness_py.context 模块"""

import unittest
import sys
import os
import tempfile
import json

# 确保可以导入 harness_py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from harness_py import utils
from harness_py.context import estimate_file_tokens, check_claude_md_budget


class ContextTest(unittest.TestCase):
    """context 模块测试用例。"""

    def test_estimate_tokens(self):
        """Token 估算：字符数 / 4，至少为 1。"""
        # estimate_tokens = max(1, len(text) // 4)
        self.assertEqual(utils.estimate_tokens("hello world"), 2)  # 11 // 4
        self.assertEqual(utils.estimate_tokens("abcd"), 1)
        self.assertEqual(utils.estimate_tokens(""), 1)  # 空字符串至少 1

        # estimate_file_tokens 读取文件后估算
        with tempfile.TemporaryDirectory() as tmp:
            fpath = os.path.join(tmp, "sample.txt")
            content = "abcdefgh" * 10  # 80 字符 → 20 Token
            with open(fpath, "w") as f:
                f.write(content)

            self.assertEqual(estimate_file_tokens(fpath), 20)
            # 不存在的文件返回 0
            self.assertEqual(
                estimate_file_tokens(os.path.join(tmp, "nope.txt")), 0
            )

    def test_claude_md_budget_ok(self):
        """正常大小的 CLAUDE.md 通过检查。"""
        with tempfile.TemporaryDirectory() as tmp:
            lines = ["# 项目说明"] + [
                f"- 第 {i} 行内容" for i in range(50)
            ]
            with open(os.path.join(tmp, "CLAUDE.md"), "w") as f:
                f.write("\n".join(lines))

            passed, issues = check_claude_md_budget(tmp, {})
            self.assertTrue(passed, f"应通过预算检查: {issues}")
            self.assertEqual(issues, [])

    def test_claude_md_budget_exceeds(self):
        """超大 CLAUDE.md 检测失败（行数与 Token 超限）。"""
        with tempfile.TemporaryDirectory() as tmp:
            # 220 行，每行约 50 字符 → 约 11000 字符 → 2750 Token
            lines = ["# 超大说明"] + [
                f"- 第 {i} 行：{'x' * 45}" for i in range(220)
            ]
            with open(os.path.join(tmp, "CLAUDE.md"), "w") as f:
                f.write("\n".join(lines))

            passed, issues = check_claude_md_budget(tmp, {})
            self.assertFalse(passed)
            joined = "\n".join(issues)
            # 至少触发行数或 Token 超限
            self.assertTrue(
                "行数超限" in joined or "Token 超限" in joined,
                f"应报告超限问题: {issues}",
            )


if __name__ == '__main__':
    unittest.main()
