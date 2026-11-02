# -*- coding: utf-8 -*-
"""验证生产环境教案生成是否真正注入题库上下文（RAG v2 线上核查）。"""
import os
import sys
import time

import httpx

BASE = "https://ai-samrt-tutor-educator.cn"
PASSWORD = os.environ["E2E_PASSWORD"]

client = httpx.Client(base_url=BASE, timeout=60, follow_redirects=False)
r = client.post("/api/auth/login", json={"username": "admin", "password": PASSWORD})
assert r.status_code == 200, r.text
client.cookies.extract_cookies(r)

# 小学数学：题库最充足（23万题，22.8万带年级）
payload = {
    "title": "分数的初步认识",
    "subject": "数学",
    "grade": "三年级",
    "period": "1 课时",
    "student_level": "中等",
    "wait": "true",
}
t0 = time.perf_counter()
r = client.post("/api/lessonplan/generate", data=payload)
elapsed = time.perf_counter() - t0
print(f"generate: HTTP {r.status_code} {elapsed:.1f}s")
body = r.json()
plan_id = body.get("id")
print(f"id={plan_id} status={body.get('status')} retrieved_questions_count={body.get('retrieved_questions_count')}")
print(f"content_len={len(body.get('content') or '')}")

# 拉详情确认字段
r2 = client.get(f"/api/lessonplan/{plan_id}")
d = r2.json()
print(f"detail: retrieved={d.get('retrieved_questions_count')} stage={d.get('stage') or d.get('status')}")

# 检查最新 api_runs 日志里请求是否含题库上下文
del client
ok = False
import glob, json
ssh_cmd = sys.argv[1] if len(sys.argv) > 1 else None
print("NEXT: check api_runs log for question bank context")
