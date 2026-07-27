#!/usr/bin/env python3
"""测试 harness_py.config 模块"""

import unittest
import sys
import os
import tempfile
import json

# 确保可以导入 harness_py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from harness_py import utils
from harness_py.config import (
    create_default_config,
    validate_config,
    get_build_commands,
    _API_VERSION,
    _KIND,
)


def _make_valid_config():
    """构造一份通过校验的合法配置 dict。"""
    return {
        "apiVersion": _API_VERSION,
        "kind": _KIND,
        "project": {
            "name": "demo-service",
            "description": "示例服务",
        },
        "runtime": {
            "language": "java",
            "javaVersion": "17",
            "buildTool": "maven",
            "defaultBranch": "main",
        },
        "profiles": ["java-common", "spring-http"],
    }


class ConfigTest(unittest.TestCase):
    """config 模块测试用例。"""

    def test_create_default_config(self):
        """创建默认配置，验证必填字段与结构。"""
        with tempfile.TemporaryDirectory() as tmp:
            config = create_default_config(
                tmp, "my-app", 17, "java-common, spring-http"
            )

            # 顶层必填字段
            self.assertEqual(config["apiVersion"], _API_VERSION)
            self.assertEqual(config["kind"], _KIND)

            # project 字段
            self.assertEqual(config["project"]["name"], "my-app")
            self.assertIn("description", config["project"])

            # runtime 字段
            self.assertEqual(config["runtime"]["language"], "java")
            self.assertEqual(config["runtime"]["javaVersion"], "17")
            self.assertEqual(config["runtime"]["buildTool"], "maven")

            # profiles 被正确切分为列表
            self.assertEqual(
                config["profiles"], ["java-common", "spring-http"]
            )

            # build 命令已生成
            self.assertIn("compileCommand", config["build"])
            self.assertIn("testCommand", config["build"])
            self.assertIn("packageCommand", config["build"])

            # 默认配置应通过校验
            valid, errors = validate_config(config)
            self.assertTrue(valid, f"默认配置应通过校验，错误: {errors}")

    def test_validate_valid_config(self):
        """验证合法配置通过校验。"""
        config = _make_valid_config()
        valid, errors = validate_config(config)
        self.assertTrue(valid)
        self.assertEqual(errors, [])

    def test_validate_missing_required(self):
        """缺少必填字段时校验失败。"""
        # 缺少 apiVersion / kind / project / runtime / profiles
        config = {"apiVersion": _API_VERSION}
        valid, errors = validate_config(config)
        self.assertFalse(valid)
        # 至少报告缺少 kind / project / runtime / profiles
        joined = "\n".join(errors)
        self.assertIn("kind", joined)
        self.assertIn("project", joined)
        self.assertIn("runtime", joined)
        self.assertIn("profiles", joined)

    def test_get_build_commands_mvnw(self):
        """有 mvnw 时返回 ./mvnw 命令。"""
        with tempfile.TemporaryDirectory() as tmp:
            # 模拟 pom.xml 与 mvnw 包装器
            with open(os.path.join(tmp, "pom.xml"), "w") as f:
                f.write("<project></project>")
            with open(os.path.join(tmp, "mvnw"), "w") as f:
                f.write("#!/bin/sh\n")

            cmds = get_build_commands(tmp)
            self.assertTrue(
                cmds["compileCommand"].startswith("./mvnw ")
            )
            self.assertTrue(cmds["testCommand"].startswith("./mvnw "))
            self.assertTrue(cmds["packageCommand"].startswith("./mvnw "))

    def test_get_build_commands_fallback(self):
        """无 mvnw 时回退 mvn 命令。"""
        with tempfile.TemporaryDirectory() as tmp:
            # 仅模拟 pom.xml，不创建 mvnw
            with open(os.path.join(tmp, "pom.xml"), "w") as f:
                f.write("<project></project>")

            cmds = get_build_commands(tmp)
            self.assertTrue(cmds["compileCommand"].startswith("mvn "))
            self.assertTrue(cmds["testCommand"].startswith("mvn "))
            self.assertTrue(cmds["packageCommand"].startswith("mvn "))
            # 确保不是 ./mvnw
            for v in cmds.values():
                self.assertFalse(v.startswith("./mvnw"))


if __name__ == '__main__':
    unittest.main()
