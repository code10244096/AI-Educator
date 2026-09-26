"""第②组 安全与部署：R1-003 生产安全基线 / R1-009 部署可用。
上线标准：L-S04、L-S05、L-S06、L-S07、L-D01~L-D05（Docker/Linux 相关项在本机为静态检查 + 模拟，见 test-plan §5）。
"""
import io
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from qa_helpers import (BACKEND, FRONTEND, PROD_JWT, REPO, grep_frontend, prod_env, run_runner, uniq, upload)

pytestmark = pytest.mark.xfail(reason="待开发：第②组 安全与部署（R1-003、R1-009）", run=False)


def _out(p) -> str:
    return (p.stdout or "") + (p.stderr or "")


# ====================================================================== R1-003 生产启动

def _prod_without(tmp_path, *keys, **over):
    env = prod_env(tmp_path, **over)
    for k in keys:
        env.pop(k, None)
    return env


@pytest.mark.slow
def test_production_refuses_without_jwt_secret(tmp_path):
    """R1-003 AC1：APP_ENV=production 且未设置 JWT_SECRET（或仍为示例值）→ 拒绝启动并提示原因。"""
    p, res = run_runner("boot", _prod_without(tmp_path / "a", "JWT_SECRET"))
    assert p.returncode != 0 and res is None, "未设置 JWT_SECRET 时仍然启动成功"
    assert "生产环境必须设置 JWT_SECRET" in _out(p), _out(p)[-800:]
    for example in ("your-secret-key-change-in-production", "change-me", "please-change-this-secret"):
        p, res = run_runner("boot", prod_env(tmp_path / f"b{len(example)}", JWT_SECRET=example))
        assert p.returncode != 0, f"JWT_SECRET={example}（示例值）时仍然启动成功"


@pytest.mark.slow
def test_production_refuses_without_llm_key(tmp_path):
    """R1-003 AC1 / Q13：生产没有有效 LLM_API_KEY → 拒绝启动（生产禁止模拟模式）。"""
    p, res = run_runner("boot", prod_env(tmp_path, LLM_API_KEY="your_api_key_here"))
    assert p.returncode != 0 and res is None, "占位 LLM_API_KEY 时生产仍然启动（会进入模拟模式）"
    assert "LLM_API_KEY" in _out(p), _out(p)[-800:]


@pytest.mark.slow
def test_production_docs_cors_debug_cookie(tmp_path):
    """R1-003 AC3 / L-S06：生产关闭 /docs /redoc /openapi.json；CORS 只放行白名单；debug=false；
    不打印 SQL；会话 Cookie 带 Secure。"""
    env = prod_env(tmp_path)
    p, _ = run_runner("initdb", env)
    assert p.returncode == 0, _out(p)[-800:]
    user = uniq("prod")
    from qa_helpers import run_manage
    pm = run_manage("create-user", "--username", user, "--name", "生产老师", "--password", "Prod2026abc",
                    "--no-force-change", env=env)
    assert pm.returncode == 0, _out(pm)[-800:]
    pre = lambda origin: {"method": "OPTIONS", "path": "/api/auth/login",  # noqa: E731
                          "headers": {"Origin": origin, "Access-Control-Request-Method": "POST"}}
    reqs = [{"path": "/docs"}, {"path": "/redoc"}, {"path": "/openapi.json"}, {"path": "/health"},
            pre("https://evil.example.com"), pre("https://school.example.com"),
            {"path": "/api/auth/me", "headers": {"Origin": "https://evil.example.com"}}]
    p, res = run_runner("boot", env, extra={"requests": reqs,
                                            "users": [{"username": user, "password": "Prod2026abc"}]})
    assert p.returncode == 0 and res, _out(p)[-1500:]
    st = {r["path"]: r["status"] for r in res["anon"] if r["method"] == "GET"}
    assert st["/docs"] == 404 and st["/redoc"] == 404 and st["/openapi.json"] == 404, st
    assert st["/health"] == 200
    evil, good = res["anon"][4], res["anon"][5]
    assert "access-control-allow-origin" not in evil["headers"], evil
    assert good["headers"].get("access-control-allow-origin") == "https://school.example.com", good
    assert "access-control-allow-origin" not in res["anon"][6]["headers"], res["anon"][6]
    assert res["debug"] is False, "生产 debug 应为 false"
    assert res["sql_echo"] is False, "生产不应打印 SQL"
    u = res["users"][0]
    assert u["login"] == 200
    cookie = [c for c in u["login_headers"]["set-cookie"] if c.startswith("aiedu_session=")]
    assert cookie and "secure" in cookie[0].lower(), cookie


# ====================================================================== R1-003 运维接口仅管理员

async def test_usage_api_admin_only(teachers):
    """R1-003 AC4 / L-S04：教师 403，管理员 200；用量接口不返回服务器绝对路径。"""
    t = await teachers()
    admin = await teachers(role="admin")
    for path in ("/api/usage/summary", "/api/usage/calls"):
        assert (await t.client.get(path)).status_code == 403, path
        r = await admin.client.get(path)
        assert r.status_code == 200, (path, r.status_code, r.text[:200])
        abs_paths = re.findall(r'"([A-Za-z]:[\\/][^"]*|/(?:home|root|app|usr|var|opt|srv|data)/[^"]*)"', r.text)
        assert not abs_paths, f"{path} 泄露服务器绝对路径: {abs_paths[:3]}"


def test_usage_menu_hidden_for_teacher_static():
    """R1-003 AC4（静态部分）：前端对 /usage 做角色判断；浏览器用例 B-003-4 实测菜单与“无权限”。"""
    hits = grep_frontend(r"usage")
    assert hits, "前端找不到 /usage 路由"
    assert grep_frontend(r"role\s*===?\s*['\"]admin['\"]|isAdmin"), "前端没有按管理员角色控制 /usage"
    assert grep_frontend(r"无权限"), "缺少“无权限”提示"


# ====================================================================== R1-003 上传安全

def _png_bytes() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(buf, "PNG")
    return buf.getvalue()


async def test_upload_magic_bytes_mismatch_rejected(teachers, fake_ai):
    """R1-003 AC5 / L-S07：.exe 改名 .jpg → 400“文件内容与格式不符”；真实 PNG 通过；伪 PDF 拒绝。"""
    t = await teachers()
    exe = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff" + b"\x00" * 200
    r = await upload(t.client, files=[("作业.jpg", exe, "image/jpeg")])
    assert r.status_code == 400 and r.json()["detail"] == "文件内容与格式不符", (r.status_code, r.text)
    r = await upload(t.client, files=[("作业.pdf", b"hello, not a pdf at all", "application/pdf")])
    assert r.status_code == 400, (r.status_code, r.text)
    assert "ocr" not in fake_ai.features(), "被拒绝的文件不应送进模型"
    r = await upload(t.client, files=[("作业.png", _png_bytes(), "image/png")])
    assert r.status_code in (200, 202), (r.status_code, r.text)


async def test_upload_more_than_10_files_rejected(teachers, fake_ai):
    """R1-003 AC5 / L-S07：单份作业 11 个文件 → 400；10 个文件可以。"""
    t = await teachers()
    mk = lambda i: (f"p{i}.md", f"### {i}. 题\n**学生答案**：{i}".encode(), "text/markdown")  # noqa: E731
    r = await upload(t.client, files=[mk(i) for i in range(11)])
    assert r.status_code == 400, (r.status_code, r.text)
    r = await upload(t.client, files=[mk(i) for i in range(10)])
    assert r.status_code in (200, 202), (r.status_code, r.text)


# ====================================================================== R1-003 密钥与镜像

def _dockerignore_rules(path: Path):
    rules = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        neg = line.startswith("!")
        if neg:
            line = line[1:].strip()
        line = os.path.normpath(line.strip("/")).replace("\\", "/")
        rules.append((neg, _glob_rx(line)))
    return rules


def _glob_rx(p: str):
    """Docker/moby patternmatcher semantics: `*` no separator, `**` any dirs, patterns anchored at context root."""
    out, i = "", 0
    while i < len(p):
        c = p[i]
        if p.startswith("**", i):
            i += 2
            if p[i:i + 1] == "/":
                out += "(?:.*/)?"
                i += 1
            else:
                out += ".*"
            continue
        if c == "*":
            out += "[^/]*"
        elif c == "?":
            out += "[^/]"
        elif c == "[":
            j = p.find("]", i)
            out += p[i:j + 1]
            i = j
        else:
            out += re.escape(c)
        i += 1
    return re.compile("^" + out + "$")


def _excluded(rel: str, rules) -> bool:
    parts = rel.split("/")
    cands = ["/".join(parts[:k]) for k in range(1, len(parts) + 1)]
    ex = False
    for neg, rx in rules:
        if any(rx.match(c) for c in cands):
            ex = not neg
    return ex


def build_context(root: Path, ignore: Path):
    """Files Docker would send as build context (paths relative to root, '/'-separated)."""
    rules = _dockerignore_rules(ignore) if ignore.exists() else []
    has_neg = any(n for n, _ in rules)
    files = []
    for d, dirs, fs in os.walk(root):
        reld = os.path.relpath(d, root).replace("\\", "/")
        reld = "" if reld == "." else reld + "/"
        if not has_neg:
            dirs[:] = [x for x in dirs if not _excluded(reld + x, rules)]
        for f in fs:
            rel = reld + f
            if not _excluded(rel, rules):
                files.append(rel)
    return files


def _compose():
    class Loader(yaml.SafeLoader):
        pass

    def no_dups(loader, node, deep=False):
        keys = [loader.construct_object(k, deep=deep) for k, _ in node.value]
        dups = {k for k in keys if keys.count(k) > 1}
        if dups:
            raise AssertionError(f"docker-compose.yml 中有重复的键: {dups}")
        return loader.construct_mapping(node, deep)

    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, no_dups)
    return yaml.load((REPO / "docker-compose.yml").read_text(encoding="utf-8"), Loader=Loader)


def _contexts():
    comp = _compose()
    out = {}
    for name, svc in comp["services"].items():
        b = svc.get("build")
        if b:
            ctx = b if isinstance(b, str) else b.get("context", ".")
            out[name] = (REPO / ctx).resolve()
    return out


def test_dockerignore_present_and_complete():
    """R1-003 方案 / L-S05：backend、frontend 均有 .dockerignore 且覆盖必需项；.gitignore 不再忽略它。"""
    need_backend = ["config.json", ".env", "*.db", "uploads", "api_runs", "venv", "__pycache__", "tests/reports"]
    for d, need in ((BACKEND, need_backend), (FRONTEND, ["node_modules", ".env"])):
        f = d / ".dockerignore"
        assert f.exists(), f"缺少 {f}"
        text = f.read_text(encoding="utf-8")
        missing = [n for n in need if n not in text]
        assert not missing, f"{f.name} 缺少: {missing}"
        p = subprocess.run(["git", "check-ignore", "-q", str(f)], cwd=REPO)
        assert p.returncode == 1, f"{f} 仍被 .gitignore 忽略，无法入库"


def test_docker_build_context_excludes_secrets_and_data():
    """R1-003 AC2 / L-S05（本机无 Docker，按 .dockerignore 规则模拟构建上下文）：
    不含 config.json、.env、*.db、uploads/ 旧文件、venv/、api_runs/、__pycache__、tests/reports。"""
    bad = []
    for svc, ctx in _contexts().items():
        files = build_context(ctx, ctx / ".dockerignore")
        for rel in files:
            base = rel.rsplit("/", 1)[-1]
            top = rel.split("/", 1)[0]
            if (rel == "config.json" or base == ".env" or base.endswith((".db", ".sqlite", ".sqlite3"))
                    or top in ("uploads", "api_runs", "venv", "node_modules", "logs", "data")
                    or "__pycache__" in rel.split("/") or rel.startswith("tests/reports/")):
                bad.append(f"{svc}: {rel}")
    assert not bad, f"构建上下文仍包含敏感/数据文件（前 20 个）: {bad[:20]}"


@pytest.mark.slow
def test_simulated_image_boots_with_env_only(tmp_path):
    """R1-003 / L-S05：把模拟的后端构建上下文拷到临时目录（即镜像内容），只用环境变量以生产模式启动。
    若部署方案要求挂载 config.json，则 compose 与部署文档必须写明该挂载。"""
    ctx = _contexts().get("backend", BACKEND)
    image = tmp_path / "app"
    for rel in build_context(ctx, ctx / ".dockerignore"):
        dst = image / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ctx / rel, dst)
    assert not (image / "config.json").exists()
    env = prod_env(tmp_path / "data", QA_BACKEND_DIR=str(image))
    p, res = run_runner("boot", env, extra={"requests": [{"path": "/health"}]})
    if p.returncode != 0 and "config.json" in _out(p):
        comp = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
        doc = (REPO / "DEPLOY_2GB.md").read_text(encoding="utf-8")
        assert "config.json" in comp and "config.json" in doc, \
            "镜像内无 config.json 时无法启动，且 compose/部署文档未说明需挂载 config.json：\n" + _out(p)[-600:]
        pytest.skip("部署方案为挂载 config.json（已在 compose 与文档中说明）")
    assert p.returncode == 0 and res, _out(p)[-1500:]
    assert res["anon"][0]["status"] == 200


SECRET_ALLOW = ("sk-test-SECRETSECRET", "sk-qa-dummy", "sk-xxx", "sk-your", "your_api_key", "your-api-key",
                "your-production-api-key")


def test_no_plaintext_secrets_tracked():
    """R1-003 方案：git 已跟踪文件中不含明文密钥（sk-… / api_key: "…"）。"""
    pat = r"sk-[A-Za-z0-9_-]{16,}|[\"']?api_key[\"']?\s*[:=]\s*[\"'][A-Za-z0-9_\-]{16,}[\"']|JWT_SECRET\s*=\s*[A-Za-z0-9_\-]{24,}"
    p = subprocess.run(["git", "grep", "-nIE", pat, "--", ".", ":!*package-lock.json"], cwd=REPO,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    hits = [l for l in p.stdout.splitlines() if not any(a in l for a in SECRET_ALLOW)]
    assert not hits, "已跟踪文件含疑似明文密钥:\n" + "\n".join(hits[:20])


def test_env_example_documents_required_vars():
    """R1-003 方案：.env.example 列出 LLM_API_KEY、JWT_SECRET、DATABASE_URL、CORS_ORIGINS、APP_ENV 等；.env 不入库。"""
    cands = [REPO / ".env.example", BACKEND / ".env.example"]
    text = "\n".join(c.read_text(encoding="utf-8") for c in cands if c.exists())
    need = ["LLM_API_KEY", "JWT_SECRET", "DATABASE_URL", "CORS_ORIGINS", "APP_ENV",
            "GRADING_CONCURRENCY", "DAILY_GRADING_QUOTA", "SEED_DEMO_DATA"]
    missing = [n for n in need if not re.search(rf"^\s*#?\s*{n}\s*=", text, re.M)]
    assert not missing, f".env.example 缺少: {missing}"
    tracked = subprocess.run(["git", "ls-files", ".env", "backend/.env", "frontend/.env"], cwd=REPO,
                             capture_output=True, text=True).stdout.strip()
    assert not tracked, f".env 被跟踪: {tracked}"
    assert PROD_JWT not in text


# ====================================================================== R1-009 部署

def _nginx_text() -> str:
    return (FRONTEND / "nginx.conf").read_text(encoding="utf-8")


def _block(text: str, header_rx: str) -> str:
    m = re.search(header_rx + r"\s*\{", text)
    assert m, f"nginx.conf 中找不到 {header_rx}"
    i, depth = m.end(), 1
    while depth and i < len(text):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def _size_mb(v: str) -> float:
    n, unit = re.fullmatch(r"(\d+)([kKmMgG]?)", v).groups()
    return int(n) * {"": 1 / 1048576, "k": 1 / 1024, "m": 1, "g": 1024}[unit.lower()]


def test_nginx_upload_limit_timeouts_headers():
    """R1-009 AC2（静态）/ L-D02：client_max_body_size ≥100m；/api 读写超时 ≥300s；安全响应头；HTTPS 样例。"""
    t = _nginx_text()
    m = re.search(r"client_max_body_size\s+(\d+[kKmMgG]?)\s*;", t)
    assert m and _size_mb(m.group(1)) >= 100, "client_max_body_size 未设置或 < 100m"
    api = _block(t, r"location\s+(?:\^~\s*)?/api/?")
    for d in ("proxy_read_timeout", "proxy_send_timeout"):
        mm = re.search(rf"{d}\s+(\d+)s?\s*;", api)
        assert mm and int(mm.group(1)) >= 300, f"/api 的 {d} 未设置或 < 300s"
    for h in ("X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy"):
        assert re.search(rf"add_header\s+{h}\b", t), f"缺少响应头 {h}"
    confs = [p for p in REPO.rglob("*.conf*") if "node_modules" not in p.parts] + list(REPO.rglob("*nginx*.example"))
    https = [p for p in confs if re.search(r"listen\s+443\s+ssl|listen\s+443.*\bssl\b", p.read_text(encoding="utf-8", errors="ignore"))]
    assert https or "listen 443" in (REPO / "DEPLOY_2GB.md").read_text(encoding="utf-8"), "没有 HTTPS server 配置样例"


def test_nginx_security_headers_not_shadowed():
    """R1-009 方案（P2 级检查）：nginx 的 add_header 不会继承到自带 add_header 的 location，
    静态资源 location 需重复安全头（或 include 公共片段）。"""
    t = _nginx_text()
    bad = []
    for m in re.finditer(r"location\s+[^{]+\{", t):
        body = _block(t[m.start():], re.escape(m.group(0)[:-1].strip()))
        if "add_header" in body and "include" not in body and "X-Content-Type-Options" not in body:
            bad.append(m.group(0).strip())
    assert not bad, f"这些 location 自带 add_header，会屏蔽 server 级安全头: {bad}"


def test_compose_backend_hidden_volumes_healthcheck():
    """R1-009 AC1/AC3（静态）/ L-D01 / L-D03：无重复 environment；后端不映射宿主端口；env_file；
    无 dataset 挂载；data/uploads/logs 卷；healthcheck /health；内存上限 ≤1.5g；对外只有 80/443。"""
    comp = _compose()
    be = comp["services"]["backend"]
    assert not be.get("ports"), f"后端不应映射宿主端口: {be.get('ports')}"
    env_file = be.get("env_file")
    assert env_file and ".env" in str(env_file), "后端应使用 env_file: .env"
    vols = [str(v) for v in be.get("volumes", [])]
    assert not any("dataset" in v for v in vols), f"生产不应挂载 dataset: {vols}"
    for need in ("data", "uploads", "logs"):
        assert any(re.match(rf"\.?/?{need}\b", v.split(":")[0].lstrip("./")) for v in vols), f"缺少 {need} 卷: {vols}"
    hc = be.get("healthcheck") or {}
    assert "/health" in str(hc.get("test")), f"healthcheck 未调用 /health: {hc}"
    mem = be.get("mem_limit") or (((be.get("deploy") or {}).get("resources") or {}).get("limits") or {}).get("memory")
    assert mem, "后端未设置内存上限"
    mm = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([mMgG])[bB]?", str(mem))
    assert mm and float(mm.group(1)) * (1024 if mm.group(2).lower() == "g" else 1) <= 1536, f"内存上限过大: {mem}"
    exposed = []
    for name, svc in comp["services"].items():
        for p in svc.get("ports", []) or []:
            host = str(p).split(":")[-2] if str(p).count(":") >= 1 else str(p)
            exposed.append((name, host.split("/")[0]))
    assert all(h in ("80", "443") for _, h in exposed), f"对外端口只应有 80/443: {exposed}"


def _bash() -> str:
    for c in (r"C:\Program Files\Git\bin\bash.exe", shutil.which("bash") or ""):
        if c and Path(c).exists():
            return c
    pytest.skip("找不到 bash")


def test_backup_restore_scripts_present():
    """R1-009 AC4（静态部分）/ L-D04：backup.sh（sqlite .backup + 打包 uploads，保留 14 天）与 restore.sh 存在且语法正确。
    实际演练见 test-plan C-009-4。"""
    b, r = REPO / "scripts" / "backup.sh", REPO / "scripts" / "restore.sh"
    assert b.exists() and r.exists(), "缺少 scripts/backup.sh 或 scripts/restore.sh"
    bt = b.read_text(encoding="utf-8")
    assert ".backup" in bt, "备份应使用 sqlite3 在线备份 .backup"
    assert "uploads" in bt and re.search(r"\b14\b", bt), "备份应打包 uploads 并保留 14 天"
    for s in (b, r):
        p = subprocess.run([_bash(), "-n", str(s)], capture_output=True, text=True)
        assert p.returncode == 0, f"{s.name} 语法错误: {p.stderr}"


def test_deploy_doc_consistent():
    """R1-009 方案 / L-D05（静态部分）：DEPLOY_2GB.md 写明 .env 配置、账号命令、备份 crontab 02:30、恢复、升级步骤。"""
    doc = (REPO / "DEPLOY_2GB.md").read_text(encoding="utf-8")
    need = {".env": ".env", "JWT_SECRET": "JWT_SECRET", "LLM_API_KEY": "LLM_API_KEY",
            "create-user": "create-user", "assign-orphans": "assign-orphans", "backup.sh": "backup.sh",
            "restore.sh": "restore.sh", "crontab": "crontab",
            "02:30": r"(?:30\s+2\s+\*|02:30|2:30)", "升级": r"docker compose up -d --build"}
    missing = [k for k, rx in need.items() if not re.search(rx if k in ("02:30", "升级") else re.escape(rx), doc)]
    assert not missing, f"DEPLOY_2GB.md 缺少: {missing}"
    stale = [s for s in ("8000:8000", "dataset:/app/dataset", "ENV=production") if s in doc]
    assert not stale, f"部署文档含过时配置: {stale}"
