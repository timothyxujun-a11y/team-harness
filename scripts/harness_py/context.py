"""上下文预算管理 — Team Harness CLI v2.0

管理 CLAUDE.md 和规则文件的上下文预算，确保 AI 上下文窗口不被超量占用。
"""

import os

from harness_py.utils import (
    find_project_root, get_core_dir, get_profiles_dir,
    estimate_tokens, safe_read_file, safe_read_yaml
)


# ------------------------------------------------------------------
# Token 估算
# ------------------------------------------------------------------

def estimate_file_tokens(filepath):
    """
    估算单个文件的 Token 数量。

    Args:
        filepath: 文件路径

    Returns:
        int: 估算的 Token 数量（文件不存在返回 0）
    """
    content = safe_read_file(filepath)
    if content is None:
        return 0
    return estimate_tokens(content)


def estimate_directory_tokens(dirpath):
    """
    估算目录下所有文件的总 Token 数量。

    递归遍历目录中所有文件（忽略隐藏文件、二进制文件），
    汇总每个文本文件的 Token 估算值。

    Args:
        dirpath: 目录路径

    Returns:
        int: 总估算 Token 数
    """
    if not os.path.isdir(dirpath):
        return 0

    total = 0
    for root, dirs, files in os.walk(dirpath):
        # 跳过隐藏目录
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for fname in files:
            if fname.startswith("."):
                continue
            total += estimate_file_tokens(os.path.join(root, fname))

    return total


# ------------------------------------------------------------------
# CLAUDE.md 预算检查
# ------------------------------------------------------------------

def check_claude_md_budget(project_root, config):
    """
    检查 CLAUDE.md 是否超出上下文预算。

    预算限制：
      - 行数 ≤ 200 行
      - 文件大小 ≤ 8KB
      - Token 数 ≤ 2000 Token

    Args:
        project_root: 项目根目录
        config: 项目配置字典（可选，用于读取自定义限制）

    Returns:
        (passed: bool, issues: list[str])
    """
    issues = []

    claude_path = os.path.join(project_root, "CLAUDE.md")
    if not os.path.isfile(claude_path):
        issues.append("CLAUDE.md 文件不存在")
        return False, issues

    content = safe_read_file(claude_path)
    if content is None:
        issues.append("无法读取 CLAUDE.md")
        return False, issues

    # 读取配置中的自定义限制
    budget = (config or {}).get("budget", {})
    claude_budget = budget.get("claudeMd", {})

    max_lines = claude_budget.get("maxLines", 200)
    max_size_kb = claude_budget.get("maxSizeKB", 8)
    max_tokens = claude_budget.get("maxTokens", 2000)

    lines = content.split("\n")
    line_count = len(lines)
    file_size_bytes = len(content.encode("utf-8"))
    file_size_kb = file_size_bytes / 1024.0
    token_count = estimate_tokens(content)

    if line_count > max_lines:
        issues.append(
            f"CLAUDE.md 行数超限: {line_count} 行（上限 {max_lines} 行）"
        )

    if file_size_kb > max_size_kb:
        issues.append(
            f"CLAUDE.md 文件大小超限: {file_size_kb:.1f}KB（上限 {max_size_kb}KB）"
        )

    if token_count > max_tokens:
        issues.append(
            f"CLAUDE.md Token 超限: {token_count} Token（上限 {max_tokens} Token）"
        )

    passed = len(issues) == 0
    return passed, issues


# ------------------------------------------------------------------
# Agent 规则内嵌检查
# ------------------------------------------------------------------

def check_agent_rules_embedded(project_root):
    """
    检查 Agent 文件是否仍然内嵌完整规则。

    v2.0 要求 Agent 使用动态规则选择，不应在 agent markdown 文件中内嵌完整规则内容。
    检查 .claude/agents/ 目录下的 .md 文件。

    启发式检测关键字：
      - "规则"、"Rule"、"rule" 段落中出现大量规则条目
      - 规则编号模式（CORE-xxx、HTTP-xxx 等）
      - 规则相关的 HTML 注释标记

    Args:
        project_root: 项目根目录

    Returns:
        (passed: bool, issues: list[str])
    """
    ISSUE_PATTERNS = [
        "## 规则",
        "### 规则",
        "## Rules",
        "### Rules",
    ]

    issues = []
    agents_dir = os.path.join(project_root, ".claude", "agents")

    if not os.path.isdir(agents_dir):
        return True, []  # 无 agent 目录则通过

    for fname in sorted(os.listdir(agents_dir)):
        if not fname.endswith(".md"):
            continue

        filepath = os.path.join(agents_dir, fname)
        content = safe_read_file(filepath)
        if content is None:
            continue

        for pattern in ISSUE_PATTERNS:
            if pattern in content:
                # 统计疑似规则条目的行数
                rule_lines = content.count("- id:") + content.count("规则")
                if rule_lines > 3:
                    issues.append(
                        f"Agent 内嵌规则: {filepath}（疑似内嵌 {rule_lines} 条规则，"
                        f"检测到 '{pattern}' 标记）"
                    )
                    break

                issues.append(
                    f"Agent 疑似内嵌规则: {filepath}（检测到 '{pattern}' 标记）"
                )
                break

    passed = len(issues) == 0
    return passed, issues


# ------------------------------------------------------------------
# 规则文件大小检查
# ------------------------------------------------------------------

def check_rule_file_sizes(project_root):
    """
    检查单个规则内容文件是否过大。

    遍历 Core 和所有 Profile 的 rules.yaml，检查每条规则指向的
    内容文件是否超过 2000 Token 限制。

    Args:
        project_root: 项目根目录

    Returns:
        (passed: bool, issues: list[str])
    """
    MAX_RULE_TOKEN = 2000
    issues = []

    # 收集所有 rules.yaml 路径
    rules_yaml_paths = []

    core_dir = get_core_dir(project_root)
    core_yaml = os.path.join(core_dir, "rules.yaml")
    if os.path.isfile(core_yaml):
        rules_yaml_paths.append(core_yaml)

    profiles_dir = get_profiles_dir(project_root)
    if os.path.isdir(profiles_dir):
        for name in sorted(os.listdir(profiles_dir)):
            profile_yaml = os.path.join(profiles_dir, name, "rules.yaml")
            if os.path.isfile(profile_yaml):
                rules_yaml_paths.append(profile_yaml)

    # 遍历所有 rules.yaml
    for yaml_path in rules_yaml_paths:
        base_dir = os.path.dirname(yaml_path)
        data = safe_read_yaml(yaml_path)
        if not data or "rules" not in data:
            continue

        for entry in data["rules"]:
            rule_id = entry.get("id", "?")
            content_path = entry.get("content", {}).get("path", "")
            if not content_path:
                continue

            full_path = os.path.join(base_dir, content_path)
            if not os.path.isfile(full_path):
                continue

            content = safe_read_file(full_path)
            if content is None:
                continue

            tokens = estimate_tokens(content)
            if tokens > MAX_RULE_TOKEN:
                issues.append(
                    f"规则文件过大: {rule_id} → {full_path} "
                    f"（{tokens} Token，上限 {MAX_RULE_TOKEN} Token）"
                )

    passed = len(issues) == 0
    return passed, issues


# ------------------------------------------------------------------
# 预算概览
# ------------------------------------------------------------------

def get_budget_summary(config):
    """
    返回上下文预算摘要。

    Args:
        config: 项目配置字典

    Returns:
        dict: 上下文预算信息
        {
            "claudeMd": {
                "maxLines": 200,
                "maxSizeKB": 8,
                "maxTokens": 2000
            },
            "rules": {
                "maxRules": 10,
                "maxTokens": 3000,
                "maxPerFile": 2000
            },
            "comments": "CLAUDE.md 常驻上下文上限 + 规则动态加载预算"
        }
    """
    budget = (config or {}).get("budget", {})

    claude_md = budget.get("claudeMd", {})
    rules_budget = budget.get("rules", {})

    summary = {
        "claudeMd": {
            "maxLines": claude_md.get("maxLines", 200),
            "maxSizeKB": claude_md.get("maxSizeKB", 8),
            "maxTokens": claude_md.get("maxTokens", 2000),
        },
        "rules": {
            "maxRules": rules_budget.get("maxRules", 10),
            "maxTokens": rules_budget.get("maxTokens", 3000),
            "maxPerFile": rules_budget.get("maxPerFile", 2000),
        },
        "comments": "CLAUDE.md 常驻上下文上限 + 规则动态加载预算",
    }

    return summary
