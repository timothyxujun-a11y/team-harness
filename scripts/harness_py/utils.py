"""Shared utilities for harness_py."""

import os
import re
import hashlib
import pathlib

HARNESS_REPO = "timothyxujun-a11y/team-harness"
HARNESS_VERSION = "2.1.0"


# 本文件位置：<harness-source>/scripts/harness_py/utils.py
# harness 安装源根目录 = 往上三级。与当前工作目录无关，保证从任意
# 业务项目子目录运行都能定位到 core/ profiles/ templates/。
_HARNESS_SOURCE_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


def find_project_root(start=None):
    """定位业务项目根目录。

    优先向上查找 ``.harness/config.yaml``（业务项目接入 Harness 的标志），
    找不到再回退到 ``.git`` 目录。这样业务项目（如 examples 子目录）
    不会错误地回退到 harness 主仓库根。
    """
    path = pathlib.Path(start or os.getcwd()).resolve()
    while True:
        if (path / ".harness" / "config.yaml").exists():
            return str(path)
        if (path / ".git").exists():
            return str(path)
        if path == path.parent:
            break
        path = path.parent
    return str(pathlib.Path(start or os.getcwd()).resolve())


_SOURCE_OVERRIDE = None


def set_harness_source(source_root):
    """临时覆盖 harness 安装源根（用于 upgrade 从指定 source 校验渲染）。

    传入 None 还原为默认源根。CLI 单线程使用，调用方须在 finally 中还原。
    """
    global _SOURCE_OVERRIDE
    _SOURCE_OVERRIDE = source_root


def get_harness_source_root():
    """返回 harness 安装源根目录（含 core/ profiles/ templates/ scripts/）。

    基于 ``utils.py`` 自身路径推断；可被 set_harness_source 临时覆盖。
    """
    return _SOURCE_OVERRIDE or _HARNESS_SOURCE_ROOT


def is_managed_project(project_root):
    """判断目录是否为已接入 Harness 的业务项目。"""
    return os.path.isfile(os.path.join(project_root, ".harness", "config.yaml"))


def _source_or_local(project_root, subdir):
    """定位 harness 资源目录：优先用 project_root/<subdir>（测试与自举场景），
    否则回退到 harness 安装源根（业务项目场景，core/profiles 不在项目内）。"""
    if project_root:
        local = os.path.join(project_root, subdir)
        if os.path.exists(local):
            return local
    return os.path.join(get_harness_source_root(), subdir)


def get_harness_dir(project_root=None):
    """Get the harness scripts directory."""
    return _source_or_local(project_root, os.path.join("scripts", "harness_py"))


def get_core_dir(project_root=None):
    """Get the core rules directory."""
    return _source_or_local(project_root, "core")


def get_profiles_dir(project_root=None):
    """Get the profiles directory."""
    return _source_or_local(project_root, "profiles")


def get_templates_dir(project_root=None):
    """Get the templates directory."""
    return _source_or_local(project_root, "templates")


def sha256_of_file(filepath):
    """Calculate SHA256 of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_of_dir(dirpath):
    """Calculate SHA256 of all files in a directory."""
    h = hashlib.sha256()
    for root, dirs, files in sorted(os.walk(dirpath)):
        dirs.sort()
        for fname in sorted(files):
            fp = os.path.join(root, fname)
            h.update(fp.encode())
            with open(fp, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
    return h.hexdigest()


def estimate_tokens(text):
    """Rough token estimation (characters / 4)."""
    return max(1, len(text) // 4)


def safe_read_file(path):
    """Read a file, return None if not found."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (IOError, OSError):
        return None


def safe_read_yaml(path):
    """Read and parse a YAML file."""
    content = safe_read_file(path)
    if content is None:
        return None
    try:
        import yaml
        return yaml.safe_load(content)
    except ImportError:
        return None
    except Exception:
        return None
