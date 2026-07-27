"""v1 → v2 迁移模块。

将 v1 风格项目（CLAUDE.md 含 ``[CUSTOMIZE: ...]`` 占位 + docs/conventions.md）
迁移到 v2 结构（.harness/config.yaml + .harness/local/ + 自动生成的 CLAUDE.md）。

遵循需求 §18：识别 [CUSTOMIZE] → 提取项目名/描述 → 推荐 Profile →
迁移项目特殊内容到 Local 文件 → 备份旧文件 → 生成新文件 → 预算检查 → Doctor。
"""

import os
import re
import shutil
import datetime

from harness_py.utils import (
    find_project_root, safe_read_file, safe_read_yaml,
)
from harness_py.config import (
    create_default_config, save_config, load_config,
)


# v1 占位标记
_CUSTOMIZE_PATTERN = re.compile(r"\[CUSTOMIZE[^\]]*\]")
_CUSTOMIZE_VALUE_PATTERN = re.compile(r"\[CUSTOMIZE:\s*([^\],]+)")


# ---------------------------------------------------------------------------
# v1 痕迹检测
# ---------------------------------------------------------------------------

def detect_v1_markers(project_root):
    """检测项目中的 v1 痕迹，返回标记 dict。

    返回：
        {
            "has_customize": bool,
            "customize_lines": [str, ...],   # 含 [CUSTOMIZE] 的行
            "has_legacy_conventions": bool,
            "claude_md": str | None,         # 旧 CLAUDE.md 内容
        }
    """
    markers = {
        "has_customize": False,
        "customize_lines": [],
        "has_legacy_conventions": False,
        "claude_md": None,
    }

    claude_md_path = os.path.join(project_root, "CLAUDE.md")
    content = safe_read_file(claude_md_path)
    if content:
        markers["claude_md"] = content
        for line in content.splitlines():
            if "[CUSTOMIZE" in line:
                markers["has_customize"] = True
                markers["customize_lines"].append(line.strip())

    # 旧的集中式规范文档（v2 已拆分为 core/profiles）
    conventions_path = os.path.join(project_root, "docs", "conventions.md")
    if os.path.isfile(conventions_path):
        markers["has_legacy_conventions"] = True

    return markers


def extract_customize_values(content):
    """从旧 CLAUDE.md 内容提取项目名与描述。

    优先解析 ``**项目名称**:`` 与 ``**模块/职责**:`` 行；
    行内 [CUSTOMIZE: xxx] 取其值，否则取冒号后的原文。
    """
    name = ""
    description = ""

    if not content:
        return name, description

    def _clean(raw):
        raw = raw.strip()
        m = _CUSTOMIZE_VALUE_PATTERN.search(raw)
        if m:
            return m.group(1).strip()
        raw = _CUSTOMIZE_PATTERN.sub("", raw).strip()
        return raw

    for line in content.splitlines():
        if "**项目名称**" in line and ":" in line:
            name = _clean(line.split(":", 1)[1])
        elif "**模块/职责**" in line and ":" in line:
            description = _clean(line.split(":", 1)[1])

    return name, description


# ---------------------------------------------------------------------------
# Profile 推荐
# ---------------------------------------------------------------------------

def recommend_profiles(project_root):
    """扫描源码注解与构建配置，推荐 Profile 组合。

    返回有序列表（java-common 始终在前）。
    """
    profiles = ["java-common"]

    src_dir = os.path.join(project_root, "src")
    java_sources = []
    if os.path.isdir(src_dir):
        for root, _dirs, files in os.walk(src_dir):
            for fname in files:
                if fname.endswith(".java"):
                    java_sources.append(os.path.join(root, fname))

    blob = ""
    for path in java_sources[:200]:  # 限制扫描量
        blob += safe_read_file(path) or ""

    if re.search(r"@(Rest)?Controller\b", blob):
        profiles.append("spring-http")
    if re.search(r"@(KafkaListener|RocketMQMessageListener|RabbitListener)\b", blob):
        profiles.append("spring-mq")
    if re.search(r"@(Scheduled|XxlJob|Job)\b", blob):
        profiles.append("spring-job")

    # Java 版本检测
    pom = safe_read_file(os.path.join(project_root, "pom.xml")) or ""
    m = re.search(r"<maven\.compiler\.source>(\d+)</maven\.compiler\.source>", pom)
    if m and m.group(1) == "8":
        profiles.append("legacy-java8")

    return profiles


# ---------------------------------------------------------------------------
# 备份
# ---------------------------------------------------------------------------

def backup_v1_files(project_root, timestamp):
    """备份 v1 相关文件到 .harness/backups/<timestamp>/。

    返回备份目录路径。
    """
    backup_dir = os.path.join(project_root, ".harness", "backups", timestamp)
    os.makedirs(backup_dir, exist_ok=True)

    candidates = [
        "CLAUDE.md",
        os.path.join("docs", "conventions.md"),
    ]
    for rel in candidates:
        src = os.path.join(project_root, rel)
        if os.path.isfile(src):
            dst = os.path.join(backup_dir, rel.replace(os.sep, "__"))
            shutil.copy2(src, dst)

    return backup_dir


# ---------------------------------------------------------------------------
# Local 文件骨架
# ---------------------------------------------------------------------------

_LOCAL_FILES = {
    "CLAUDE.local.md": "# {name} 本地规则\n\n> 项目级 AI 协作规则（从 v1 迁移生成，请补充项目特定内容）。\n\n## 项目身份\n\n- **项目名称**: {name}\n- **模块/职责**: {description}\n\n## 本地约定\n\n<!-- 在此补充本项目特有的规则 -->\n",
    os.path.join(".harness", "local", "business.md"): "# 业务说明\n\n<!-- 从 v1 迁移：补充业务领域、核心流程、状态机等 -->\n",
    os.path.join(".harness", "local", "architecture.md"): "# 架构说明\n\n<!-- 从 v1 迁移：补充分层架构、包结构、技术选型 -->\n",
    os.path.join(".harness", "local", "database.md"): "# 数据库说明\n\n<!-- 补充表归属、核心表、迁移规范 -->\n",
    os.path.join(".harness", "local", "mq.md"): "# 消息说明\n\n<!-- 补充 Topic、生产/消费、幂等 -->\n",
    os.path.join("docs", "conventions.local.md"): "# 本地开发规范补充\n\n<!-- 补充项目特有的开发规范 -->\n",
}


def _local_index_yaml():
    """生成 .harness/local/index.yaml（sections 结构，对齐需求 §11.10）。"""
    return (
        "# 本地规则索引（v2 结构）\n"
        "# AI 助手按需加载以下文档，避免一次性注入过多上下文\n\n"
        "sections:\n"
        "  - id: local-business\n"
        "    path: business.md\n"
        "    loadWhen:\n"
        "      tasks:\n"
        "        - requirement-analysis\n"
        "        - feature-development\n"
        "  - id: local-architecture\n"
        "    path: architecture.md\n"
        "    loadWhen:\n"
        "      tasks:\n"
        "        - feature-development\n"
        "        - refactor\n"
        "        - code-review\n"
        "  - id: local-database\n"
        "    path: database.md\n"
        "    loadWhen:\n"
        "      paths:\n"
        "        - \"**/mapper/**\"\n"
        "        - \"**/repository/**\"\n"
        "  - id: local-mq\n"
        "    path: mq.md\n"
        "    loadWhen:\n"
        "      paths:\n"
        "        - \"**/consumer/**\"\n"
        "        - \"**/producer/**\"\n"
        "  - id: local-protected\n"
        "    path: protected-files.md\n"
        "    alwaysLoad: true\n"
    )


def create_local_scaffolding(project_root, project_name, description):
    """创建 Local 文件骨架（已存在的不覆盖）。返回新建文件列表。"""
    created = []
    variables = {"name": project_name or "my-project",
                 "description": description or ""}

    for rel, template in _LOCAL_FILES.items():
        dst = os.path.join(project_root, rel)
        if os.path.exists(dst):
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        content = template.format(**variables)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(content)
        created.append(rel)

    # local/index.yaml + protected-files.md
    index_path = os.path.join(project_root, ".harness", "local", "index.yaml")
    if not os.path.exists(index_path):
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(_local_index_yaml())
        created.append(os.path.join(".harness", "local", "index.yaml"))

    protected_path = os.path.join(project_root, ".harness", "local", "protected-files.md")
    if not os.path.exists(protected_path):
        with open(protected_path, "w", encoding="utf-8") as f:
            f.write("# 受保护文件\n\n> 此处声明的文件 AI 不得擅自修改或删除。\n\n<!-- 补充本项目受保护文件清单 -->\n")
        created.append(os.path.join(".harness", "local", "protected-files.md"))

    return created


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def migrate_v1_to_v2(project_root=None):
    """执行 v1 → v2 迁移。

    返回 int 退出码（0 成功，1 无需迁移或失败）。
    """
    root = project_root or find_project_root()

    is_v2 = load_config(root) is not None

    # 幂等：已是 v2 结构即返回（遗留旧文件不触发重复迁移）
    if is_v2:
        print("该项目已是 v2 结构，无需迁移。")
        print("提示: 运行 ./scripts/harness render 更新受管文件。")
        return 0

    markers = detect_v1_markers(root)

    # 既无 v1 痕迹也不是 v2：建议用 init
    if not markers["has_customize"] and not markers["has_legacy_conventions"]:
        print("未检测到 v1 痕迹（[CUSTOMIZE] 占位或 docs/conventions.md）。")
        print("提示: 新项目请运行 ./scripts/harness init 初始化。")
        return 1

    # ---- 开始迁移 ----
    print(f"开始迁移: v1 → v2\n")

    # 提取项目信息
    name, description = extract_customize_values(markers.get("claude_md"))
    if not name:
        name = os.path.basename(root)
    if not description:
        description = "TODO: 填写项目描述（迁移自 v1，请补充）"

    # 推荐 Profile
    profiles = recommend_profiles(root)

    # 备份
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = backup_v1_files(root, timestamp)

    print("## 已识别")
    print(f"  - 项目名称: {name}")
    print(f"  - 业务描述: {description}")
    print(f"  - 推荐 Profile: {', '.join(profiles)}")
    print(f"  - 备份目录: {os.path.relpath(backup_dir, root)}")
    print()

    # 生成 config（若已存在则保留，仅补全空字段）
    if is_v2:
        config = load_config(root)
    else:
        java_version = "8" if "legacy-java8" in profiles else "17"
        config = create_default_config(root, name, java_version, profiles)
        config["project"]["name"] = name
        config["project"]["description"] = description
        save_config(config, root)
        print("## 已生成 .harness/config.yaml")

    # 创建 Local 骨架
    created = create_local_scaffolding(root, name, description)
    if created:
        print(f"## 已创建 Local 文件 ({len(created)} 个)")
        for rel in created:
            print(f"  - {rel}")

    # 生成受管文件
    render_errors = []
    try:
        from harness_py.render import render_all
        result = render_all(root)
        generated = result.get("generated", [])
        render_errors = result.get("errors", [])
        if generated:
            print(f"\n## 已生成受管文件 ({len(generated)} 个)")
            for rel in generated:
                print(f"  - {rel}")
        if render_errors:
            print(f"\n[警告] 生成过程有 {len(render_errors)} 个错误:")
            for e in render_errors:
                print(f"  - {e}")
    except Exception as e:
        render_errors.append(str(e))
        print(f"\n[错误] 生成受管文件失败: {e}")

    # 上下文预算检查 + Doctor
    print("\n## 迁移后自检")
    try:
        from harness_py.doctor import run_doctor
        _exit_code, doctor_result = run_doctor(root, verbose=False)
        summary = doctor_result.get("summary", {})
        print(f"  Doctor: {summary.get('passed', 0)} 通过 / "
              f"{summary.get('warnings', 0)} 警告 / "
              f"{summary.get('failed', 0)} 失败")
    except Exception as e:
        print(f"  [警告] Doctor 执行失败: {e}")

    # 迁移报告
    report_path = os.path.join(root, ".harness", "MIGRATION_REPORT.md")
    _write_report(report_path, {
        "name": name,
        "description": description,
        "profiles": profiles,
        "backup_dir": os.path.relpath(backup_dir, root),
        "created_local": created,
        "render_errors": render_errors,
    })
    print(f"\n## 迁移报告: {os.path.relpath(report_path, root)}")
    print("\n迁移完成。请人工确认推荐 Profile 与 Local 文件内容。")

    return 0 if not render_errors else 1


def _write_report(path, info):
    """生成迁移报告（需求 §18.4）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        "# Harness Migration Report",
        "",
        f"迁移时间: {datetime.datetime.now().isoformat()}",
        f"目标版本: v2",
        "",
        "## 项目信息",
        f"- 项目名称: {info['name']}",
        f"- 业务描述: {info['description']}",
        "",
        "## 推荐 Profile",
    ]
    lines += [f"- {p}" for p in info["profiles"]]
    lines += [
        "",
        "## 备份",
        f"- 旧文件已备份至: {info['backup_dir']}",
        "",
        "## 迁移的 Local 文件",
    ]
    lines += [f"- {rel}" for rel in info["created_local"]] or ["- （均已存在，未创建新文件）"]
    lines += ["", "## 人工确认事项", "- 确认推荐的 Profile 是否符合项目实际"]
    lines += ["- 检查 .harness/local/ 下文件并补充项目特定内容"]
    lines += ["- 旧的 [CUSTOMIZE] 占位机制已废弃，配置统一在 .harness/config.yaml"]
    if info["render_errors"]:
        lines += ["", "## 生成错误", ""] + [f"- {e}" for e in info["render_errors"]]
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
