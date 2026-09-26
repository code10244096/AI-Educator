"""第⑥组 前端信息架构：R1-006 常驻导航 + 工作台；R1-004 下线假功能。
后端部分（/api/dashboard、/api/tasks/jobs）为接口用例；页面部分为静态检查 + 浏览器用例（B-006-*、B-004-*）。
"""
import json
import re

import pytest

from qa_helpers import (FRONTEND_SRC, REPO, add_member, class_key, create_class, create_homework, drain_jobs,
                        grep_frontend, hw_key, items_of, require_route, strip_js_comments, uniq, upload,
                        wait_submission)

pytestmark = pytest.mark.xfail(reason="待开发：第⑥组 信息架构（R1-006、R1-004）", run=False)

Q = lambda n, ok: {"question_number": n, "question_text": f"第{n}题", "student_answer": "a",  # noqa: E731
                   "correct_answer": "a" if ok else "b", "is_correct": ok, "explanation": ""}


def _src(name: str) -> str:
    hits = [p for p in FRONTEND_SRC.rglob(name)]
    assert hits, f"找不到 {name}"
    return strip_js_comments(hits[0].read_text(encoding="utf-8"))


def _num(d, *keys):
    """Find the first numeric value whose (nested) key path contains all given fragments."""
    found = []

    def walk(x, path):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, path + [str(k).lower()])
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            p = ".".join(path)
            if all(k in p for k in keys):
                found.append(x)
    walk(d, [])
    return found[0] if found else None


# ====================================================================== 工作台接口

async def test_dashboard_new_teacher_is_empty(app, teachers):
    """R1-006 AC3（接口部分）：新账号工作台 200，各计数为 0，前端据此显示三步引导。"""
    require_route(app, "/api/dashboard")
    t = await teachers()
    r = await t.client.get("/api/dashboard")
    assert r.status_code == 200, r.text
    nums = []

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            nums.append(len(x))
        elif isinstance(x, (int, float)) and not isinstance(x, bool):
            nums.append(x)
    walk(r.json())
    assert nums and not any(nums), f"新账号工作台应全为 0/空: {r.json()}"


async def test_dashboard_cards_match_homework(app, teachers, fake_ai, restore_settings):
    """R1-006 AC2 / R1-007 AC5：构造 1 份待复核、1 份批改中、1 份失败、1 次作业有未上传学生，
    工作台 4 张卡片数字与作业详情一致；标记已复核后“待复核”减 1。"""
    require_route(app, "/api/dashboard")
    t = await teachers()
    ck = class_key(await create_class(t.client))
    ms = [await add_member(t.client, ck, f"卡片生{i}", f"2027{i:03d}") for i in range(4)]
    hw = await create_homework(t.client, ck, uniq("工作台作业"))
    fake_ai.grade_result = {"questions": [Q(1, True), Q(2, False)]}
    r = await upload(t.client, assignment_id=hw["assignment_id"], member_id=ms[0]["id"])
    done = await wait_submission(t.client, r.json()["submission_id"])
    r = await upload(t.client, assignment_id=hw["assignment_id"], member_id=ms[1]["id"],
                     files=[("blank.txt", "。。".encode(), "text/plain")])
    failed = await wait_submission(t.client, r.json()["submission_id"])
    assert done["status"] == "completed" and failed["status"] == "failed"
    fake_ai.delay = 3
    r = await upload(t.client, assignment_id=hw["assignment_id"], member_id=ms[2]["id"])
    running = r.json()["submission_id"]
    d = (await t.client.get("/api/dashboard")).json()
    got = {"pending_review": _num(d, "review"), "processing": _num(d, "process") or _num(d, "grading"),
           "failed": _num(d, "fail"), "collecting": _num(d, "collect")}
    assert got["pending_review"] == 1 and got["failed"] == 1 and got["processing"] == 1, (got, d)
    assert got["collecting"] == 1, (got, d)
    detail_rows = items_of((await t.client.get(f"/api/class/{ck}/homework/{hw_key(hw)}/submissions")).json())
    assert sum(1 for x in detail_rows if x.get("review_status") == "pending_review") == 1
    await drain_jobs()
    assert (await t.client.get(f"/api/grader/{running}")).json()["status"] == "completed"
    before = _num((await t.client.get("/api/dashboard")).json(), "review")
    assert before == 2, "第 3 份完成后应有 2 份待复核"
    from test_r1_grading_trust import _mark_reviewed
    assert (await _mark_reviewed(app, t, done["submission_id"])).status_code == 200
    assert _num((await t.client.get("/api/dashboard")).json(), "review") == 1, "标记已复核后“待复核”应减 1"


async def test_task_drawer_is_server_side(teachers, fake_ai, app):
    """R1-006 AC4（接口部分）：提交批改后 /api/tasks/jobs 出现该任务；同一账号另一个会话（“换浏览器”）看到同样的任务。"""
    t = await teachers()
    ck = class_key(await create_class(t.client))
    m = await add_member(t.client, ck, "抽屉生", "2028001")
    hw = await create_homework(t.client, ck)
    fake_ai.delay = 1
    r = await upload(t.client, assignment_id=hw["assignment_id"], member_id=m["id"])
    sid = r.json()["submission_id"]
    from qa_helpers import TeacherFactory, login
    f = TeacherFactory(app)
    try:
        c2 = f.client()
        assert (await login(c2, t.username, t.password)).status_code == 200
        j1 = items_of((await t.client.get("/api/tasks/jobs")).json())
        j2 = items_of((await c2.get("/api/tasks/jobs")).json())
        ids1 = {(x.get("job_type"), x.get("id")) for x in j1}
        assert ("grader", sid) in ids1 or any(x.get("id") == sid for x in j1), j1
        assert ids1 == {(x.get("job_type"), x.get("id")) for x in j2}
        running = [x for x in j1 if x.get("id") == sid][0]
        assert running["status"] in ("queued", "processing") and running.get("progress_stage")
    finally:
        await drain_jobs()
        await f.aclose()


# ====================================================================== 菜单与页面（静态）

def test_sidebar_menu_items():
    """R1-006 AC6（静态）：教师菜单 = 工作台/我的班级/作业批改/错题本/教案/设置；无我的任务、题库管理；用量统计仅管理员。"""
    s = _src("Sidebar.jsx")
    for need in ("工作台", "我的班级", "作业批改", "错题本", "教案", "设置", "新建班级"):
        assert need in s, f"侧栏缺少“{need}”"
    for bad in ("我的任务", "题库管理"):
        assert bad not in s, f"侧栏仍有“{bad}”"
    if "用量统计" in s:
        assert re.search(r"admin", s), "“用量统计”菜单未按管理员角色控制"


def test_questionbank_hidden_and_redirected():
    """R1-004 AC1（静态）：页面代码中不出现题库管理三个子页面名；/questionbank/* 重定向工作台。"""
    hits = grep_frontend(r"题库管理|我的题库|真题资源库|AI\s*智题库")
    assert not hits, hits
    app = _src("App.jsx")
    assert not re.search(r"import\s+QuestionBank", app), "QuestionBank 仍被打包"
    assert re.search(r"questionbank[^\n]*Navigate[^\n]*to=[\"']/[\"']|Navigate[^\n]*questionbank", app, re.I), \
        "未找到 /questionbank/* → / 的重定向"


def test_settings_only_profile_and_password():
    """R1-004 AC2（静态）：设置页只有“个人资料”“修改密码”，接真实接口；无班级管理等假功能。"""
    s = _src("Settings.jsx")
    for need in ("个人资料", "修改密码", "/auth/me", "change-password"):
        assert need in s or need in json.dumps(grep_frontend(re.escape(need))), f"设置页缺少 {need}"
    for bad in ("通知设置", "外观设置", "登录设备", "导出数据", "清除缓存", "班级管理", "深色"):
        assert bad not in s, f"设置页仍有“{bad}”"


DEAD = ["pages/Home.jsx", "pages/WelcomePage.jsx", "components/AnimatedBook.jsx", "components/GlobalTaskBar.jsx",
        "components/TaskBar.jsx", "components/PageTransition.jsx", "components/BubbleBackground.jsx",
        "components/ParticleStream.jsx", "components/TopGlowEffect.jsx", "store/index.js", "pages/MyTasks.jsx",
        "pages/QuestionBank.jsx"]


def test_dead_code_and_fake_pages_removed():
    """R1-004 方案 / R1-006：死代码、动画欢迎页、我的任务页、题库假页面已删除。"""
    left = [d for d in DEAD if (FRONTEND_SRC / d).exists()]
    assert not left, f"仍存在: {left}"


def test_no_local_task_storage():
    """R1-006 方案：删除 localStorage.globalTasks 与 localStorage.clear()。"""
    hits = grep_frontend(r"globalTasks|localStorage\.clear\(")
    assert not hits, hits


def test_settimeout_not_faking_success():
    """R1-004 AC3：setTimeout 不用于模拟保存/上传/生成（前后 3 行出现“成功/已保存/生成完成”即判可疑，逐条人工确认见 test-plan）。"""
    bad = []
    for p in FRONTEND_SRC.rglob("*.js*"):
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        for i, line in enumerate(lines):
            if "setTimeout" in line:
                ctx = "\n".join(lines[max(0, i - 3): i + 4])
                if re.search(r"成功|已保存|保存完成|上传完成|生成完成|已发送", ctx) and not re.search(r"(api|axios|fetch|await)\b", ctx):
                    bad.append(f"{p.relative_to(REPO).as_posix()}:{i + 1}: {line.strip()[:100]}")
    assert not bad, "\n".join(bad)


def test_navbar_logo_and_no_fake_buttons():
    """R1-006 / R1-004：Logo 回工作台；顶栏无搜索按钮；产品名去掉“(教师版)”括号；有用户菜单（退出登录）。"""
    s = _src("Navbar.jsx")
    assert re.search(r"to=[\"']/[\"']|navigate\([\"']/[\"']\)", s), "Logo 未链接到工作台"
    assert not re.search(r"\bSearch\b", s), "顶栏仍有搜索按钮"
    assert "(教师版)" not in s and "（教师版）" not in s
    assert "退出登录" in s and "修改密码" in s and "个人资料" in s, "顶栏缺少用户菜单"
