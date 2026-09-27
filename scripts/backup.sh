#!/usr/bin/env bash
# ============================================================
# AI 教学助手 每日备份（R1-009）
#   - 数据库：SQLite 在线备份（.backup，服务运行中也能得到一致的副本）
#   - 学生作业照片：打包 uploads/
#   - 按时间命名，默认保留最近 14 天
#
# 用法（在部署目录，即 docker-compose.yml 所在目录执行）：
#   bash scripts/backup.sh
# crontab 示例（每天 02:30）：
#   30 2 * * * cd /opt/ai-teaching && bash scripts/backup.sh >> logs/backup.log 2>&1
#
# 可选环境变量：
#   BACKUP_DIR  备份存放目录，默认 <部署目录>/backups（建议再定期同步到另一台机器或对象存储）
#   KEEP_DAYS   保留天数，默认 14
# ============================================================
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
DATA_DIR="$APP_DIR/data"
DB_FILE="$DATA_DIR/teaching_assistant.db"
UPLOADS_DIR="$APP_DIR/uploads"
STAMP="$(date +%Y%m%d_%H%M%S)"
TARGET="$BACKUP_DIR/$STAMP"

log() { echo "[$(date '+%F %T')] $*"; }

# 找一个真正可用、带 sqlite3 模块的 Python（Windows 上的 python3 可能只是应用商店占位程序）
PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import sqlite3" >/dev/null 2>&1; then
    PY="$candidate"
    break
  fi
done

if [ ! -f "$DB_FILE" ]; then
  log "错误：找不到数据库 $DB_FILE（请在部署目录执行，或确认服务已启动过）"
  exit 1
fi

mkdir -p "$TARGET"
log "开始备份到 $TARGET"

# 1) 数据库在线备份
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "$DB_FILE" ".backup '$TARGET/teaching_assistant.db'"
elif [ -n "$PY" ]; then
  # 与 sqlite3 .backup 相同的在线备份 API
  "$PY" - "$DB_FILE" "$TARGET/teaching_assistant.db" <<'PY'
import sqlite3, sys
src = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
dst = sqlite3.connect(sys.argv[2])
with dst:
    src.backup(dst)
dst.close()
src.close()
PY
elif command -v docker >/dev/null 2>&1; then
  # 宿主机没有 sqlite3/python3 时，借用后端容器里的 Python 做 .backup
  docker compose -f "$APP_DIR/docker-compose.yml" exec -T backend python -c \
    "import sqlite3; s=sqlite3.connect('/app/data/teaching_assistant.db'); d=sqlite3.connect('/app/data/.backup_tmp.db'); s.backup(d); d.close(); s.close()"
  mv "$DATA_DIR/.backup_tmp.db" "$TARGET/teaching_assistant.db"
else
  log "错误：需要 sqlite3、python3 或 docker 之一来做数据库在线备份"
  exit 1
fi

# 校验备份库完整性
if command -v sqlite3 >/dev/null 2>&1; then
  CHECK="$(sqlite3 "$TARGET/teaching_assistant.db" 'PRAGMA integrity_check;')"
elif [ -n "$PY" ]; then
  CHECK="$("$PY" -c "import sqlite3,sys; print(sqlite3.connect(sys.argv[1]).execute('PRAGMA integrity_check').fetchone()[0])" "$TARGET/teaching_assistant.db")"
else
  CHECK="ok"
fi
if [ "$CHECK" != "ok" ]; then
  log "错误：备份库完整性检查失败：$CHECK"
  exit 1
fi

# 2) 学生作业照片等上传文件
if [ -d "$UPLOADS_DIR" ]; then
  tar -czf "$TARGET/uploads.tar.gz" -C "$APP_DIR" uploads
else
  log "提示：没有 uploads 目录，跳过（新部署还没有上传过作业）"
  tar -czf "$TARGET/uploads.tar.gz" --files-from /dev/null
fi

# 3) 备份说明
{
  echo "backup_time=$STAMP"
  echo "db_size=$(wc -c < "$TARGET/teaching_assistant.db")"
  echo "uploads_size=$(wc -c < "$TARGET/uploads.tar.gz")"
} > "$TARGET/BACKUP_INFO"

log "备份完成：数据库 $(du -h "$TARGET/teaching_assistant.db" | cut -f1)，上传文件 $(du -h "$TARGET/uploads.tar.gz" | cut -f1)"

# 4) 只保留最近 KEEP_DAYS（默认 14）天的备份
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -name '20*' -mtime +"$((KEEP_DAYS - 1))" -print0 |
  while IFS= read -r -d '' old; do
    log "清理过期备份：$old"
    rm -rf -- "$old"
  done

log "完成"
