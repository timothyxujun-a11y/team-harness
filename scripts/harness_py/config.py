"""配置加载与校验模块."""

import os

from harness_py.utils import safe_read_yaml, find_project_root


# --------------------------------------------------------------------------- #
# 默认值
# --------------------------------------------------------------------------- #

_API_VERSION = "harness.company.io/v1"
_KIND = "HarnessConfig"

_DEFAULT_CONTEXT = {
    "alwaysLoaded": {"maxFiles": 3, "maxTokens": 2000},
    "taskRules": {"maxFiles": 8, "maxRules": 12, "maxTokens": 6000},
    "codeReview": {"maxFiles": 12, "maxRules": 15, "maxTokens": 8000},
}

_DEFAULT_UPDATE = {
    "channel": "stable",
    "allowMinorUpgrade": True,
    "allowPatchUpgrade": True,
}


# --------------------------------------------------------------------------- #
# 公共函数
# --------------------------------------------------------------------------- #

def load_config(project_root):
    """从 .harness/config.yaml 加载配置，返回 dict。

    文件不存在时返回 None；文件存在但无法解析时抛出 RuntimeError。
    """
    config_path = os.path.join(project_root, ".harness", "config.yaml")
    if not os.path.exists(config_path):
        return None

    config = safe_read_yaml(config_path)
    if config is None:
        raise RuntimeError(
            f"无法解析配置文件 {config_path}，请确保已安装 pyyaml (pip install pyyaml)"
        )
    return config


def create_default_config(project_root, project_name, java_version, profiles):
    """创建默认配置 dict。

    自动检测 Maven Wrapper 来设置构建命令。
    """
    build_commands = get_build_commands(project_root)

    if isinstance(profiles, str):
        profiles = [p.strip() for p in profiles.split(",") if p.strip()]

    return {
        "apiVersion": _API_VERSION,
        "kind": _KIND,
        "project": {
            "name": project_name,
            "description": "TODO: 填写项目描述",
        },
        "runtime": {
            "language": "java",
            "javaVersion": str(java_version),
            "buildTool": "maven",
            "defaultBranch": "main",
        },
        "profiles": profiles,
        "build": build_commands,
        "quality": {
            "diffCoverage": {
                "enabled": True,
                "threshold": 80,
                "baseBranch": "origin/main",
            },
        },
        "context": _DEFAULT_CONTEXT,
        "localRules": {
            "main": "CLAUDE.local.md",
            "index": ".harness/local/index.yaml",
        },
        "update": dict(_DEFAULT_UPDATE),
    }


def validate_config(config):
    """校验必填字段，返回 (valid, errors)。"""
    if config is None:
        return (False, ["配置为空"])

    errors = []

    # 必填顶层字段
    required_top = ["apiVersion", "kind", "project", "runtime", "profiles"]
    for field in required_top:
        if field not in config:
            errors.append(f"缺少必填字段: {field}")

    if errors:
        return (False, errors)

    # apiVersion
    if config.get("apiVersion") != _API_VERSION:
        errors.append(
            f"apiVersion 必须为 '{_API_VERSION}'，当前: {config.get('apiVersion')}"
        )

    # kind
    if config.get("kind") != _KIND:
        errors.append(f"kind 必须为 '{_KIND}'，当前: {config.get('kind')}")

    # project
    project = config.get("project", {})
    if not project.get("name"):
        errors.append("project.name 不能为空")
    if not project.get("description"):
        errors.append("project.description 不能为空")

    # runtime
    runtime = config.get("runtime", {})
    if not runtime.get("language"):
        errors.append("runtime.language 不能为空")
    if not runtime.get("buildTool"):
        errors.append("runtime.buildTool 不能为空")

    # profiles
    profiles = config.get("profiles", [])
    if not profiles or not isinstance(profiles, list):
        errors.append("profiles 必须为非空列表")

    return (len(errors) == 0, errors)


def save_config(config, project_root):
    """保存配置到 .harness/config.yaml，返回文件路径。"""
    try:
        import yaml
    except ImportError:
        raise RuntimeError(
            "保存配置需要 pyyaml，请运行 pip install pyyaml"
        )

    harness_dir = os.path.join(project_root, ".harness")
    os.makedirs(harness_dir, exist_ok=True)
    config_path = os.path.join(harness_dir, "config.yaml")

    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(
            config,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    return config_path


def get_build_commands(project_root):
    """自动检测 Maven Wrapper，返回 compile/test/package 命令 dict。"""
    mvnw = os.path.join(project_root, "mvnw")
    maven_cmd = "./mvnw" if os.path.exists(mvnw) else "mvn"

    return {
        "compileCommand": f"{maven_cmd} clean compile -DskipTests",
        "testCommand": f"{maven_cmd} test",
        "packageCommand": f"{maven_cmd} clean package -DskipTests",
    }
