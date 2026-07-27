#!/usr/bin/env python3
"""测试 harness_py.version 模块 — 嵌套锁结构、本地校验升级、回滚。"""

import unittest
import sys
import os
import tempfile
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from harness_py.config import create_default_config, save_config
from harness_py.utils import HARNESS_VERSION, get_harness_source_root
from harness_py.version import load_lock, do_upgrade, do_rollback


def _bootstrap(tmp, profiles):
    subprocess.run(['git', 'init', '-q', tmp], check=True)
    config = create_default_config(tmp, 'version-test', '17', profiles)
    config['project']['description'] = '版本测试服务'
    save_config(config, tmp)


class VersionLockTest(unittest.TestCase):

    def test_lock_nested_structure(self):
        """锁文件产出对齐 harness-lock.schema.json 嵌套结构。"""
        with tempfile.TemporaryDirectory() as tmp:
            _bootstrap(tmp, ['java-common', 'spring-http'])
            success, _ = do_upgrade(tmp, HARNESS_VERSION, source=get_harness_source_root())
            self.assertTrue(success)

            lock = load_lock(tmp)
            self.assertEqual(lock['apiVersion'], 'harness.company.io/v1')
            self.assertEqual(lock['kind'], 'HarnessLock')
            self.assertEqual(lock['harness']['version'], HARNESS_VERSION)
            self.assertEqual(lock['harness']['ref'], f'v{HARNESS_VERSION}')
            self.assertIn('java-common', lock['profiles'])
            self.assertIn('checksum', lock['profiles']['java-common'])
            self.assertTrue(lock['profiles']['java-common']['checksum'])

    def test_upgrade_version_mismatch_rejected(self):
        """source 版本与目标不一致时校验失败（需求 §12.8）。"""
        with tempfile.TemporaryDirectory() as tmp:
            _bootstrap(tmp, ['java-common'])
            success, msg = do_upgrade(tmp, '9.9.9', source=get_harness_source_root())
            self.assertFalse(success)
            self.assertIn('校验失败', msg)

    def test_rollback_requires_previous(self):
        """首次升级无 previousVersion，回滚应失败。"""
        with tempfile.TemporaryDirectory() as tmp:
            _bootstrap(tmp, ['java-common'])
            do_upgrade(tmp, HARNESS_VERSION, source=get_harness_source_root())
            success, msg = do_rollback(tmp)
            self.assertFalse(success)
            self.assertIn('previousVersion', msg)

    def test_upgrade_then_rollback(self):
        """二次升级产生 previousVersion 后可回滚。"""
        with tempfile.TemporaryDirectory() as tmp:
            _bootstrap(tmp, ['java-common'])
            do_upgrade(tmp, HARNESS_VERSION, source=get_harness_source_root())
            do_upgrade(tmp, HARNESS_VERSION, source=get_harness_source_root())
            success, _ = do_rollback(tmp)
            self.assertTrue(success)
            # 回滚后 previousVersion 应被清除（避免无限回滚）
            lock = load_lock(tmp)
            self.assertNotIn('previousVersion', lock)


if __name__ == '__main__':
    unittest.main()
