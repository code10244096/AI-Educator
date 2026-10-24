"""按账号留存生成内容：写入、列出，以及拒绝路径穿越。"""
import pytest

import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from user_archive import account_zip, count_by_day, list_accounts, list_records, read_record, save_record, zip_by_days


def test_save_lists_and_reads_by_account():
    save_record("13900005555", "老师5555", "lessonplan", 7, "导数", "# 教案正文", {"period": "1"})
    save_record("13900005555", "老师5555", "grade", 3, "张三 · 数学", {"score": 80, "ocr_result": "1+1"})

    accounts = list_accounts()
    row = next(item for item in accounts if item["username"] == "13900005555")
    assert row["counts"]["lessonplan"] == 1
    assert row["counts"]["grade"] == 1

    names = {item["name"] for item in list_records("13900005555")}
    assert names == {"lessonplan-7.json", "grade-3.json"}
    body = read_record("13900005555", "lessonplan", "lessonplan-7.json")
    assert body["body"] == "# 教案正文"
    assert body["title"] == "导数"


def test_account_zip_contains_only_that_folder():
    save_record("13900005555", "老师5555", "lessonplan", 7, "导数", "# 教案正文")
    save_record("13900005555", "老师5555", "grade", 3, "张三 · 数学", {"score": 80})
    payload = account_zip("13900005555")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        lesson_md = archive.read("lessonplan/lessonplan-7.md").decode("utf-8")
    assert "教案正文" in lesson_md
    assert names == {
        "lessonplan/lessonplan-7.json",
        "lessonplan/lessonplan-7.md",
        "grade/grade-3.json",
        "grade/grade-3.md",
    }


def test_zip_by_days_groups_files_under_that_date(monkeypatch, tmp_path):
    from config import settings
    isolated = Path(tmp_path) / "records"
    monkeypatch.setattr(settings, "USER_RECORDS_DIR", str(isolated))
    save_record("13900005555", "老师5555", "lessonplan", 7, "导数", "# 教案正文")
    save_record("13800001111", "另一位", "grade", 3, "李四", {"score": 60})
    day = datetime.now().strftime("%Y-%m-%d")
    rows = {item["day"]: item for item in count_by_day()}
    assert rows[day]["files"] == 2
    assert rows[day]["lessonplan"] == 1
    assert rows[day]["grade"] == 1

    payload = zip_by_days([day])
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = set(archive.namelist())
        lesson_md = archive.read(f"{day}/13900005555/lessonplan/lessonplan-7.md").decode("utf-8")
    assert "教案正文" in lesson_md
    assert names == {
        f"{day}/13900005555/lessonplan/lessonplan-7.json",
        f"{day}/13900005555/lessonplan/lessonplan-7.md",
        f"{day}/13800001111/grade/grade-3.json",
        f"{day}/13800001111/grade/grade-3.md",
    }
    with pytest.raises(FileNotFoundError):
        zip_by_days(["1999-01-01"])
    with pytest.raises(ValueError):
        zip_by_days(["not-a-day"])

    save_record(
        "13900005555", "老师5555", "variant", 9, "旧题", {"variants": []},
        saved_at=datetime(2020, 5, 1, 8, 0, tzinfo=timezone.utc),
    )
    rows = {item["day"]: item for item in count_by_day()}
    assert rows["2020-05-01"]["variant"] == 1


def test_rejects_path_escape():
    with pytest.raises((ValueError, FileNotFoundError)):
        read_record("13900005555", "lessonplan", "../grade-3.json")
    with pytest.raises((ValueError, FileNotFoundError)):
        read_record("13900005555", "grade", "lessonplan-7.json")
    with pytest.raises((ValueError, FileNotFoundError)):
        read_record("..", "lessonplan", "lessonplan-7.json")
