"""Shared utilities for harness_py."""

import os
import re
import hashlib
import pathlib

HARNESS_REPO = "timothyxujun-a11y/team-harness"
HARNESS_VERSION = "2.0.0"


def find_project_root(start=None):
    """Find the project root by looking for .git directory."""
    path = pathlib.Path(start or os.getcwd()).resolve()
    while path != path.parent:
        if (path / ".git").exists():
            return str(path)
        path = path.parent
    return str(pathlib.Path(os.getcwd()).resolve())


def get_harness_dir(project_root=None):
    """Get the harness scripts directory."""
    root = project_root or find_project_root()
    return os.path.join(root, "scripts", "harness_py")


def get_core_dir(project_root=None):
    """Get the core rules directory."""
    root = project_root or find_project_root()
    return os.path.join(root, "core")


def get_profiles_dir(project_root=None):
    """Get the profiles directory."""
    root = project_root or find_project_root()
    return os.path.join(root, "profiles")


def get_templates_dir(project_root=None):
    """Get the templates directory."""
    root = project_root or find_project_root()
    return os.path.join(root, "templates")


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
