"""Profile 加载与合并模块."""

import os

from harness_py.utils import safe_read_yaml, get_profiles_dir, get_core_dir


# --------------------------------------------------------------------------- #
# 公共函数
# --------------------------------------------------------------------------- #

def load_profile(project_root, profile_name):
    """从 profiles/<name>/ 加载 profile.yaml，返回 dict。

    文件不存在时返回 None；文件存在但无法解析时抛出 RuntimeError。
    """
    profiles_dir = get_profiles_dir(project_root)
    profile_path = os.path.join(profiles_dir, profile_name, "profile.yaml")
    if not os.path.exists(profile_path):
        return None

    data = safe_read_yaml(profile_path)
    if data is None:
        raise RuntimeError(
            f"无法解析 Profile 文件 {profile_path}，请确保已安装 pyyaml (pip install pyyaml)"
        )
    return data


def resolve_profiles(project_root, profile_names):
    """解析 Profile 依赖链，返回有序列表（依赖在前，依赖者在后）。

    检测循环依赖和缺失依赖，发现时抛出 ValueError。
    """
    result = []
    visited = set()
    visiting = set()

    def _visit(name):
        if name in visited:
            return
        if name in visiting:
            raise ValueError(f"检测到循环依赖: {name}")

        profile = load_profile(project_root, name)
        if profile is None:
            raise ValueError(f"Profile 不存在: {name}")

        visiting.add(name)

        deps = profile.get("dependsOn", []) or []
        for dep in deps:
            _visit(dep)

        visiting.discard(name)
        visited.add(name)
        result.append(name)

    for name in profile_names:
        _visit(name)

    return result


def merge_profiles(project_root, core_data, profile_data_list):
    """按 Core → Profile 依赖 → 显式选择顺序合并所有 rules.yaml 条目。

    若同一规则 ID 在不同来源中定义不一致，抛出 ValueError。
    若 Profile 间存在 conflictsWith 冲突，抛出 ValueError。
    """
    # 先检查 conflictsWith 冲突
    validate_profile_conflicts(profile_data_list)

    merged_rules = []
    seen = {}  # rule_id -> (source_name, rule_dict)

    def _add_rules(source_name, rules):
        for rule in rules:
            rule_id = rule.get("id", "")
            if rule_id in seen:
                existing_source, existing_rule = seen[rule_id]
                if rule != existing_rule:
                    raise ValueError(
                        f"规则冲突: 规则 '{rule_id}' 定义不一致 "
                        f"(来源: '{existing_source}' 与 '{source_name}')"
                    )
                # 内容一致，跳过（去重）
            else:
                seen[rule_id] = (source_name, rule)
                merged_rules.append(rule)

    # 1. 加载 Core 规则
    core_dir = get_core_dir(project_root)
    core_rules_name = core_data.get("content", {}).get("rules", "rules.yaml")
    core_rules_path = os.path.join(core_dir, core_rules_name)
    core_rules_data = safe_read_yaml(core_rules_path)
    if core_rules_data and "rules" in core_rules_data:
        _add_rules("core", core_rules_data["rules"])

    # 2. 按依赖顺序加载 Profile 规则
    profiles_dir = get_profiles_dir(project_root)
    for profile_data in profile_data_list:
        profile_name = profile_data.get("metadata", {}).get("name", "")
        rules_name = profile_data.get("content", {}).get("rules", "rules.yaml")
        rules_path = os.path.join(profiles_dir, profile_name, rules_name)
        rules_data = safe_read_yaml(rules_path)
        if rules_data and "rules" in rules_data:
            _add_rules(profile_name, rules_data["rules"])

    return {
        "rules": merged_rules,
        "ruleCount": len(merged_rules),
        "sources": {rid: src for rid, (src, _) in seen.items()},
    }


def get_enabled_profiles_text(profile_names):
    """返回人类可读的启用 Profile 描述。"""
    if not profile_names:
        return "无"
    return ", ".join(profile_names)


def validate_profile_conflicts(profiles):
    """检查 Profile 间的 conflictsWith 冲突。

    发现冲突时抛出 ValueError 并说明冲突来源。
    无冲突时返回 True。
    """
    profile_names = [
        p.get("metadata", {}).get("name", "") for p in profiles
    ]
    for profile in profiles:
        name = profile.get("metadata", {}).get("name", "")
        conflicts = profile.get("conflictsWith", []) or []
        for conflict in conflicts:
            if conflict in profile_names:
                raise ValueError(
                    f"Profile 冲突: '{name}' 声明与 '{conflict}' 不兼容 "
                    f"(来源: '{name}' profile.yaml 的 conflictsWith)"
                )
    return True
