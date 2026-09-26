"""dataset/测试集/批改作业 parsing and the dataset grading endpoint (mock mode)."""
import re

import pytest

import homework_dataset
from conftest import DATASET_HW_DIR
from helpers import grade, grading_payload, submission_id_of

MD_FILES = sorted(p.name for p in DATASET_HW_DIR.glob("*.md"))


def test_dataset_dir_points_at_repo_dataset():
    assert MD_FILES, "no dataset homework files found"
    assert len(homework_dataset.list_dataset_homeworks()) == len(MD_FILES)


@pytest.mark.parametrize("filename", MD_FILES)
def test_every_dataset_file_parses(filename):
    parsed = homework_dataset.parse_homework_file(str(DATASET_HW_DIR / filename))
    assert parsed["title"].startswith("高考数学作业集")
    assert parsed["question_count"] >= 5
    assert "学生答案" in parsed["student_content"]
    assert parsed["reference_answer"], "reference answer section missing"
    # every numbered question has a numbered reference answer line
    ref_numbers = {int(n) for n in re.findall(r"^\s*(\d+)\.", parsed["reference_answer"], re.MULTILINE)}
    for n in range(1, parsed["question_count"] + 1):
        assert n in ref_numbers, f"reference answer for Q{n} missing"


def test_list_ids_are_stable_and_detail_roundtrips():
    items = homework_dataset.list_dataset_homeworks()
    assert [i["id"] for i in items] == list(range(1, len(items) + 1))
    for item in items:
        d = homework_dataset.get_dataset_homework(file_id=item["id"])
        assert d["filename"] == item["filename"]
        assert homework_dataset.get_dataset_homework(filename=item["filename"])["id"] == item["id"]
    assert homework_dataset.get_dataset_homework(file_id=0) is None
    assert homework_dataset.get_dataset_homework(file_id=len(items) + 1) is None


def test_dataset_filename_lookup_rejects_traversal():
    assert homework_dataset.get_dataset_homework(filename="../../../backend/config.json") is None


async def test_dataset_list_endpoint(client):
    r = await client.get("/api/homework/dataset")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == len(MD_FILES)
    assert {i["filename"] for i in body["items"]} == set(MD_FILES)


async def test_dataset_detail_endpoint(client):
    r = await client.get("/api/homework/dataset/1")
    assert r.status_code == 200
    assert r.json()["reference_answer"]
    assert (await client.get("/api/homework/dataset/999")).status_code == 404


@pytest.mark.parametrize("file_id", range(1, len(MD_FILES) + 1))
async def test_upload_dataset_grades_each_file_mock_mode(client, file_id):
    """Default (mock) mode: deterministic grading of every dataset file."""
    r = await grade(client, f"/api/grader/upload-dataset/{file_id}", data={"subject": "数学"})
    body = r.json()
    detail = homework_dataset.get_dataset_homework(file_id=file_id)
    assert body.get("dataset_filename", detail["filename"]) == detail["filename"]
    gr = grading_payload(body)
    assert gr["total_questions"] == detail["question_count"]
    assert 0 <= gr["score"] <= 100
    sid = submission_id_of(body)
    g = (await client.get(f"/api/grader/{sid}")).json()
    assert g["score"] == gr["score"]


async def test_upload_dataset_with_fake_model(client, fake_ai):
    r = await grade(client, "/api/grader/upload-dataset/1", data={"student_name": "数据集学生"})
    gr = grading_payload(r.json())
    assert gr["score"] == fake_ai.grade_result["score"]
    call = [c for c in fake_ai.calls if c["feature"] == "grade"][0]
    text = call["messages"][0]["content"]
    ref = homework_dataset.get_dataset_homework(file_id=1)["reference_answer"]
    assert ref[:30] in text


async def test_upload_dataset_linked_to_class_homework(client):
    """class_slug + homework_id resolves the assignment; submission lands in class view."""
    r = await grade(client, "/api/grader/upload-dataset/10",
                    data={"class_slug": "class1", "homework_id": "10", "student_name": "数据集班级学生"})
    body = r.json()
    assert body.get("assignment_id")


async def test_upload_dataset_unknown_id(client):
    r = await client.post("/api/grader/upload-dataset/999", data={})
    assert r.status_code == 404


@pytest.mark.xfail(strict=False, reason="FINDING F-12: seeded class1 homework '高考数学作业集N' is linked to the "
                   "N-th file in sorted order, whose own title is a different 作业集 number")
async def test_seeded_homework_title_matches_dataset_file(client):
    items = (await client.get("/api/class/class1/homework")).json()["items"]
    mismatches = []
    for hw in items:
        if hw.get("datasetFileId"):
            d = homework_dataset.get_dataset_homework(file_id=hw["datasetFileId"])
            if d["title"] != hw["title"]:
                mismatches.append((hw["title"], d["title"]))
    assert not mismatches, mismatches
