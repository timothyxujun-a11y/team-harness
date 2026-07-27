"""Git Hook 安装与管理模块。

封装 git-hooks/pre-commit、pre-push 的安装、卸载、版本校验。
行为与 scripts/install-git-hooks.sh 对齐，并补充版本戳以支持幂等升级
与 DOC-010（检测 hook 是否为当前版本）。
"""

import os
import shutil

from harness_py.utils import find_project_root, get_harness_source_root, HARNESS_VERSION


# 支持的 hook 列表
SUPPORTED_HOOKS = ["pre-commit", "pre-push"]

# 写入已安装 hook 的版本戳标记
_VERSION_MARKER = "HARNESS_HOOK_VERSION"


def _git_dir(project_root):
    """返回 .git 目录路径（兼容 .git 为文件的 worktree 场景）。"""
    git_path = os.path.join(project_root, ".git")
    if os.path.isfile(git_path):
        try:
            with open(git_path, "r", encoding="utf-8") as f:
                line = f.read().strip()
            if line.startswith("gitdir:"):
                resolved = line.split(":", 1)[1].strip()
                if not os.path.isabs(resolved):
                    resolved = os.path.join(project_root, resolved)
                return resolved
        except (IOError, IndexError):
            pass
    return git_path


def _hooks_dir(project_root):
    return os.path.join(_git_dir(project_root), "hooks")


def _hook_source_path(hook_name):
    """返回 harness 安装源中的 hook 源文件路径。"""
    return os.path.join(get_harness_source_root(), "git-hooks", hook_name)


def installed_version(hook_path):
    """读取已安装 hook 的版本戳，无则返回 None。"""
    if not os.path.isfile(hook_path):
        return None
    try:
        with open(hook_path, "r", encoding="utf-8") as f:
            for line in f:
                if _VERSION_MARKER in line and "=" in line:
                    return line.split("=", 1)[1].strip()
                if line and not line.startswith("#") and not line.startswith("!"):
                    break
    except (IOError, IndexError):
        pass
    return None


def is_hook_installed(project_root, hook_name):
    """检查指定 hook 是否已安装、可执行且为当前版本。"""
    dst = os.path.join(_hooks_dir(project_root), hook_name)
    return (
        os.path.isfile(dst)
        and os.access(dst, os.X_OK)
        and installed_version(dst) == HARNESS_VERSION
    )


def install_hooks(project_root=None, hook=None):
    """安装 Git Hook 到 .git/hooks/。

    参数：
        project_root: 项目根目录（默认自动定位）
        hook: 指定单个 hook（如 'pre-commit'），None 表示安装全部受支持 hook

    返回：
        int: 0 成功（含全部跳过），1 存在失败
    """
    root = project_root or find_project_root()
    git_dir = _git_dir(root)

    if not os.path.isdir(git_dir):
        print(f"错误: 不是 Git 仓库（未找到 .git）: {root}")
        print("提示: 先运行 git init 初始化仓库")
        return 1

    hooks_dir = _hooks_dir(root)
    os.makedirs(hooks_dir, exist_ok=True)

    targets = [hook] if hook else list(SUPPORTED_HOOKS)
    installed = []
    skipped = []
    failed = []

    for name in targets:
        if name not in SUPPORTED_HOOKS:
            failed.append(f"{name}（不支持的 hook，可选: {', '.join(SUPPORTED_HOOKS)}）")
            continue

        src = _hook_source_path(name)
        if not os.path.isfile(src):
            failed.append(f"{name}（源文件缺失: {src}）")
            continue

        dst = os.path.join(hooks_dir, name)

        # 幂等：已是当前版本且可执行则跳过
        if installed_version(dst) == HARNESS_VERSION and os.access(dst, os.X_OK):
            skipped.append(name)
            continue

        try:
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)
            installed.append(name)
        except OSError as e:
            failed.append(f"{name}（{e}）")

    for name in installed:
        print(f"  ✓ 已安装 {name} → .git/hooks/{name} (v{HARNESS_VERSION})")
    for name in skipped:
        print(f"  · 跳过 {name}（已是当前版本 v{HARNESS_VERSION}）")
    for msg in failed:
        print(f"  ✗ 失败 {msg}")

    if failed:
        return 1

    if installed:
        print("\nGit Hook 安装完成。")
        print("说明:")
        print("  - pre-commit: 提交前 Maven 编译检查（阻止提交）")
        print("  - pre-push:   推送前增量行覆盖率 > 80%（需 diff-cover）")
        print("  - 临时跳过(不推荐): git commit/push --no-verify")
        print("  - 卸载: ./scripts/harness install-hooks --uninstall")
    elif skipped and not installed:
        print("\n所有 Hook 已是最新版本，无需操作。")
    return 0


def uninstall_hooks(project_root=None, hook=None):
    """卸载已安装的 Git Hook。"""
    root = project_root or find_project_root()
    hooks_dir = _hooks_dir(root)
    targets = [hook] if hook else list(SUPPORTED_HOOKS)

    removed = []
    for name in targets:
        dst = os.path.join(hooks_dir, name)
        if os.path.isfile(dst):
            try:
                os.remove(dst)
                removed.append(name)
            except OSError as e:
                print(f"  ✗ 卸载失败 {name}（{e}）")

    if removed:
        print(f"已卸载 Hook: {', '.join(removed)}")
    else:
        print("无已安装的 Hook 可卸载。")
    return 0
