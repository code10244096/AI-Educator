#!/usr/bin/env bash
# 从 GitHub 部署到本机，一条命令更新正在运行的服务。
#
#   bash /opt/ai-teaching/scripts/deploy.sh
#
# 只覆盖程序文件。下面这些留在服务器上，不会被仓库里的版本替换：
#   .env、data/、uploads/、logs/、backups/、nginx/ssl/、nginx/https.conf
#
# 可选环境变量：
#   DEPLOY_REPO    默认 https://github.com/code10244096/AI-Educator.git
#   DEPLOY_BRANCH  默认 feat/ai-teaching-launch
#   APP_DIR        默认 /opt/ai-teaching
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/ai-teaching}"
REPO="${DEPLOY_REPO:-https://github.com/code10244096/AI-Educator.git}"
BRANCH="${DEPLOY_BRANCH:-feat/ai-teaching-launch}"

log() { echo "[deploy] $*"; }

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

log "克隆 $REPO 分支 $BRANCH"
git clone --depth 1 --branch "$BRANCH" "$REPO" "$tmp/src"
rev="$(git -C "$tmp/src" rev-parse --short HEAD)"
log "目标提交 $rev"

if [[ ! -f "$tmp/src/scripts/deploy.sh" || ! -f "$tmp/src/docker-compose.https.yml" ]]; then
  log "GitHub 上的 $BRANCH 还不是可直接部署的版本，已中止，线上服务没有改动。"
  log "请先把包含 scripts/deploy.sh 的代码推送到该分支，再重新执行。"
  exit 1
fi

mkdir -p "$APP_DIR"
log "同步代码到 $APP_DIR（保留配置、数据和证书）"
rsync -a --delete \
  --exclude '.env' \
  --exclude 'data/' \
  --exclude 'uploads/' \
  --exclude 'logs/' \
  --exclude 'backups/' \
  --exclude 'nginx/ssl/' \
  --exclude 'nginx/https.conf' \
  "$tmp/src/" "$APP_DIR/"

cd "$APP_DIR"
if [[ ! -f .env ]]; then
  log "缺少 $APP_DIR/.env。请按 .env.example 填写 JWT_SECRET 和 LLM_API_KEY 后再部署。"
  exit 1
fi

compose=(docker compose -f docker-compose.yml)
if [[ -f nginx/https.conf && -f nginx/ssl/fullchain.pem && -f nginx/ssl/privkey.pem ]]; then
  compose+=(-f docker-compose.https.yml)
  log "使用已有 HTTPS 证书"
fi

export COMPOSE_PARALLEL_LIMIT=1
log "重建并启动容器"
"${compose[@]}" up -d --build
"${compose[@]}" ps

if ! curl -fsS --max-time 15 http://127.0.0.1/healthz >/dev/null; then
  log "本机健康检查失败，请查看：docker compose logs --tail=80 backend"
  exit 1
fi
log "部署完成：$rev"
