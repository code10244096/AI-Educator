"""线上生产环境 API 级端到端走查。仅依赖 httpx + 标准库。

    py scripts/e2e_prod.py
    py scripts/e2e_prod.py --base https://ai-samrt-tutor-educator.cn --cleanup

密码从环境变量 E2E_PASSWORD 读取；未设置则跳过需登录的步骤。
用户名默认 admin，可用 E2E_USERNAME 覆盖。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin

import httpx

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE = "https://ai-samrt-tutor-educator.cn"
SESSION_COOKIE = "aiedu_session"
USAGE_SINCE = "2026-10-01"
USAGE_UNTIL = "2026-10-27"
SUBJECTS = ("语文", "数学", "英语", "科学")
SEARCH_KEYWORDS = ("的", "了", "是", "一")
CN_OK = ("语文", "朗读", "课文", "段落")
CN_BAD = ("函数", "导数", "方程")
FEEDBACK_TOPIC = "页面操作不方便"
HOMEWORK_PNG = ROOT / "qa-reports" / "model-eval-2026-10-15" / "homework_test.png"

DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=15.0)
AI_TIMEOUT = httpx.Timeout(300.0, connect=15.0)

AUTH_STEPS = (
    "用量统计",
    "题库学科接口",
    "题库列表四学科",
    "题库搜索翻页",
    "keyset 分页",
    "教案生成",
    "批改链路",
    "反馈提交",
)


# --------------------------------------------------------------------------- helpers

def _enable_utf8() -> None:
    if sys.platform != "win32":
        return
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _color(code: str, text: str) -> str:
    if not getattr(sys.stdout, "isatty", lambda: False)():
        return text
    return f"\033[{code}m{text}\033[0m"


def _status_text(status: str) -> str:
    palette = {"PASS": "32", "FAIL": "31", "SKIP": "36", "WARN": "33"}
    return _color(palette.get(status, "0"), f"{status:<4}")


def parse_ts(value: Any) -> Optional[float]:
    """与 backend/usage_stats.parse_ts 对齐：ISO / 日期；无时区按 UTC。"""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    if s.endswith(("Z", "z")):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def json_body(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        text = (resp.text or "")[:300]
        return {"_raw": text}


def as_list(body: Any) -> list:
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        for key in ("items", "questions", "data", "results"):
            val = body.get(key)
            if isinstance(val, list):
                return val
    return []


def body_text(body: Any) -> str:
    if isinstance(body, str):
        return body
    try:
        return json.dumps(body, ensure_ascii=False)
    except Exception:
        return str(body)


def call_ts(item: dict) -> Optional[float]:
    for key in ("ts_utc", "timestamp", "ts", "created_at"):
        ts = parse_ts(item.get(key))
        if ts is not None:
            return ts
    return None


def token_hint(body: Any) -> str:
    if not isinstance(body, dict):
        return "接口未返回 token 字段"
    usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
    parts = []
    for key in ("total_tokens", "prompt_tokens", "completion_tokens", "tokens"):
        val = body.get(key)
        if val is None:
            val = usage.get(key)
        if val is not None:
            parts.append(f"{key}={val}")
    return ", ".join(parts) if parts else "接口未返回 token 字段"


def pick_script_src(html: str) -> Optional[str]:
    tags = re.findall(r"<script\b([^>]*)>", html, flags=re.I)
    candidates = []
    for attrs in tags:
        src_m = re.search(r"""src\s*=\s*['"]([^'"]+)['"]""", attrs, flags=re.I)
        if not src_m:
            continue
        src = src_m.group(1).strip()
        if not src or src.startswith("data:"):
            continue
        module = bool(re.search(r"""type\s*=\s*['"]module['"]""", attrs, flags=re.I))
        name = src.lower()
        score = 0
        if module:
            score += 10
        if "index" in name:
            score += 5
        if "/assets/" in name or name.endswith(".js"):
            score += 3
        candidates.append((score, src))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


# --------------------------------------------------------------------------- runner

class Reporter:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, name: str, status: str, detail: str, elapsed_s: Optional[float] = None) -> None:
        self.rows.append({
            "name": name,
            "status": status,
            "detail": detail,
            "elapsed_s": elapsed_s,
        })
        extra = f"  {elapsed_s:.2f}s" if elapsed_s is not None else ""
        print(f"[{_status_text(status)}] {name}{extra}  {detail}", flush=True)

    def has_fail(self) -> bool:
        return any(r["status"] == "FAIL" for r in self.rows)

    def summary(self) -> None:
        counts = {k: 0 for k in ("PASS", "FAIL", "SKIP", "WARN")}
        for row in self.rows:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        print("", flush=True)
        print(
            "汇总  "
            f"PASS={counts['PASS']}  FAIL={counts['FAIL']}  "
            f"WARN={counts['WARN']}  SKIP={counts['SKIP']}",
            flush=True,
        )


class ProdE2E:
    def __init__(self, base: str, cleanup: bool) -> None:
        self.base = base.rstrip("/")
        self.do_cleanup = cleanup
        self.username = (os.environ.get("E2E_USERNAME") or "admin").strip() or "admin"
        self.password = os.environ.get("E2E_PASSWORD") or ""
        self.rep = Reporter()
        self.logged_in = False
        self.token = ""
        self.created_plans: list[int] = []
        self.created_grades: list[int] = []
        self.created_feedback: list[tuple[Optional[int], str]] = []
        self.list_subject = "语文"
        self.client = httpx.Client(
            base_url=self.base,
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "ai-educator-e2e-prod/1.0"},
        )

    def close(self) -> None:
        self.client.close()

    def auth_headers(self) -> dict[str, str]:
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def _extract_token(self) -> str:
        try:
            value = self.client.cookies.get(SESSION_COOKIE)
            if value:
                return value
        except Exception:
            pass
        for cookie in self.client.cookies.jar:
            if cookie.name == SESSION_COOKIE and cookie.value:
                return cookie.value
        return ""

    def request(self, method: str, path: str, *, auth: bool = True, **kwargs) -> httpx.Response:
        headers = dict(kwargs.pop("headers", None) or {})
        if auth:
            headers.update(self.auth_headers())
        return self.client.request(method, path, headers=headers, **kwargs)

    def skip_auth(self, reason: str) -> None:
        for name in AUTH_STEPS:
            self.rep.add(name, "SKIP", reason)

    # ----- steps -----

    def step_login(self) -> None:
        name = "登录"
        if not self.password:
            self.rep.add(name, "SKIP", "未设置 E2E_PASSWORD，跳过需登录的步骤")
            self.skip_auth("未登录")
            return
        t0 = time.perf_counter()
        try:
            resp = self.request(
                "POST",
                "/api/auth/login",
                auth=False,
                json={"username": self.username, "password": self.password},
            )
        except Exception as exc:
            self.rep.add(name, "FAIL", f"请求异常 {type(exc).__name__}: {exc}", time.perf_counter() - t0)
            self.skip_auth("登录失败")
            return
        elapsed = time.perf_counter() - t0
        body = json_body(resp)
        if resp.status_code != 200:
            self.rep.add(name, "FAIL", f"HTTP {resp.status_code} {body_text(body)[:180]}", elapsed)
            self.skip_auth("登录失败")
            return
        self.token = self._extract_token()
        if self.token:
            self.client.headers["Authorization"] = f"Bearer {self.token}"
        self.logged_in = True
        user = body if isinstance(body, dict) else {}
        role = user.get("role") or "?"
        note = f"user={user.get('username') or self.username} role={role}"
        if user.get("must_change_password"):
            note += "；账号 must_change_password=true，后续业务接口可能 403"
        if not self.token:
            note += "；未拿到 aiedu_session，仅依赖 Cookie 罐"
        self.rep.add(name, "PASS", note, elapsed)

    def step_usage(self) -> None:
        name = "用量统计"
        params = {"since": USAGE_SINCE, "until": USAGE_UNTIL, "limit": 500}
        t0 = time.perf_counter()
        try:
            summary_resp = self.request("GET", "/api/usage/summary", params={"since": USAGE_SINCE, "until": USAGE_UNTIL})
            calls_resp = self.request("GET", "/api/usage/calls", params=params)
        except Exception as exc:
            self.rep.add(name, "FAIL", f"请求异常 {type(exc).__name__}: {exc}", time.perf_counter() - t0)
            return
        elapsed = time.perf_counter() - t0
        if summary_resp.status_code != 200:
            self.rep.add(name, "FAIL", f"summary HTTP {summary_resp.status_code} {summary_resp.text[:180]}", elapsed)
            return
        if calls_resp.status_code != 200:
            self.rep.add(name, "FAIL", f"calls HTTP {calls_resp.status_code} {calls_resp.text[:180]}", elapsed)
            return
        summary = json_body(summary_resp)
        calls_body = json_body(calls_resp)
        if not isinstance(summary, dict) or not isinstance(summary.get("overview"), dict):
            self.rep.add(name, "FAIL", "summary 无 overview 数据", elapsed)
            return
        overview = summary["overview"]
        items = as_list(calls_body)
        since_ts = parse_ts(USAGE_SINCE)
        until_ts = parse_ts(USAGE_UNTIL)
        out_of_range = []
        for item in items:
            if not isinstance(item, dict):
                out_of_range.append("非对象记录")
                continue
            ts = call_ts(item)
            if ts is None:
                out_of_range.append(str(item.get("call_id") or item.get("ts_utc") or "?"))
                continue
            if since_ts is not None and ts < since_ts:
                out_of_range.append(item.get("ts_utc") or "?")
            elif until_ts is not None and ts > until_ts:
                out_of_range.append(item.get("ts_utc") or "?")
        if out_of_range:
            sample = ", ".join(str(x) for x in out_of_range[:5])
            self.rep.add(
                name, "FAIL",
                f"calls 有 {len(out_of_range)} 条落在 {USAGE_SINCE}~{USAGE_UNTIL} 外：{sample}",
                elapsed,
            )
            return
        detail = (
            f"overview.calls={overview.get('calls')} tokens={overview.get('total_tokens')} "
            f"records={len(items)} bytes={len(summary_resp.content)}/{len(calls_resp.content)}"
        )
        if not items:
            self.rep.add(name, "WARN", detail + "；区间内无调用记录", elapsed)
            return
        self.rep.add(name, "PASS", detail, elapsed)

    def step_subjects(self) -> None:
        name = "题库学科接口"
        t0 = time.perf_counter()
        try:
            resp = self.request("GET", "/api/questionbank/subjects")
        except Exception as exc:
            self.rep.add(name, "FAIL", f"请求异常 {type(exc).__name__}: {exc}", time.perf_counter() - t0)
            return
        elapsed = time.perf_counter() - t0
        if resp.status_code != 200:
            self.rep.add(name, "FAIL", f"HTTP {resp.status_code} {resp.text[:180]}", elapsed)
            return
        body = json_body(resp)
        names = []
        if isinstance(body, dict):
            names = body.get("subjects") or []
        if not isinstance(names, list):
            names = []
        missing = [s for s in SUBJECTS if s not in names]
        if missing:
            self.rep.add(name, "FAIL", f"缺少学科 {missing}；实际={names}", elapsed)
            return
        self.rep.add(name, "PASS", f"subjects={names}  {len(resp.content)}B", elapsed)

    def step_list_subjects(self) -> None:
        name = "题库列表四学科"
        t0 = time.perf_counter()
        notes = []
        first_bytes = None
        try:
            for i, subject in enumerate(SUBJECTS):
                resp = self.request("GET", "/api/questionbank/list", params={"subject": subject, "limit": 5})
                if first_bytes is None:
                    first_bytes = len(resp.content)
                if resp.status_code != 200:
                    self.rep.add(name, "FAIL", f"{subject} HTTP {resp.status_code}", time.perf_counter() - t0)
                    return
                items = as_list(json_body(resp))
                if not items:
                    self.rep.add(name, "FAIL", f"{subject} 列表为空  {len(resp.content)}B", time.perf_counter() - t0)
                    return
                sample = items[0] if isinstance(items[0], dict) else {}
                missing = [k for k in ("id", "question_text", "answer", "difficulty") if k not in sample]
                if missing:
                    self.rep.add(name, "FAIL", f"{subject} 缺字段 {missing}", time.perf_counter() - t0)
                    return
                notes.append(f"{subject} n={len(items)} {len(resp.content)}B")
                if i == 0:
                    self.list_subject = subject
        except Exception as exc:
            self.rep.add(name, "FAIL", f"请求异常 {type(exc).__name__}: {exc}", time.perf_counter() - t0)
            return
        self.rep.add(
            name, "PASS",
            f"首包 {first_bytes}B；" + "；".join(notes),
            time.perf_counter() - t0,
        )

    def step_search_pages(self) -> None:
        name = "题库搜索翻页"
        t0 = time.perf_counter()
        last_warn = ""
        try:
            for keyword in SEARCH_KEYWORDS:
                first = self.request(
                    "POST",
                    "/api/questionbank/search",
                    data={"keyword": keyword, "subject": "语文", "limit": 20, "offset": 0},
                )
                second = self.request(
                    "POST",
                    "/api/questionbank/search",
                    data={"keyword": keyword, "subject": "语文", "limit": 20, "offset": 20},
                )
                elapsed = time.perf_counter() - t0
                combined = f"{first.text} {second.text}"
                truncated = (
                    "结果过多" in combined
                    or "offset 被截断" in combined
                    or "请细化筛选" in combined
                )
                if first.status_code != 200:
                    self.rep.add(name, "FAIL", f"第一页 HTTP {first.status_code} keyword={keyword}", elapsed)
                    return
                if second.status_code != 200:
                    if truncated:
                        self.rep.add(name, "WARN", f"第二页 HTTP {second.status_code}，后端提示结果过多 keyword={keyword}", elapsed)
                        return
                    self.rep.add(name, "FAIL", f"第二页 HTTP {second.status_code} keyword={keyword}", elapsed)
                    return
                page1 = as_list(json_body(first))
                page2 = as_list(json_body(second))
                ids1 = {x.get("id") for x in page1 if isinstance(x, dict) and x.get("id") is not None}
                ids2 = {x.get("id") for x in page2 if isinstance(x, dict) and x.get("id") is not None}
                if truncated:
                    self.rep.add(
                        name, "WARN",
                        f"keyword={keyword} 结果过多/offset 截断；p1={len(page1)} p2={len(page2)}",
                        elapsed,
                    )
                    return
                if not page2:
                    last_warn = f"keyword={keyword} 第二页为空 p1={len(page1)}"
                    continue
                overlap = ids1 & ids2
                if overlap:
                    self.rep.add(name, "FAIL", f"keyword={keyword} 两页 id 有交集 {sorted(overlap)[:5]}", elapsed)
                    return
                self.rep.add(
                    name, "PASS",
                    f"keyword={keyword} p1={len(page1)} p2={len(page2)} 无交集 {len(first.content)}B/{len(second.content)}B",
                    elapsed,
                )
                return
        except Exception as exc:
            self.rep.add(name, "FAIL", f"请求异常 {type(exc).__name__}: {exc}", time.perf_counter() - t0)
            return
        self.rep.add(name, "FAIL", last_warn or "搜索翻页未拿到第二页", time.perf_counter() - t0)

    def step_keyset(self) -> None:
        name = "keyset 分页"
        t0 = time.perf_counter()
        try:
            first = self.request(
                "GET", "/api/questionbank/list",
                params={"subject": self.list_subject, "limit": 3},
            )
            if first.status_code != 200:
                self.rep.add(name, "FAIL", f"第一页 HTTP {first.status_code}", time.perf_counter() - t0)
                return
            items = as_list(json_body(first))
            if not items or not isinstance(items[0], dict) or items[0].get("id") is None:
                self.rep.add(name, "FAIL", "列表无可用 id", time.perf_counter() - t0)
                return
            after_id = items[0]["id"]
            second = self.request(
                "GET", "/api/questionbank/list",
                params={"subject": self.list_subject, "limit": 3, "after_id": after_id},
            )
            elapsed = time.perf_counter() - t0
            if second.status_code != 200:
                self.rep.add(name, "FAIL", f"after_id HTTP {second.status_code}", elapsed)
                return
            page2 = as_list(json_body(second))
            ids2 = [x.get("id") for x in page2 if isinstance(x, dict)]
            if after_id in ids2:
                self.rep.add(name, "FAIL", f"after_id={after_id} 仍出现在下一页 {ids2}", elapsed)
                return
            self.rep.add(
                name, "PASS",
                f"subject={self.list_subject} after_id={after_id} next={ids2}",
                elapsed,
            )
        except Exception as exc:
            self.rep.add(name, "FAIL", f"请求异常 {type(exc).__name__}: {exc}", time.perf_counter() - t0)

    def _poll_plan(self, plan_id: int, timeout_s: float = 240.0) -> dict:
        deadline = time.time() + timeout_s
        last: dict = {}
        while time.time() < deadline:
            resp = self.request("GET", f"/api/lessonplan/{plan_id}")
            body = json_body(resp)
            last = body if isinstance(body, dict) else {"_raw": body}
            status = last.get("status")
            if status in ("completed", "failed") or last.get("content"):
                return last
            time.sleep(2)
        return last

    def step_lessonplan(self) -> None:
        name = "教案生成"
        t0 = time.perf_counter()
        try:
            resp = self.request(
                "POST",
                "/api/lessonplan/generate",
                data={"title": "秋天的雨", "subject": "语文", "wait": "true", "period": "1 课时", "student_level": "中等"},
                timeout=AI_TIMEOUT,
            )
        except Exception as exc:
            self.rep.add(name, "FAIL", f"请求异常 {type(exc).__name__}: {exc}", time.perf_counter() - t0)
            return
        body = json_body(resp)
        if isinstance(body, dict) and body.get("id") is not None:
            try:
                self.created_plans.append(int(body["id"]))
            except (TypeError, ValueError):
                pass
        if resp.status_code != 200:
            self.rep.add(name, "FAIL", f"HTTP {resp.status_code} {body_text(body)[:180]}", time.perf_counter() - t0)
            return
        if not isinstance(body, dict):
            self.rep.add(name, "FAIL", "返回不是对象", time.perf_counter() - t0)
            return
        if body.get("status") == "processing" and body.get("id") is not None:
            body = {**body, **self._poll_plan(int(body["id"]))}
        elapsed = time.perf_counter() - t0
        subject = (body.get("subject") or "").strip()
        content = body.get("content") or ""
        if subject != "语文":
            self.rep.add(name, "FAIL", f"subject={subject!r} 期望 语文；id={body.get('id')}", elapsed)
            return
        has_ok = any(word in content for word in CN_OK)
        has_bad = any(word in content for word in CN_BAD)
        if not has_ok or has_bad:
            self.rep.add(
                name, "FAIL",
                f"正文疑似跑题 ok={has_ok} bad={has_bad} chars={len(content)} id={body.get('id')}",
                elapsed,
            )
            return
        self.rep.add(
            name, "PASS",
            f"id={body.get('id')} chars={len(content)} {token_hint(body)}",
            elapsed,
        )

    def step_grader(self) -> None:
        name = "批改链路"
        if not HOMEWORK_PNG.is_file():
            self.rep.add(name, "SKIP", f"缺图 {HOMEWORK_PNG.as_posix()}")
            return
        t0 = time.perf_counter()
        try:
            with HOMEWORK_PNG.open("rb") as fh:
                resp = self.request(
                    "POST",
                    "/api/grader/upload",
                    data={"wait": "true", "subject": "数学", "student_name": "E2E走查"},
                    files=[("files", (HOMEWORK_PNG.name, fh, "image/png"))],
                    timeout=AI_TIMEOUT,
                )
        except Exception as exc:
            self.rep.add(name, "FAIL", f"请求异常 {type(exc).__name__}: {exc}", time.perf_counter() - t0)
            return
        body = json_body(resp)
        sid = None
        if isinstance(body, dict):
            sid = body.get("submission_id") or body.get("id")
            if sid is not None:
                try:
                    self.created_grades.append(int(sid))
                except (TypeError, ValueError):
                    sid = None
        if resp.status_code != 200:
            self.rep.add(name, "FAIL", f"HTTP {resp.status_code} {body_text(body)[:180]}", time.perf_counter() - t0)
            return
        detail = body if isinstance(body, dict) else {}
        if sid is not None and detail.get("score") is None and "needs_review" not in detail:
            try:
                got = self.request("GET", f"/api/grader/{sid}")
                if got.status_code == 200 and isinstance(json_body(got), dict):
                    detail = {**detail, **json_body(got)}
            except Exception:
                pass
        elapsed = time.perf_counter() - t0
        grading = detail.get("grading_result") if isinstance(detail.get("grading_result"), dict) else {}
        score = detail.get("score")
        if score is None:
            score = grading.get("score")
        needs_review = detail.get("needs_review")
        if needs_review is None:
            needs_review = grading.get("needs_review")
        if score is None and not needs_review:
            self.rep.add(name, "FAIL", f"返回缺分数/待复核 id={sid} keys={list(detail)[:12]}", elapsed)
            return
        self.rep.add(
            name, "PASS",
            f"id={sid} score={score} needs_review={bool(needs_review)} status={detail.get('status')}",
            elapsed,
        )

    def step_feedback(self) -> None:
        name = "反馈提交"
        marker = f"【自动化走查】{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 线上端到端脚本"
        t0 = time.perf_counter()
        try:
            posted = self.request(
                "POST",
                "/api/feedback",
                json={
                    "topics": [{"name": FEEDBACK_TOPIC, "detail": ""}],
                    "content": marker,
                    "contact": "",
                    "page": "/e2e-prod",
                },
            )
        except Exception as exc:
            self.rep.add(name, "FAIL", f"提交异常 {type(exc).__name__}: {exc}", time.perf_counter() - t0)
            return
        if posted.status_code != 200:
            self.rep.add(name, "FAIL", f"提交 HTTP {posted.status_code} {posted.text[:180]}", time.perf_counter() - t0)
            return
        try:
            listed = self.request("GET", "/api/feedback/list")
        except Exception as exc:
            self.rep.add(name, "FAIL", f"列表异常 {type(exc).__name__}: {exc}", time.perf_counter() - t0)
            return
        elapsed = time.perf_counter() - t0
        if listed.status_code != 200:
            self.rep.add(name, "FAIL", f"列表 HTTP {listed.status_code} {listed.text[:180]}", elapsed)
            return
        items = as_list(json_body(listed))
        hit = None
        for item in items:
            if isinstance(item, dict) and marker in str(item.get("content") or ""):
                hit = item
                break
        if not hit:
            self.created_feedback.append((None, marker))
            self.rep.add(name, "FAIL", "管理端列表未找到本条反馈", elapsed)
            return
        fid = hit.get("id")
        try:
            self.created_feedback.append((int(fid) if fid is not None else None, marker))
        except (TypeError, ValueError):
            self.created_feedback.append((None, marker))
        self.rep.add(name, "PASS", f"id={fid} topic={FEEDBACK_TOPIC}", elapsed)

    def step_permission(self) -> None:
        name = "权限"
        t0 = time.perf_counter()
        try:
            anon = httpx.Client(base_url=self.base, timeout=DEFAULT_TIMEOUT, follow_redirects=False)
            try:
                codes = []
                for path in ("/api/usage/summary", "/api/usage/calls"):
                    resp = anon.get(path, params={"since": USAGE_SINCE, "until": USAGE_UNTIL})
                    codes.append((path, resp.status_code))
                    if resp.status_code not in (401, 403):
                        self.rep.add(
                            name, "FAIL",
                            f"{path} 期望 401/403，实际 {resp.status_code}",
                            time.perf_counter() - t0,
                        )
                        return
            finally:
                anon.close()
        except Exception as exc:
            self.rep.add(name, "FAIL", f"请求异常 {type(exc).__name__}: {exc}", time.perf_counter() - t0)
            return
        shown = ", ".join(f"{p}={c}" for p, c in codes)
        self.rep.add(name, "PASS", shown, time.perf_counter() - t0)

    def step_static(self) -> None:
        name = "静态页"
        t0 = time.perf_counter()
        try:
            home = self.request("GET", "/", auth=False)
        except Exception as exc:
            self.rep.add(name, "FAIL", f"GET / 异常 {type(exc).__name__}: {exc}", time.perf_counter() - t0)
            return
        if home.status_code != 200:
            self.rep.add(name, "FAIL", f"GET / HTTP {home.status_code}", time.perf_counter() - t0)
            return
        html = home.text or ""
        if 'id="root"' not in html and "id='root'" not in html:
            self.rep.add(name, "FAIL", "HTML 不含 root 挂载点", time.perf_counter() - t0)
            return
        src = pick_script_src(html)
        if not src:
            self.rep.add(name, "FAIL", "HTML 未解析到 script src", time.perf_counter() - t0)
            return
        bundle_url = urljoin(self.base + "/", src)
        try:
            bundle = self.request("GET", bundle_url, auth=False)
        except Exception as exc:
            self.rep.add(name, "FAIL", f"bundle 异常 {type(exc).__name__}: {exc} src={src}", time.perf_counter() - t0)
            return
        elapsed = time.perf_counter() - t0
        if bundle.status_code != 200:
            self.rep.add(name, "FAIL", f"bundle HTTP {bundle.status_code} src={src}", elapsed)
            return
        self.rep.add(name, "PASS", f"/ {len(home.content)}B；bundle {src} {len(bundle.content)}B", elapsed)

    def cleanup(self) -> None:
        leftovers: list[str] = []
        for pid in self.created_plans:
            try:
                resp = self.request("DELETE", f"/api/lessonplan/{pid}")
                if resp.status_code == 200:
                    self.rep.add("清理教案", "PASS", f"已删除 lessonplan id={pid}")
                else:
                    leftovers.append(f"lessonplan:{pid} HTTP {resp.status_code}")
                    self.rep.add("清理教案", "WARN", f"id={pid} HTTP {resp.status_code} {resp.text[:120]}")
            except Exception as exc:
                leftovers.append(f"lessonplan:{pid} {exc}")
                self.rep.add("清理教案", "WARN", f"id={pid} {type(exc).__name__}: {exc}")
        for sid in self.created_grades:
            try:
                resp = self.request("DELETE", f"/api/grader/{sid}")
                if resp.status_code == 200:
                    self.rep.add("清理批改", "PASS", f"已删除 grader id={sid}")
                else:
                    leftovers.append(f"grader:{sid} HTTP {resp.status_code}")
                    self.rep.add("清理批改", "WARN", f"id={sid} HTTP {resp.status_code} {resp.text[:120]}")
            except Exception as exc:
                leftovers.append(f"grader:{sid} {exc}")
                self.rep.add("清理批改", "WARN", f"id={sid} {type(exc).__name__}: {exc}")
        if self.created_feedback:
            shown = ", ".join(
                f"id={fid or '?'} {marker}" for fid, marker in self.created_feedback
            )
            leftovers.append("feedback 无删除接口: " + shown)
            self.rep.add("清理反馈", "WARN", "接口不支持删除，遗留 " + shown)
        if leftovers:
            print("遗留 id 清单: " + " | ".join(leftovers), flush=True)
        elif self.do_cleanup:
            print("遗留 id 清单: （无）", flush=True)

    def run(self) -> int:
        print(f"目标 {self.base}", flush=True)
        print(f"时间 {datetime.now().isoformat(timespec='seconds')}", flush=True)
        self.step_login()
        if self.logged_in:
            self.step_usage()
            self.step_subjects()
            self.step_list_subjects()
            self.step_search_pages()
            self.step_keyset()
            self.step_lessonplan()
            self.step_grader()
            self.step_feedback()
        self.step_permission()
        self.step_static()
        if self.do_cleanup:
            self.cleanup()
        self.rep.summary()
        return 1 if self.rep.has_fail() else 0


def main() -> int:
    _enable_utf8()
    parser = argparse.ArgumentParser(description="线上生产环境 API 级端到端走查")
    parser.add_argument("--base", default=DEFAULT_BASE, help="站点根 URL")
    parser.add_argument("--cleanup", action="store_true", help="结束后删除本脚本创建的教案/批改；反馈仅打印遗留 id")
    args = parser.parse_args()
    runner = ProdE2E(args.base, args.cleanup)
    try:
        return runner.run()
    finally:
        runner.close()


if __name__ == "__main__":
    sys.exit(main())
