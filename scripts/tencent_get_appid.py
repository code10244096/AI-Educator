# -*- coding: utf-8 -*-
"""一次性脚本：用 TC3-HMAC-SHA256 签名调用 CAM GetUserAppId，拿 UIN/AppId。
密钥只从环境变量读取，不落盘。"""
import hashlib, hmac, json, os, sys, time
from datetime import datetime, timezone
from urllib import request

SECRET_ID = os.environ["TENCENT_SECRET_ID"]
SECRET_KEY = os.environ["TENCENT_SECRET_KEY"]

HOST = "cam.tencentcloudapi.com"
SERVICE = "cam"
ACTION = "GetUserAppId"
VERSION = "2019-01-16"

payload = "{}"
t = int(time.time())
date = datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

canonical_headers = f"content-type:application/json; charset=utf-8\nhost:{HOST}\nx-tc-action:{ACTION.lower()}\n"
signed_headers = "content-type;host;x-tc-action"
canonical_request = "\n".join([
    "POST", "/", "",
    canonical_headers, signed_headers, sha256_hex(payload),
])
credential_scope = f"{date}/{SERVICE}/tc3_request"
string_to_sign = "\n".join([
    "TC3-HMAC-SHA256", str(t), credential_scope, sha256_hex(canonical_request),
])

def hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

secret_date = hmac_sha256(("TC3" + SECRET_KEY).encode("utf-8"), date)
secret_service = hmac_sha256(secret_date, SERVICE)
secret_signing = hmac_sha256(secret_service, "tc3_request")
signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

headers = {
    "Authorization": (
        "TC3-HMAC-SHA256 "
        f"Credential={SECRET_ID}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    ),
    "Content-Type": "application/json; charset=utf-8",
    "Host": HOST,
    "X-TC-Action": ACTION,
    "X-TC-Timestamp": str(t),
    "X-TC-Version": VERSION,
}
req = request.Request(f"https://{HOST}", data=payload.encode("utf-8"), headers=headers)
try:
    with request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode("utf-8"))
except Exception as e:
    print("HTTP_ERROR:", e)
    sys.exit(1)
print(json.dumps(body, ensure_ascii=False, indent=2))
