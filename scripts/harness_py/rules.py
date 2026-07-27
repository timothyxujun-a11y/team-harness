"""规则选择引擎 — Team Harness CLI v2.0

负责根据任务类型、变更文件、已启用 Profile 选择匹配的规则，
支持上下文预算限制和一致性检查。
"""

import os
import fnmatch
import json

from harness_py.utils import (
    find_project_root, get_core_dir, get_profiles_dir,
    estimate_tokens, safe_read_file, safe_read_yaml
)


# ------------------------------------------------------------------
# Glob 匹配（支持 ** 多级目录通配）
# ------------------------------------------------------------------

def _glob_match(path, pattern):
    """
    使用双指针回溯算法匹配 glob 模式，正确支持 ** 通配符。

    Args:
        path: 文件路径字符串（如 src/main/java/com/example/controller/OrderController.java）
        pattern: glob 模式（如 **/controller/**/*.java）

    Returns:
        bool: 是否匹配
    """
    path = path.replace("\\", "/")
    pattern = pattern.replace("\\", "/")

    path_parts = path.split("/")
    pattern_parts = pattern.split("/")

    pi, pj = 0, 0          # 当前指针
    star_pi, star_pj = -1, -1  # 上一次 ** 的锚点

    while pi < len(path_parts):
        if pj < len(pattern_parts):
            pat = pattern_parts[pj]
            if pat == "**":
                # 保存 ** 位置，跳过 ** 先尝试匹配下一段
                star_pi = pi
                star_pj = pj
                pj += 1
                continue
            if fnmatch.fnmatch(path_parts[pi], pat):
                # 当前段匹配，双方前进
                pi += 1
                pj += 1
                continue

        # 当前段不匹配 → 回退到上一个 ** 的位置，多消耗一个路径段
        if star_pj >= 0:
            star_pi += 1
            pi = star_pi
            pj = star_pj + 1
            continue

        return False

    # 路径消耗完毕，消耗模式末尾剩余的 **
    while pj < len(pattern_parts) and pattern_parts[pj] == "**":
        pj += 1

    return pj == len(pattern_parts)

# 尝试导入 profile 模块（模块可能尚未创建）
try:
    from harness_py.profile import resolve_profiles, merge_profiles
except ImportError:
    resolve_profiles = None
    merge_profiles = None


class RuleSelector:
    """规则选择器，负责从 Core 和已启用 Profile 中加载规则并匹配选择。"""

    def __init__(self, project_root, config):
        """
        初始化规则选择器。

        Args:
            project_root: 项目根目录路径
            config: 项目配置字典（.harness/config.yaml 解析结果）
        """
        self.project_root = project_root
        self.config = config or {}
        self.all_rules = []
        self._profiles_cache = None
        self._load_all_rules()

    # ------------------------------------------------------------------
    # Profile 解析
    # ------------------------------------------------------------------

    def _get_enabled_profiles(self):
        """获取已启用的 Profile 列表（含依赖解析）。"""
        if self._profiles_cache is not None:
            return self._profiles_cache

        enabled = self.config.get("profiles", [])

        if resolve_profiles is not None and enabled:
            try:
                resolved = resolve_profiles(enabled, self.project_root)
                self._profiles_cache = resolved
                return resolved
            except Exception:
                pass

        self._profiles_cache = enabled
        return enabled

    # ------------------------------------------------------------------
    # 规则加载
    # ------------------------------------------------------------------

    def _load_all_rules(self):
        """从 Core 和已启用 Profile 加载全部规则。"""
        all_rules = []

        # 1. 加载 Core 规则
        core_dir = get_core_dir(self.project_root)
        core_rules = self._load_rules_from_dir(core_dir, profile_name=None, is_core=True)
        all_rules.extend(core_rules)

        # 2. 加载各 Profile 规则
        enabled = self._get_enabled_profiles()
        profiles_dir = get_profiles_dir(self.project_root)
        for profile_name in enabled:
            profile_dir = os.path.join(profiles_dir, profile_name)
            if os.path.isdir(profile_dir):
                profile_rules = self._load_rules_from_dir(
                    profile_dir, profile_name=profile_name, is_core=False
                )
                all_rules.extend(profile_rules)

        self.all_rules = all_rules

    @staticmethod
    def _load_rules_from_dir(directory, profile_name, is_core):
        """从指定目录加载 rules.yaml 中的规则列表。"""
        rules_path = os.path.join(directory, "rules.yaml")
        data = safe_read_yaml(rules_path)
        if not data or "rules" not in data:
            return []

        rules = []
        for entry in data["rules"]:
            rule = {
                "id": entry.get("id", ""),
                "title": entry.get("title", ""),
                "description": entry.get("description", ""),
                "severity": entry.get("severity", "info"),
                "enforced": entry.get("enforced", False),
                "selectors": entry.get("selectors", {}),
                "content": entry.get("content", {}),
                "context": entry.get("context", {}),
                "profile": profile_name,
                "is_core": is_core,
                "dir": directory,
            }
            rules.append(rule)

        return rules

    # ------------------------------------------------------------------
    # 匹配逻辑
    # ------------------------------------------------------------------

    def _matches_profile(self, rule):
        """检查规则所属 Profile 是否在已启用列表中（Core 规则始终通过）。"""
        if rule.get("is_core"):
            return True

        enabled = self._get_enabled_profiles()
        rp = rule.get("profile")
        if not rp:
            return True
        return rp in enabled

    def _matches_paths(self, rule, files):
        """
        检查提供的文件列表是否与规则路径选择器匹配。

        规则至少有一条 include glob 匹配、且全部文件均不匹配 exclude glob 时通过。
        当 files 为 None 或空列表时不限制路径。

        使用 _glob_match 正确支持 ** 多级目录通配符。
        """
        if not files:
            return True

        selectors = rule.get("selectors", {})
        paths_cfg = selectors.get("paths", None)
        if not paths_cfg:
            return True

        include_patterns = paths_cfg.get("include", [])
        exclude_patterns = paths_cfg.get("exclude", [])

        if not include_patterns:
            return True

        for f in files:
            f_normalized = f.replace("\\", "/")

            matched_include = any(
                _glob_match(f_normalized, pat) for pat in include_patterns
            )
            if not matched_include:
                continue

            matched_exclude = any(
                _glob_match(f_normalized, pat) for pat in exclude_patterns
            )
            if matched_exclude:
                continue

            # 至少一个文件匹配 include 且不匹配 exclude
            return True

        return False

    def _matches_tasks(self, rule, task):
        """检查规则的任务选择器是否匹配给定任务类型。"""
        if not task:
            return True

        selectors = rule.get("selectors", {})
        valid_tasks = selectors.get("tasks", None)
        if not valid_tasks:
            return True

        return task in valid_tasks

    # ------------------------------------------------------------------
    # 排序
    # ------------------------------------------------------------------

    @staticmethod
    def _sort_priority(rule):
        """生成规则排序键：priority > enforced > severity。"""
        priority_order = {"high": 0, "medium": 1, "low": 2}
        severity_order = {"error": 0, "warning": 1, "info": 2}

        ctx = rule.get("context", {})
        priority = ctx.get("priority", "low")
        enforced = rule.get("enforced", False)
        severity = rule.get("severity", "info")

        return (
            priority_order.get(priority, 2),
            0 if enforced else 1,
            severity_order.get(severity, 2),
        )

    # ------------------------------------------------------------------
    # 主选择入口
    # ------------------------------------------------------------------

    def select(self, task=None, files=None, annotations=None,
               max_rules=None, max_tokens=None, budget_config=None):
        """
        根据任务、变更文件、注解筛选匹配的规则。

        Args:
            task: 任务类型，如 "code-review"、"feature-development"
            files: 变更文件路径列表（相对于项目根目录）
            annotations: 注解列表（预留参数，当前不在此模块实现）
            max_rules: 最多返回的规则数量
            max_tokens: 规则内容的总 Token 上限
            budget_config: 预算配置字典，可覆盖 max_rules/max_tokens

        Returns:
            dict: {
                "task": str | None,
                "matchedProfiles": [str, ...],
                "selectedRules": [
                    {
                        "id": "HTTP-ARCH-001",
                        "path": "profiles/spring-http/rules/controller.md",
                        "reason": "Controller file changed (路径匹配)",
                        "estimatedTokens": 450
                    },
                    ...
                ],
                "estimatedTotalTokens": int
            }
        """
        # 解析最终预算限制（budget_config 优先级高于显式参数）
        if budget_config:
            budget_max_rules = budget_config.get("maxRules", None)
            budget_max_tokens = budget_config.get("maxTokens", None)
        else:
            budget_max_rules = None
            budget_max_tokens = None

        final_max_rules = budget_max_rules if budget_max_rules is not None else max_rules
        final_max_tokens = budget_max_tokens if budget_max_tokens is not None else max_tokens

        # ---- 遍历全部规则，收集匹配项 ----
        enabled_profiles = self._get_enabled_profiles()
        matched_rules = []          # 排序前的原始匹配列表

        for rule in self.all_rules:
            # 1. Profile 准入
            if not self._matches_profile(rule):
                continue

            # 2. 路径匹配
            if not self._matches_paths(rule, files):
                continue

            # 3. 任务匹配
            if not self._matches_tasks(rule, task):
                continue

            # 4. 注解匹配（预留，不在本模块实现）
            #    外部调用方可在调用 select 前使用 annotations 参数自行过滤

            # ---- 生成匹配原因 ----
            reason_parts = []
            if not rule.get("is_core"):
                reason_parts.append(f"Profile({rule.get('profile', '')})")
            if file_reason := self._path_match_reason(rule, files):
                reason_parts.append(f"路径匹配({file_reason})")
            if task and self._matches_tasks(rule, task):
                reason_parts.append(f"任务匹配({task})")
            if not reason_parts:
                reason_parts.append("全局适用")
            reason = " ".join(reason_parts) if reason_parts else "默认加载"

            # ---- 规则文件路径（相对于项目根目录） ----
            content_rel_path = rule.get("content", {}).get("path", "")
            if content_rel_path:
                try:
                    full = os.path.join(rule["dir"], content_rel_path)
                    display_path = os.path.relpath(full, self.project_root)
                except ValueError:
                    display_path = content_rel_path
            else:
                display_path = ""

            matched_rules.append((self._sort_priority(rule), {
                "id": rule["id"],
                "path": display_path,
                "reason": reason,
                "estimatedTokens": rule.get("context", {}).get("estimatedTokens", 0),
                "_profile": rule.get("profile"),
            }))

        # ---- 排序 ----
        matched_rules.sort(key=lambda x: x[0])
        sorted_matches = [item[1] for item in matched_rules]

        # ---- 应用预算截断 ----
        selected = []
        running_tokens = 0

        for r in sorted_matches:
            if final_max_rules is not None and len(selected) >= final_max_rules:
                break
            if final_max_tokens is not None and (running_tokens + r["estimatedTokens"]) > final_max_tokens:
                break

            selected.append(r)
            running_tokens += r["estimatedTokens"]

        # ---- 收集匹配的 Profile ----
        matched_profiles = []
        profile_counts = {}
        for r in selected:
            p = r.pop("_profile", None)
            if p:
                profile_counts[p] = profile_counts.get(p, 0) + 1

        # 保持启用顺序
        for p in enabled_profiles:
            if p in profile_counts:
                matched_profiles.append(p)
        for p in sorted(profile_counts.keys()):
            if p not in matched_profiles:
                matched_profiles.append(p)

        return {
            "task": task,
            "matchedProfiles": matched_profiles,
            "selectedRules": selected,
            "estimatedTotalTokens": running_tokens,
        }

    @staticmethod
    def _path_match_reason(rule, files):
        """生成路径匹配原因的人类可读文本。"""
        if not files:
            return ""
        selectors = rule.get("selectors", {})
        paths_cfg = selectors.get("paths", None)
        if not paths_cfg:
            return ""
        include = paths_cfg.get("include", [])
        if not include:
            return ""
        return ", ".join(include[:3])  # 最多展示 3 个 pattern


# ------------------------------------------------------------------
# 一致性检查
# ------------------------------------------------------------------

def check_consistency(project_root, config):
    """
    规则一致性检查。

    检查项：
      - 重复规则 ID
      - 规则文件缺失（content.path 指向的文件不存在）
      - 废弃规则仍在使用
      - Token 估算缺失

    Args:
        project_root: 项目根目录
        config: 项目配置字典

    Returns:
        (passed: bool, issues: list[str])
    """
    issues = []
    selector = RuleSelector(project_root, config)
    all_rules = selector.all_rules

    # 1. 重复规则 ID
    id_counts = {}
    for rule in all_rules:
        rid = rule["id"]
        id_counts[rid] = id_counts.get(rid, 0) + 1

    for rid, count in id_counts.items():
        if count > 1:
            issues.append(f"重复规则 ID: {rid}（出现 {count} 次）")

    # 2. 规则文件缺失
    for rule in all_rules:
        content_path = rule.get("content", {}).get("path", "")
        if not content_path:
            continue
        full_path = os.path.join(rule["dir"], content_path)
        if not os.path.isfile(full_path):
            title = rule.get("title", "")
            issues.append(f"规则文件缺失: {rule['id']} → {full_path}（{title}）")

    # 3. 废弃规则仍在使用
    for rule in all_rules:
        if rule.get("selectors", {}).get("deprecated"):
            issues.append(f"废弃规则仍在使用: {rule['id']} — {rule.get('title', '')}")

    # 4. Token 估算缺失
    for rule in all_rules:
        estimated = rule.get("context", {}).get("estimatedTokens")
        if estimated is None or estimated <= 0:
            issues.append(f"Token 估算缺失: {rule['id']} — {rule.get('title', '')}")

    passed = len(issues) == 0
    return passed, issues
