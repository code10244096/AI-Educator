"""Online homework grading (background-job API, see backend/API.md): file types,
reference answers, assignments, persistence, notebook sync, job lifecycle, errors."""
import io
import json
import uuid

import pytest

from conftest import DATASET_HW_DIR, GAOKAO_SCAN_DIR
from fakes import DEFAULT_OCR, FAKE_WRONG_MARKER, prompt_text
from helpers import grade, grading_payload, poll_job, submission_id_of

UPLOAD = "/api/grader/upload"
_used_submissions: set = set()


def _dataset_md_files():
    return sorted(DATASET_HW_DIR.glob("*.md"))


def _make_docx(text_lines) -> bytes:
    from docx import Document
    doc = Document()
    for line in text_lines:
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_pdf(text: str) -> bytes:
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 720, text)
    c.save()
    return buf.getvalue()


def _grade_calls(fake):
    return [c for c in fake.calls if c["feature"] == "grade"]


async def pending_submission(client, class_slug="class1", homework_id=10):
    r = await client.get(f"/api/class/{class_slug}/homework/{homework_id}/submissions")
    assert r.status_code == 200, r.text
    for s in r.json()["items"]:
        if s.get("submission_id") and s["gradingStatus"] == "待批改" and s["submission_id"] not in _used_submissions:
            _used_submissions.add(s["submission_id"])
            return s
    pytest.skip("no pending submission left in seed data")


async def assignment_id_for(client, class_slug="class1", homework_id=10) -> int:
    r = await client.get(f"/api/class/{class_slug}/homework/{homework_id}")
    assert r.status_code == 200, r.text
    return r.json()["assignment_id"]


async def _notebook(client, **params):
    r = await client.get("/api/notebook/list", params={"limit": 100, **params})
    assert r.status_code == 200
    items = r.json()
    return items.get("items", items) if isinstance(items, dict) else items


# ---------------------------------------------------------------- file types

@pytest.mark.parametrize("path", _dataset_md_files(), ids=lambda p: p.name)
async def test_upload_dataset_md_with_reference(client, fake_ai, path):
    content = path.read_bytes()
    ref = content.decode("utf-8").split("## 参考答案", 1)[1]
    r = await grade(client, UPLOAD, files={"files": (path.name, content, "text/markdown")},
                    data={"reference_answer": ref, "subject": "数学"})
    body = r.json()
    assert grading_payload(body)["score"] == fake_ai.grade_result["score"]
    assert "ocr" not in fake_ai.features(), "text files must not be OCR'd"
    assert len(_grade_calls(fake_ai)) == 1
    p = prompt_text(_grade_calls(fake_ai)[0])
    assert "学生答案" in p and ref.strip()[:20] in p, "student text + reference must reach the model"


async def test_upload_txt_without_reference(client, fake_ai):
    r = await grade(client, UPLOAD, files={"files": ("hw.txt", "### 1. 填空题\n1+1=?\n**学生答案**：3\n".encode(), "text/plain")})
    assert submission_id_of(r.json())
    p = prompt_text(_grade_calls(fake_ai)[0])
    assert "1+1=?" in p
    assert "参考答案：" not in p


async def test_upload_jpg_goes_through_ocr(client, fake_ai):
    jpg = GAOKAO_SCAN_DIR / "20240608-3.jpg"
    r = await grade(client, UPLOAD, files={"files": (jpg.name, jpg.read_bytes(), "image/jpeg")})
    body = r.json()
    assert fake_ai.features() == ["ocr", "grade"]
    assert "[image_url:data:image/jpeg;base64," in prompt_text(fake_ai.calls[0])
    assert "1+1=?" in (body.get("ocr_result") or "")
    assert "1+1=?" in prompt_text(_grade_calls(fake_ai)[0]), "OCR text must be fed to grading"


async def test_upload_multiple_images_ocr_each(client, fake_ai):
    jpgs = [GAOKAO_SCAN_DIR / "20240608-1.jpg", GAOKAO_SCAN_DIR / "20240608-3.jpg"]
    files = [("files", (p.name, p.read_bytes(), "image/jpeg")) for p in jpgs]
    r = await grade(client, UPLOAD, files=files)
    assert fake_ai.features().count("ocr") == 2
    assert r.json().get("image_count") == 2


async def test_upload_multiple_files_in_one_submission(client, fake_ai):
    files = [
        ("files", ("a.md", "### 1. A题\n**学生答案**：MULTI_A".encode(), "text/markdown")),
        ("files", ("b.txt", "### 2. B题\n**学生答案**：MULTI_B".encode(), "text/plain")),
    ]
    r = await grade(client, UPLOAD, files=files)
    p = prompt_text(_grade_calls(fake_ai)[0])
    assert "MULTI_A" in p and "MULTI_B" in p
    assert r.json().get("file_names") == ["a.md", "b.txt"]


async def test_upload_generated_docx_extracts_text_locally(client, fake_ai):
    marker = f"DOCX_{uuid.uuid4().hex[:8]}"
    data = _make_docx(["### 1. 填空题", f"题目 {marker}", "**学生答案**：2"])
    await grade(client, UPLOAD, files={"files": ("hw.docx", data,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert "ocr" not in fake_ai.features(), "docx should be parsed locally (python-docx)"
    assert marker in prompt_text(_grade_calls(fake_ai)[0])


def _pdf_lib_available():
    for mod in ("fitz", "pypdf"):
        try:
            __import__(mod)
            return True
        except ImportError:
            pass
    return False


PDF_XFAIL = pytest.mark.xfail(not _pdf_lib_available(), strict=False,
                              reason="FINDING F-05: neither PyMuPDF nor pypdf is installed/listed in "
                                     "requirements.txt -> every PDF upload fails ('服务器未安装 PDF 解析组件')")


@PDF_XFAIL
async def test_upload_dataset_pdf(client, fake_ai):
    pdf = GAOKAO_SCAN_DIR / "20240608-1.pdf"
    r = await grade(client, UPLOAD, files={"files": (pdf.name, pdf.read_bytes(), "application/pdf")})
    assert r.json()["status"] == "completed"


@PDF_XFAIL
async def test_generated_pdf_text_is_extracted_without_sending_pdf_as_image(client, fake_ai):
    marker = f"PDFMARK{uuid.uuid4().hex[:8]}"
    await grade(client, UPLOAD, files={"files": ("hw.pdf", _make_pdf(f"Q1 {marker} answer 2"), "application/pdf")})
    for c in fake_ai.calls:
        assert "data:application/pdf" not in prompt_text(c)
    assert marker in prompt_text(_grade_calls(fake_ai)[0])


async def test_pdf_without_parser_fails_cleanly(client, fake_ai):
    """Whatever the PDF support, a PDF must end completed or failed with a readable message."""
    r = await grade(client, UPLOAD, files={"files": ("hw.pdf", _make_pdf("Q1 x"), "application/pdf")},
                    expect_ok=False)
    body = r.json()
    assert body["status"] in ("completed", "failed")
    if body["status"] == "failed":
        assert body["error_message"]
        assert not _grade_calls(fake_ai), "no grading call should be spent on an unreadable file"


# ---------------------------------------------------------------- job lifecycle

async def test_job_status_transitions(client, fake_ai):
    fake_ai.delay = 0.3
    r = await client.post(UPLOAD, files={"files": ("j.md", DEFAULT_OCR.encode(), "text/markdown")},
                          data={"student_name": "任务状态学生"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "processing"
    assert body["grading_status"] == "批改中"
    assert body["grading_result"] in (None, {})
    sid = body["submission_id"]
    mid = (await client.get(f"/api/grader/{sid}")).json()
    assert mid["status"] == "processing" and mid["progress_stage"]
    final = await poll_job(client, body, timeout=10)
    states = [s for s, _ in final["_history"]]
    assert states[0] == "processing" and states[-1] == "completed"
    stages = [st for _, st in final["_history"]]
    assert "批改中" in stages and stages[-1] == "批改完成"
    assert final["grading_status"] == "已批改" and final["finished_at"]
    assert final["error_message"] is None


async def test_wait_true_is_synchronous(client, fake_ai):
    r = await client.post(UPLOAD, files={"files": ("w.md", DEFAULT_OCR.encode(), "text/markdown")},
                          data={"wait": "true"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["grading_result"]["score"] == fake_ai.grade_result["score"]


async def test_regrade_while_processing_conflicts(client, fake_ai):
    fake_ai.delay = 0.5
    r = await client.post(UPLOAD, files={"files": ("c.md", DEFAULT_OCR.encode(), "text/markdown")})
    sid = r.json()["submission_id"]
    r2 = await client.post(UPLOAD, files={"files": ("c.md", DEFAULT_OCR.encode(), "text/markdown")},
                           data={"submission_id": str(sid)})
    assert r2.status_code == 409
    assert (await client.delete(f"/api/grader/{sid}")).status_code == 409
    await poll_job(client, r.json(), timeout=10)


async def test_submissions_list_and_file_download(client, fake_ai):
    name = f"列表学生{uuid.uuid4().hex[:4]}"
    content = f"### 1. 题\n**学生答案**：{name}".encode()
    r = await grade(client, UPLOAD, files={"files": ("orig name.md", content, "text/markdown")},
                    data={"student_name": name})
    sid = submission_id_of(r.json())
    lst = await client.get("/api/grader/submissions", params={"student_name": name})
    assert lst.status_code == 200
    items = lst.json()["items"]
    assert [i["submission_id"] for i in items] == [sid]
    assert items[0]["file_names"] == ["orig name.md"]
    f = await client.get(f"/api/grader/{sid}/files/0")
    assert f.status_code == 200 and f.content == content
    assert (await client.get(f"/api/grader/{sid}/files/5")).status_code == 404
    seed_default = (await client.get("/api/grader/submissions", params={"limit": 200})).json()
    assert all(i["status"] != "pending" for i in seed_default["items"]), "seed rows hidden by default"


async def test_retry_and_delete(client, fake_ai):
    fake_ai.fail_features = {"grade"}
    r = await client.post(UPLOAD, files={"files": ("r.md", DEFAULT_OCR.encode(), "text/markdown")},
                          data={"student_name": "重试学生"})
    final = await poll_job(client, r.json())
    assert final["status"] == "failed"
    sid = final["submission_id"]
    fake_ai.fail_features = set()
    rr = await client.post(f"/api/grader/{sid}/retry")
    assert rr.status_code == 200
    final = await poll_job(client, rr.json())
    assert final["status"] == "completed" and final["score"] == fake_ai.grade_result["score"]
    assert len(await _notebook(client, student_name="重试学生")) == 1
    d = await client.delete(f"/api/grader/{sid}")
    assert d.status_code == 200
    assert (await client.get(f"/api/grader/{sid}")).status_code == 404
    assert await _notebook(client, student_name="重试学生") == [], "synced wrong questions removed with submission"
    assert (await client.post("/api/grader/99999999/retry")).status_code == 404


# ---------------------------------------------------------------- assignments / persistence

async def test_grade_with_assignment_uses_assignment_reference(client, fake_ai):
    aid = await assignment_id_for(client, "class1", 10)
    r = await grade(client, UPLOAD, files={"files": ("hw.md", DEFAULT_OCR.encode(), "text/markdown")},
                    data={"assignment_id": str(aid), "student_name": "测试学生A"})
    assert r.json().get("assignment_id") == aid
    assert "参考答案" in prompt_text(_grade_calls(fake_ai)[0]), \
        "assignment's stored reference answer should be used when none uploaded"


async def test_grade_unknown_assignment_404(client, fake_ai):
    r = await client.post(UPLOAD, files={"files": ("hw.md", DEFAULT_OCR.encode(), "text/markdown")},
                          data={"assignment_id": "987654"})
    assert r.status_code == 404
    assert fake_ai.calls == []


async def test_grade_existing_submission_updates_class_view(client, fake_ai):
    pending = await pending_submission(client)
    sid = pending["submission_id"]
    aid = await assignment_id_for(client)
    r = await grade(client, UPLOAD, files={"files": ("hw.md", DEFAULT_OCR.encode(), "text/markdown")},
                    data={"assignment_id": str(aid), "submission_id": str(sid)})
    assert submission_id_of(r.json()) == sid

    gb = (await client.get(f"/api/grader/{sid}")).json()
    assert gb["score"] == fake_ai.grade_result["score"]
    assert gb["wrong_count"] == fake_ai.grade_result["wrong_count"]
    assert gb["grading_status"] == "已批改"
    assert gb["grading_result"]["questions"][1]["is_correct"] is False

    lst = (await client.get("/api/class/class1/homework/10/submissions")).json()["items"]
    row = next(s for s in lst if s["submission_id"] == sid)
    assert row["gradingStatus"] == "已批改" and row["score"] == fake_ai.grade_result["score"]


async def test_result_persisted_and_retrievable(client, fake_ai):
    r = await grade(client, UPLOAD, files={"files": ("p.md", DEFAULT_OCR.encode(), "text/markdown")},
                    data={"student_name": "持久化学生"})
    sid = submission_id_of(r.json())
    body = (await client.get(f"/api/grader/{sid}")).json()
    assert body["id"] == sid
    assert body["student_name"] == "持久化学生"
    assert body["status"] == "completed"
    assert "1+1=?" in (body.get("ocr_result") or "")
    assert body["grading_result"]["total_questions"] == 3


async def test_get_missing_submission_404(client):
    assert (await client.get("/api/grader/99999999")).status_code == 404


async def test_wrong_questions_synced_to_notebook(client, fake_ai):
    student = f"错题同步{uuid.uuid4().hex[:6]}"
    await grade(client, UPLOAD, files={"files": ("w.md", DEFAULT_OCR.encode(), "text/markdown")},
                data={"student_name": student})
    items = await _notebook(client, student_name=student)
    assert len(items) == fake_ai.grade_result["wrong_count"]
    assert FAKE_WRONG_MARKER in items[0]["question_text"]
    assert items[0]["correct_answer"] == "4" and items[0]["user_answer"] == "5"
    assert items[0].get("source", "grading") == "grading"


async def test_grading_existing_submission_syncs_notebook(client, fake_ai):
    pending = await pending_submission(client)
    sid, name = pending["submission_id"], pending["name"]
    await grade(client, UPLOAD, files={"files": ("w.md", DEFAULT_OCR.encode(), "text/markdown")},
                data={"submission_id": str(sid)})
    items = [i for i in await _notebook(client, student_name=name) if i.get("submission_id") == sid]
    assert len(items) == fake_ai.grade_result["wrong_count"]


async def test_regrading_same_submission_does_not_duplicate_notebook(client, fake_ai):
    pending = await pending_submission(client)
    sid, name = pending["submission_id"], pending["name"]
    for _ in range(2):
        await grade(client, UPLOAD, files={"files": ("w.md", DEFAULT_OCR.encode(), "text/markdown")},
                    data={"submission_id": str(sid), "student_name": name})
    items = [i for i in await _notebook(client, student_name=name) if i.get("submission_id") == sid]
    assert len(items) == fake_ai.grade_result["wrong_count"]


# ---------------------------------------------------------------- error paths

async def test_ai_failure_marks_submission_failed(client, fake_ai):
    fake_ai.fail_features = {"grade"}
    r = await client.post(UPLOAD, files={"files": ("f.md", DEFAULT_OCR.encode(), "text/markdown")})
    assert r.status_code == 200
    final = await poll_job(client, r.json())
    assert final["status"] == "failed"
    assert "fake upstream failure" in (final["error_message"] or "")
    assert final["grading_status"] == "待批改"
    assert (await client.get("/health")).status_code == 200


async def test_ai_failure_wait_true_returns_502_with_message(client, fake_ai):
    fake_ai.fail_features = {"grade"}
    r = await client.post(UPLOAD, files={"files": ("f.md", DEFAULT_OCR.encode(), "text/markdown")},
                          data={"wait": "true"})
    assert r.status_code == 502
    assert "fake upstream failure" in r.json()["detail"]


async def test_ai_failure_on_existing_submission_marks_it_failed(client, fake_ai):
    pending = await pending_submission(client)
    sid = pending["submission_id"]
    fake_ai.fail_features = {"grade"}
    r = await client.post(UPLOAD, files={"files": ("f.md", DEFAULT_OCR.encode(), "text/markdown")},
                          data={"submission_id": str(sid)})
    final = await poll_job(client, r.json())
    assert final["status"] == "failed" and final["error_message"]
    row = next(s for s in (await client.get("/api/class/class1/homework/10/submissions")).json()["items"]
               if s["submission_id"] == sid)
    assert row["gradingStatus"] != "已批改"


async def test_unparseable_model_output_not_saved_as_completed(client, fake_ai):
    fake_ai.responses["grade"] = "抱歉，我无法批改。"
    r = await grade(client, UPLOAD, files={"files": ("f.md", DEFAULT_OCR.encode(), "text/markdown")},
                    expect_ok=False)
    if r.status_code >= 400:
        return
    assert r.json()["status"] == "failed"


async def test_ocr_failure_on_single_image_fails_job(client, fake_ai):
    fake_ai.fail_features = {"ocr"}
    jpg = GAOKAO_SCAN_DIR / "20240608-3.jpg"
    r = await grade(client, UPLOAD, files={"files": (jpg.name, jpg.read_bytes(), "image/jpeg")}, expect_ok=False)
    body = r.json()
    assert body["status"] == "failed", "OCR failure must not produce a 'completed' grading"
    assert not _grade_calls(fake_ai)


async def test_ai_failure_does_not_leak_background_tasks(client, fake_ai):
    try:
        import jobs
    except ImportError:
        pytest.skip("no jobs module")
    fake_ai.fail_features = {"*"}
    r = await client.post(UPLOAD, files={"files": ("f.md", DEFAULT_OCR.encode(), "text/markdown")})
    await poll_job(client, r.json())
    await jobs.wait_all_jobs(timeout=5)
    assert jobs.running_job_count() == 0


async def test_concurrent_uploads_all_complete(client, fake_ai):
    """Several background jobs writing to SQLite at once must not hit 'database is locked'."""
    import asyncio
    fake_ai.delay = 0.1
    jpg = (GAOKAO_SCAN_DIR / "20240608-3.jpg").read_bytes()
    posts = await asyncio.gather(*[
        client.post(UPLOAD, files=[("files", (f"a{i}.jpg", jpg, "image/jpeg")),
                                   ("files", (f"b{i}.md", DEFAULT_OCR.encode(), "text/markdown"))],
                    data={"student_name": f"并发学生{i}"})
        for i in range(8)
    ])
    assert all(p.status_code == 200 for p in posts), [p.text[:200] for p in posts if p.status_code != 200]
    finals = await asyncio.gather(*[poll_job(client, p.json(), timeout=30) for p in posts])
    assert [f["status"] for f in finals] == ["completed"] * 8, [f.get("error_message") for f in finals]
    assert fake_ai.features().count("ocr") == 8 and fake_ai.features().count("grade") == 8
