# -*- coding: utf-8 -*-
"""一次性：用 COS 原生签名（非 TC3）PUT 上传文件到私有桶。
用法：COS_SECRET_ID/KEY/BUCKET/REGION 环境变量，参数：本地路径 [对象键]。"""
import hashlib, hmac, os, sys, time
from urllib import request

SECRET_ID = os.environ["COS_SECRET_ID"]
SECRET_KEY = os.environ["COS_SECRET_KEY"]
BUCKET = os.environ["COS_BUCKET"]
REGION = os.environ.get("COS_REGION", "ap-guangzhou")

local = sys.argv[1]
key = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(local)
host = f"{BUCKET}.cos.{REGION}.myqcloud.com"
url = f"https://{host}/{key}"

start = int(time.time()) - 60
end = start + 3600
key_time = f"{start};{end}"

def hmac_sha1_hex(key_bytes: bytes, msg: str) -> str:
    return hmac.new(key_bytes, msg.encode("utf-8"), hashlib.sha1).hexdigest()

sign_key = hmac_sha1_hex(SECRET_KEY.encode("utf-8"), key_time)

http_string = f"put\n/{key}\n\nhost={host}\n"
string_to_sign = f"sha1\n{key_time}\n{hashlib.sha1(http_string.encode('utf-8')).hexdigest()}\n"
signature = hmac_sha1_hex(sign_key.encode("utf-8"), string_to_sign)

authorization = (
    "q-sign-algorithm=sha1"
    f"&q-ak={SECRET_ID}"
    f"&q-sign-time={key_time}"
    f"&q-key-time={key_time}"
    "&q-header-list=host"
    "&q-url-param-list="
    f"&q-signature={signature}"
)

size = os.path.getsize(local)
print(f"uploading {local} ({size} bytes) -> {url}", flush=True)
req = request.Request(url, data=open(local, "rb"), method="PUT", headers={
    "Host": host,
    "Authorization": authorization,
    "Content-Length": str(size),
})
try:
    with request.urlopen(req, timeout=600) as resp:
        print("OK", resp.status, resp.read()[:200])
except Exception as e:  # noqa: BLE001
    body = getattr(e, "read", lambda: b"")()
    print("FAILED:", e, body[:300])
    sys.exit(1)
