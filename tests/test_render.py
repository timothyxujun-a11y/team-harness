#!/usr/bin/env python3
"""测试 harness_py.render 模块 — 受管文件生成、漂移检测、幂等。"""

import unittest
import sys
import os
import tempfile
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from harness_py.config import create_default_config, save_config
from harness_py.render import render_all, render_check


def _bootstrap(tmp, profiles):
    """创建临时业务项目（git + config）。"""
    subprocess.run(['git', 'init', '-q', tmp], check=True)
    config = create_default_config(tmp, 'render-test', '17', profiles)
    config['project']['description'] = '渲染测试服务'
    save_config(config, tmp)


class RenderTest(unittest.TestCase):

    def test_render_generates_managed_files(self):
        """render 生成全部受管文件（CLAUDE.md/settings/workflow/agents/profile-index）。"""
        with tempfile.TemporaryDirectory() as tmp:
            _bootstrap(tmp, ['java-common', 'spring-http'])
            result = render_all(tmp)

            self.assertEqual(result['errors'], [])
            self.assertTrue(os.path.isfile(os.path.join(tmp, 'CLAUDE.md')))
            self.assertTrue(os.path.isfile(os.path.join(tmp, '.claude', 'settings.json')))
            self.assertTrue(os.path.isfile(os.path.join(tmp, '.github', 'workflows', 'harness-check.yml')))
            self.assertTrue(os.path.isfile(os.path.join(tmp, '.claude', 'agents', 'code-reviewer.md')))
            self.assertTrue(os.path.isfile(os.path.join(tmp, 'docs', 'harness', 'spring-http', 'index.md')))

    def test_render_check_no_drift(self):
        """render 后立即 check 应无漂移。"""
        with tempfile.TemporaryDirectory() as tmp:
            _bootstrap(tmp, ['java-common', 'spring-http'])
            render_all(tmp)
            ok, drifts = render_check(tmp)
            self.assertTrue(ok, f"检测到漂移: {drifts}")

    def test_render_check_detects_drift(self):
        """手工修改 CLAUDE.md 后 check 应报告漂移。"""
        with tempfile.TemporaryDirectory() as tmp:
            _bootstrap(tmp, ['java-common'])
            render_all(tmp)
            with open(os.path.join(tmp, 'CLAUDE.md'), 'a') as f:
                f.write('\n# 手工修改\n')
            ok, drifts = render_check(tmp)
            self.assertFalse(ok)
            self.assertIn('CLAUDE.md', drifts)

    def test_render_idempotent(self):
        """重复 render 不产生无意义变化（需求 §19.3）。"""
        with tempfile.TemporaryDirectory() as tmp:
            _bootstrap(tmp, ['java-common'])
            render_all(tmp)
            r2 = render_all(tmp)
            self.assertEqual(r2['generated'], [])


if __name__ == '__main__':
    unittest.main()
