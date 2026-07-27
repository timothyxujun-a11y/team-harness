#!/usr/bin/env python3
"""测试 harness_py.hooks 模块 — 安装、幂等、版本校验、卸载。"""

import unittest
import sys
import os
import tempfile
import subprocess
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from harness_py import hooks


def _git_init(tmp):
    subprocess.run(['git', 'init', '-q', tmp], check=True)


class HooksTest(unittest.TestCase):

    def test_install_and_uninstall_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            _git_init(tmp)
            self.assertEqual(hooks.install_hooks(tmp), 0)
            self.assertTrue(hooks.is_hook_installed(tmp, 'pre-commit'))
            self.assertTrue(hooks.is_hook_installed(tmp, 'pre-push'))
            self.assertEqual(hooks.uninstall_hooks(tmp), 0)
            self.assertFalse(hooks.is_hook_installed(tmp, 'pre-commit'))

    def test_idempotent_install(self):
        """重复安装跳过已就绪 hook。"""
        with tempfile.TemporaryDirectory() as tmp:
            _git_init(tmp)
            self.assertEqual(hooks.install_hooks(tmp), 0)
            self.assertEqual(hooks.install_hooks(tmp), 0)
            self.assertTrue(hooks.is_hook_installed(tmp, 'pre-commit'))

    def test_install_requires_git(self):
        """非 git 目录安装失败。"""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(hooks.install_hooks(tmp), 1)

    def test_uninstall_when_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            _git_init(tmp)
            self.assertEqual(hooks.uninstall_hooks(tmp), 0)


if __name__ == '__main__':
    unittest.main()
