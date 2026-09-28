#!/usr/bin/env bash
# 旧入口。生产更新请使用 scripts/deploy.sh（从 GitHub 拉取并保留服务器上的配置与数据）。
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/deploy.sh" "$@"
