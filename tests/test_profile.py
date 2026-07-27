#!/usr/bin/env python3
"""测试 harness_py.profile 模块"""

import unittest
import sys
import os
import tempfile
import json

# 确保可以导入 harness_py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from harness_py import utils
from harness_py.profile import (
    load_profile,
    resolve_profiles,
    validate_profile_conflicts,
)


def _write_profile(root, name, depends_on=None, conflicts_with=None):
    """在临时项目的 profiles/<name>/profile.yaml 写入一个 Profile。"""
    profiles_dir = os.path.join(root, "profiles", name)
    os.makedirs(profiles_dir, exist_ok=True)

    deps = depends_on or []
    conflicts = conflicts_with or []

    content = (
        "apiVersion: harness.company.io/v1\n"
        "kind: HarnessProfile\n"
        "metadata:\n"
        f"  name: {name}\n"
        "  version: 1.0.0\n"
        f"  description: {name} 测试 Profile\n"
        "dependsOn:\n"
        + "".join(f"  - {d}\n" for d in deps)
        + "conflictsWith:\n"
        + "".join(f"  - {c}\n" for c in conflicts)
        + "content:\n"
        "  index: index.md\n"
        "  rules: rules.yaml\n"
    )

    with open(os.path.join(profiles_dir, "profile.yaml"), "w") as f:
        f.write(content)


class ProfileTest(unittest.TestCase):
    """profile 模块测试用例。"""

    def test_load_profile_valid(self):
        """加载合法 profile.yaml。"""
        with tempfile.TemporaryDirectory() as tmp:
            _write_profile(tmp, "spring-http")

            profile = load_profile(tmp, "spring-http")
            self.assertIsNotNone(profile)
            self.assertEqual(
                profile["metadata"]["name"], "spring-http"
            )
            self.assertEqual(profile["kind"], "HarnessProfile")

    def test_resolve_dependency_chain(self):
        """resolve_profiles 正确解析依赖链（java-common ← spring-http）。"""
        with tempfile.TemporaryDirectory() as tmp:
            _write_profile(tmp, "java-common")  # 无依赖
            _write_profile(
                tmp, "spring-http", depends_on=["java-common"]
            )

            resolved = resolve_profiles(tmp, ["spring-http"])

            # 依赖在前，依赖者在后
            self.assertEqual(resolved, ["java-common", "spring-http"])

    def test_resolve_circular_dependency(self):
        """循环依赖抛出异常。"""
        with tempfile.TemporaryDirectory() as tmp:
            _write_profile(tmp, "a", depends_on=["b"])
            _write_profile(tmp, "b", depends_on=["a"])

            with self.assertRaises(ValueError) as ctx:
                resolve_profiles(tmp, ["a"])
            self.assertIn("循环依赖", str(ctx.exception))

    def test_resolve_missing_dep(self):
        """缺失依赖抛出异常。"""
        with tempfile.TemporaryDirectory() as tmp:
            _write_profile(tmp, "a", depends_on=["nonexistent"])

            with self.assertRaises(ValueError) as ctx:
                resolve_profiles(tmp, ["a"])
            self.assertIn("不存在", str(ctx.exception))

    def test_validate_conflicts(self):
        """冲突 Profile 抛出异常。"""
        with tempfile.TemporaryDirectory() as tmp:
            _write_profile(
                tmp, "spring-http", conflicts_with=["legacy-java8"]
            )
            _write_profile(tmp, "legacy-java8")

            spring = load_profile(tmp, "spring-http")
            legacy = load_profile(tmp, "legacy-java8")

            with self.assertRaises(ValueError) as ctx:
                validate_profile_conflicts([spring, legacy])
            self.assertIn("冲突", str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
