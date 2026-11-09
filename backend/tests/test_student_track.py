"""身份选择页埋点：按天计数 student/teacher 点击，管理端可见。"""
from student_track import reset_for_tests, stats, track


def test_track_counts_by_day_and_role(tmp_path, monkeypatch):
    monkeypatch.setattr("student_track._path", lambda: tmp_path / "visits.json")
    reset_for_tests()
    track("student")
    track("student")
    track("teacher")
    data = stats()
    assert data["today"]["student"] == 2
    assert data["today"]["teacher"] == 1
    assert len(data["days"]) == 1


def test_invalid_role_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr("student_track._path", lambda: tmp_path / "visits.json")
    reset_for_tests()
    track("hacker")
    track("")
    assert stats()["today"] == {**stats()["today"], "student": 0, "teacher": 0}


def test_persistence_across_reload(tmp_path, monkeypatch):
    import student_track
    path = tmp_path / "visits.json"
    monkeypatch.setattr("student_track._path", lambda: path)
    reset_for_tests()
    track("student")
    student_track._counts = {}  # 模拟进程重启：内存清空、文件保留
    track("teacher")  # 触发加载，应读回之前的 student=1
    data = stats()
    assert data["today"]["student"] == 1
    assert data["today"]["teacher"] == 1


async def test_track_role_endpoint(client, tmp_path, monkeypatch):
    monkeypatch.setattr("student_track._path", lambda: tmp_path / "visits.json")
    reset_for_tests()
    r = await client.post("/api/track/role", json={"role": "student"})
    assert r.status_code == 200
    r = await client.post("/api/track/role", json={"role": "Student"})
    assert r.status_code == 200  # 大小写不敏感
    r = await client.post("/api/track/role", json={"role": "admin"})
    assert r.status_code == 422
    data = stats()
    assert data["today"]["student"] == 2
