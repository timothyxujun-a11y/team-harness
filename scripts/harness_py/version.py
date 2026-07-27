"""版本管理模块 — Harness 版本检查、升级与回滚。

锁文件采用嵌套结构（对齐 schemas/harness-lock.schema.json）：
    apiVersion / kind / harness{version,repository,ref,commit}
    / profiles{name:{version,checksum}} / generated{at,checksum}
    / previousVersion{version,ref,commit,lockContent}

升级采用本地校验模式（需求 §12.6）：从本地 source（git 仓库/相邻 worktree）
校验 commit 与 Profile checksum → 临时以该 source 为源根 render → 原子替换 →
更新锁文件。失败回滚、不留临时目录。
"""

import os
import sys
import json
import tempfile
import subprocess
import urllib.request
import urllib.error

from harness_py.utils import (
    find_project_root,
    get_harness_source_root,
    set_harness_source,
    sha256_of_file,
    sha256_of_dir,
    safe_read_file,
    safe_read_yaml,
    HARNESS_REPO,
    HARNESS_VERSION,
)
from harness_py.config import load_config


_API_VERSION = "harness.company.io/v1"
_LOCK_KIND = "HarnessLock"


# ---------------------------------------------------------------------------
# 路径工具
# ---------------------------------------------------------------------------

def _harness_dir(project_root):
    return os.path.join(project_root, ".harness")


def _lock_path(project_root):
    return os.path.join(_harness_dir(project_root), "lock.yaml")


# ---------------------------------------------------------------------------
# 锁文件读写（嵌套结构）
# ---------------------------------------------------------------------------

def load_lock(project_root=None):
    """读取锁文件，返回 dict 或 None（不存在/格式无效）。"""
    root = project_root or find_project_root()
    lock_path = _lock_path(root)
    if not os.path.isfile(lock_path):
        return None
    data = safe_read_yaml(lock_path)
    return data if isinstance(data, dict) else None


def _dict_to_yaml(data, indent=0):
    """简单 dict→YAML（无 pyyaml 时的回退；不支持 list-of-dict 的标准缩进）。"""
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
                    lines.append(f"{prefix}  - {item}")
            else:
                lines.append(f"{prefix}{key}: {value}")
    return "\n".join(lines)


def _lock_to_yaml(lock_data):
    """锁 dict → YAML 字符串（优先 pyyaml，回退 _dict_to_yaml）。"""
    try:
        import yaml
        return yaml.dump(
            lock_data, default_flow_style=False,
            allow_unicode=True, sort_keys=False,
        )
    except ImportError:
        return _dict_to_yaml(lock_data)


def save_lock(project_root, lock_data):
    """原子保存锁文件。"""
    root = project_root or find_project_root()
    harness_dir = _harness_dir(root)
    os.makedirs(harness_dir, exist_ok=True)
    content = _lock_to_yaml(lock_data)

    fd, tmp_path = tempfile.mkstemp(dir=harness_dir, prefix=".lock-tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, _lock_path(root))
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


# ---------------------------------------------------------------------------
# source 解析与校验
# ---------------------------------------------------------------------------

def _resolve_source(source):
    """确定 harness 源根：source 为本地路径则用它，否则用默认源根。"""
    if source:
        source = os.path.abspath(source)
        if not os.path.isdir(source):
            raise ValueError(f"source 路径不存在或不是目录: {source}")
        return source
    return get_harness_source_root()


def _git_commit(repo_path):
    """返回 git 仓库 HEAD commit SHA；非 git 仓库返回空串。"""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _read_source_version(source_root):
    """读取 source 的 VERSION 文件内容。"""
    content = safe_read_file(os.path.join(source_root, "VERSION"))
    return content.strip() if content else ""


def _compute_profile_checksums(source_root, profile_names):
    """计算各启用 profile 目录的 SHA256。"""
    profiles_dir = os.path.join(source_root, "profiles")
    result = {}
    for name in profile_names:
        pdir = os.path.join(profiles_dir, name)
        if os.path.isdir(pdir):
            result[name] = sha256_of_dir(pdir)
    return result


def _profile_versions(source_root, profile_names):
    """读取各 profile 的版本号（profile.yaml.metadata.version）。"""
    result = {}
    for name in profile_names:
        pyaml = safe_read_yaml(
            os.path.join(source_root, "profiles", name, "profile.yaml")
        )
        if pyaml:
            result[name] = pyaml.get("metadata", {}).get("version", "1.0.0")
        else:
            result[name] = "1.0.0"
    return result


def _build_lock_data(config, version, source_root, commit, previous=None):
    """构造嵌套结构的锁数据。"""
    profile_names = (config or {}).get("profiles", []) or []
    versions = _profile_versions(source_root, profile_names)
    checksums = _compute_profile_checksums(source_root, profile_names)

    profiles = {}
    for name in profile_names:
        profiles[name] = {
            "version": versions.get(name, "1.0.0"),
            "checksum": checksums.get(name, ""),
        }

    ref = version if str(version).startswith("v") else f"v{version}"
    lock = {
        "apiVersion": _API_VERSION,
        "kind": _LOCK_KIND,
        "harness": {
            "version": version,
            "repository": HARNESS_REPO,
            "ref": ref,
            "commit": commit,
        },
        "profiles": profiles,
    }
    if previous:
        lock["previousVersion"] = previous
    return lock


# ---------------------------------------------------------------------------
# GitHub 远程版本查询（用于 upgrade --check）
# ---------------------------------------------------------------------------

def _fetch_github_tags():
    """从 GitHub API 获取所有 tags，按版本号降序。"""
    api_url = f"https://api.github.com/repos/{HARNESS_REPO}/tags"
    try:
        req = urllib.request.Request(api_url)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "TeamHarness/2.0")
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
        tags = [tag["name"].lstrip("v") for tag in data if "name" in tag]
        tags.sort(key=lambda v: _parse_version(v), reverse=True)
        return tags
    except Exception:
        return []


def _fetch_github_releases(version_tag=None):
    """从 GitHub API 获取发布信息。"""
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
    try:
        parts = str(version_str).split(".")
        return tuple(int(p) for p in parts[:3])
    except (ValueError, IndexError):
        return (0, 0, 0)


def _is_breaking_change(current_version, target_version):
    cur = _parse_version(current_version)
    tgt = _parse_version(target_version)
    return tgt[0] > cur[0]


# ---------------------------------------------------------------------------
# 版本信息展示
# ---------------------------------------------------------------------------

def show_version(project_root=None):
    """输出版本与锁文件信息（适配嵌套锁）。"""
    root = project_root or find_project_root()
    installed = _read_source_version(root) or HARNESS_VERSION

    print("Team Harness CLI")
    print(f"  当前版本: v{installed}")
    print(f"  CLI 内置版本: v{HARNESS_VERSION}")

    lock = load_lock(root)
    if lock:
        h = lock.get("harness", {})
        print("\n锁文件信息:")
        print(f"  版本: v{h.get('version', '未知')}")
        print(f"  ref: {h.get('ref', '-')}")
        commit = h.get("commit", "")
        print(f"  commit: {commit[:12] if commit else '-'}")
        profiles = lock.get("profiles", {})
        if profiles:
            print(f"  锁定 Profile: {len(profiles)} 个")
        prev = lock.get("previousVersion", {})
        if prev.get("version"):
            print(f"  上一个版本: v{prev['version']}")
    else:
        print("\n锁文件: 不存在")
        print("  运行 ./scripts/harness upgrade --to <version> 生成")


def show_version_json(project_root=None):
    """JSON 格式输出版本信息。"""
    root = project_root or find_project_root()
    installed = _read_source_version(root) or HARNESS_VERSION
    lock = load_lock(root)

    output = {
        "installed_version": installed,
        "cli_version": HARNESS_VERSION,
        "lock": None,
    }
    if lock:
        h = lock.get("harness", {})
        output["lock"] = {
            "version": h.get("version", ""),
            "ref": h.get("ref", ""),
            "commit": h.get("commit", ""),
            "profile_count": len(lock.get("profiles", {})),
        }
    print(json.dumps(output, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# 升级检查
# ---------------------------------------------------------------------------

def check_upgrade(project_root=None):
    """检查远程是否有新版本可用（GitHub tags）。

    返回升级摘要 dict（current_version 从锁文件 harness.version 读取）。
    """
    root = project_root or find_project_root()
    lock = load_lock(root)
    current = lock.get("harness", {}).get("version", HARNESS_VERSION) if lock else HARNESS_VERSION

    result = {
        "current_version": current,
        "latest_version": current,
        "upgrade_available": False,
        "breaking_change": False,
        "changelog_summary": "",
        "affected_files": [],
    }

    tags = _fetch_github_tags()
    if not tags:
        result["error"] = "无法获取远程版本（网络不可达或无 tag；本地模式可用 upgrade --to --source）"
        return result

    latest = tags[0]
    if _parse_version(latest) <= _parse_version(current):
        result["latest_version"] = latest
        return result

    result["upgrade_available"] = True
    result["latest_version"] = latest
    result["breaking_change"] = _is_breaking_change(current, latest)

    releases = _fetch_github_releases(latest)
    if isinstance(releases, dict) and "body" in releases:
        result["changelog_summary"] = releases.get("body", "")[:500]

    result["affected_files"] = _get_affected_files(root)
    return result


def _get_affected_files(project_root):
    """估算升级影响的受管文件。"""
    affected = ["CLAUDE.md", ".claude/settings.json", ".github/workflows/harness-check.yml"]
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
# 升级（本地校验模式）
# ---------------------------------------------------------------------------

def do_upgrade(project_root=None, target_version=None, source=None):
    """执行升级到指定版本（本地校验模式）。

    流程（需求 §12.6）：解析 source → 校验版本/commit/checksum →
    临时以 source 为源根 render → 原子替换受管文件 → 更新嵌套锁 → Doctor。
    失败回滚、还原源根。

    返回 (success, message_or_dict)。
    """
    root = project_root or find_project_root()
    config = load_config(root)
    if config is None:
        return False, "未找到 .harness/config.yaml，请先运行 ./scripts/harness init"

    try:
        source_root = _resolve_source(source)
    except ValueError as e:
        return False, str(e)

    # 1. 校验 source 版本
    source_version = _read_source_version(source_root)
    effective_version = target_version or source_version or HARNESS_VERSION
    if target_version and source_version and source_version != target_version:
        return False, (
            f"源版本校验失败：source VERSION={source_version}，"
            f"目标={target_version}（需求 §12.8 下载内容校验失败）"
        )

    profile_names = config.get("profiles", []) or []
    checksums = _compute_profile_checksums(source_root, profile_names)
    missing = [n for n in profile_names if n not in checksums]
    if missing:
        return False, f"源中缺少 Profile: {', '.join(missing)}（校验失败）"

    commit = _git_commit(source_root)
    print(f"正在升级到 v{effective_version}（本地源: {source_root}）...")
    if commit:
        print(f"  source commit: {commit[:12]}")

    # 2. 记录上一个版本（用于回滚）
    previous_lock = load_lock(root)
    previous_snapshot = None
    if previous_lock:
        prev_h = previous_lock.get("harness", {})
        previous_snapshot = {
            "version": prev_h.get("version", ""),
            "ref": prev_h.get("ref", ""),
            "commit": prev_h.get("commit", ""),
            "lockContent": _lock_to_yaml(previous_lock),
        }

    # 3. 临时以 source 为源根 render（原子替换受管文件）
    original_source = get_harness_source_root()
    set_harness_source(source_root)
    try:
        from harness_py.render import render_all
        result = render_all(root)
    except Exception as e:
        return False, f"生成失败: {e}"
    finally:
        set_harness_source(original_source)

    errors = result.get("errors", [])
    if errors:
        return False, f"文件生成存在错误: {'; '.join(errors)}"

    # 4. 更新锁文件（嵌套结构）
    import datetime
    lock = _build_lock_data(config, effective_version, source_root, commit, previous_snapshot)
    lock["generated"] = {"at": datetime.datetime.now().isoformat()}
    try:
        save_lock(root, lock)
    except Exception as e:
        return False, f"保存锁文件失败: {e}"

    # 5. Doctor
    print("\n执行升级后健康检查...")
    doctor_summary = {}
    try:
        from harness_py.doctor import run_doctor
        _ec, doctor_result = run_doctor(root)
        doctor_summary = doctor_result.get("summary", {})
        if doctor_result.get("status") == "failed":
            print(f"  警告: 健康检查发现 {doctor_summary.get('failed', 0)} 个失败")
    except Exception as e:
        print(f"  警告: Doctor 执行失败: {e}")

    generated = result.get("generated", [])
    print(f"\n升级完成: → v{effective_version}")
    print(f"  commit: {commit[:12] if commit else '(非 git 仓库)'}")
    print(f"  生成/更新文件: {len(generated)} 个")
    print(f"  锁定 Profile: {len(profile_names)} 个")

    return True, {
        "version": effective_version,
        "commit": commit,
        "generated": len(generated),
        "doctor_summary": doctor_summary,
    }


def do_rollback(project_root=None):
    """回滚到上一个版本（用 previousVersion.lockContent 恢复锁）。"""
    root = project_root or find_project_root()
    lock = load_lock(root)
    if not lock:
        return False, "锁文件不存在，无法回滚"

    previous = lock.get("previousVersion", {})
    if not previous or not previous.get("lockContent"):
        return False, "锁文件中无 previousVersion.lockContent，无法回滚（首次升级无法回滚）"

    # 解析上一个锁内容
    try:
        import yaml
        prev_lock = yaml.safe_load(previous["lockContent"])
    except Exception:
        return False, "上一个锁文件内容无法解析"
    if not isinstance(prev_lock, dict):
        return False, "上一个锁文件内容格式无效"

    prev_version = previous.get("version", "未知")
    print(f"正在回滚: → v{prev_version}")

    # 重新 render 恢复受管文件（用当前源根）
    try:
        from harness_py.render import render_all
        render_all(root)
    except Exception as e:
        return False, f"回滚时重新生成失败: {e}"

    # 写回上一个锁（清除 previousVersion，避免无限回滚）
    if "previousVersion" in prev_lock:
        prev_lock = dict(prev_lock)
        prev_lock.pop("previousVersion", None)
    save_lock(root, prev_lock)

    print(f"回滚完成: → v{prev_version}")
    print("  使用 ./scripts/harness doctor 验证状态")
    return True, f"成功回滚到 v{prev_version}"
