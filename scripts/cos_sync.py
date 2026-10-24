# -*- coding: utf-8 -*-
"""把本地 backups/ 同步到腾讯云 COS（幂等：已存在且大小一致则跳过）。
用法（在部署目录执行）：
  docker run --rm -v /opt/ai-teaching:/data cos-sync python /data/scripts/cos_sync.py
环境变量（必填）：COS_SECRET_ID / COS_SECRET_KEY / COS_BUCKET / COS_REGION
可选：COS_DAILY_KEEP_DAYS（同步最近 N 天的每日备份目录，默认 2，0 表示只同步月度归档）
"""
import os, sys, time, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger("cos_sync")

SECRET_ID = os.environ["COS_SECRET_ID"]
SECRET_KEY = os.environ["COS_SECRET_KEY"]
BUCKET = os.environ["COS_BUCKET"]            # 形如 ai-educator-backups-1408630682
REGION = os.environ.get("COS_REGION", "ap-guangzhou")
DAILY_KEEP = int(os.environ.get("COS_DAILY_KEEP_DAYS", "2"))
APP_DIR = Path("/data")

from qcloud_cos import CosConfig, CosS3Client

cfg = CosConfig(Region=REGION, SecretId=SECRET_ID, SecretKey=SECRET_KEY,
                Scheme="https")
client = CosS3Client(cfg)


def ensure_bucket():
    try:
        client.head_bucket(Bucket=BUCKET)
        log.info("桶已存在: %s", BUCKET)
        return
    except Exception:
        pass
    log.info("创建桶: %s 区域: %s", BUCKET, REGION)
    client.create_bucket(Bucket=BUCKET, ACL="private")


def already_synced(key: str, size: int) -> bool:
    try:
        resp = client.head_object(Bucket=BUCKET, Key=key)
        return int(resp["Content-Length"]) == size
    except Exception:
        return False


def upload(local: Path, key: str):
    size = local.stat().st_size
    if already_synced(key, size):
        log.info("跳过(已同步) %s", key)
        return
    log.info("上传 %s -> cos://%s/%s (%d bytes)", local, BUCKET, key, size)
    client.upload_file(Bucket=BUCKET, Key=key, LocalFilePath=str(local),
                       EnableMD5=False)


def main():
    ensure_bucket()
    monthly = APP_DIR / "backups" / "monthly"
    n = 0
    if monthly.is_dir():
        for f in sorted(monthly.glob("*.tar.gz")):
            upload(f, f"backups/monthly/{f.name}")
            n += 1
    if DAILY_KEEP > 0:
        cutoff = time.time() - DAILY_KEEP * 86400
        for d in sorted(APP_DIR.glob("backups/2*")):
            if not d.is_dir() or d.stat().st_mtime < cutoff:
                continue
            for f in sorted(d.rglob("*")):
                if f.is_file():
                    upload(f, f"backups/{d.name}/{f.relative_to(d).as_posix()}")
                    n += 1
    log.info("同步完成，共处理 %d 个文件", n)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log.error("同步失败: %s", e)
        sys.exit(1)
