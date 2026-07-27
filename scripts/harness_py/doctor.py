"""健康检查模块 — 诊断 Harness 配置与项目状态。"""

import os
import sys
import json
import shutil
import subprocess

from harness_py.utils import (
    find_project_root,
    get_core_dir,
    get_profiles_dir,
    get_templates_dir,
    sha256_of_file,
    estimate_tokens,
    safe_read_file,
    safe_read_yaml,
    HARNESS_REPO,
    HARNESS_VERSION,
)
from harness_py.config import load_config, get_build_commands
from harness_py.profile import resolve_profiles, get_enabled_profiles_text
from harness_py.rules import RuleSelector, check_consistency


# ---------------------------------------------------------------------------
# 退出码
# ---------------------------------------------------------------------------

EXIT_OK = 0           # 通过（可含 warning）
EXIT_FAILURE = 1      # 存在失败项
EXIT_ARG_ERROR = 2    # 参数错误
EXIT_INTERNAL = 3     # 内部错误


# ---------------------------------------------------------------------------
# 私有辅助方法
# ---------------------------------------------------------------------------

def _check(cid, status, message, suggestion=None):
    """构建单个检查项结果。"""
    item = {"id": cid, "status": status, "message": message}
    if suggestion:
        item["suggestion"] = suggestion
    return item


def _harness_dir(project_root):
    return os.path.join(project_root, ".harness")


def _config_path(project_root):
    return os.path.join(_harness_dir(project_root), "config.yaml")


def _lock_path(project_root):
    return os.path.join(_harness_dir(project_root), "lock.yaml")


def _managed_files_path(project_root):
    return os.path.join(_harness_dir(project_root), "managed-files.json")


def _local_rules_index(project_root):
    return os.path.join(_harness_dir(project_root), "local", "index.yaml")


def _run_cmd(cmd, cwd=None, capture=True):
    """执行 shell 命令。"""
    try:
        if capture:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=cwd, timeout=30
            )
        else:
            result = subprocess.run(cmd, shell=True, cwd=cwd, timeout=30)
        return result.returncode, result.stdout.strip() if capture else "", result.stderr.strip() if capture else ""
    except subprocess.TimeoutExpired:
        return -1, "", "命令执行超时"
    except Exception as e:
        return -1, "", str(e)


# ---------------------------------------------------------------------------
# 各检查项实现
# ---------------------------------------------------------------------------

def _doc001(project_root):
    """DOC-001: 基础环境 — Git 仓库、pom.xml、Harness 配置、锁文件。"""
    issues = []

    git_dir = os.path.join(project_root, ".git")
    if os.path.isdir(git_dir):
        issues.append(_check("DOC-001", "passed", "Git 仓库检测通过"))
    else:
        issues.append(_check("DOC-001", "warning", "未找到 .git 目录（子目录或未 git init 时可忽略）"))

    pom = os.path.join(project_root, "pom.xml")
    if os.path.isfile(pom):
        issues.append(_check("DOC-001", "passed", "pom.xml 存在"))
    else:
        issues.append(_check("DOC-001", "warning", "未找到 pom.xml（非 Maven 项目可忽略）"))

    config_path = _config_path(project_root)
    if os.path.isfile(config_path):
        issues.append(_check("DOC-001", "passed", "Harness 配置文件存在"))
    else:
        issues.append(_check("DOC-001", "failed", "缺少 Harness 配置文件 .harness/config.yaml"))

    lock_path = _lock_path(project_root)
    if os.path.isfile(lock_path):
        issues.append(_check("DOC-001", "passed", "Harness 锁文件存在"))
    else:
        issues.append(_check("DOC-001", "warning", "Harness 锁文件缺失，运行 render 命令生成"))

    return issues


def _doc002(project_root):
    """DOC-002: Java 版本。"""
    issues = []

    rc, stdout, stderr = _run_cmd("java -version 2>&1", cwd=project_root)
    if rc == 0:
        version_line = stderr or stdout
        issues.append(_check("DOC-002", "passed", f"Java 环境可用: {version_line[:80]}"))
    else:
        issues.append(_check("DOC-002", "failed", "未检测到 Java 运行环境，请安装 JDK 8+"))

    rc, stdout, stderr = _run_cmd("javac -version 2>&1", cwd=project_root)
    if rc != 0:
        issues.append(_check("DOC-002", "warning", "javac 编译器不可用，无法编译项目"))

    return issues


def _doc003(project_root):
    """DOC-003: Maven（项目 mvnw 或系统 mvn，任一可用即可）。"""
    issues = []

    mvnw = os.path.join(project_root, "mvnw")
    has_mvnw = os.path.isfile(mvnw)

    rc, stdout, stderr = _run_cmd("mvn --version 2>&1", cwd=project_root)
    system_mvn_ok = (rc == 0)

    if has_mvnw:
        if os.access(mvnw, os.X_OK):
            issues.append(_check("DOC-003", "passed", "Maven Wrapper (mvnw) 可用"))
        else:
            issues.append(_check("DOC-003", "warning", "mvnw 存在但无可执行权限",
                                suggestion="运行 chmod +x mvnw"))
    elif system_mvn_ok:
        first_line = stdout.split("\n")[0] if stdout else "未知版本"
        issues.append(_check("DOC-003", "passed",
                            f"系统 Maven 可用: {first_line}（建议启用 mvnw）"))
    else:
        issues.append(_check("DOC-003", "failed", "Maven 未安装且无 mvnw",
                            suggestion="安装 Maven 或运行 mvn wrapper:wrapper 生成 mvnw"))

    return issues


def _doc004(project_root):
    """DOC-004: 配置格式。"""
    issues = []

    config_path = _config_path(project_root)
    if not os.path.isfile(config_path):
        return [_check("DOC-004", "warning", "跳过 — 配置文件不存在")]

    data = safe_read_yaml(config_path)
    if data is None:
        issues.append(_check("DOC-004", "failed", "配置格式无效，YAML 解析失败",
                            suggestion="检查 .harness/config.yaml 的语法"))
        return issues

    # 基本结构校验
    if not isinstance(data, dict):
        issues.append(_check("DOC-004", "failed", "配置文件根节点必须是映射",
                            suggestion="检查 YAML 根节点格式"))
        return issues

    if "project" not in data:
        issues.append(_check("DOC-004", "warning", "缺少 project 配置节",
                            suggestion="在 config.yaml 中添加 project 配置"))
    else:
        project = data["project"]
        if not project.get("name"):
            issues.append(_check("DOC-004", "warning", "project.name 未设置",
                                suggestion="在 config.yaml 中设置项目名称"))

    if "profiles" not in data:
        issues.append(_check("DOC-004", "warning", "缺少 profiles 配置节",
                            suggestion="至少启用一个 Profile"))
    else:
        profiles = data.get("profiles", [])
        if not profiles:
            issues.append(_check("DOC-004", "warning", "未启用任何 Profile"))

    if not issues:
        issues.append(_check("DOC-004", "passed", "配置文件格式正确"))

    return issues


def _doc005(project_root):
    """DOC-005: 版本锁定。"""
    issues = []

    lock_path = _lock_path(project_root)
    if not os.path.isfile(lock_path):
        issues.append(_check("DOC-005", "warning", "锁文件不存在",
                            suggestion="运行 ./scripts/harness render 生成锁文件"))
        return issues

    lock_data = safe_read_yaml(lock_path)
    if not lock_data or not isinstance(lock_data, dict):
        issues.append(_check("DOC-005", "failed", "锁文件格式无效",
                            suggestion="删除 .harness/lock.yaml 后重新生成"))
        return issues

    lock_version = lock_data.get("version", "")
    if lock_version == HARNESS_VERSION:
        issues.append(_check("DOC-005", "passed", f"锁文件版本一致: v{lock_version}"))
    else:
        issues.append(_check("DOC-005", "warning",
                            f"锁文件版本 {lock_version} 与当前版本 {HARNESS_VERSION} 不一致",
                            suggestion="运行 ./scripts/harness render 更新"))

    # 检查锁文件哈希
    if "files" in lock_data and isinstance(lock_data["files"], dict):
        mismatched = []
        for rel_path, info in lock_data["files"].items():
            abs_path = os.path.join(project_root, rel_path)
            if not os.path.isfile(abs_path):
                mismatched.append(rel_path)
        if mismatched:
            issues.append(_check("DOC-005", "warning",
                                f"以下受管文件已丢失: {', '.join(mismatched)}",
                                suggestion="运行 ./scripts/harness render 重新生成"))

    if len(issues) == 0:
        issues.append(_check("DOC-005", "passed", "版本锁定正常"))

    return issues


def _doc006(project_root):
    """DOC-006: 受管文件。"""
    issues = []

    managed_path = _managed_files_path(project_root)
    if not os.path.isfile(managed_path):
        issues.append(_check("DOC-006", "warning", "受管文件清单缺失",
                            suggestion="运行 ./scripts/harness render 生成"))
        return issues

    try:
        with open(managed_path, "r", encoding="utf-8") as f:
            managed = json.load(f)
    except json.JSONDecodeError:
        issues.append(_check("DOC-006", "failed", "受管文件清单 JSON 格式无效",
                            suggestion="删除 .harness/managed-files.json 后重新生成"))
        return issues

    all_ok = True
    for rel_path, info in managed.items():
        abs_path = info.get("path", "")
        if not abs_path or not os.path.isfile(abs_path):
            issues.append(_check("DOC-006", "failed", f"受管文件缺失: {rel_path}",
                                suggestion="运行 ./scripts/harness render 重新生成"))
            all_ok = False
            continue

        expected_hash = info.get("sha256", "")
        if expected_hash:
            actual_hash = sha256_of_file(abs_path)
            if actual_hash != expected_hash:
                issues.append(_check("DOC-006", "warning", f"受管文件发生漂移: {rel_path}",
                                    suggestion="运行 ./scripts/harness render 重新生成"))
                all_ok = False

    if all_ok:
        issues.append(_check("DOC-006", "passed", "受管文件完整无漂移"))

    return issues


def _doc007(project_root):
    """DOC-007: 规则一致性 — 重复 ID、规则文件缺失、废弃规则、Token 估算缺失。"""
    issues = []
    config = load_config(project_root)

    if config is not None:
        # 业务项目：基于启用的 Profile 做全面一致性检查
        try:
            passed, cissues = check_consistency(project_root, config)
        except Exception as e:
            return [_check("DOC-007", "failed", f"规则一致性检查异常: {e}")]
        if passed:
            issues.append(_check("DOC-007", "passed", "规则文件体系一致"))
        else:
            for msg in cissues:
                issues.append(_check("DOC-007", "warning", msg))
        return issues

    # 无配置（如 harness 主仓库自检）：遍历所有 Profile + Core 检查规则文件存在性
    profiles_dir = get_profiles_dir(project_root)
    core_dir = get_core_dir(project_root)
    targets = [("Core", core_dir)]
    if os.path.isdir(profiles_dir):
        for name in sorted(os.listdir(profiles_dir)):
            pdir = os.path.join(profiles_dir, name)
            if os.path.isdir(pdir):
                targets.append((name, pdir))

    checked = 0
    for label, pdir in targets:
        rules_yaml = safe_read_yaml(os.path.join(pdir, "rules.yaml"))
        if not rules_yaml or "rules" not in rules_yaml:
            continue
        rule_dir = os.path.join(pdir, "rules")
        for rule in rules_yaml["rules"]:
            content_path = rule.get("content", {}).get("path", "")
            if not content_path:
                continue
            checked += 1
            abs_path = os.path.join(rule_dir, os.path.basename(content_path))
            if not os.path.isfile(abs_path):
                issues.append(_check("DOC-007", "warning",
                    f"{label}: 规则文件缺失: {rule.get('id', '?')} → {content_path}"))

    if not issues:
        issues.append(_check("DOC-007", "passed",
            f"规则文件体系一致（检查 {checked} 条规则文件）"))
    return issues


def _doc008(project_root):
    """DOC-008: 上下文预算。"""
    issues = []

    claude_md = os.path.join(project_root, "CLAUDE.md")
    content = safe_read_file(claude_md)

    if content is None:
        issues.append(_check("DOC-008", "failed", "CLAUDE.md 不存在",
                            suggestion="运行 ./scripts/harness render 生成"))
        return issues

    token_count = estimate_tokens(content)
    token_limit = 2000

    if token_count <= token_limit * 0.8:
        issues.append(_check("DOC-008", "passed", f"CLAUDE.md 预算正常: ~{token_count} Token / {token_limit}"))
    elif token_count <= token_limit:
        issues.append(_check("DOC-008", "warning", f"CLAUDE.md 接近预算上限: ~{token_count} Token / {token_limit}",
                            suggestion="检查规则索引，移除不必要的 Profile"))
    else:
        issues.append(_check("DOC-008", "warning", f"CLAUDE.md 超出预算: ~{token_count} Token / {token_limit}",
                            suggestion="减少启用的 Profile 数量或精简规则索引"))

    return issues


def _doc009(project_root):
    """DOC-009: CI Workflow。"""
    issues = []
    workflow = os.path.join(project_root, ".github", "workflows", "harness-check.yml")

    if os.path.isfile(workflow):
        issues.append(_check("DOC-009", "passed", "CI Workflow 配置存在"))
    else:
        issues.append(_check("DOC-009", "warning", "CI Workflow 缺失: .github/workflows/harness-check.yml",
                            suggestion="运行 ./scripts/harness render 生成"))

    return issues


def _doc010(project_root):
    """DOC-010: Git Hook（是否安装、是否当前版本、是否可执行）。"""
    from harness_py.hooks import is_hook_installed, SUPPORTED_HOOKS
    issues = []

    if not os.path.isdir(os.path.join(project_root, ".git")):
        return [_check("DOC-010", "warning", "非 Git 仓库，跳过 Hook 检查")]

    for name in SUPPORTED_HOOKS:
        if is_hook_installed(project_root, name):
            issues.append(_check("DOC-010", "passed", f"{name} Hook 已安装且为当前版本"))
        else:
            issues.append(_check("DOC-010", "warning",
                                f"{name} Hook 未安装或版本过期",
                                suggestion="运行 ./scripts/harness install-hooks 安装"))

    return issues


def _doc011(project_root):
    """DOC-011: 覆盖率配置。"""
    issues = []

    pom = os.path.join(project_root, "pom.xml")
    if not os.path.isfile(pom):
        issues.append(_check("DOC-011", "warning", "pom.xml 不存在，跳过覆盖率检查"))
        return issues

    pom_content = safe_read_file(pom)
    if pom_content and "jacoco" in pom_content.lower():
        issues.append(_check("DOC-011", "passed", "pom.xml 中包含 JaCoCo 配置"))
    else:
        issues.append(_check("DOC-011", "warning", "pom.xml 中未发现 JaCoCo 覆盖率插件配置",
                            suggestion="在 pom.xml 中添加 jacoco-maven-plugin"))

    return issues


def _doc012(project_root):
    """DOC-012: 安全设置。"""
    issues = []

    settings = os.path.join(project_root, ".claude", "settings.json")
    if not os.path.isfile(settings):
        issues.append(_check("DOC-012", "warning", ".claude/settings.json 缺失",
                            suggestion="运行 ./scripts/harness render 生成"))
        return issues

    try:
        with open(settings, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        issues.append(_check("DOC-012", "failed", "settings.json 格式无效"))
        return issues

    permissions = data.get("permissions", {})
    allow_rules = permissions.get("allow", [])
    deny_rules = permissions.get("deny", [])

    if allow_rules and deny_rules:
        issues.append(_check("DOC-012", "passed",
                             f"权限配置已设置 (allow: {len(allow_rules)}, deny: {len(deny_rules)})"))
    else:
        issues.append(_check("DOC-012", "warning", "权限规则不完整"))

    # 检查危险操作是否被封禁
    dangerous_ops = ["rm -rf", "git push --force", "git reset --hard"]
    for op in dangerous_ops:
        found = any(op in rule for rule in deny_rules)
        if not found:
            issues.append(_check("DOC-012", "warning",
                                f"危险操作未被封禁: {op}",
                                suggestion="在 settings.json 的 deny 列表中添加该操作"))

    return issues


# ---------------------------------------------------------------------------
# 自动修复
# ---------------------------------------------------------------------------

def _auto_fix(project_root, checks):
    """尝试自动修复可修复的问题。"""
    fixed = []

    for check_item in checks:
        cid = check_item["id"]
        status = check_item["status"]
        if status != "failed" and status != "warning":
            continue

        suggestion = check_item.get("suggestion", "")

        # DOC-006: 重新生成受管文件
        if cid == "DOC-006" and "render" in suggestion:
            try:
                from harness_py.render import render_all
                result = render_all(project_root)
                fixed.append(f"重新生成了 {len(result.get('generated', []))} 个受管文件")
            except Exception as e:
                fixed.append(f"受管文件生成失败: {e}")

        # DOC-001: 创建缺失的配置文件（合法 YAML）
        if cid == "DOC-001" and "Harness 配置文件" in check_item["message"]:
            from harness_py.config import create_default_config, save_config
            config_path = _config_path(project_root)
            if not os.path.isfile(config_path):
                default_config = create_default_config(
                    project_root, os.path.basename(project_root), "17", ["java-common"]
                )
                try:
                    save_config(default_config, project_root)
                    fixed.append("创建了默认配置文件 .harness/config.yaml")
                except Exception as e:
                    fixed.append(f"创建配置文件失败: {e}")

        # DOC-010: 安装 Git Hook
        if cid == "DOC-010" and "Hook 未安装" in check_item["message"]:
            hook_src = os.path.join(project_root, "git-hooks", "pre-commit")
            hook_dst = os.path.join(project_root, ".git", "hooks", "pre-commit")
            if os.path.isfile(hook_src):
                try:
                    shutil.copy2(hook_src, hook_dst)
                    os.chmod(hook_dst, 0o755)
                    fixed.append("安装了 Pre-commit Hook")
                except Exception as e:
                    fixed.append(f"安装 Hook 失败: {e}")
            else:
                fixed.append("git-hooks/pre-commit 源文件不存在，无法安装")

        # DOC-009: 生成 CI Workflow
        if cid == "DOC-009" and "render" in suggestion:
            try:
                from harness_py.render import render_all
                result = render_all(project_root)
                if ".github/workflows/harness-check.yml" in result.get("generated", []):
                    fixed.append("生成了 CI Workflow 文件")
            except Exception as e:
                fixed.append(f"生成 Workflow 失败: {e}")

        # DOC-005: 更新锁文件
        if cid == "DOC-005" and "render" in suggestion:
            try:
                from harness_py.render import render_all
                render_all(project_root)
                fixed.append("更新了锁文件")
            except Exception as e:
                fixed.append(f"更新锁文件失败: {e}")

    return fixed


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

_ALL_CHECKS = [
    ("DOC-001", "基础环境", _doc001),
    ("DOC-002", "Java 版本", _doc002),
    ("DOC-003", "Maven 工具", _doc003),
    ("DOC-004", "配置格式", _doc004),
    ("DOC-005", "版本锁定", _doc005),
    ("DOC-006", "受管文件完整性", _doc006),
    ("DOC-007", "规则一致性", _doc007),
    ("DOC-008", "上下文预算", _doc008),
    ("DOC-009", "CI Workflow", _doc009),
    ("DOC-010", "Git Hook", _doc010),
    ("DOC-011", "覆盖率配置", _doc011),
    ("DOC-012", "安全设置", _doc012),
]


def run_doctor(project_root=None, verbose=False, json_output=False,
               ci_mode=False, fix=False):
    """运行所有健康检查。

    参数：
        project_root: 项目根目录
        verbose: 详细输出模式
        json_output: JSON 格式输出
        ci_mode: CI 模式（严格检查）
        fix: 尝试自动修复

    返回：
        tuple: (exit_code, result_dict)
    """
    root = project_root or find_project_root()

    # 不强制要求 .git：业务项目接入标志为 .harness/config.yaml，
    # .git 的检测交由 DOC-001 以 warning 形式给出，避免 examples 等子目录误报。

    all_checks = []
    total = {"passed": 0, "warnings": 0, "failed": 0}

    # 执行所有检查
    for cid, label, check_fn in _ALL_CHECKS:
        try:
            results = check_fn(root)
            if not isinstance(results, list):
                results = [results]
            for item in results:
                all_checks.append(item)
                if item["status"] == "passed":
                    total["passed"] += 1
                elif item["status"] == "warning":
                    total["warnings"] += 1
                elif item["status"] == "failed":
                    total["failed"] += 1
        except Exception as e:
            all_checks.append(_check(cid, "failed", f"检查异常: {e}"))
            total["failed"] += 1

    # 自动修复
    fixed_items = []
    if fix:
        fixed_items = _auto_fix(root, all_checks)
        if fixed_items:
            # 修复后重新检查
            all_checks = []
            total = {"passed": 0, "warnings": 0, "failed": 0}
            for cid, label, check_fn in _ALL_CHECKS:
                try:
                    results = check_fn(root)
                    if not isinstance(results, list):
                        results = [results]
                    for item in results:
                        all_checks.append(item)
                        if item["status"] == "passed":
                            total["passed"] += 1
                        elif item["status"] == "warning":
                            total["warnings"] += 1
                        elif item["status"] == "failed":
                            total["failed"] += 1
                except Exception as e:
                    all_checks.append(_check(cid, "failed", f"检查异常: {e}"))
                    total["failed"] += 1

    # 判定最终状态
    if total["failed"] > 0:
        status = "failed"
    elif total["warnings"] > 0:
        status = "warning"
    else:
        status = "passed"

    # 输出
    if json_output:
        output = {
            "status": status,
            "summary": total,
            "checks": all_checks,
        }
        if fixed_items:
            output["fixed"] = fixed_items
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        if not verbose and not ci_mode:
            # 简洁模式
            status_icon = "✓" if status == "passed" else "⚠" if status == "warning" else "✗"
            print(f"[{status_icon}] Harness 健康检查: {status}")
            print(f"    通过: {total['passed']}  警告: {total['warnings']}  失败: {total['failed']}")

            for item in all_checks:
                if item["status"] == "failed":
                    icon = "✗"
                elif item["status"] == "warning":
                    icon = "⚠"
                else:
                    continue
                print(f"  [{icon}] {item['id']}: {item['message']}")
                if "suggestion" in item:
                    print(f"       建议: {item['suggestion']}")

            if fixed_items:
                print(f"\n自动修复执行结果:")
                for f in fixed_items:
                    print(f"  ✓ {f}")
        else:
            # 详细模式 / CI 模式
            status_map = {"passed": "✓", "warning": "⚠", "failed": "✗"}
            for item in all_checks:
                icon = status_map.get(item["status"], "?")
                line = f"[{icon}] {item['id']}: {item['message']}"
                print(line)
                if "suggestion" in item:
                    print(f"      建议: {item['suggestion']}")

            print(f"\n摘要: {total['passed']} 通过, {total['warnings']} 警告, {total['failed']} 失败")

            if fixed_items:
                print(f"\n自动修复:")
                for f in fixed_items:
                    print(f"  ✓ {f}")

    # CI 模式退出码
    if ci_mode:
        if total["failed"] > 0:
            exit_code = EXIT_FAILURE
        else:
            exit_code = EXIT_OK
    else:
        if total["failed"] > 0:
            exit_code = EXIT_FAILURE
        else:
            exit_code = EXIT_OK

    return exit_code, {
        "status": status,
        "summary": total,
        "checks": all_checks,
    }
