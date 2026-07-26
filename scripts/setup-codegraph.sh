#!/usr/bin/env bash
# setup-codegraph.sh - 一键接入 codegraph 代码图谱
#
# 职责：
#   1. 检测本机是否已安装 codegraph CLI
#   2. 未安装 → 打印安装命令并退出（不自动安装，避免引入未确认的全局依赖）
#   3. 已安装 → 在本项目执行 codegraph init 建立知识图谱索引
#
# 用法：./scripts/setup-codegraph.sh
#
# 关于 .mcp.json：本仓库已预置团队共享的 MCP server 配置，
#   装好 CLI 并 init 后，重启 Claude Code 即可自动加载（首次会提示信任）。

set -euo pipefail

# ====== 颜色输出 ======
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[ OK ]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERR]${NC} $1"; }

# ====== 确定项目根目录（向上查找 .git） ======
PROJECT_ROOT="$(pwd)"
while [ "$PROJECT_ROOT" != "/" ] && [ ! -d "$PROJECT_ROOT/.git" ]; do
  PROJECT_ROOT="$(dirname "$PROJECT_ROOT")"
done
if [ ! -d "$PROJECT_ROOT/.git" ]; then
  log_warning "当前不在 Git 仓库中，将以当前目录作为项目根目录"
  PROJECT_ROOT="$(pwd)"
fi
cd "$PROJECT_ROOT"

# ====== 检测 codegraph CLI ======
if ! command -v codegraph &>/dev/null; then
  log_error "未检测到 codegraph CLI，请先安装（任选其一）："
  echo ""
  echo -e "  ${GREEN}# 方式一：自包含安装（无需 Node，macOS / Linux）${NC}"
  echo    "  curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh"
  echo ""
  echo -e "  ${GREEN}# 方式二：npm 全局安装${NC}"
  echo    "  npm i -g @colbymchenry/codegraph"
  echo ""
  echo -e "  ${BLUE}# Windows (PowerShell)${NC}"
  echo    "  irm https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.ps1 | iex"
  echo ""
  echo -e "  ${YELLOW}安装后请打开新终端使 codegraph 进入 PATH，再重新运行本脚本。${NC}"
  exit 1
fi

CG_VERSION="$(codegraph version 2>/dev/null || echo unknown)"
log_success "检测到 codegraph CLI（版本: ${CG_VERSION}）"

# ====== 确保 .codegraph/ 被 .gitignore 忽略（索引产物 per-machine，不入库） ======
if [ -f ".gitignore" ] && ! grep -q '\.codegraph' .gitignore; then
  printf '\n# codegraph 索引产物（per-machine，不入库）\n.codegraph/\n' >> .gitignore
  log_info "已将 .codegraph/ 加入 .gitignore"
fi

# ====== 执行 codegraph init ======
log_info "在 $PROJECT_ROOT 执行 codegraph init（首次建索引可能需要一点时间）..."
if codegraph init; then
  echo ""
  log_success "codegraph 索引已建立：$PROJECT_ROOT/.codegraph/"
  echo ""
  echo "📝 接下来："
  echo "  1. 重启 Claude Code（让 .mcp.json 生效，首次会提示信任 MCP server）"
  echo "  2. /mcp 查看 codegraph 是否 connected"
  echo "  3. 调用 codegraph_explore 做结构化探索（已预置权限，无需确认）"
  echo ""
  echo -e "  ${BLUE}索引会随文件改动自动同步，无需手动重跑。${NC}"
  echo ""
  echo "🔧 常用命令："
  echo "  codegraph status             # 查看索引状态"
  echo "  codegraph explore '<问题>'    # CLI 等价于 codegraph_explore 工具"
  echo "  codegraph uninit             # 移除本项目索引（.codegraph/）"
else
  log_error "codegraph init 失败，请根据上方提示排查"
  exit 1
fi
