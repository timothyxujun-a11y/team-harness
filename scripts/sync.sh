#!/usr/bin/env bash
# sync.sh - 从 team-harness 仓库同步 AI 工程化配置到当前项目
#
# 用法：
#   ./scripts/sync.sh            # 同步（交互式确认覆盖已修改的文件）
#   ./scripts/sync.sh --check    # 仅检查有哪些更新，不实际修改
#   ./scripts/sync.sh --force    # 强制覆盖所有文件（不推荐，会丢失 [CUSTOMIZE] 填写值）
#   ./scripts/sync.sh --hooks    # 同步后自动运行 install-git-hooks.sh
#   ./scripts/sync.sh --with-codegraph  # 同时同步 codegraph 配置（.mcp.json / setup-codegraph.sh，默认跳过）
#   ./scripts/sync.sh --help     # 显示帮助
#
# 首次使用（目标项目还没有 sync.sh）：
#   curl -fsSL https://raw.githubusercontent.com/timothyxujun-a11y/team-harness/main/scripts/sync.sh | bash
#
# 首次使用后，sync.sh 会复制到 scripts/sync.sh，之后直接运行：
#   ./scripts/sync.sh

set -euo pipefail

# ====== 配置 ======
REPO_URL="https://github.com/timothyxujun-a11y/team-harness.git"
UPSTREAM_DIR=".harness-upstream"
BRANCH="main"

# 同步清单：这些文件/目录会从仓库同步到当前项目
SYNC_ITEMS=(
  "CLAUDE.md"
  "docs/conventions.md"
  ".mcp.json"
  ".claude/settings.json"
  ".claude/agents"
  ".claude/commands"
  ".claude/skills"
  "git-hooks/pre-commit"
  "scripts/install-git-hooks.sh"
  "scripts/setup-codegraph.sh"
  "scripts/sync.sh"
)

# 不同步的文件（项目专属，同步时跳过）：
#   README.md                     — 项目说明
#   .gitignore                    — 项目 git 配置
#   .claude/settings.local.json   — 个人 Claude Code 配置
#   docs/superpowers/             — 设计文档

# ====== 颜色输出 ======
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[ OK ]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERR]${NC} $1"; }
log_diff()    { echo -e "${CYAN}[DIFF]${NC} $1"; }

# ====== 参数解析 ======
MODE="sync"       # sync | check | force
INSTALL_HOOKS=false
WITH_CODEGRAPH=false

for arg in "$@"; do
  case "$arg" in
    --check)  MODE="check" ;;
    --force)  MODE="force" ;;
    --hooks)  INSTALL_HOOKS=true ;;
    --with-codegraph) WITH_CODEGRAPH=true ;;
    --help|-h)
      sed -n '2,20p' "$0"
      exit 0
      ;;
    *)
      log_error "未知参数: $arg（使用 --help 查看帮助）"
      exit 1
      ;;
  esac
done

# ====== 前置检查 ======
if ! command -v git &>/dev/null; then
  log_error "未找到 git，请先安装 git"
  exit 1
fi

# 确定项目根目录（向上查找 .git 目录）
PROJECT_ROOT="$(pwd)"
while [ "$PROJECT_ROOT" != "/" ] && [ ! -d "$PROJECT_ROOT/.git" ]; do
  PROJECT_ROOT="$(dirname "$PROJECT_ROOT")"
done
if [ ! -d "$PROJECT_ROOT/.git" ]; then
  log_warning "当前不在 Git 仓库中，将以当前目录作为项目根目录"
  PROJECT_ROOT="$(pwd)"
fi
cd "$PROJECT_ROOT"

log_info "项目根目录: $PROJECT_ROOT"
log_info "同步模式: $MODE"

# ====== 拉取/更新上游仓库 ======
if [ -d "$UPSTREAM_DIR/.git" ]; then
  log_info "更新上游仓库 ($UPSTREAM_DIR)..."
  git -C "$UPSTREAM_DIR" fetch origin "$BRANCH" --quiet
  git -C "$UPSTREAM_DIR" checkout "$BRANCH" --quiet 2>/dev/null || true
  git -C "$UPSTREAM_DIR" reset --hard "origin/$BRANCH" --quiet
else
  log_info "克隆上游仓库到 $UPSTREAM_DIR ..."
  rm -rf "$UPSTREAM_DIR"
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$UPSTREAM_DIR" --quiet
fi

UPSTREAM_COMMIT=$(git -C "$UPSTREAM_DIR" rev-parse --short HEAD)
UPSTREAM_DATE=$(git -C "$UPSTREAM_DIR" log -1 --format='%ci' | cut -d' ' -f1)
log_success "上游仓库已就绪 (commit: $UPSTREAM_COMMIT, date: $UPSTREAM_DATE)"

# ====== 同步文件 ======
NEW_COUNT=0
UPDATED_COUNT=0
SKIPPED_COUNT=0
UNCHANGED_COUNT=0

sync_file() {
  local src="$UPSTREAM_DIR/$1"
  local dst="$1"

  if [ ! -e "$src" ]; then
    log_warning "上游不存在: $1，跳过"
    ((SKIPPED_COUNT++)) || true
    return
  fi

  # 确保目标目录存在
  mkdir -p "$(dirname "$dst")"

  if [ ! -e "$dst" ]; then
    # 新文件
    if [ "$MODE" = "check" ]; then
      log_diff "  [新增] $1"
      ((NEW_COUNT++)) || true
      return
    fi
    cp -r "$src" "$dst"
    # 脚本类文件保持可执行权限，其余文件设为 644
    # 注意：case 的模式匹配才会做通配展开（*.sh），不能用 [ "x" = "*.sh" ] 字面比较
    if [ -f "$dst" ]; then
      case "$(basename "$dst")" in
        pre-commit|*.sh) chmod +x "$dst" 2>/dev/null || true ;;
        *)               chmod 644 "$dst" 2>/dev/null || true ;;
      esac
    fi
    log_success "  [新增] $1"
    ((NEW_COUNT++)) || true
    return
  fi

  # 比较内容
  if diff -rq "$src" "$dst" &>/dev/null; then
    ((UNCHANGED_COUNT++)) || true
    return
  fi

  # 有差异
  if [ "$MODE" = "check" ]; then
    log_diff "  [更新] $1"
    diff --color=auto "$dst" "$src" | head -30 || true
    echo "  ..."
    ((UPDATED_COUNT++)) || true
    return
  fi

  if [ "$MODE" = "force" ]; then
    cp -r "$src" "$dst"
    log_success "  [覆盖] $1"
    ((UPDATED_COUNT++)) || true
    return
  fi

  # 交互模式：检查本地文件是否已填写 [CUSTOMIZE]
  if grep -q '\[CUSTOMIZE' "$dst" 2>/dev/null; then
    # 本地文件还有未填写的占位符，安全覆盖
    cp -r "$src" "$dst"
    log_success "  [更新] $1"
    ((UPDATED_COUNT++)) || true
  else
    # 本地文件已填写 [CUSTOMIZE]，需要确认
    log_warning "  [冲突] $1 — 本地已修改（可能已填写 [CUSTOMIZE]）"
    echo -ne "    覆盖会丢失本地修改，是否覆盖？[y/N] "
    read -r answer || answer=""
    if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
      cp -r "$src" "$dst"
      log_success "  [覆盖] $1"
      ((UPDATED_COUNT++)) || true
    else
      log_info "  [跳过] $1"
      ((SKIPPED_COUNT++)) || true
    fi
  fi
}

sync_dir() {
  local src="$UPSTREAM_DIR/$1"
  local dst="$1"

  if [ ! -d "$src" ]; then
    log_warning "上游目录不存在: $1，跳过"
    ((SKIPPED_COUNT++)) || true
    return
  fi

  # 同步目录中的每个文件
  while IFS= read -r -d '' file; do
    local rel="${file#$src/}"
    sync_file "$1/$rel"
  done < <(find "$src" -type f -print0)
}

echo ""
log_info "========== 开始同步 =========="
echo ""

for item in "${SYNC_ITEMS[@]}"; do
  # codegraph 为可选增强：默认跳过，需 --with-codegraph 显式启用
  if [ "$WITH_CODEGRAPH" != "true" ]; then
    case "$item" in
      .mcp.json|scripts/setup-codegraph.sh)
        log_info "  [跳过] ${item}（codegraph 可选，加 --with-codegraph 启用）"
        ((SKIPPED_COUNT++)) || true
        continue
        ;;
    esac
  fi
  if [[ "$item" == */ ]]; then
    # 目录（去掉末尾斜杠）
    sync_dir "${item%/}"
  elif [ -d "$UPSTREAM_DIR/$item" ]; then
    sync_dir "$item"
  else
    sync_file "$item"
  fi
done

echo ""
log_info "========== 同步结果 =========="
echo -e "  ${GREEN}新增: $NEW_COUNT${NC}  |  ${YELLOW}更新: $UPDATED_COUNT${NC}  |  ${BLUE}未变: $UNCHANGED_COUNT${NC}  |  ${CYAN}跳过: $SKIPPED_COUNT${NC}"
echo ""

# ====== [CUSTOMIZE] 提醒 ======
if [ "$MODE" != "check" ]; then
  CUSTOMIZE_FILES=()
  for item in "${SYNC_ITEMS[@]}"; do
    target="$item"
    [ -f "$target" ] && grep -q '\[CUSTOMIZE' "$target" 2>/dev/null && CUSTOMIZE_FILES+=("$target")
  done

  if [ ${#CUSTOMIZE_FILES[@]} -gt 0 ]; then
    echo ""
    log_warning "以下文件包含 [CUSTOMIZE] 占位符，请填写后使用："
    for f in "${CUSTOMIZE_FILES[@]}"; do
      echo -e "  ${YELLOW}→ $f${NC}"
    done
    echo ""
    echo "  搜索命令: grep -rn '\[CUSTOMIZE' ."
  fi
fi

# ====== 安装 git hooks ======
if [ "$INSTALL_HOOKS" = true ] && [ "$MODE" != "check" ]; then
  echo ""
  if [ -f "scripts/install-git-hooks.sh" ]; then
    log_info "运行 install-git-hooks.sh ..."
    bash scripts/install-git-hooks.sh
  else
    log_warning "未找到 scripts/install-git-hooks.sh，跳过 hook 安装"
  fi
fi

# ====== 清理 ======
if [ "$MODE" = "check" ]; then
  rm -rf "$UPSTREAM_DIR"
  log_info "已清理临时目录（--check 模式）"
fi

echo ""
if [ "$MODE" = "check" ] && [ $((NEW_COUNT + UPDATED_COUNT)) -gt 0 ]; then
  log_warning "检测到 $((NEW_COUNT + UPDATED_COUNT)) 个文件可更新，运行 ./scripts/sync.sh 应用更新"
elif [ "$MODE" = "check" ]; then
  log_success "已是最新，无需更新"
elif [ $((NEW_COUNT + UPDATED_COUNT)) -gt 0 ]; then
  log_success "同步完成！记得提交更改: git add . && git commit -m 'chore: sync team-harness'"
else
  log_success "同步完成，无变更"
fi
