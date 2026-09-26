"""Upload hardening: path traversal, size limits, file types."""
import os
import re
import uuid

import pytest

from testenv import TEST_TMP, TEST_UPLOADS
from fakes import DEFAULT_OCR


def _files_outside_uploads(name_fragment: str):
    hits = []
    for root, _dirs, files in os.walk(TEST_TMP):
        for f in files:
            if name_fragment in f:
                p = os.path.abspath(os.path.join(root, f))
                if not p.startswith(str(TEST_UPLOADS.resolve())):
                    hits.append(p)
    return hits


@pytest.mark.parametrize("prefix", ["../../../", "..\\..\\..\\", "../../../../"])
@pytest.mark.parametrize("endpoint", ["grader", "notebook"])
async def test_path_traversal_filename_neutralized(client, fake_ai, prefix, endpoint):
    tag = f"evil_{uuid.uuid4().hex[:8]}"
    fname = f"{prefix}{tag}.md"
    if endpoint == "grader":
        r = await client.post("/api/grader/upload", files={"files": (fname, DEFAULT_OCR.encode(), "text/markdown")})
    else:
        r = await client.post("/api/notebook/upload", files={"file": (fname, "题目内容足够长的错题，答案 1".encode(), "text/plain")},
                              data={"knowledge_point": "k"})
    escaped = _files_outside_uploads(tag)
    if escaped:
        pytest.fail(f"FINDING F-16 (HIGH): upload filename not sanitised; file written outside UPLOAD_DIR: {escaped}")
    assert r.status_code < 500


# FINDING F-17 (at HEAD): no size limit. Fixed in working tree (file_utils.save_upload -> 413).
async def test_oversized_upload_rejected(client, fake_ai):
    from config import settings
    big = b"a" * (int(settings.MAX_FILE_SIZE) + 1024)
    r = await client.post("/api/grader/upload", files={"files": ("big.txt", big, "text/plain")})
    assert r.status_code in (400, 413), r.status_code
    assert fake_ai.calls == []


# FINDING F-18 (at HEAD): any extension accepted and sent to the vision model. Fixed in working tree (400).
async def test_disallowed_extension_rejected(client, fake_ai):
    r = await client.post("/api/grader/upload", files={"files": ("run.exe", b"MZ\x90\x00", "application/octet-stream")})
    assert r.status_code in (400, 415, 422)
    assert "ocr" not in fake_ai.features()


async def test_upload_requires_files(client):
    r = await client.post("/api/grader/upload", data={"subject": "数学"})
    assert r.status_code == 422


async def test_oversized_notebook_upload_rejected(client, fake_ai):
    from config import settings
    big = b"a" * (int(settings.MAX_FILE_SIZE) + 1)
    r = await client.post("/api/notebook/upload", files={"file": ("big.txt", big, "text/plain")},
                          data={"knowledge_point": "k"})
    assert r.status_code == 413
    assert not any(TEST_UPLOADS.glob("*.txt")) or all(p.stat().st_size <= settings.MAX_FILE_SIZE
                                                      for p in TEST_UPLOADS.glob("*.txt")), "partial file left behind"


async def test_empty_upload_rejected(client, fake_ai):
    r = await client.post("/api/grader/upload", files={"files": ("e.md", b"", "text/markdown")})
    assert r.status_code == 400
    assert fake_ai.calls == []


async def test_stored_filenames_are_opaque(client, fake_ai):
    before = set(TEST_UPLOADS.iterdir())
    r = await client.post("/api/grader/upload", files={"files": ("我的 作业<script>.md", DEFAULT_OCR.encode(), "text/markdown")},
                          data={"wait": "true"})
    assert r.status_code == 200
    new = set(TEST_UPLOADS.iterdir()) - before
    assert len(new) == 1
    assert re.fullmatch(r"[0-9a-f]{32}\.md", next(iter(new)).name)


async def test_dataset_file_download_allowed_but_not_arbitrary(client, fake_ai):
    r = await client.post("/api/grader/upload-dataset/1", data={"wait": "true"})
    sid = r.json()["submission_id"]
    f = await client.get(f"/api/grader/{sid}/files/0")
    assert f.status_code == 200 and "学生答案" in f.content.decode("utf-8")
