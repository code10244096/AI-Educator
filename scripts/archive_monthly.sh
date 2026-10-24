#!/usr/bin/env bash
# ============================================================
# AI 教学助手 月度归档（R1-010）
#   - 把 data/user_records/（按账号留存的教案、批改、变式题）按月打包
#   - 数据库整库快照一并纳入（sqlite3 .backup 或 python3 VACUUM INTO）
#   - 存放 backups/monthly/YYYY-MM.tar.gz，默认保留最近 13 个月
#
# 用法（在部署目录执行）：
#   bash scripts/archive_monthly.sh           # 归档上个月（默认）
#   bash scripts/archive_monthly.sh 2026-09   # 归档指定月份
# crontab 示例（每月 1 日 03:10）：
#   10 3 1 * * cd /opt/ai-teaching && bash scripts/archive_monthly.sh >> logs/archive.log 2>&1
#
# 可选环境变量：
#   ARCHIVE_DIR 归档存放目录，默认 <部署目录>/backups/monthly
#   KEEP_MONTHS 保留月数，默认 13
# ============================================================
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

# 默认归档上个月；传参可指定 YYYY-MM
if [[ $# -ge 1 && "$1" =~ ^[0-9]{4}-[0-9]{2}$ ]]; then
  MONTH="$1"
else
  MONTH="$(date -d "last month" +%Y-%m 2>/dev/null || date -v-1m +%Y-%m)"
fi

ARCHIVE_DIR="${ARCHIVE_DIR:-$APP_DIR/backups/monthly}"
KEEP_MONTHS="${KEEP_MONTHS:-13}"
mkdir -p "$ARCHIVE_DIR"
OUT="$ARCHIVE_DIR/${MONTH}.tar.gz"
TMP="$ARCHIVE_DIR/.${MONTH}.tmp.tar.gz"
DB_SNAP="/tmp/archive_${MONTH}.db"

echo "[$(date '+%F %T')] 开始月度归档 $MONTH"

# --- 步骤 1：数据库在线一致性快照 ---
DB_SRC="$APP_DIR/data/teaching_assistant.db"
SNAP_OK=""
rm -f "$DB_SNAP"   # 清掉上次残留的同名文件（VACUUM INTO 不允许覆盖已存在文件）
if [[ -f "$DB_SRC" ]]; then
  if command -v sqlite3 >/dev/null 2>&1; then
    sqlite3 "$DB_SRC" ".backup '$DB_SNAP'" && SNAP_OK=1 || SNAP_OK=""
  fi
  if [[ -z "$SNAP_OK" ]]; then
    python3 - "$DB_SRC" "$DB_SNAP" <<'PY' && SNAP_OK=1 || echo "警告: 数据库快照失败"
import sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
con = sqlite3.connect(src)
con.execute(f"VACUUM INTO '{dst}'")
con.close()
PY
  fi
else
  echo "警告: 未找到 $DB_SRC"
fi

# --- 步骤 2：打包（先打未压缩 tar，追加快照后统一 gzip；GNU tar 不支持向 .gz 追加） ---
TARTMP="${TMP%.gz}"
tar -cf "$TARTMP" -C "$APP_DIR" data/user_records uploads

# --- 步骤 3：把数据库快照追加进 tar（先复制到统一文件名再追加，避免带月份的路径） ---
if [[ -n "$SNAP_OK" && -f "$DB_SNAP" ]]; then
  cp "$DB_SNAP" /tmp/archive_monthly_snapshot.db
  tar -rf "$TARTMP" -C /tmp archive_monthly_snapshot.db
  echo "已纳入数据库快照"
fi

gzip -f "$TARTMP"
mv "$TARTMP.gz" "$OUT"
rm -f "$DB_SNAP" /tmp/archive_monthly_snapshot.db

echo "[$(date '+%F %T')] 归档完成: $OUT ($(du -h "$OUT" | cut -f1))"

# --- 步骤 4：清理超期月份 ---
ls -1 "$ARCHIVE_DIR"/*.tar.gz 2>/dev/null | sort | head -n -"$KEEP_MONTHS" | while read -r old; do
  echo "清理过期归档: $old"
  rm -f "$old"
done
