#!/usr/bin/env python3
"""测试 harness_py.cli 模块 — 命令路由与入口。"""

import unittest
import sys
import os
import tempfile
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from harness_py import cli
from harness_py.config import create_default_config, save_config


class CliTest(unittest.TestCase):

    def test_version_flag_exits(self):
        """--version 触发 argparse 退出。"""
        with self.assertRaises(SystemExit):
            cli.run(['--version'])

    def test_no_command_returns_zero(self):
        """无子命令时打印帮助并返回 0。"""
        rc = cli.run([])
        self.assertEqual(rc, 0)

    def test_rules_select_command(self):
        """在已接入项目内 rules select 返回 0。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(['git', 'init', '-q', tmp], check=True)
            config = create_default_config(tmp, 'cli-test', '17', ['java-common', 'spring-http'])
            config['project']['description'] = 'cli 测试服务'
            save_config(config, tmp)

            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                rc = cli.run([
                    'rules', 'select',
                    '--task', 'code-review',
                    '--files', 'src/main/java/x/controller/C.java',
                ])
            finally:
                os.chdir(old_cwd)
            self.assertEqual(rc, 0)

    def test_rules_select_without_config_fails(self):
        """无 config 时 rules select 返回 1。"""
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(['git', 'init', '-q', tmp], check=True)
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                rc = cli.run(['rules', 'select', '--task', 'code-review', '--files', 'x.java'])
            finally:
                os.chdir(old_cwd)
            self.assertEqual(rc, 1)


if __name__ == '__main__':
    unittest.main()
