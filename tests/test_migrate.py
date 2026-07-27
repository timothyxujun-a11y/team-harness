#!/usr/bin/env python3
"""测试 harness_py.migrate 模块 — v1 检测、提取、推荐、幂等。"""

import unittest
import sys
import os
import tempfile
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from harness_py import migrate


def _write_v1_claude(tmp, name='order-service', desc='订单交易核心服务'):
    """构造 v1 风格 CLAUDE.md。"""
    os.makedirs(tmp, exist_ok=True)
    with open(os.path.join(tmp, 'CLAUDE.md'), 'w') as f:
        f.write(
            '# 项目约定总纲\n'
            f'- **项目名称**: {name}\n'
            f'- **模块/职责**: {desc}\n'
            '\n[CUSTOMIZE: 其它占位]\n'
        )


class MigrateTest(unittest.TestCase):

    def test_detect_v1_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_v1_claude(tmp)
            markers = migrate.detect_v1_markers(tmp)
            self.assertTrue(markers['has_customize'])
            self.assertGreater(len(markers['customize_lines']), 0)

    def test_extract_customize_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_v1_claude(tmp, 'order-service', '订单交易核心服务')
            markers = migrate.detect_v1_markers(tmp)
            name, desc = migrate.extract_customize_values(markers['claude_md'])
            self.assertEqual(name, 'order-service')
            self.assertEqual(desc, '订单交易核心服务')

    def test_recommend_profiles_defaults(self):
        """无源码时推荐 java-common。"""
        with tempfile.TemporaryDirectory() as tmp:
            profiles = migrate.recommend_profiles(tmp)
            self.assertEqual(profiles[0], 'java-common')

    def test_migrate_creates_config_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(['git', 'init', '-q', tmp], check=True)
            _write_v1_claude(tmp)
            rc = migrate.migrate_v1_to_v2(tmp)
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.isfile(os.path.join(tmp, '.harness', 'config.yaml')))
            self.assertTrue(os.path.isfile(os.path.join(tmp, '.harness', 'local', 'index.yaml')))
            self.assertTrue(os.path.isfile(os.path.join(tmp, '.harness', 'MIGRATION_REPORT.md')))
            # 幂等：再迁移提示已是 v2
            rc2 = migrate.migrate_v1_to_v2(tmp)
            self.assertEqual(rc2, 0)

    def test_migrate_no_markers_suggests_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(['git', 'init', '-q', tmp], check=True)
            rc = migrate.migrate_v1_to_v2(tmp)
            self.assertEqual(rc, 1)


if __name__ == '__main__':
    unittest.main()
