#!/usr/bin/env python3
"""端到端测试 — init→render→render --check→rules select→doctor 全链路。

验证需求 §23 验收场景的核心断言：HTTP 文件变更命中 spring-http 规则、不加载 MQ 规则。
"""

import unittest
import sys
import os
import tempfile
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from harness_py import cli
from harness_py.config import create_default_config, save_config, load_config
from harness_py.render import render_all, render_check
from harness_py.doctor import run_doctor
from harness_py.rules import RuleSelector


# 环境相关的检查项（无 Java/Maven 时可能 failed，不视为回归）
_ENV_CHECKS = {'DOC-002', 'DOC-003'}


class EndToEndTest(unittest.TestCase):

    def test_full_workflow_http_service(self):
        """模拟 HTTP 服务接入：init→render→check→rules select→doctor。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(['git', 'init', '-q', tmp], check=True)
            # init 等价：生成 config
            config = create_default_config(tmp, 'e2e-http', '17', ['java-common', 'spring-http'])
            config['project']['description'] = 'E2E HTTP 测试服务'
            save_config(config, tmp)

            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                # 1. render 生成受管文件
                r = render_all(tmp)
                self.assertEqual(r['errors'], [])
                self.assertTrue(os.path.isfile(os.path.join(tmp, 'CLAUDE.md')))

                # 2. render --check 无漂移
                ok, drifts = render_check(tmp)
                self.assertTrue(ok, f"漂移: {drifts}")

                # 3. rules select 命中 HTTP、不含 MQ（需求 §9.8 / §23 场景二）
                rc = cli.run([
                    'rules', 'select', '--task', 'code-review',
                    '--files', 'src/main/java/x/controller/UserController.java',
                ])
                self.assertEqual(rc, 0)
            finally:
                os.chdir(old_cwd)

            # 4. 规则选择断言：HTTP 命中、MQ 不加载
            cfg = load_config(tmp)
            selector = RuleSelector(tmp, cfg)
            result = selector.select(
                task='code-review',
                files=['src/main/java/x/controller/UserController.java'],
            )
            ids = [x['id'] for x in result['selectedRules']]
            self.assertTrue(any(i.startswith('HTTP') for i in ids), f"未命中 HTTP 规则: {ids}")
            self.assertFalse(any(i.startswith('MQ') for i in ids), f"误加载 MQ 规则: {ids}")

            # 5. doctor：非环境检查项不应 failed
            _ec, data = run_doctor(tmp)
            failed = [c['id'] for c in data['checks'] if c['status'] == 'failed']
            unexpected = [fid for fid in failed if fid not in _ENV_CHECKS]
            self.assertEqual(unexpected, [], f"意外失败项: {unexpected}")


if __name__ == '__main__':
    unittest.main()
