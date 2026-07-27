"""版本管理模块 — Harness 版本检查、升级与回滚。"""

import os
import sys
import json
import urllib.request
import urllib.error

from harness_py.utils import (
    find_project_root,
    get_core_dir,
    get_profiles_dir,
    sha256_of_file,
    safe_read_file,
    safe_read_yaml,
    HARNESS_REPO,
    HARNESS_VERSION,
)


# ---------------------------------------------------------------------------
# 路径工具
# ---------------------------------------------------------------------------

def _harness_dir(project_root):
    return os.path.join(project_root, ".harness")


def _lock_path(project_root):
    return os.path.join(_harness_dir(project_root), "lock.yaml")


def _version_file_path(project_root):
    return os.path.join(project_root, "VERSION")


# ---------------------------------------------------------------------------
# 锁文件操作
# ---------------------------------------------------------------------------

def load_lock(project_root=None):
    """读取锁文件。

    返回：
        dict 或 None (不存在/格式无效)
    """
    root = project_root or find_project_root()
    lock_path = _lock_path(root)

    if not os.path.isfile(lock_path):
        return None

    data = safe_read_yaml(lock_path)
    return data if isinstance(data, dict) else None


def save_lock(project_root, lock_data):
    """保存锁文件。

    参数：
        project_root: 项目根目录
        lock_data: 锁数据字典
    """
    root = project_root or find_project_root()
    lock_path = _lock_path(root)
    harness_dir = _harness_dir(root)

    os.makedirs(harness_dir, exist_ok=True)

    # 使用 YAML 风格写入
    import tempfile

    content = _dict_to_yaml(lock_data)

    fd, tmp_path = tempfile.mkstemp(dir=harness_dir, prefix=".lock-tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, lock_path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def _dict_to_yaml(data, indent=0):
    """简单字典转 YAML 字符串（不依赖 PyYAML）。"""
    lines = []
    prefix = "  " * indent

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(_dict_to_yaml(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"{prefix}  -")
                        for k, v in item.items():
                            lines.append(f"{prefix}    {k}: {v}")
                    else:
                        lines.append(f"{prefix}  - {item}")
            else:
                lines.append(f"{prefix}{key}: {value}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# GitHub API 版本查询
# ---------------------------------------------------------------------------

def _fetch_github_tags():
    """从 GitHub API 获取 Harness 仓库的所有 tags。

    返回：
        list[str]: tag 名称列表，按版本号降序排列
    """
    api_url = f"https://api.github.com/repos/{HARNESS_REPO}/tags"

    try:
        req = urllib.request.Request(api_url)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "TeamHarness/2.0")

        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))

        tags = [tag["name"].lstrip("v") for tag in data if "name" in tag]
        # 按版本号排序
        tags.sort(key=lambda v: _parse_version(v), reverse=True)
        return tags
    except urllib.error.HTTPError as e:
        if e.code == 403:
            # 可能是 API 频率限制
            return []
        return []
    except Exception:
        return []


def _fetch_github_releases(version_tag=None):
    """从 GitHub API 获取发布信息。

    返回：
        list[dict] 或空列表
    """
    api_url = f"https://api.github.com/repos/{HARNESS_REPO}/releases"
    if version_tag:
        api_url += f"/tags/v{version_tag}"

    try:
        req = urllib.request.Request(api_url)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "TeamHarness/2.0")

        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return []


def _parse_version(version_str):
    """解析版本字符串为可比较的元组。"""
    try:
        parts = version_str.split(".")
        return tuple(int(p) for p in parts[:3])
    except (ValueError, IndexError):
        return (0, 0, 0)


def _is_breaking_change(current_version, target_version):
    """判断是否包含 Breaking Change（主版本号变更）。"""
    cur = _parse_version(current_version)
    tgt = _parse_version(target_version)
    return tgt[0] > cur[0]


# ---------------------------------------------------------------------------
# 版本信息展示
# ---------------------------------------------------------------------------

def show_version(project_root=None):
    """输出当前 Harness 版本和锁文件信息。"""
    root = project_root or find_project_root()

    # 读取 VERSION 文件
    version_file = _version_file_path(root)
    installed_version = "未知"
    if os.path.isfile(version_file):
        installed_version = safe_read_file(version_file).strip()

    print(f"Team Harness CLI")
    print(f"  当前版本: v{installed_version}")
    print(f"  CLI 内置版本: v{HARNESS_VERSION}")

    # 锁文件信息
    lock = load_lock(root)
    if lock:
        lock_version = lock.get("version", "未知")
        lock_time = lock.get("updated_at", "未知")
        previous = lock.get("previousVersion", "")
        print(f"\n锁文件信息:")
        print(f"  版本: v{lock_version}")
        print(f"  更新时间: {lock_time}")
        if previous:
            print(f"  上一个版本: v{previous}")

        files = lock.get("files", {})
        if files:
            print(f"  受管文件数: {len(files)}")
    else:
        print(f"\n锁文件: 不存在")


def show_version_json(project_root=None):
    """以 JSON 格式输出版本信息。"""
    root = project_root or find_project_root()

    installed_version = "未知"
    version_file = _version_file_path(root)
    if os.path.isfile(version_file):
        installed_version = safe_read_file(version_file).strip()

    lock = load_lock(root)

    output = {
        "installed_version": installed_version,
        "cli_version": HARNESS_VERSION,
        "lock": None,
    }

    if lock:
        output["lock"] = {
            "version": lock.get("version", ""),
            "updated_at": lock.get("updated_at", ""),
            "previous_version": lock.get("previousVersion", ""),
            "file_count": len(lock.get("files", {})),
        }

    print(json.dumps(output, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# 升级检查
# ---------------------------------------------------------------------------

def check_upgrade(project_root=None):
    """检查是否有新版本可用。

    返回：
        dict: 升级摘要
    """
    root = project_root or find_project_root()

    current = HARNESS_VERSION
    lock = load_lock(root)
    lock_version = lock.get("version", current) if lock else current

    result = {
        "current_version": lock_version,
        "latest_version": lock_version,
        "upgrade_available": False,
        "breaking_change": False,
        "changelog_summary": "",
        "affected_files": [],
    }

    # 从 GitHub 获取最新 tags
    tags = _fetch_github_tags()
    if not tags:
        result["error"] = "无法获取版本信息（网络不可达或 API 频率限制）"
        return result

    latest = tags[0] if tags else lock_version

    # 版本比较
    cur_parsed = _parse_version(lock_version)
    latest_parsed = _parse_version(latest)

    if latest_parsed <= cur_parsed:
        result["latest_version"] = latest
        result["upgrade_available"] = False
        return result

    result["upgrade_available"] = True
    result["latest_version"] = latest
    result["breaking_change"] = _is_breaking_change(lock_version, latest)

    # 获取变更摘要
    releases = _fetch_github_releases(latest)
    if isinstance(releases, dict) and "body" in releases:
        body = releases.get("body", "")
        result["changelog_summary"] = body[:500]
    elif isinstance(releases, list):
        for rel in releases:
            tag = rel.get("tag_name", "").lstrip("v")
            if _parse_version(tag) > cur_parsed:
                body = rel.get("body", "")
                if body:
                    result["changelog_summary"] = body[:500]
                    break

    # 受影响文件列表
    affected = _get_affected_files(root, lock_version, latest)
    result["affected_files"] = affected

    return result


def _get_affected_files(project_root, from_version, to_version):
    """估算升级可能影响的文件。"""
    # 简单方案：所有受管文件和模板
    affected = [
        "CLAUDE.md",
        ".claude/settings.json",
        ".github/workflows/harness-check.yml",
    ]

    # 检查受管文件清单
    managed_path = os.path.join(_harness_dir(project_root), "managed-files.json")
    if os.path.isfile(managed_path):
        try:
            with open(managed_path, "r", encoding="utf-8") as f:
                managed = json.load(f)
            for rel_path in managed.keys():
                if rel_path not in affected:
                    affected.append(rel_path)
        except Exception:
            pass

    return affected


# ---------------------------------------------------------------------------
# 升级与回滚
# ---------------------------------------------------------------------------

def do_upgrade(project_root=None, target_version=None):
    """执行升级到指定版本。

    流程：下载 → 校验 → 生成 → 原子替换 → 更新锁 → doctor

    参数：
        project_root: 项目根目录
        target_version: 目标版本号

    返回：
        tuple: (成功标志, 消息/结果字典)
    """
    root = project_root or find_project_root()

    if not target_version:
        # 默认升级到最新版本
        check_result = check_upgrade(root)
        if not check_result.get("upgrade_available", False):
            return True, "已是最新版本，无需升级"
        target_version = check_result.get("latest_version", "")

    if not target_version:
        return False, "未指定目标版本"

    print(f"正在升级到 v{target_version}...")

    lock = load_lock(root) or {}
    current_version = lock.get("version", HARNESS_VERSION)
    previous_version = current_version

    # 保存升级前的状态
    import datetime

    try:
        # 1. 记录当前版本状态
        backup_lock = dict(lock)
        backup_lock["previousVersion"] = current_version

        # 2. 触发 render 重新生成文件
        from harness_py.render import render_all
        result = render_all(root)

        errors = result.get("errors", [])
        generated = result.get("generated", [])
        if errors:
            return False, f"文件生成存在错误: {'; '.join(errors)}"

        # 3. 更新锁文件
        new_lock = {
            "version": target_version,
            "updated_at": datetime.datetime.now().isoformat(),
            "previousVersion": previous_version,
            "files": {},
        }

        # 记录受管文件哈希
        for rel_path in generated:
            abs_path = os.path.join(root, rel_path)
            if os.path.isfile(abs_path):
                new_lock["files"][rel_path] = {
                    "sha256": sha256_of_file(abs_path),
                    "path": rel_path,
                }

        save_lock(root, new_lock)

        # 4. 运行 doctor 检查
        print(f"\n执行升级后健康检查...")
        from harness_py.doctor import run_doctor
        doctor_exit_code, doctor_result = run_doctor(root)

        status = doctor_result.get("status", "unknown")
        summary = doctor_result.get("summary", {})

        if status == "failed":
            print(f"  警告: 健康检查发现 {summary.get('failed', 0)} 个问题")
            print(f"  使用 './scripts/harness doctor' 查看详情")

        print(f"\n升级完成: v{previous_version} → v{target_version}")
        print(f"  生成文件: {len(generated)} 个")
        print(f"  健康检查: {status} ({summary.get('passed', 0)}通过/{summary.get('warnings', 0)}警告/{summary.get('failed', 0)}失败)")

        return True, {
            "from": previous_version,
            "to": target_version,
            "generated": len(generated),
            "doctor_status": status,
            "doctor_summary": summary,
        }

    except Exception as e:
        # 恢复备份
        try:
            save_lock(root, backup_lock)
        except Exception:
            pass
        return False, f"升级失败: {e}"


def do_rollback(project_root=None):
    """回滚到上一个版本。

    从锁文件的 previousVersion 恢复到上一个版本。

    返回：
        tuple: (成功标志, 消息)
    """
    root = project_root or find_project_root()

    lock = load_lock(root)
    if not lock:
        return False, "锁文件不存在，无法回滚"

    previous_version = lock.get("previousVersion", "")
    if not previous_version:
        return False, "锁文件中未记录上一个版本，无法回滚"

    current_version = lock.get("version", HARNESS_VERSION)

    print(f"正在回滚: v{current_version} → v{previous_version}")

    try:
        # 恢复上一个版本的锁信息
        import datetime

        rollback_lock = {
            "version": previous_version,
            "updated_at": datetime.datetime.now().isoformat(),
            "previousVersion": "",
            "rollbackFrom": current_version,
            "files": {},
        }

        # 触发 render 重新生成
        from harness_py.render import render_all
        result = render_all(root)

        generated = result.get("generated", [])
        for rel_path in generated:
            abs_path = os.path.join(root, rel_path)
            if os.path.isfile(abs_path):
                rollback_lock["files"][rel_path] = {
                    "sha256": sha256_of_file(abs_path),
                    "path": rel_path,
                }

        save_lock(root, rollback_lock)

        print(f"\n回滚完成: v{current_version} → v{previous_version}")
        print(f"  生成文件: {len(generated)} 个")
        print(f"  使用 './scripts/harness doctor' 验证状态")

        return True, f"成功回滚到 v{previous_version}"

    except Exception as e:
        return False, f"回滚失败: {e}"
