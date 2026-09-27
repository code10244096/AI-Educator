"""
第 1 轮真实模型评测（L-Q03 一致率、L-P03 单份耗时、L-F01“真实模型走通上传→批改→结果”）。
不被 pytest 收集。会花钱：每份 md 作业 1 次批改调用（md 文本不走识别），可选 1 张图片（识别 1 + 批改 1）。

    python backend/tests/acceptance/real_eval/run_real_eval.py --max-calls 10            # 默认 6 份 md + 1 张图片 = 8 次
    python backend/tests/acceptance/real_eval/run_real_eval.py --dry-run                  # 假模型，0 次真实调用，只验证流程

- 临时库、临时上传目录、调用日志写到 scratch（--out，默认系统临时目录），绝不碰 teaching_assistant.db / api_runs/
- 通过真实 HTTP 接口走：建教师 → 建班 → 建学生 → 布置作业（参考答案取数据集原文，含已知错误）→ 上传 → 轮询结果
- 与人工判定表 human_judgement_r1.json 对比逐题 is_correct，输出 JSON + Markdown 报告
- 硬上限：包装 gateway.chat，达到 --max-calls 即抛错，不会超预算
"""
import argparse
import asyncio
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ACC = HERE.parent
TESTS = ACC.parent
BACKEND = TESTS.parent
REPO = BACKEND.parent
DATASET = REPO / "dataset" / "测试集" / "批改作业"

ap = argparse.ArgumentParser()
ap.add_argument("--max-calls", type=int, default=10)
ap.add_argument("--files", default="", help="逗号分隔的文件名；默认为判定表中的全部文件")
ap.add_argument("--no-image", action="store_true")
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--out", default="")
ap.add_argument("--timeout", type=int, default=600)
ARGS = ap.parse_args()

OUT = Path(ARGS.out or tempfile.mkdtemp(prefix="aiedu_real_eval_"))
OUT.mkdir(parents=True, exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(OUT / 'eval.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(OUT / "uploads")
os.environ["API_OUTPUT_ROOT"] = str(OUT / "api_runs")
os.environ["SEED_DEMO_DATA"] = "false"
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if os.environ.get("LLM_API_KEY", "").startswith("your_"):
    del os.environ["LLM_API_KEY"]  # real key comes from backend/config.json (never printed)
os.chdir(BACKEND)
sys.path[:0] = [str(BACKEND), str(TESTS)]

import logging  # noqa: E402
logging.disable(logging.WARNING)
import httpx  # noqa: E402


def split_md(text: str):
    student, _, ref = text.partition("## 参考答案")
    return student.strip(), ref.strip()


def make_image(path: Path):
    """一张“手机拍照”风格的作业图片：4 道题，第 2、4 题学生答错。"""
    from PIL import Image, ImageDraw, ImageFont
    font = None
    for f in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\simsun.ttc"):
        if Path(f).exists():
            font = ImageFont.truetype(f, 34)
            break
    img = Image.new("RGB", (1240, 1000), (250, 248, 240))
    d = ImageDraw.Draw(img)
    lines = ["高一数学 课后练习（函数）  姓名：林雨桐", "",
             "1. 函数 f(x)=√(x-1) 的定义域是 ______。", "   答：[1, +∞)", "",
             "2. 已知 f(x)=2x+1，则 f(3) = ______。", "   答：6", "",
             "3. 函数 y=x² 在区间 (0,+∞) 上是增函数还是减函数？", "   答：增函数", "",
             "4. 若以 2 为底 8 的对数等于 a，则 a = ______。", "   答：4"]
    y = 40
    for ln in lines:
        d.text((50, y), ln, fill=(20, 20, 60), font=font)
        y += 60
    img = img.rotate(1.2, expand=True, fillcolor=(235, 235, 230))
    img.save(path, "JPEG", quality=88)
    return {"1": True, "2": False, "3": True, "4": False}, "1. [1,+∞)\n2. 7\n3. 增函数\n4. 3"


def main_number(q) -> int | None:
    m = re.match(r"\s*(\d+)", str(q.get("question_number", "")))
    return int(m.group(1)) if m else None


def verdicts(result: dict) -> dict:
    """{题号: bool}；同一大题拆成多小问时，全部判对才算对。"""
    out = {}
    for q in (result or {}).get("questions") or []:
        n = main_number(q)
        if n is None:
            continue
        out[n] = out.get(n, True) and bool(q.get("is_correct"))
    return out


async def run():
    from fakes import FakeGateway, install_gateway
    import ai_client as ai_mod
    from main import app
    import database
    from manage import create_user
    database.engine.sync_engine.echo = False

    gw = ai_mod.ai_client.gateway
    if ARGS.dry_run:
        install_gateway(FakeGateway())
        gw = ai_mod.ai_client.gateway
    elif not gw.enabled:
        print("真实模型未配置（LLM_API_KEY / config.json），中止")
        return 2
    calls = {"n": 0, "log": []}
    orig_chat = gw.chat

    async def capped_chat(messages, *, feature, **kw):
        if calls["n"] >= ARGS.max_calls:
            raise RuntimeError(f"达到真实调用上限 {ARGS.max_calls}，停止")
        calls["n"] += 1
        t0 = time.time()
        try:
            res = await orig_chat(messages, feature=feature, **kw)
            calls["log"].append({"feature": feature, "ok": True, "s": round(time.time() - t0, 1),
                                 "model": getattr(res, "model", None), "tokens": (getattr(res, "usage", None) or {}).get("total_tokens")})
            return res
        except Exception as e:
            calls["log"].append({"feature": feature, "ok": False, "s": round(time.time() - t0, 1), "error": str(e)[:200]})
            raise
    gw.chat = capped_chat

    judge = json.loads((HERE / "human_judgement_r1.json").read_text(encoding="utf-8"))["files"]
    files = [f for f in (ARGS.files.split(",") if ARGS.files else list(judge)) if f]
    planned = len(files) + (0 if ARGS.no_image else 2)
    print(f"计划真实调用 {planned} 次（上限 {ARGS.max_calls}）；输出目录 {OUT}")
    if planned > ARGS.max_calls:
        print("计划次数超过上限，中止")
        return 2

    create_user("eval_teacher", "评测老师", password="Eval2026abc", must_change_password=False)
    report = {"started": datetime.now().isoformat(timespec="seconds"), "files": [], "calls": calls["log"]}
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://eval", timeout=ARGS.timeout) as c:
            assert (await c.post("/api/auth/login", json={"username": "eval_teacher", "password": "Eval2026abc"})).status_code == 200
            cls = (await c.post("/api/class", json={"name": "评测班", "grade": "高三"})).json()
            ck = cls.get("slug") or cls["id"]
            jobs = []
            for i, fname in enumerate(files):
                student, ref = split_md((DATASET / fname).read_text(encoding="utf-8"))
                m = (await c.post(f"/api/class/{ck}/members", json={"name": f"评测生{i + 1}", "student_no": f"E{i + 1:03d}"})).json()
                hw = (await c.post(f"/api/class/{ck}/homework", json={"title": judge[fname]["title"], "reference_answer": ref})).json()
                jobs.append(("md", fname, m, hw, [("files", (f"{m['name']}.md", student.encode("utf-8"), "text/markdown"))], None))
            if not ARGS.no_image:
                img = OUT / "photo.jpg"
                truth, ref = make_image(img)
                m = (await c.post(f"/api/class/{ck}/members", json={"name": "林雨桐", "student_no": "E100"})).json()
                hw = (await c.post(f"/api/class/{ck}/homework", json={"title": "函数 课后练习（图片）", "reference_answer": ref})).json()
                jobs.append(("image", "photo.jpg", m, hw, [("files", ("林雨桐.jpg", img.read_bytes(), "image/jpeg"))], truth))
            started = {}
            for kind, fname, m, hw, fl, truth in jobs:
                r = await c.post("/api/grader/upload", files=fl,
                                 data={"assignment_id": str(hw["assignment_id"]), "member_id": str(m["id"])})
                assert r.status_code in (200, 202), r.text
                started[r.json()["submission_id"]] = (kind, fname, truth, time.time())
            pending = dict(started)
            finals = {}
            deadline = time.time() + ARGS.timeout
            while pending and time.time() < deadline:
                await asyncio.sleep(2)
                for sid in list(pending):
                    d = (await c.get(f"/api/grader/{sid}")).json()
                    if d.get("status") in ("completed", "failed"):
                        kind, fname, truth, t0 = pending.pop(sid)
                        finals[sid] = (d, round(time.time() - t0, 1))
            for sid, (kind, fname, truth, t0) in started.items():
                d, secs = finals.get(sid, ({"status": "timeout"}, None))
                v = verdicts(d.get("grading_result") or {})
                human = truth or {k: q.get("verdict") for k, q in judge[fname]["questions"].items()}
                meta = {} if truth else judge[fname]["questions"]
                rows = []
                for k, hv in human.items():
                    n = int(k)
                    q = meta.get(k, {})
                    rows.append({"q": n, "human": hv, "model": v.get(n), "exclude": bool(q.get("exclude")),
                                 "debatable": bool(q.get("debatable")), "ref_ok": q.get("ref_ok", True),
                                 "agree": (v.get(n) == hv) if hv is not None else None})
                issues = [{"q": q.get("question_number"), "reference_issue": q.get("reference_issue"),
                           "needs_review": q.get("needs_review")}
                          for q in (d.get("grading_result") or {}).get("questions") or []
                          if q.get("reference_issue") or q.get("needs_review")]
                report["files"].append({"kind": kind, "file": fname, "submission_id": sid, "status": d.get("status"),
                                        "error": d.get("error_message"), "seconds": secs, "score": d.get("score"),
                                        "model_questions": len((d.get("grading_result") or {}).get("questions") or []),
                                        "rows": rows, "flags": issues})
    report["calls"] = calls["log"]
    report["real_calls"] = calls["n"]

    def rate(pred):
        rs = [r for f in report["files"] for r in f["rows"] if r["agree"] is not None and pred(r)]
        ok = sum(1 for r in rs if r["agree"])
        return {"agree": ok, "total": len(rs), "rate": round(ok / len(rs) * 100, 1) if rs else None}
    report["summary"] = {
        "all": rate(lambda r: not r["exclude"]),
        "clear_only": rate(lambda r: not r["exclude"] and not r["debatable"]),
        "ref_wrong": rate(lambda r: not r["exclude"] and r["ref_ok"] is False),
        "files_ok": sum(1 for f in report["files"] if f["status"] == "completed"),
        "files": len(report["files"]),
        "max_seconds": max((f["seconds"] or 0) for f in report["files"]) if report["files"] else None,
    }
    (OUT / "real_eval_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# 第 1 轮真实模型评测 {report['started']}", "",
             f"- 真实调用 {report['real_calls']} 次；完成 {report['summary']['files_ok']}/{report['summary']['files']} 份；单份最长 {report['summary']['max_seconds']} 秒",
             f"- 逐题一致率（全部可判题）：{report['summary']['all']}",
             f"- 逐题一致率（去掉过程类有争议题）：{report['summary']['clear_only']}",
             f"- 参考答案有误的题上的一致率：{report['summary']['ref_wrong']}", "",
             "| 类型 | 文件 | 状态 | 耗时s | 得分 | 不一致题号（人工/模型） | AI 标记 |", "|---|---|---|---|---|---|---|"]
    for f in report["files"]:
        diff = ", ".join(f"{r['q']}({'对' if r['human'] else '错'}/{'对' if r['model'] else ('错' if r['model'] is False else '缺')})"
                         for r in f["rows"] if r["agree"] is False)
        lines.append(f"| {f['kind']} | {f['file'][-12:]} | {f['status']} | {f['seconds']} | {f['score']} | {diff or '—'} | {len(f['flags'])} |")
    (OUT / "real_eval_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    await database.engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
