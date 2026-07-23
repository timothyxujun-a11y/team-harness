#!/bin/bash
# install-git-hooks.sh - 一键安装 git pre-commit hook
# 使用方法：在项目根目录执行 ./scripts/install-git-hooks.sh

set -e

# ====== 颜色输出 ======
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# ====== 检查是否在 Git 仓库中 ======
if [ ! -d ".git" ]; then
    log_error "当前目录不是 Git 仓库（未找到 .git 目录）"
    exit 1
fi

# ====== 检查 hook 源文件是否存在 ======
HOOK_SOURCE="git-hooks/pre-commit"
if [ ! -f "$HOOK_SOURCE" ]; then
    log_error "未找到 $HOOK_SOURCE，请确保在项目根目录执行此脚本"
    exit 1
fi

# ====== 创建 .git/hooks 目录（如果不存在） ======
mkdir -p .git/hooks

# ====== 安装 pre-commit hook ======
HOOK_TARGET=".git/hooks/pre-commit"

if [ -f "$HOOK_TARGET" ]; then
    log_warning "已存在 pre-commit hook，将覆盖"
    rm -f "$HOOK_TARGET"
fi

cp "$HOOK_SOURCE" "$HOOK_TARGET"
chmod +x "$HOOK_TARGET"

log_success "pre-commit hook 已安装到 $HOOK_TARGET"

# ====== 验证安装 ======
if [ -x "$HOOK_TARGET" ]; then
    log_success "hook 可执行权限验证通过"
else
    log_error "hook 不可执行，请手动执行: chmod +x $HOOK_TARGET"
    exit 1
fi

# ====== 完成 ======
echo ""
log_success "Git hooks 安装完成！"
echo ""
echo "📝 说明："
echo "  - 提交代码时会自动执行 Checkstyle 静态检查"
echo "  - 检查不通过会阻止提交"
echo "  - 如需跳过检查（不推荐）：git commit --no-verify"
echo ""
echo "🔧 如需卸载：rm -f .git/hooks/pre-commit"
