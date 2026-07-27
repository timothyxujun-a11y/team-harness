"""Team Harness CLI — 入口与参数解析."""

import argparse
import json
import os
import sys

from harness_py import __version__
from harness_py.utils import HARNESS_REPO, HARNESS_VERSION, find_project_root


# --------------------------------------------------------------------------- #
# 子命令处理函数
# --------------------------------------------------------------------------- #

def _cmd_init(args):
    """初始化项目。"""
    try:
        from harness_py.config import (
            create_default_config, save_config,
        )
    except ImportError as e:
        print(f"错误: 无法加载配置模块 — {e}", file=sys.stderr)
        return 1

    project_root = find_project_root()
    harness_dir = os.path.join(project_root, ".harness")
    config_path = os.path.join(harness_dir, "config.yaml")

    if os.path.exists(config_path):
        print(f"配置文件已存在: {config_path}")
        print("如需重新初始化，请先删除该文件。")
        return 1

    project_name = args.name or os.path.basename(project_root)
    java_version = args.java_version

    if args.profiles:
        profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
    else:
        profiles = ["java-common"]

    config = create_default_config(project_root, project_name, java_version, profiles)

    if args.description:
        config["project"]["description"] = args.description

    os.makedirs(harness_dir, exist_ok=True)
    os.makedirs(os.path.join(harness_dir, "local"), exist_ok=True)

    try:
        save_config(config, project_root)
    except RuntimeError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    print(f"已创建配置文件: {config_path}")
    print(f"  项目名称: {project_name}")
    print(f"  Java 版本: {java_version}")
    print(f"  启用 Profile: {', '.join(profiles)}")
    print()
    print("下一步:")
    print("  1. 编辑 .harness/config.yaml 填写项目描述")
    print("  2. 运行 ./scripts/harness render 生成受管文件")
    print("  3. 运行 ./scripts/harness doctor 检查配置")
    return 0


def _cmd_render(args):
    """生成受管文件。"""
    try:
        from harness_py.render import render_all, render_check, render_diff
    except ImportError as e:
        print(f"错误: 渲染模块不可用 — {e}", file=sys.stderr)
        print("提示: 请确保已安装 pyyaml (pip install pyyaml)", file=sys.stderr)
        return 1

    project_root = find_project_root()
    if args.check:
        ok, drifts = render_check(project_root)
        if ok:
            print("所有受管文件一致，无漂移。")
            return 0
        else:
            print(f"检测到 {len(drifts)} 个文件漂移:")
            for f in drifts:
                print(f"  - {f}")
            return 1
    elif args.diff:
        render_diff(project_root)
        return 0
    else:
        result = render_all(project_root)
        errors = result.get("errors", [])
        if errors:
            print(f"生成完成，但有 {len(errors)} 个错误:")
            for e in errors:
                print(f"  - {e}")
            return 1
        generated = result.get("generated", [])
        print(f"已生成 {len(generated)} 个文件。")
        return 0


def _cmd_rules(args):
    """rules 子命令入口 — 无子命令时打印帮助。"""
    print("用法: harness rules <select|check> [options]")
    print()
    print("子命令:")
    print("  select  规则选择 (--task <type> --files <file1,file2>)")
    print("  check   规则一致性检查")
    return 1


def _cmd_rules_select(args):
    """规则选择。"""
    try:
        from harness_py.rules import RuleSelector
        from harness_py.config import load_config, get_context_budget
    except ImportError as e:
        print(f"错误: 规则模块不可用 — {e}", file=sys.stderr)
        return 1

    project_root = find_project_root()
    config = load_config(project_root)
    if config is None:
        print("错误: 未找到配置文件 .harness/config.yaml，请先运行 ./scripts/harness init", file=sys.stderr)
        return 1

    files = [f.strip() for f in args.files.split(",") if f.strip()]
    selector = RuleSelector(project_root, config)
    # 根据任务类型应用上下文预算（§11.7/11.12：超预算按优先级截断）
    budget = get_context_budget(config, args.task)
    result = selector.select(task=args.task, files=files, budget_config=budget)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _cmd_rules_check(args):
    """规则一致性检查。"""
    try:
        from harness_py.rules import check_consistency
        from harness_py.config import load_config
    except ImportError as e:
        print(f"错误: 规则模块不可用 — {e}", file=sys.stderr)
        return 1

    project_root = find_project_root()
    config = load_config(project_root)
    if config is None:
        print("错误: 未找到配置文件 .harness/config.yaml，请先运行 ./scripts/harness init", file=sys.stderr)
        return 1

    passed, issues = check_consistency(project_root, config)
    if passed:
        print("规则一致性检查通过。")
        return 0
    else:
        print(f"规则一致性检查失败，发现 {len(issues)} 个问题:")
        for issue in issues:
            print(f"  - {issue}")
        return 1


def _cmd_doctor(args):
    """自检。"""
    try:
        from harness_py.doctor import run_doctor
    except ImportError as e:
        print(f"错误: 自检模块不可用 — {e}", file=sys.stderr)
        return 1

    project_root = find_project_root()
    result = run_doctor(
        project_root,
        verbose=args.verbose,
        json_output=args.json,
        ci_mode=args.ci,
        fix=args.fix,
    )
    # run_doctor 返回 (exit_code, result_dict)
    if isinstance(result, tuple):
        return result[0]
    return result


def _cmd_version(args):
    """版本信息。"""
    try:
        from harness_py.version import show_version
        show_version(find_project_root())
    except ImportError:
        # 回退到内置版本信息
        print(f"Team Harness CLI v{__version__}")
        print(f"Harness 版本: {HARNESS_VERSION}")
        print(f"仓库地址: https://github.com/{HARNESS_REPO}")
        print(f"Python: {sys.version.split()[0]}")
    return 0


def _cmd_upgrade(args):
    """升级 Harness。"""
    try:
        from harness_py.version import check_upgrade, do_upgrade
    except ImportError as e:
        print(f"错误: 版本管理模块不可用 — {e}", file=sys.stderr)
        return 1

    project_root = find_project_root()
    if args.check:
        result = check_upgrade(project_root)
        if result.get("upgrade_available"):
            print(f"有新版本可用: {result.get('current_version')} -> {result.get('latest_version')}")
            if result.get("breaking_change"):
                print("  ⚠ 包含 Breaking Change（主版本号变更）")
        elif result.get("error"):
            print(f"已是最新版本: {result.get('current_version')}（{result['error']}）")
        else:
            print(f"已是最新版本: {result.get('current_version')}")
        return 0
    elif args.to:
        source = getattr(args, "source", None)
        success, message = do_upgrade(project_root, args.to, source=source)
        if not success and isinstance(message, str):
            print(message, file=sys.stderr)
        return 0 if success else 1
    else:
        print("用法: harness upgrade [--check | --to <version> [--source <path>]]")
        return 1


def _cmd_rollback(args):
    """回滚。"""
    try:
        from harness_py.version import do_rollback
    except ImportError as e:
        print(f"错误: 版本管理模块不可用 — {e}", file=sys.stderr)
        return 1

    project_root = find_project_root()
    success, message = do_rollback(project_root)
    print(message)
    return 0 if success else 1


def _cmd_install_hooks(args):
    """安装/卸载 Git Hook。"""
    try:
        from harness_py.hooks import install_hooks, uninstall_hooks
    except ImportError as e:
        print(f"错误: Hook 模块不可用 — {e}", file=sys.stderr)
        return 1

    project_root = find_project_root()
    if args.uninstall:
        return uninstall_hooks(project_root)
    return install_hooks(project_root)


def _cmd_migrate(args):
    """v1 → v2 迁移。"""
    try:
        from harness_py.migrate import migrate_v1_to_v2
    except ImportError as e:
        print(f"错误: 迁移模块不可用 — {e}", file=sys.stderr)
        return 1

    project_root = find_project_root()
    return migrate_v1_to_v2(project_root)


# --------------------------------------------------------------------------- #
# 参数解析
# --------------------------------------------------------------------------- #

def build_parser():
    """构建 argparse 解析器。"""
    parser = argparse.ArgumentParser(
        prog="harness",
        description="Team Harness CLI v2.0 — AI 工程化规范工具",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Team Harness CLI v{__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # --- init ---
    sub_init = subparsers.add_parser("init", help="初始化项目")
    sub_init.add_argument("--name", help="项目名称（默认: 目录名）")
    sub_init.add_argument("--java-version", default="17", help="Java 版本（默认: 17）")
    sub_init.add_argument("--profiles", help="启用的 Profile，逗号分隔（默认: java-common）")
    sub_init.add_argument("--description", help="项目描述")
    sub_init.set_defaults(func=_cmd_init)

    # --- render ---
    sub_render = subparsers.add_parser("render", help="生成受管文件")
    sub_render.add_argument("--check", action="store_true", help="检查漂移（不修改文件）")
    sub_render.add_argument("--diff", action="store_true", help="显示差异")
    sub_render.set_defaults(func=_cmd_render)

    # --- rules ---
    sub_rules = subparsers.add_parser("rules", help="规则管理")
    sub_rules.set_defaults(func=_cmd_rules)
    rules_sub = sub_rules.add_subparsers(dest="rules_command", help="规则子命令")

    sub_rules_select = rules_sub.add_parser("select", help="规则选择")
    sub_rules_select.add_argument("--task", required=True, help="任务类型")
    sub_rules_select.add_argument("--files", required=True, help="文件列表（逗号分隔）")
    sub_rules_select.set_defaults(func=_cmd_rules_select)

    sub_rules_check = rules_sub.add_parser("check", help="规则一致性检查")
    sub_rules_check.set_defaults(func=_cmd_rules_check)

    # --- doctor ---
    sub_doctor = subparsers.add_parser("doctor", help="自检")
    sub_doctor.add_argument("--verbose", action="store_true", help="详细输出")
    sub_doctor.add_argument("--json", action="store_true", help="JSON 格式输出")
    sub_doctor.add_argument("--ci", action="store_true", help="CI 模式")
    sub_doctor.add_argument("--fix", action="store_true", help="自动修复")
    sub_doctor.set_defaults(func=_cmd_doctor)

    # --- version ---
    sub_version = subparsers.add_parser("version", help="版本信息")
    sub_version.set_defaults(func=_cmd_version)

    # --- upgrade ---
    sub_upgrade = subparsers.add_parser("upgrade", help="升级 Harness")
    sub_upgrade.add_argument("--check", action="store_true", help="检查升级")
    sub_upgrade.add_argument("--to", metavar="VERSION", help="指定版本升级")
    sub_upgrade.add_argument("--source", metavar="PATH", help="本地 harness 源路径（本地校验模式）")
    sub_upgrade.set_defaults(func=_cmd_upgrade)

    # --- rollback ---
    sub_rollback = subparsers.add_parser("rollback", help="回滚")
    sub_rollback.set_defaults(func=_cmd_rollback)

    # --- install-hooks ---
    sub_hooks = subparsers.add_parser("install-hooks", help="安装 Git Hook")
    sub_hooks.add_argument("--uninstall", action="store_true", help="卸载已安装的 Hook")
    sub_hooks.set_defaults(func=_cmd_install_hooks)

    # --- migrate ---
    sub_migrate = subparsers.add_parser("migrate", help="v1 → v2 迁移")
    sub_migrate.set_defaults(func=_cmd_migrate)

    return parser


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #

def run(argv=None):
    """运行 CLI，返回退出码。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    result = args.func(args)
    return result if result is not None else 0


def main():
    """CLI 入口点，调用 run()。"""
    sys.exit(run())
