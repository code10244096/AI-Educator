"""第①组 账号与鉴权：R1-001 真实登录 / R1-002 鉴权与按教师隔离。
上线标准：L-S01、L-S02、L-S03、L-S07（越权下载）。用例与验收标准的对应见 docs/product/test-plan-r1.md。
"""
import asyncio
import random
import re
from datetime import timedelta

import pytest
import pytest_asyncio

from fakes import FakeGateway, install_gateway, restore_gateway
from qa_helpers import (GENERIC_LOGIN_ERROR, INITIAL_PASSWORD, NEW_PASSWORD, SESSION_COOKIE, TeacherFactory,
                        add_member, change_password, class_key, copy_real_db, create_class, create_homework,
                        create_user, drain_jobs, fresh_env, grep_frontend, hw_key, items_of, login, run_manage,
                        run_runner, sql, uniq, upload, wait_submission)

pytestmark = pytest.mark.xfail(reason="待开发：第①组 账号与鉴权（R1-001、R1-002）", run=False)


def phone() -> str:
    return "139" + "".join(random.choice("0123456789") for _ in range(8))


# ====================================================================== R1-001

async def test_create_user_cli_initial_password_must_change(anon):
    """R1-001 AC1：命令开通 → 初始密码登录 → 必须先改密 → 改密后进入业务，显示姓名。"""
    username = phone()
    p = run_manage("create-user", "--username", username, "--name", "王老师")
    assert p.returncode == 0, p.stderr[-800:]
    m = re.findall(r"初始密码\s*[:：]\s*(\S+)", p.stdout)
    assert m, f"输出中没有“初始密码: xxx”一行：{p.stdout[-500:]}"
    pwd = m[-1]
    r = await login(anon, username, pwd)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["must_change_password"] is True
    assert body["display_name"] == "王老师"
    # 后端强制首次改密（与开发约定：业务接口 403 “请先修改初始密码”）
    r = await anon.get("/api/class/list")
    assert r.status_code == 403 and "修改初始密码" in r.json().get("detail", ""), (r.status_code, r.text)
    r = await change_password(anon, pwd, NEW_PASSWORD)
    assert r.status_code == 200, r.text
    me = await anon.get("/api/auth/me")
    if me.status_code == 401:  # 改密使旧会话失效时，前端会重新登录
        assert (await login(anon, username, NEW_PASSWORD)).status_code == 200
        me = await anon.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["must_change_password"] is False
    assert me.json()["display_name"] == "王老师"
    assert (await anon.get("/api/class/list")).status_code == 200


async def test_login_success_cookie_and_body(anon):
    """L-S01 / R1-001 方案：httpOnly + SameSite=Lax 会话 Cookie；返回用户信息字段。"""
    username = uniq("t")
    create_user(username, "李老师", school="实验中学", password=INITIAL_PASSWORD)
    r = await login(anon, username, INITIAL_PASSWORD)
    assert r.status_code == 200, r.text
    cookies = r.headers.get_list("set-cookie")
    sess = [c for c in cookies if c.startswith(SESSION_COOKIE + "=")]
    assert sess, f"没有 {SESSION_COOKIE} Cookie：{cookies}"
    low = sess[0].lower()
    assert "httponly" in low and "samesite=lax" in low, sess[0]
    body = r.json()
    for k in ("id", "username", "display_name", "school", "role", "must_change_password"):
        assert k in body, f"登录响应缺少字段 {k}: {body}"
    assert body["username"] == username and body["role"] == "teacher" and body["school"] == "实验中学"
    assert "password" not in str(body).lower() or "must_change_password" in body


async def test_login_failure_message_identical(anon):
    """R1-001 AC2 / L-S01：错误密码与不存在账号的提示一致，均 401。"""
    username = uniq("t")
    create_user(username, "赵老师", password=INITIAL_PASSWORD)
    r1 = await login(anon, username, "wrong-pass-1")
    r2 = await login(anon, uniq("nobody"), "wrong-pass-1")
    assert r1.status_code == 401 and r2.status_code == 401
    assert r1.json()["detail"] == r2.json()["detail"] == GENERIC_LOGIN_ERROR


async def test_login_lockout_after_10_failures(anon, teachers):
    """R1-001 AC3 / L-S01：连续 10 次失败后，第 11 次即使密码正确也 429。其他账号不受影响。"""
    username = uniq("t")
    create_user(username, "锁定老师", password=INITIAL_PASSWORD)
    for i in range(10):
        r = await login(anon, username, f"bad-{i}")
        assert r.status_code == 401, (i, r.status_code, r.text)
    r = await login(anon, username, INITIAL_PASSWORD)
    assert r.status_code == 429, r.text
    assert r.json()["detail"] == "尝试次数过多，请 15 分钟后再试"
    other = await teachers()  # 不同账号照常登录（按账号而不是按 IP 限流）
    assert (await other.client.get("/api/auth/me")).status_code == 200


async def test_logout_then_business_api_401(teachers):
    """R1-001 AC5：退出后接口返回 401。"""
    t = await teachers()
    c = t.client
    assert (await c.get("/api/auth/me")).status_code == 200
    r = await c.post("/api/auth/logout")
    assert r.status_code == 200
    assert (await c.get("/api/auth/me")).status_code == 401
    assert (await c.get("/api/class/list")).status_code == 401


async def test_logout_anonymous_is_harmless(anon):
    """与开发约定：未登录调用 logout 返回 200（只清 Cookie）。"""
    assert (await anon.post("/api/auth/logout")).status_code == 200


async def test_expired_session_returns_401(app, teachers, restore_settings):
    """R1-001 AC6：会话过期后任意接口 401（前端据此跳登录页并提示，见浏览器用例 B-001-6）。"""
    import auth
    t = await teachers()
    expired = auth.create_access_token(t.id, expires_delta=timedelta(seconds=-5))
    f = TeacherFactory(app)
    try:
        c1 = f.client()
        c1.cookies.set(SESSION_COOKIE, expired)
        assert (await c1.get("/api/auth/me")).status_code == 401
        assert (await c1.get("/api/class/list")).status_code == 401
        c2 = f.client(headers={"Authorization": f"Bearer {expired}"})
        assert (await c2.get("/api/class/list")).status_code == 401
        # 配置项 SESSION_EXPIRE_MINUTES 生效：配成约 1 秒，登录后等待过期
        restore_settings("SESSION_EXPIRE_MINUTES", 1 / 60)
        c3 = f.client()
        assert (await login(c3, t.username, t.password)).status_code == 200
        await asyncio.sleep(2.5)
        assert (await c3.get("/api/class/list")).status_code == 401
    finally:
        await f.aclose()


async def test_password_hash_is_bcrypt():
    """R1-001 AC7：users.password_hash 以 $2b$ 开头。"""
    username = uniq("t")
    create_user(username, "哈希老师", password=INITIAL_PASSWORD)
    rows = sql("SELECT password_hash FROM users WHERE username = ?", (username,))
    assert rows and rows[0][0].startswith("$2b$"), rows


async def test_change_password_rules(teachers, app):
    """R1-001 AC8：旧密码错误 / 新密码不合规 / 成功后新密码可登录、旧密码不可。"""
    t = await teachers()
    c = t.client
    r = await change_password(c, "not-the-password1", "Newpass2026")
    assert 400 <= r.status_code < 500 and r.json()["detail"] == "当前密码不正确", r.text
    for weak in ("abc12", "abcdefghij", "1234567890"):
        r = await change_password(c, t.password, weak)
        assert 400 <= r.status_code < 500, (weak, r.status_code)
        d = str(r.json().get("detail"))
        assert "8" in d and "字母" in d and "数字" in d, f"未提示具体规则: {d}"
    r = await change_password(c, t.password, "Newpass2026")
    assert r.status_code == 200, r.text
    f = TeacherFactory(app)
    try:
        assert (await login(f.client(), t.username, "Newpass2026")).status_code == 200
        assert (await login(f.client(), t.username, t.password)).status_code == 401
    finally:
        await f.aclose()


async def test_update_profile_me(teachers, app):
    """R1-004 AC2（后端部分）/ R1-001：PUT /api/auth/me 改姓名、学校；账号只读；重新登录后仍是新值。"""
    t = await teachers()
    r = await t.client.put("/api/auth/me", json={"display_name": "新名字老师", "school": "第二中学",
                                                  "username": "hijack", "role": "admin"})
    assert r.status_code == 200, r.text
    me = (await t.client.get("/api/auth/me")).json()
    assert me["display_name"] == "新名字老师" and me["school"] == "第二中学"
    assert me["username"] == t.username and me["role"] == "teacher", "账号/角色不应可被本人修改"
    f = TeacherFactory(app)
    try:
        r = await login(f.client(), t.username, t.password)
        assert r.json()["display_name"] == "新名字老师"
    finally:
        await f.aclose()


async def test_manage_reset_disable_list(app, teachers):
    """R1-001 方案：manage.py reset-password / disable-user / list-users。"""
    t = await teachers()
    p = run_manage("list-users")
    assert p.returncode == 0 and t.username in p.stdout, p.stdout[-500:]
    p = run_manage("reset-password", "--username", t.username)
    assert p.returncode == 0, p.stderr[-500:]
    m = re.findall(r"(?:初始密码|新密码|密码)\s*[:：]\s*(\S+)", p.stdout)
    assert m, p.stdout[-500:]
    f = TeacherFactory(app)
    try:
        assert (await login(f.client(), t.username, t.password)).status_code == 401, "重置后旧密码仍可登录"
        c = f.client()
        r = await login(c, t.username, m[-1])
        assert r.status_code == 200 and r.json()["must_change_password"] is True
        assert (await t.client.get("/api/auth/me")).status_code == 401, "重置密码后旧会话应失效"
        p = run_manage("disable-user", "--username", t.username)
        assert p.returncode == 0, p.stderr[-500:]
        r = await login(f.client(), t.username, m[-1])
        assert r.status_code == 401 and r.json()["detail"] == GENERIC_LOGIN_ERROR
        assert (await c.get("/api/auth/me")).status_code == 401, "停用后已有会话应失效"
    finally:
        await f.aclose()


def test_frontend_has_no_demo_password():
    """R1-001 AC7：全站不再出现“123456”“演示账号”“演示密码”；登录页无“返回首页”。"""
    hits = grep_frontend(r"123456|演示账号|演示密码")
    assert not hits, hits
    assert not grep_frontend(r"返回首页"), grep_frontend(r"返回首页")


def test_frontend_handles_401():
    """R1-001 AC6 / R1-002 AC5（静态部分）：axios 拦截 401 → 跳登录并提示。浏览器用例 B-001-4/6 做实测。"""
    hits = grep_frontend(r"401")
    assert any("api" in h[0] or "axios" in h[2] for h in hits), hits
    assert grep_frontend(r"登录已过期，请重新登录"), "缺少“登录已过期，请重新登录”提示文案"


# ====================================================================== R1-002

PUBLIC = {("POST", "/api/auth/login"), ("POST", "/api/auth/logout")}


def _fill(path: str) -> str:
    def repl(m):
        name = m.group(1).split(":")[0]
        if "slug" in name or name in ("class_id", "classId"):
            return "1"
        if name in ("path", "file_path"):
            return "x"
        return "1"
    return re.sub(r"\{([^}]+)\}", repl, path)


async def test_all_api_routes_require_auth(app, anon):
    """R1-002 AC1 / L-S02：遍历 app.routes，未带凭证访问每个 /api/* 业务接口都 401。"""
    from fastapi.routing import APIRoute
    from config import settings
    prefix = settings.API_PREFIX.rstrip("/") + "/"
    checked, bad = 0, []
    for r in app.routes:
        if not isinstance(r, APIRoute) or not r.path.startswith(prefix):
            continue
        for method in sorted(r.methods - {"HEAD", "OPTIONS"}):
            if (method, r.path) in PUBLIC:
                continue
            url = _fill(r.path)
            kw = {"json": {}} if method in ("POST", "PUT", "PATCH") else {}
            resp = await anon.request(method, url, **kw)
            checked += 1
            if resp.status_code != 401:
                bad.append(f"{method} {r.path} -> {resp.status_code} {resp.text[:80]}")
    assert checked >= 40, f"只检查到 {checked} 个接口，路由遍历可能有误"
    assert not bad, "以下接口未登录也可访问：\n" + "\n".join(bad)
    assert (await anon.get("/health")).status_code == 200


# ---------------------------------------------------------------- two-teacher isolation

@pytest_asyncio.fixture(scope="module")
async def world(app):
    """教师 A 的一整套资源 + 一个全新的教师 B。"""
    await drain_jobs()
    fake = FakeGateway()
    prev = install_gateway(fake)
    f = TeacherFactory(app)
    try:
        a_name, b_name = uniq("ta"), uniq("tb")
        create_user(a_name, "甲老师", password=NEW_PASSWORD)
        create_user(b_name, "乙老师", password=NEW_PASSWORD)
        a, b = f.client(), f.client()
        ra = await login(a, a_name, NEW_PASSWORD)
        rb = await login(b, b_name, NEW_PASSWORD)
        assert ra.status_code == 200 and rb.status_code == 200
        cls = await create_class(a, "甲的班级")
        ck = class_key(cls)
        m = await add_member(a, ck, "陈晓明", "2025001")
        hw = await create_homework(a, ck, "甲的作业")
        r = await upload(a, assignment_id=hw["assignment_id"], member_id=m["id"], student_name="陈晓明")
        assert r.status_code in (200, 202), r.text
        sid = int(r.json()["submission_id"])
        done = await wait_submission(a, sid)
        assert done["status"] == "completed", done
        r = await a.post("/api/notebook/upload", files={"file": ("错题.txt", "已知 x+1=3，求 x 的值。学生答案 x=1".encode(), "text/plain")},
                         data={"knowledge_point": "一元一次方程"})
        assert r.status_code == 200, r.text
        wq_manual = r.json().get("id") or (r.json().get("questions") or [{}])[0].get("id")
        wqs = [q["id"] for q in items_of((await a.get("/api/notebook/list", params={"limit": 500})).json())]
        assert wq_manual and len(wqs) >= 2, wqs
        r = await a.post("/api/lessonplan/generate", data={"title": "甲的教案"})
        assert r.status_code in (200, 202), r.text
        lp = r.json()["id"]
        await drain_jobs()
        yield {"a": a, "b": b, "a_user": ra.json(), "b_user": rb.json(), "ck": ck, "cls": cls, "mid": m["id"],
               "hk": hw_key(hw), "aid": hw["assignment_id"], "sid": sid, "wqs": wqs, "lp": lp, "fake": fake}
    finally:
        await drain_jobs()
        restore_gateway(prev)
        await f.aclose()


def _reads(w):
    ck, hk, sid, lp = w["ck"], w["hk"], w["sid"], w["lp"]
    return [
        f"/api/class/{ck}", f"/api/class/{ck}/members", f"/api/class/{ck}/homework",
        f"/api/class/{ck}/homework/{hk}", f"/api/class/{ck}/homework/{hk}/submissions",
        f"/api/class/{ck}/homework/{hk}/analysis", f"/api/class/{ck}/homework-stats",
        f"/api/class/{ck}/grading-tasks", f"/api/class/{ck}/alert-students", f"/api/class/{ck}/score-archive",
        f"/api/class/stats?class_slug={ck}",
        f"/api/grader/{sid}", f"/api/grader/{sid}/files/0",
        f"/api/lessonplan/{lp}", f"/api/lessonplan/{lp}/export?format=md",
    ]


async def test_cross_teacher_reads_return_404(world, app):
    """R1-002 AC2/AC3 / L-S03 / L-S07：B 读取 A 的每个资源（含原始文件）都 404；A 自己读取正常。"""
    from fastapi.routing import APIRoute
    a, b = world["a"], world["b"]
    paths = _reads(world)
    route_paths = {r.path for r in app.routes if isinstance(r, APIRoute)}
    if "/api/class/{class_slug}/homework/{homework_id}/progress" in route_paths or \
            any(p.endswith("/progress") for p in route_paths):
        paths.append(f"/api/class/{world['ck']}/homework/{world['hk']}/progress")
    bad = []
    for p in paths:
        ra = await a.get(p)
        rb = await b.get(p)
        if ra.status_code != 200:
            bad.append(f"A 自己读取 {p} -> {ra.status_code}（用例前提不成立）")
        if rb.status_code != 404:
            bad.append(f"B 读取 {p} -> {rb.status_code} {rb.text[:80]}")
    assert not bad, "\n".join(bad)


async def test_cross_teacher_lists_are_empty(world, app):
    """R1-002 AC2：全新教师 B 的所有列表接口不含任何他人（或无归属存量）数据。"""
    from fastapi.routing import APIRoute
    b = world["b"]
    bad = []
    lists = ["/api/class/list", "/api/grader/submissions?include_seed=true&limit=200",
             "/api/notebook/list?limit=500", "/api/lessonplan/list?limit=100", "/api/tasks/all",
             "/api/tasks/jobs?limit=100"]
    for p in lists:
        r = await b.get(p)
        if r.status_code != 200 or items_of(r.json()):
            bad.append(f"{p} -> {r.status_code} {str(r.json())[:200]}")
    st = (await b.get("/api/notebook/stats")).json()
    if st.get("total"):
        bad.append(f"/api/notebook/stats total={st.get('total')}")
    cs = await b.get("/api/class/stats")
    if cs.status_code == 200 and cs.json().get("total_students"):
        bad.append(f"/api/class/stats total_students={cs.json().get('total_students')}")
    if any(isinstance(r, APIRoute) and r.path == "/api/dashboard" for r in app.routes):
        d = (await b.get("/api/dashboard")).json()
        if str(world["cls"]["name"]) in str(d) or "甲的作业" in str(d):
            bad.append(f"/api/dashboard 泄露 A 的数据: {str(d)[:200]}")
    assert not bad, "\n".join(bad)


async def test_cross_teacher_mutations_rejected(world, app):
    """R1-002 AC2：B 对 A 资源的 PUT/POST/PATCH/DELETE 全部 404，且 A 的数据完好。"""
    from fastapi.routing import APIRoute
    a, b = world["a"], world["b"]
    ck, hk, sid, lp, mid, aid = world["ck"], world["hk"], world["sid"], world["lp"], world["mid"], world["aid"]
    wq = world["wqs"][0]
    before_hw = (await a.get(f"/api/class/{ck}/homework/{hk}")).json()
    before_sub = (await a.get(f"/api/grader/{sid}")).json()
    calls = [
        ("PUT", f"/api/class/{ck}", {"json": {"name": "被篡改"}}),
        ("POST", f"/api/class/{ck}/members", {"json": {"name": "入侵者"}}),
        ("POST", f"/api/class/{ck}/members/import", {"data": {"text": "入侵者甲\n入侵者乙"}}),
        ("PUT", f"/api/class/{ck}/members/{mid}", {"json": {"name": "改名"}}),
        ("POST", f"/api/class/{ck}/homework", {"json": {"title": "入侵作业"}}),
        ("PUT", f"/api/class/{ck}/homework/{hk}", {"json": {"title": "改标题"}}),
        ("POST", "/api/grader/upload", {"files": [("files", ("x.md", b"### 1. x\n**student**: 1", "text/markdown"))],
                                         "data": {"assignment_id": str(aid)}}),
        ("POST", "/api/grader/upload", {"files": [("files", ("x.md", b"### 1. x\n**student**: 1", "text/markdown"))],
                                         "data": {"submission_id": str(sid)}}),
        ("POST", f"/api/grader/{sid}/retry", {}),
        ("POST", f"/api/notebook/{wq}/mastered", {}),
        ("POST", f"/api/notebook/{wq}/unmastered", {}),
        ("POST", f"/api/notebook/{wq}/variants", {"data": {"count": "1"}}),
        ("PUT", f"/api/lessonplan/{lp}", {"json": {"title": "改教案"}}),
        ("POST", f"/api/lessonplan/{lp}/regenerate", {}),
    ]
    route_paths = {r.path for r in app.routes if isinstance(r, APIRoute)}
    if "/api/grader/{submission_id}/questions/{question_number}" in route_paths:
        calls.append(("PATCH", f"/api/grader/{sid}/questions/1", {"json": {"is_correct": False}}))
    destructive = [
        ("DELETE", f"/api/class/{ck}/homework/{hk}/submissions/pending", {}),
        ("DELETE", f"/api/class/{ck}/members/{mid}", {}),
        ("DELETE", f"/api/grader/{sid}", {}),
        ("DELETE", f"/api/notebook/{wq}", {}),
        ("DELETE", f"/api/lessonplan/{lp}", {}),
        ("DELETE", f"/api/class/{ck}/homework/{hk}", {}),
        ("DELETE", f"/api/class/{ck}", {}),
    ]
    bad = []
    for method, path, kw in calls + destructive:
        r = await b.request(method, path, **kw)
        if r.status_code != 404:
            bad.append(f"B {method} {path} -> {r.status_code} {r.text[:80]}")
    await drain_jobs()
    # A 的数据完好
    cls = await a.get(f"/api/class/{ck}")
    if cls.status_code != 200 or cls.json()["name"] != "甲的班级":
        bad.append(f"A 的班级被改动: {cls.status_code} {cls.text[:100]}")
    names = [m["name"] for m in items_of((await a.get(f"/api/class/{ck}/members")).json())]
    if names != ["陈晓明"]:
        bad.append(f"A 的成员被改动: {names}")
    hw = await a.get(f"/api/class/{ck}/homework/{hk}")
    if hw.status_code != 200 or hw.json()["title"] != before_hw["title"]:
        bad.append(f"A 的作业被改动: {hw.status_code}")
    titles = [h["title"] for h in items_of((await a.get(f"/api/class/{ck}/homework")).json())]
    if "入侵作业" in titles:
        bad.append("B 在 A 的班级下建了作业")
    sub = await a.get(f"/api/grader/{sid}")
    if sub.status_code != 200 or sub.json().get("score") != before_sub.get("score"):
        bad.append(f"A 的批改记录被改动: {sub.status_code}")
    wqs = [q["id"] for q in items_of((await a.get("/api/notebook/list", params={"limit": 500})).json())]
    if wq not in wqs:
        bad.append("A 的错题被删除")
    plan = await a.get(f"/api/lessonplan/{lp}")
    if plan.status_code != 200 or plan.json()["title"] != "甲的教案":
        bad.append(f"A 的教案被改动: {plan.status_code}")
    assert not bad, "\n".join(bad)


async def test_ownership_columns_and_llm_teacher_id(world):
    """R1-002 方案：归属字段写入当前教师（后台任务也用任务所属教师）；大模型调用带 teacher_id。"""
    a_id = int(world["a_user"]["id"])
    checks = {
        "classes": ("teacher_id", "SELECT teacher_id FROM classes WHERE class_name = ?", ("甲的班级",)),
        "homework_assignments": ("teacher_id", "SELECT teacher_id FROM homework_assignments WHERE id = ?", (world["aid"],)),
        "homework_submissions": ("teacher_id", "SELECT teacher_id FROM homework_submissions WHERE id = ?", (world["sid"],)),
        "lesson_plans": ("teacher_id", "SELECT teacher_id FROM lesson_plans WHERE id = ?", (world["lp"],)),
    }
    bad = []
    for table, (_col, q, params) in checks.items():
        rows = sql(q, params)
        if not rows or rows[0][0] != a_id:
            bad.append(f"{table}: {rows}")
    wq_owners = {r[0] for r in sql("SELECT user_id FROM wrong_questions WHERE id IN (%s)" %
                                   ",".join("?" * len(world["wqs"])), world["wqs"])}
    if wq_owners != {a_id}:
        bad.append(f"wrong_questions.user_id = {wq_owners}（期望 {a_id}，不应写死 1）")
    metas = [c["task_meta"] for c in world["fake"].calls]
    if not metas or not all(m.get("teacher_id") == a_id for m in metas):
        bad.append(f"大模型调用 task_meta 缺 teacher_id: {metas[:3]}")
    assert not bad, "\n".join(bad)


@pytest.mark.slow
def test_assign_orphans_on_real_db_copy(tmp_path):
    """R1-002 AC4：用 teaching_assistant.db 副本迁移 + assign-orphans 到 A；A 看到全部旧数据，新教师 C 看不到。"""
    db = copy_real_db(tmp_path / "qa.db")
    env = fresh_env(tmp_path)
    tables = ["classes", "class_members", "homework_assignments", "homework_submissions",
              "wrong_questions", "lesson_plans"]
    p, res = run_runner("initdb", env)
    assert p.returncode == 0, p.stdout[-500:] + p.stderr[-1500:]
    before = {t: sql(f"SELECT COUNT(*) FROM {t}", db=db)[0][0] for t in tables}
    a_name, c_name = uniq("mig_a"), uniq("mig_c")
    for u in (a_name, c_name):
        p = run_manage("create-user", "--username", u, "--name", "迁移老师", "--password", NEW_PASSWORD,
                       "--no-force-change", env=env)
        assert p.returncode == 0, p.stderr[-800:]
    for _ in range(2):  # 幂等
        p = run_manage("assign-orphans", "--username", a_name, env=env)
        assert p.returncode == 0, p.stderr[-800:]
    after = {t: sql(f"SELECT COUNT(*) FROM {t}", db=db)[0][0] for t in tables}
    assert after == before, f"迁移不应增删数据: {before} -> {after}"
    orphan = sql("SELECT COUNT(*) FROM classes WHERE teacher_id IS NULL", db=db)[0][0]
    assert orphan == 0
    reqs = [{"path": "/api/class/list"}, {"path": "/api/grader/submissions?include_seed=true&limit=200"},
            {"path": "/api/lessonplan/list?limit=100"}, {"path": "/api/notebook/list?limit=500"}]
    p, res = run_runner("boot", env, extra={"users": [
        {"username": a_name, "password": NEW_PASSWORD, "requests": reqs},
        {"username": c_name, "password": NEW_PASSWORD, "requests": reqs}]})
    assert p.returncode == 0 and res, p.stdout[-500:] + p.stderr[-1500:]
    ua, uc = res["users"]
    assert ua["login"] == 200 and uc["login"] == 200
    assert ua["results"][0]["count"] == before["classes"],         f"A 应看到全部 {before['classes']} 个旧班级: {ua['results'][0]['count']}"
    assert ua["results"][1]["count"], f"A 应看到旧的批改记录: {str(ua['results'][1]['body'])[:200]}"
    for r in uc["results"]:
        assert r["status"] == 200 and r["count"] == 0, f"C 不应看到旧数据: {r['path']} {str(r['body'])[:200]}"
