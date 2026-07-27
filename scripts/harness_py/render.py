"""文件生成模块 — 生成所有 Harness 受管文件。"""

import os
import re
import sys
import json
import hashlib
import shutil
import difflib
import tempfile

from harness_py.utils import (
    find_project_root,
    get_core_dir,
    get_profiles_dir,
    get_templates_dir,
    sha256_of_file,
    safe_read_file,
    safe_read_yaml,
    HARNESS_VERSION,
)
from harness_py.config import load_config, get_build_commands
from harness_py.profile import resolve_profiles, get_enabled_profiles_text
from harness_py.rules import RuleSelector


# ---------------------------------------------------------------------------
# 路径工具
# ---------------------------------------------------------------------------

def _harness_dir(project_root):
    return os.path.join(project_root, ".harness")


def _managed_files_path(project_root):
    return os.path.join(_harness_dir(project_root), "managed-files.json")


def _docs_harness_dir(project_root):
    return os.path.join(project_root, "docs", "harness")


def _claude_md_path(project_root):
    return os.path.join(project_root, "CLAUDE.md")


def _claude_local_md_path(project_root):
    return os.path.join(project_root, "CLAUDE.local.md")


def _settings_json_path(project_root):
    return os.path.join(project_root, ".claude", "settings.json")


def _github_workflow_path(project_root):
    return os.path.join(project_root, ".github", "workflows", "harness-check.yml")


# ---------------------------------------------------------------------------
# 简单模板渲染（支持 {{ var }} / {% if var %} / {% for x in y %}）
# ---------------------------------------------------------------------------

def _render_template(template_text, variables):
    """简易模板渲染。

    支持语法：
        {{ var }}                       — 变量替换
        {% if var %} ... {% endif %}    — 条件块
        {% for item in list %} ... {% endfor %} — 循环块
        {{ var | filter1 | filter2 }}   — 管道过滤器（join）
    """
    result = template_text
    result = _render_for_blocks(result, variables)
    result = _render_if_blocks(result, variables)
    result = _render_variables(result, variables)
    return result


def _render_for_blocks(text, variables):
    """处理 {% for item in list_name %} ... {% endfor %}"""

    pattern = r'\{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%\}'
    end_pattern = r'\{%\s*endfor\s*%\}'

    while True:
        match = re.search(pattern, text)
        if not match:
            break

        # 找到对应的 {% endfor %}
        start = match.start()
        depth = 1
        pos = match.end()
        end_tag = None
        while pos < len(text):
            next_for = re.search(pattern, text[pos:])
            next_end = re.search(end_pattern, text[pos:])
            if next_end is None:
                break
            if next_for and next_for.start() < next_end.start():
                depth += 1
                pos += next_for.end()
            else:
                depth -= 1
                if depth == 0:
                    end_tag = next_end
                    break
                pos += next_end.end()

        if end_tag is None:
            break

        item_var = match.group(1)
        list_name = match.group(2)
        inner = text[match.end():start + end_tag.start()]

        items = variables.get(list_name, [])
        rendered = ""
        for item_data in items:
            item_vars = dict(variables)
            if isinstance(item_data, dict):
                item_vars[item_var] = item_data
            else:
                item_vars[item_var] = item_data
            rendered += _render_template(inner, item_vars)

        text = text[:start] + rendered + text[start + end_tag.end():]
    return text


def _render_if_blocks(text, variables):
    """处理 {% if var %} ... {% endif %}"""

    pattern = r'\{%\s*if\s+(\w+)\s*%\}'
    end_pattern = r'\{%\s*endif\s*%\}'

    while True:
        match = re.search(pattern, text)
        if not match:
            break

        start = match.start()
        var_name = match.group(1)
        inner_start = match.end()

        # 找对应的 {% endif %}
        depth = 1
        pos = inner_start
        end_tag = None
        while pos < len(text):
            next_if = re.search(pattern, text[pos:])
            next_end = re.search(end_pattern, text[pos:])
            if next_end is None:
                break
            if next_if and next_if.start() < next_end.start():
                depth += 1
                pos += next_if.end()
            else:
                depth -= 1
                if depth == 0:
                    end_tag = next_end
                    break
                pos += next_end.end()

        if end_tag is None:
            break

        inner = text[inner_start:start + end_tag.start()]
        value = variables.get(var_name, False)

        if value:
            text = text[:start] + inner + text[start + end_tag.end():]
        else:
            text = text[:start] + text[start + end_tag.end():]
    return text


def _render_variables(text, variables):
    """处理 {{ var }} 和 {{ var | filter }}"""

    def replace_var(match):
        expr = match.group(1).strip()
        parts = expr.split("|")
        var_name = parts[0].strip()
        filters = [p.strip() for p in parts[1:]]

        value = variables.get(var_name, "")
        for f in filters:
            if f == "join" and isinstance(value, list):
                # {{ x | join(', ') }} — already handled in the context
                pass
        return str(value)

    return re.sub(r'\{\{\s*(.+?)\s*\}\}', replace_var, text)


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------

def _load_template(name):
    """加载模板文件内容。"""
    tpl_dir = get_templates_dir()
    tpl_path = os.path.join(tpl_dir, name)
    content = safe_read_file(tpl_path)
    if content is None:
        raise FileNotFoundError(f"模板文件不存在: {tpl_path}")
    return content


def _ensure_dir(path):
    """确保目录存在。"""
    os.makedirs(path, exist_ok=True)


def _write_file_atomic(path, content):
    """原子写入文件：先写临时文件 → 重命名。"""
    _ensure_dir(os.path.dirname(path))
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".harness-tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def _load_json(path):
    """安全加载 JSON 文件。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError):
        return {}


def _save_json(path, data):
    """保存 JSON 文件。"""
    _ensure_dir(os.path.dirname(path))
    _write_file_atomic(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _load_managed_files(project_root):
    """加载受管文件清单。"""
    path = _managed_files_path(project_root)
    return _load_json(path)


def _save_managed_files(project_root, data):
    """保存受管文件清单。"""
    path = _managed_files_path(project_root)
    _save_json(path, data)


def _build_file_map(project_root):
    """构建受管文件路径映射。"""
    return {
        "CLAUDE.md": _claude_md_path(project_root),
        ".claude/settings.json": _settings_json_path(project_root),
        ".github/workflows/harness-check.yml": _github_workflow_path(project_root),
    }


# ---------------------------------------------------------------------------
# 构建模板变量
# ---------------------------------------------------------------------------

def _build_claude_variables(project_root, config):
    """构建 CLAUDE.md 模板变量。"""
    build_cmds = get_build_commands(config) or {}

    profiles = resolve_profiles(config)
    enabled_names = [p.get("name", "") for p in profiles if p.get("name")]
    enabled_profiles_text = ", ".join(enabled_names)

    # 构建规则索引
    rule_index = []
    # Core 入口
    core_dir = get_core_dir(project_root)
    if os.path.isdir(core_dir):
        rule_index.append({
            "name": "核心规则",
            "path": "docs/harness/core/index.md"
        })
    # 各 Profile 入口
    for p in profiles:
        pname = p.get("name", "")
        if pname:
            rule_index.append({
                "name": f"{pname} Profile",
                "path": f"docs/harness/{pname}/index.md"
            })

    has_local = os.path.exists(_claude_local_md_path(project_root))

    return {
        "harness_version": HARNESS_VERSION,
        "project_name": config.get("project", {}).get("name", "[未配置]"),
        "project_description": config.get("project", {}).get("description", ""),
        "java_version": config.get("runtime", {}).get("javaVersion", "11"),
        "enabled_profiles": enabled_profiles_text,
        "compile_command": build_cmds.get("compile", "mvn compile -DskipTests"),
        "test_command": build_cmds.get("test", "mvn test"),
        "package_command": build_cmds.get("package", "mvn clean package -DskipTests"),
        "rule_index": rule_index,
        "local_rules_index": ".harness/local/index.yaml",
        "context_max_tokens": 2000,
        "context_max_files": 3,
        "task_max_tokens": 6000,
        "task_max_files": 8,
        "review_max_tokens": 8000,
        "review_max_rules": 15,
        "has_local_readme": has_local,
        "local_rules_main": "CLAUDE.local.md",
    }


def _build_profile_variables(profile_dir, profile_name):
    """为单个 Profile 构建 index.md 模板变量。"""
    profile_yaml = safe_read_yaml(os.path.join(profile_dir, "profile.yaml"))
    if not profile_yaml:
        return None

    meta = profile_yaml.get("metadata", {})
    rules_data = safe_read_yaml(os.path.join(profile_dir, "rules.yaml"))
    rules = []
    if rules_data and "rules" in rules_data:
        for r in rules_data["rules"]:
            rules.append({
                "id": r.get("id", "-"),
                "severity": r.get("severity", "-"),
                "title": r.get("title", "-"),
                "triggers": r.get("triggers", []),
                "path": r.get("path", "-"),
            })

    return {
        "harness_version": HARNESS_VERSION,
        "profile_name": meta.get("name", profile_name),
        "profile_version": meta.get("version", "1.0.0"),
        "profile_description": meta.get("description", ""),
        "rules": rules,
    }


# ---------------------------------------------------------------------------
# 生成各文件内容
# ---------------------------------------------------------------------------

def _generate_claude_md(project_root, config):
    """生成 CLAUDE.md 内容。"""
    tpl = _load_template("CLAUDE.md.tpl")
    vars_ = _build_claude_variables(project_root, config)
    return _render_template(tpl, vars_)


def _generate_profile_indexes(project_root, config):
    """为每个启用的 Profile 生成 docs/harness/<name>/index.md。"""
    profiles = resolve_profiles(config)
    tpl = _load_template("profile-index.md.tpl")
    results = {}

    for p in profiles:
        pname = p.get("name", "")
        pdir = p.get("dir", "")
        if not pname or not pdir or not os.path.isdir(pdir):
            continue

        vars_ = _build_profile_variables(pdir, pname)
        if vars_ is None:
            continue

        content = _render_template(tpl, vars_)
        dest_rel = f"docs/harness/{pname}/index.md"
        results[dest_rel] = content

    # Core 的 index.md
    core_dir = get_core_dir(project_root)
    if os.path.isdir(core_dir):
        vars_ = _build_profile_variables(core_dir, "core")
        if vars_:
            results["docs/harness/core/index.md"] = _render_template(tpl, vars_)

    return results


def _generate_settings_json(project_root, config):
    """生成 .claude/settings.json 内容。"""
    tpl = _load_template("settings.json.tpl")
    return _render_template(tpl, {})


def _generate_workflow(project_root, config):
    """生成 .github/workflows/harness-check.yml 内容。"""
    tpl = _load_template("workflows/harness-check.yml.tpl")
    build_cmds = get_build_commands(config) or {}
    return _render_template(tpl, {
        "harness_version": HARNESS_VERSION,
        "java_version": config.get("runtime", {}).get("javaVersion", "11"),
        "compile_command": build_cmds.get("compile", "mvn compile -DskipTests"),
        "test_command": build_cmds.get("test", "mvn test"),
        "diff_base_branch": "origin/main",
        "diff_coverage_threshold": "80",
        "project_name": config.get("project", {}).get("name", "unknown"),
    })


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------

def render_all(project_root=None, dry_run=False, diff_mode=False):
    """生成所有受管文件。

    参数：
        project_root: 项目根目录路径
        dry_run: 仅预览，不实际写入文件
        diff_mode: 以 diff 形式输出变更

    返回：
        dict: {"generated": [...], "skipped": [...], "errors": [...]}
    """
    root = project_root or find_project_root()
    config = load_config(root)
    errors = []

    # 所有待生成文件的清单
    file_manifest = {}
    managed_files = {}
    file_map = _build_file_map(root)

    try:
        # 1. CLAUDE.md
        claude_content = _generate_claude_md(root, config)
        file_manifest["CLAUDE.md"] = claude_content
        managed_files["CLAUDE.md"] = file_map["CLAUDE.md"]
    except Exception as e:
        errors.append(f"生成 CLAUDE.md 失败: {e}")

    try:
        # 2. Profile index.md 文件
        profile_indexes = _generate_profile_indexes(root, config)
        for rel_path, content in profile_indexes.items():
            file_manifest[rel_path] = content
            managed_files[rel_path] = os.path.join(root, rel_path)
    except Exception as e:
        errors.append(f"生成 Profile index 失败: {e}")

    try:
        # 3. settings.json
        settings_content = _generate_settings_json(root, config)
        file_manifest[".claude/settings.json"] = settings_content
        managed_files[".claude/settings.json"] = file_map[".claude/settings.json"]
    except Exception as e:
        errors.append(f"生成 settings.json 失败: {e}")

    try:
        # 4. GitHub Workflow
        workflow_content = _generate_workflow(root, config)
        file_manifest[".github/workflows/harness-check.yml"] = workflow_content
        managed_files[".github/workflows/harness-check.yml"] = file_map[".github/workflows/harness-check.yml"]
    except Exception as e:
        errors.append(f"生成 Workflow 失败: {e}")

    # 记录受管文件清单（含 SHA256）
    managed_records = {}
    for rel_path, abs_path in managed_files.items():
        managed_records[rel_path] = {
            "path": abs_path,
            "generated": True,
        }

    # dry_run 模式只打印不写入
    if dry_run:
        print("[dry-run] 以下文件将会生成/更新：")
        for rel_path in sorted(file_manifest.keys()):
            print(f"  - {rel_path}")
        return {
            "generated": list(file_manifest.keys()),
            "skipped": [],
            "errors": errors,
        }

    # diff_mode 输出 diff
    if diff_mode:
        for rel_path, content in sorted(file_manifest.items()):
            abs_path = managed_files.get(rel_path, "")
            existing = safe_read_file(abs_path) or ""
            if existing != content:
                diff = difflib.unified_diff(
                    existing.splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile=f"a/{rel_path}",
                    tofile=f"b/{rel_path}",
                )
                sys.stdout.writelines(diff)
        return {
            "generated": list(file_manifest.keys()),
            "skipped": [],
            "errors": errors,
        }

    # 正常生成模式
    generated = []
    skipped = []
    for rel_path, content in sorted(file_manifest.items()):
        abs_path = managed_files.get(rel_path, "")
        assert abs_path, f"未知路径: {rel_path}"

        # 检查是否需要更新
        existing = safe_read_file(abs_path)
        if existing == content:
            skipped.append(rel_path)
            _record_hash(managed_records, rel_path, content)
            continue

        _write_file_atomic(abs_path, content)
        generated.append(rel_path)
        _record_hash(managed_records, rel_path, content)

    # 保存受管文件清单
    _save_managed_files(root, managed_records)

    return {
        "generated": generated,
        "skipped": skipped,
        "errors": errors,
    }


def _record_hash(records, rel_path, content):
    """记录文件内容的 SHA256。"""
    h = hashlib.sha256()
    h.update(content.encode("utf-8"))
    records[rel_path]["sha256"] = h.hexdigest()


def render_check(project_root=None):
    """检查生成文件是否有漂移。

    返回：
        (bool, list): (文件是否全部一致, 漂移文件列表)
    """
    root = project_root or find_project_root()
    config = load_config(root)
    drifts = []
    file_map = _build_file_map(root)

    # 检查 CLAUDE.md
    try:
        expected = _generate_claude_md(root, config)
        actual = safe_read_file(file_map["CLAUDE.md"]) or ""
        if actual != expected:
            drifts.append("CLAUDE.md")
    except Exception as e:
        drifts.append(f"CLAUDE.md (错误: {e})")

    # 检查 Profile indexes
    try:
        profile_indexes = _generate_profile_indexes(root, config)
        for rel_path, expected_content in profile_indexes.items():
            actual = safe_read_file(os.path.join(root, rel_path)) or ""
            if actual != expected_content:
                drifts.append(rel_path)
    except Exception as e:
        drifts.append(f"profile indexes (错误: {e})")

    # 检查 settings.json
    try:
        expected = _generate_settings_json(root, config)
        actual = safe_read_file(file_map[".claude/settings.json"]) or ""
        if actual != expected:
            drifts.append(".claude/settings.json")
    except Exception as e:
        drifts.append(f".claude/settings.json (错误: {e})")

    # 检查 workflow
    try:
        expected = _generate_workflow(root, config)
        actual = safe_read_file(file_map[".github/workflows/harness-check.yml"]) or ""
        if actual != expected:
            drifts.append(".github/workflows/harness-check.yml")
    except Exception as e:
        drifts.append(f".github/workflows/harness-check.yml (错误: {e})")

    ok = len(drifts) == 0
    return ok, drifts


def render_diff(project_root=None):
    """以 diff 格式输出当前文件与预期文件的差异。"""
    root = project_root or find_project_root()
    config = load_config(root)
    file_map = _build_file_map(root)

    checks = {
        "CLAUDE.md": (_generate_claude_md(root, config), file_map["CLAUDE.md"]),
        ".claude/settings.json": (_generate_settings_json(root, config), file_map[".claude/settings.json"]),
        ".github/workflows/harness-check.yml": (_generate_workflow(root, config), file_map[".github/workflows/harness-check.yml"]),
    }

    try:
        profile_indexes = _generate_profile_indexes(root, config)
        for rel_path, expected_content in profile_indexes.items():
            checks[rel_path] = (expected_content, os.path.join(root, rel_path))
    except Exception:
        pass

    has_diff = False
    for rel_path, (expected, abs_path) in sorted(checks.items()):
        actual = safe_read_file(abs_path) or ""
        if actual != expected:
            has_diff = True
            diff_lines = difflib.unified_diff(
                actual.splitlines(keepends=True),
                expected.splitlines(keepends=True),
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
            )
            sys.stdout.writelines(diff_lines)

    return has_diff
