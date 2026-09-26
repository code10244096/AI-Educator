"""
Opt-in end-to-end run against the REAL model (costs money / quota; ~20-60 s per call).
Not collected by pytest (file name does not match test_*.py).

    python backend/tests/e2e_real_model.py            # grade 3 dataset files + 1 lesson plan
    python backend/tests/e2e_real_model.py -n 1 --no-lessonplan
    python backend/tests/e2e_real_model.py --ids 3,7

What it does
  * temp SQLite DB + temp uploads; call logs go to tests/reports/e2e_<ts>/api_runs
    (never the real api_runs/ nor teaching_assistant.db)
  * app startup seeding (which would call the model 9x as "seed_grade") runs with a FAKE
    gateway; the real gateway is swapped in only afterwards
  * grades N files of dataset/测试集/批改作业 via POST /api/grader/upload-dataset/{id}
    (sync or background-job API) and compares the model's per-question verdicts with a
    string-normalised comparison of student answer vs the file's reference answer
  * generates 1 lesson plan (via the API if it works with a fake model, otherwise directly
    through ai_client so the real call is not wasted by an API bug)
  * writes tests/reports/e2e_real_model_<ts>.md
Budget: N + 1 real calls (default 4).
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
BACKEND = HERE.parent
REPORTS = HERE / "reports"
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
RUN_DIR = REPORTS / f"e2e_{TS}"
TMP = Path(tempfile.mkdtemp(prefix="aiedu_e2e_"))

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(TMP / 'e2e.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(TMP / "uploads")
os.environ["API_OUTPUT_ROOT"] = str(RUN_DIR / "api_runs")
if os.environ.get("LLM_API_KEY", "").startswith("your_"):
    del os.environ["LLM_API_KEY"]  # we want the real key from config.json here
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.path[:0] = [str(BACKEND), str(HERE)]

import logging  # noqa: E402
logging.disable(logging.WARNING)

import httpx  # noqa: E402


# ------------------------------------------------------------------ reference comparison

def _norm(ans: str) -> str:
    s = ans or ""
    s = re.sub(r"（[^）]*）|\([^)]*[一-鿿][^)]*\)", "", s)   # remarks in parentheses
    s = s.replace("\\(", "").replace("\\)", "").replace("$", "")
    s = re.sub(r"\\left|\\right|\\,|\\;|\\!|\s+", "", s)
    s = s.replace("\\dfrac", "\\frac").replace("^\\circ", "°").replace("^{\\circ}", "°")
    s = re.sub(r"(或|等|即可)$", "", s)
    s = s.rstrip("。.，,")
    return s


def parse_student_answers(student_part: str) -> dict:
    out = {}
    for m in re.finditer(r"^###\s*(\d+)\.(.*?)(?=^###\s*\d+\.|\Z)", student_part, re.S | re.M):
        n = int(m.group(1))
        a = re.search(r"\*\*学生答案\*\*[：:]\s*(.+?)(?=\n---|\Z)", m.group(2), re.S)
        out[n] = a.group(1).strip() if a else ""
    return out


def parse_reference(ref: str) -> dict:
    out = {}
    for m in re.finditer(r"^\s*(\d+)\.\s*(.+?)(?=^\s*\d+\.|\Z)", ref, re.S | re.M):
        out[int(m.group(1))] = m.group(2).strip()
    return out


def baseline_verdict(student: str, ref: str):
    """True/False when the reference makes it clear-cut, None when it needs judgement."""
    if not student or not ref:
        return None
    if "\n" in student.strip() or len(student) > 60 or re.search(r"\(1\)|（1）|学生|正确应|需", ref):
        return None  # multi-part / worked solutions / commentary -> needs a human
    s, r = _norm(student), _norm(ref)
    alts = [_norm(x) for x in re.split(r"或", ref)]
    if s == r or s in alts:
        return True
    if s and r and (s in r or r in s):
        return None
    return False


# ------------------------------------------------------------------ run

async def poll(client, body, timeout=900, kind="grader"):
    from helpers import poll_job
    return await poll_job(client, body, timeout=timeout, kind=kind, interval=1.0)


def read_calls():
    rows = []
    for f in (RUN_DIR / "api_runs").glob("*/api_calls.jsonl"):
        rows += [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows


async def main(args):
    import homework_dataset
    from fakes import FakeGateway, install_gateway, restore_gateway
    import ai_client as ai_mod
    from main import app
    import database
    database.engine.sync_engine.echo = False

    real_gateway = ai_mod.ai_client.gateway
    if not real_gateway.enabled and not args.dry_run:
        sys.exit("real LLM key not configured (config.json llm.api_key / env LLM_API_KEY)")

    items = homework_dataset.list_dataset_homeworks()
    def n_clear_wrong(fid):
        d = homework_dataset.get_dataset_homework(file_id=fid)
        s, r = parse_student_answers(d["student_content"]), parse_reference(d["reference_answer"])
        return sum(1 for n in r if baseline_verdict(s.get(n, ""), r[n]) is False)

    if args.ids:
        ids = [int(x) for x in args.ids.split(",")]
    else:  # prefer files that contain clear-cut wrong answers (more discriminating)
        ids = sorted((i["id"] for i in items), key=lambda f: (-n_clear_wrong(f), f))[: args.n]

    report = {"grading": [], "lessonplan": None, "errors": []}
    fake = FakeGateway()
    prev = install_gateway(fake)  # seed + probe with fake
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://e2e", timeout=1200) as client:
            # probe lesson plan API with fake model (free)
            probe = await client.post("/api/lessonplan/generate", data={"title": "探测", "wait": "true"})
            lesson_api_ok = probe.status_code in (200, 202)
            seed_calls = len(fake.calls)
            if not args.dry_run:
                restore_gateway(prev)  # ---- real model from here on ----
                ai_mod.ai_client.is_debug_mode = False

            for fid in ids:
                detail = homework_dataset.get_dataset_homework(file_id=fid)
                t0 = time.perf_counter()
                r = await client.post(f"/api/grader/upload-dataset/{fid}",
                                      data={"student_name": f"E2E-{fid}", "subject": "数学"})
                body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}
                if r.status_code in (200, 202) and not body.get("grading_result"):
                    body = {**body, **(await poll(client, body))}
                wall = time.perf_counter() - t0
                gr = body.get("grading_result") or body.get("result") or {}
                if isinstance(gr, str):
                    try:
                        gr = json.loads(gr)
                    except Exception:
                        gr = {"raw": gr}
                entry = {"file_id": fid, "filename": detail["filename"], "title": detail["title"],
                         "http": r.status_code, "wall_s": round(wall, 1), "status": body.get("status"),
                         "error": body.get("error_message") or body.get("detail") or gr.get("error"),
                         "ai_score": gr.get("score"), "ai_wrong": gr.get("wrong_count"),
                         "ai_total": gr.get("total_questions"), "questions": []}
                students = parse_student_answers(detail["student_content"])
                refs = parse_reference(detail["reference_answer"])
                ai_q = {}
                for q in gr.get("questions") or []:
                    try:
                        ai_q[int(str(q.get("question_number")).strip("第题. "))] = q
                    except (TypeError, ValueError):
                        pass
                for n in sorted(set(students) | set(refs)):
                    base = baseline_verdict(students.get(n, ""), refs.get(n, ""))
                    aq = ai_q.get(n, {})
                    entry["questions"].append({
                        "n": n, "student": students.get(n, "")[:60], "reference": refs.get(n, "")[:60],
                        "baseline": base, "ai": aq.get("is_correct"),
                    })
                report["grading"].append(entry)
                print(f"graded {fid} {detail['title']}: http={r.status_code} score={entry['ai_score']} "
                      f"wrong={entry['ai_wrong']} in {wall:.0f}s", flush=True)

            if not args.no_lessonplan:
                t0 = time.perf_counter()
                topic = args.topic
                lp = {"topic": topic, "via": None}
                try:
                    if lesson_api_ok:
                        lp["via"] = "api"
                        r = await client.post("/api/lessonplan/generate",
                                              data={"title": topic, "period": "1 课时", "student_level": "中等"})
                        b = r.json()
                        if r.status_code in (200, 202) and b.get("status") == "processing":
                            b = {**b, **(await poll(client, b, kind="lessonplan"))}
                        lp.update(http=r.status_code, content=b.get("content") or "", id=b.get("id"),
                                  error=b.get("detail") or b.get("error_message"))
                    else:
                        lp["via"] = "ai_client (API broken, see FINDINGS F-04)"
                        lp["content"] = await ai_mod.ai_client.generate_lesson_plan(topic=topic)
                except Exception as e:  # noqa: BLE001
                    lp["error"] = f"{type(e).__name__}: {e}"
                lp["wall_s"] = round(time.perf_counter() - t0, 1)
                c = lp.get("content") or ""
                lp["chars"] = len(c)
                lp["sections_found"] = [s for s in ("教学目标", "教学重难点", "教学过程", "板书", "作业", "易错")
                                        if s in c]
                report["lessonplan"] = lp
                print(f"lesson plan via {lp['via']}: {lp['chars']} chars in {lp['wall_s']}s", flush=True)
        try:
            import jobs
            await jobs.wait_all_jobs(timeout=5)
        except ImportError:
            pass

    report["seed_fake_calls"] = seed_calls
    report["calls"] = read_calls()
    path = write_report(report, args)
    print(f"report: {path}")


def write_report(rep, args) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    calls = rep["calls"]
    L = [f"# E2E real-model report ({TS})", ""]
    L.append(f"- model/base_url: {', '.join(sorted({c['model'] for c in calls})) or 'n/a'} @ "
             f"{calls[0]['base_url'] if calls else 'n/a'}")
    L.append(f"- real calls: {len(calls)} (success {sum(c['success'] for c in calls)}); "
             f"seed/probe calls served by fake gateway: {rep['seed_fake_calls']}")
    tok = sum(c["usage"].get("total_tokens", 0) for c in calls)
    L.append(f"- tokens: total {tok}, prompt {sum(c['usage'].get('prompt_tokens', 0) for c in calls)}, "
             f"completion {sum(c['usage'].get('completion_tokens', 0) for c in calls)}, "
             f"reasoning {sum(c['usage'].get('reasoning_tokens', 0) for c in calls)}")
    L.append(f"- call logs: `{(RUN_DIR / 'api_runs').relative_to(BACKEND.parent)}`")
    L += ["", "## Calls", "", "| feature | model | ok | latency s | prompt | completion | total | error |",
          "|---|---|---|---|---|---|---|---|"]
    for c in calls:
        u = c["usage"]
        err = (c.get("error") or {}).get("message", "")[:80].replace("|", "/") if c.get("error") else ""
        L.append(f"| {c['feature']} | {c['model']} | {c['success']} | {c['elapsed_seconds']:.1f} | "
                 f"{u.get('prompt_tokens')} | {u.get('completion_tokens')} | {u.get('total_tokens')} | {err} |")

    L += ["", "## Grading vs reference answers", ""]
    agree_all = clear_all = 0
    for g in rep["grading"]:
        qs = g["questions"]
        clear = [q for q in qs if q["baseline"] is not None and q["ai"] is not None]
        agree = [q for q in clear if bool(q["ai"]) == q["baseline"]]
        agree_all += len(agree)
        clear_all += len(clear)
        base_wrong_min = sum(1 for q in qs if q["baseline"] is False)
        base_unclear = sum(1 for q in qs if q["baseline"] is None)
        L.append(f"### {g['title']} (`{g['filename']}`, dataset id {g['file_id']})")
        L.append("")
        L.append(f"- HTTP {g['http']}, status {g['status']}, wall {g['wall_s']} s"
                 + (f", error: {g['error']}" if g['error'] else ""))
        L.append(f"- AI: score {g['ai_score']}, wrong {g['ai_wrong']} / {g['ai_total']} questions")
        L.append(f"- reference baseline: wrong >= {base_wrong_min}, <= {base_wrong_min + base_unclear} "
                 f"({base_unclear} questions need human judgement)")
        L.append(f"- per-question agreement on clear-cut questions: {len(agree)}/{len(clear)}")
        L.append("")
        L.append("| Q | student | reference | baseline | AI |")
        L.append("|---|---|---|---|---|")
        for q in qs:
            fmt = {True: "correct", False: "wrong", None: "?"}
            L.append(f"| {q['n']} | {q['student'].replace('|', '/')} | {q['reference'].replace('|', '/')} | "
                     f"{fmt[q['baseline']]} | {fmt.get(q['ai'], str(q['ai']))} |")
        L.append("")
    L.append(f"**Overall agreement on clear-cut questions: {agree_all}/{clear_all}"
             + (f" ({agree_all / clear_all * 100:.0f}%)" if clear_all else "") + "**")

    lp = rep["lessonplan"]
    if lp:
        L += ["", "## Lesson plan", "",
              f"- topic: {lp['topic']}; via {lp['via']}; http {lp.get('http', '-')}; wall {lp['wall_s']} s",
              f"- length: {lp['chars']} chars; sections found: {', '.join(lp['sections_found']) or 'none'}"]
        if lp.get("error"):
            L.append(f"- error: {lp['error']}")
        if lp.get("content"):
            L += ["", "<details><summary>first 1500 chars</summary>", "", lp["content"][:1500], "", "</details>"]
    path = REPORTS / f"e2e_real_model_{TS}.md"
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    (RUN_DIR / "raw_report.json").write_text(
        json.dumps({k: v for k, v in rep.items() if k != "calls"}, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=3, help="number of dataset files to grade")
    ap.add_argument("--ids", default="", help="comma separated dataset ids (overrides -n)")
    ap.add_argument("--no-lessonplan", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="keep the fake gateway (pipeline check, 0 real calls)")
    ap.add_argument("--topic", default="导数的几何意义与切线方程")
    asyncio.run(main(ap.parse_args()))
