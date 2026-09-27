#!/usr/bin/env bash
# ============================================================
# AI 教学助手 从备份恢复（R1-009）
#
# 用法（在部署目录，即 docker-compose.yml 所在目录执行）：
#   bash scripts/restore.sh backups/20260926_023000          # 交互确认
#   bash scripts/restore.sh backups/20260926_023000 --yes    # 不询问（演练 / 脚本用）
#
# 过程：
#   1. 停止后端容器（没有 docker 时跳过，适合在新目录演练）
#   2. 当前的数据库和 uploads 改名保留为 *.before-restore-<时间>（不删除，确认无误后再手动清理）
#   3. 用备份覆盖 data/teaching_assistant.db 与 uploads/
#   4. 启动后端容器
# ============================================================
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${1:-}"
ASSUME_YES="${2:-}"
STAMP="$(date +%Y%m%d_%H%M%S)"
DATA_DIR="$APP_DIR/data"
COMPOSE_FILE="$APP_DIR/docker-compose.yml"

log() { echo "[$(date '+%F %T')] $*"; }

if [ -z "$SRC" ]; then
  echo "用法：bash scripts/restore.sh <备份目录> [--yes]"
  echo "可用的备份："
  ls -1d "$APP_DIR"/backups/20* 2>/dev/null || echo "  （没有找到备份）"
  exit 1
fi
case "$SRC" in
  /*) ;;
  *) SRC="$APP_DIR/$SRC" ;;
esac

if [ ! -f "$SRC/teaching_assistant.db" ] || [ ! -f "$SRC/uploads.tar.gz" ]; then
  log "错误：$SRC 不是完整的备份（需要 teaching_assistant.db 和 uploads.tar.gz）"
  exit 1
fi

if [ "$ASSUME_YES" != "--yes" ]; then
  read -r -p "将用 $SRC 覆盖当前数据（当前数据会改名保留），确定吗？输入 yes 继续：" answer
  if [ "$answer" != "yes" ]; then
    echo "已取消"
    exit 1
  fi
fi

has_docker() {
  command -v docker >/dev/null 2>&1 && [ -f "$COMPOSE_FILE" ] && \
    docker compose -f "$COMPOSE_FILE" ps --services 2>/dev/null | grep -q '^backend$'
}

USE_DOCKER=0
if has_docker; then
  USE_DOCKER=1
  log "停止后端容器"
  docker compose -f "$COMPOSE_FILE" stop backend
else
  log "未检测到运行中的 docker compose 后端，跳过停止（演练模式）"
fi

mkdir -p "$DATA_DIR"
for suffix in "" "-wal" "-shm"; do
  if [ -f "$DATA_DIR/teaching_assistant.db$suffix" ]; then
    mv "$DATA_DIR/teaching_assistant.db$suffix" "$DATA_DIR/teaching_assistant.db$suffix.before-restore-$STAMP"
  fi
done
cp "$SRC/teaching_assistant.db" "$DATA_DIR/teaching_assistant.db"
log "数据库已恢复"

if [ -d "$APP_DIR/uploads" ]; then
  mv "$APP_DIR/uploads" "$APP_DIR/uploads.before-restore-$STAMP"
fi
tar -xzf "$SRC/uploads.tar.gz" -C "$APP_DIR"
mkdir -p "$APP_DIR/uploads"
log "上传文件已恢复"

if [ "$USE_DOCKER" = "1" ]; then
  log "启动后端容器"
  docker compose -f "$COMPOSE_FILE" start backend
fi

log "恢复完成。旧数据保留在 data/teaching_assistant.db.before-restore-$STAMP 与 uploads.before-restore-$STAMP，核对无误后可手动删除。"
