#!/usr/bin/env python3
"""测试 harness_py.doctor 模块 — 检查项、JSON 输出、自动修复。"""

import unittest
import sys
import os
import tempfile
import subprocess
import json
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from harness_py.config import create_default_config, save_config
from harness_py.doctor import run_doctor
from harness_py.render import render_all


def _bootstrap(tmp, profiles):
    subprocess.run(['git', 'init', '-q', tmp], check=True)
    config = create_default_config(tmp, 'doctor-test', '17', profiles)
    config['project']['description'] = 'doctor 测试服务'
    save_config(config, tmp)


class DoctorTest(unittest.TestCase):

    def test_doctor_returns_tuple_with_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            _bootstrap(tmp, ['java-common'])
            render_all(tmp)
            result = run_doctor(tmp)
            self.assertIsInstance(result, tuple)
            exit_code, data = result
            self.assertIn('summary', data)
            self.assertIn('checks', data)
            # 12 类检查都应执行
            ids = {c['id'] for c in data['checks']}
            for expected in ['DOC-001', 'DOC-004', 'DOC-006', 'DOC-007', 'DOC-008', 'DOC-009']:
                self.assertIn(expected, ids)

    def test_doctor_json_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            _bootstrap(tmp, ['java-common'])
            render_all(tmp)
            old = sys.stdout
            sys.stdout = io.StringIO()
            try:
                run_doctor(tmp, json_output=True)
                output = sys.stdout.getvalue()
            finally:
                sys.stdout = old
            data = json.loads(output)
            self.assertIn('status', data)
            self.assertIn('summary', data)
            self.assertIn('checks', data)

    def test_auto_fix_creates_yaml_config(self):
        """DOC-001 auto_fix 应生成合法 YAML 配置（非 JSON）。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(['git', 'init', '-q', tmp], check=True)
            run_doctor(tmp, fix=True)
            cfg_path = os.path.join(tmp, '.harness', 'config.yaml')
            self.assertTrue(os.path.isfile(cfg_path))
            # 确认是 YAML（含 apiVersion 键，非 JSON 大括号）
            content = open(cfg_path).read()
            self.assertIn('apiVersion:', content)
            self.assertNotIn('{', content)


if __name__ == '__main__':
    unittest.main()
