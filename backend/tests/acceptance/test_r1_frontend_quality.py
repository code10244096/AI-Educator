"""第⑦组 前端质量：R1-010 拆包与首屏体积、R1-012 KaTeX 公式、R1-014 三态与 404。
上线标准：L-P01（打包产物分析）、L-U05（组件级）、L-U08（静态）。页面实测见浏览器用例 B-010-*、B-012-*、B-014-*。

打包体积用例默认自己执行 `npx vite build --manifest` 到临时目录（约 30~60 秒）；
也可设置环境变量 QA_BUILD_DIR 指向已有的构建产物（须含 .vite/manifest.json）。
"""
import gzip
import html as htmlmod
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from qa_helpers import ACCEPTANCE_DIR, FRONTEND, FRONTEND_SRC, grep_frontend, strip_js_comments

pytestmark = pytest.mark.xfail(reason="待开发：第⑦组 前端质量（R1-010、R1-012、R1-014）", run=False)

LIMIT_INITIAL_GZIP = 300 * 1024
LIMIT_CHUNK_RAW = 500 * 1000


def _app_src() -> str:
    return strip_js_comments((FRONTEND_SRC / "App.jsx").read_text(encoding="utf-8"))


# ====================================================================== R1-010 拆包（静态）

def test_pages_are_lazy_loaded():
    """R1-010 方案：所有页面 React.lazy + Suspense；App.jsx 不静态 import 页面。"""
    app = _app_src()
    static_pages = re.findall(r"^\s*import\s+\w+\s+from\s+['\"]\./pages/[^'\"]+['\"]", app, re.M)
    assert not static_pages, f"页面仍被静态 import: {static_pages}"
    assert re.search(r"lazy\(\s*\(\)\s*=>\s*import\(", app) and "Suspense" in app


def test_heavy_deps_not_in_entry_path():
    """R1-010 AC2（静态）：html2pdf 只能动态 import；KaTeX / react-markdown 不在入口与布局组件中。"""
    static_h2p = grep_frontend(r"^\s*import\s+[^;]*['\"]html2pdf(\.js)?['\"]")
    assert not static_h2p, f"html2pdf 被静态 import: {static_h2p}"
    for f in ("main.jsx", "App.jsx", "components/Navbar.jsx", "components/Sidebar.jsx"):
        p = FRONTEND_SRC / f
        if p.exists():
            t = strip_js_comments(p.read_text(encoding="utf-8"))
            assert not re.search(r"katex|react-markdown|html2pdf", t, re.I), f"{f} 直接引入了重依赖"
    cfg = (FRONTEND / "vite.config.js").read_text(encoding="utf-8")
    assert "manualChunks" in cfg, "vite 配置缺少 manualChunks"


# ====================================================================== R1-010 打包产物（L-P01）

@pytest.fixture(scope="module")
def build_dir(tmp_path_factory):
    env_dir = os.environ.get("QA_BUILD_DIR")
    if env_dir:
        return Path(env_dir)
    out = tmp_path_factory.mktemp("vite_build")
    p = subprocess.run("npx vite build --manifest --emptyOutDir --outDir " + str(out), cwd=str(FRONTEND),
                       shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    assert p.returncode == 0, f"vite build 失败（L-Q02）:\n{p.stdout[-1500:]}\n{p.stderr[-1500:]}"
    (out / "build-log.txt").write_text(p.stdout + p.stderr, encoding="utf-8")
    return out


def _manifest(build_dir: Path):
    m = build_dir / ".vite" / "manifest.json"
    if not m.exists():
        m = build_dir / "manifest.json"
    assert m.exists(), "构建产物缺少 manifest（需 --manifest）"
    return json.loads(m.read_text(encoding="utf-8"))


def _closure(man, keys):
    seen, stack = set(), list(keys)
    while stack:
        k = stack.pop()
        if k in seen or k not in man:
            continue
        seen.add(k)
        stack.extend(man[k].get("imports", []))
    return seen


def _gz(p: Path) -> int:
    return len(gzip.compress(p.read_bytes(), compresslevel=9))


def initial_chunks(build_dir: Path):
    """登录页 + 工作台首屏会加载的 JS：入口的静态依赖闭包 + 登录页、工作台两个路由 chunk 的静态依赖闭包。"""
    man = _manifest(build_dir)
    entry = [k for k, v in man.items() if v.get("isEntry")]
    routes = [k for k in man if re.search(r"pages/(Login\w*|Dashboard\w*|Workbench\w*|Workspace\w*|Home\w*)\.jsx$", k)]
    assert any("Login" in k for k in routes), f"manifest 中找不到登录页 chunk: {list(man)[:20]}"
    assert any(re.search(r"Dashboard|Workbench|Workspace|Home", k) for k in routes), "manifest 中找不到工作台页 chunk"
    keys = _closure(man, entry + routes)
    return man, sorted({man[k]["file"] for k in keys if man[k]["file"].endswith(".js")})


def test_initial_js_gzip_budget(build_dir):
    """R1-010 AC1 / L-P01：登录页 + 工作台首屏 JS 合计 gzip ≤ 300KB。"""
    _man, files = initial_chunks(build_dir)
    sizes = {f: _gz(build_dir / f) for f in files}
    total = sum(sizes.values())
    (build_dir / "initial-js.json").write_text(json.dumps({"total_gzip": total, "files": sizes}, indent=1), encoding="utf-8")
    assert total <= LIMIT_INITIAL_GZIP, f"首屏 JS gzip {total / 1024:.1f}KB > 300KB: {sizes}"


def test_no_chunk_over_500kb(build_dir):
    """R1-010 AC1：不存在 >500KB 的 chunk。"""
    big = {p.name: p.stat().st_size for p in (build_dir / "assets").glob("*.js") if p.stat().st_size > LIMIT_CHUNK_RAW}
    assert not big, f"超过 500KB 的 chunk: {big}"


def test_login_path_excludes_html2pdf_and_katex(build_dir):
    """R1-010 AC2：登录页/工作台首屏不包含 html2pdf（html2canvas/jspdf）与 KaTeX 代码。"""
    _man, files = initial_chunks(build_dir)
    bad = []
    for f in files:
        t = (build_dir / f).read_text(encoding="utf-8", errors="ignore")
        for sig in ("html2canvas", "jsPDF", "KaTeX parse error", "katex-display", "remark-math"):
            if sig in t:
                bad.append((f, sig))
    assert not bad, bad
    css = [p.name for p in (build_dir / "assets").glob("*.css")
           if "katex" in p.read_text(encoding="utf-8", errors="ignore")[:2000].lower()]
    idx = (build_dir / "index.html").read_text(encoding="utf-8")
    assert not any(c in idx for c in css), f"KaTeX CSS 被 index.html 直接引用: {css}"


# ====================================================================== R1-012 KaTeX（组件级）

REAL_Q4 = ("所以 \\(f(x_1)-f(x_2)=\\displaystyle =\\frac{x_2-x_1}{x_1x_2}>0\\)\\n故 \\(f(x)\\) 在 \\((0,+\\infty)\\) 上单调递减。"
           "\\n另有 $$\\sqrt{2}+x^{2}$$")


def _mathtext():
    hits = [p for p in FRONTEND_SRC.rglob("MathText.*")]
    if not hits:
        pytest.xfail("待开发：公共组件 MathText")
    return "src/" + hits[0].relative_to(FRONTEND_SRC).as_posix()


def _render(mod: str, text: str):
    props = {"text": text, "content": text, "children": text}
    p = subprocess.run(["node", str(ACCEPTANCE_DIR / "js" / "ssr_call.mjs"), "render", mod, "default",
                        json.dumps(props, ensure_ascii=False)], cwd=str(FRONTEND), capture_output=True,
                       text=True, encoding="utf-8", timeout=180)
    line = next((l for l in p.stdout.splitlines() if l.startswith("RESULT:")), None)
    assert line, p.stdout[-500:] + p.stderr[-800:]
    out = json.loads(line[7:])
    if "error" in out and "export default not found" in out["error"]:
        pytest.fail(f"MathText 未默认导出: {out['error'][:200]}")
    return out


def _visible_text(html: str) -> str:
    html = re.sub(r"<annotation[^>]*>.*?</annotation>", "", html, flags=re.S)   # MathML 中的 TeX 源码对用户不可见
    html = re.sub(r'<span class="katex-mathml">.*?</math></span>', "", html, flags=re.S)
    return htmlmod.unescape(re.sub(r"<[^>]+>", "", html))


def test_mathtext_renders_real_result():
    """R1-012 AC1 / L-U05：真实批改结果渲染出 .katex，文本中无 \\displaystyle、\\frac、\\(、字面量 \\n。"""
    out = _render(_mathtext(), REAL_Q4)
    assert "error" not in out, out.get("error")
    h = out["html"]
    assert 'class="katex' in h, h[:500]
    vis = _visible_text(h)
    for bad in ("\\displaystyle", "\\frac", "\\(", "\\n", "\\sqrt", "$$"):
        assert bad not in vis, f"可见文本出现 {bad!r}: {vis[:300]}"


def test_mathtext_invalid_latex_falls_back():
    """R1-012 AC3：非法 LaTeX（$\\frac{1$）显示原文，不抛异常。"""
    out = _render(_mathtext(), "错误公式 $\\frac{1$ 之后的文字")
    assert "error" not in out, f"渲染抛异常: {out.get('error', '')[:300]}"
    vis = _visible_text(out["html"])
    assert "之后的文字" in vis and ("\\frac{1" in vis or "katex-error" in out["html"]), vis


def test_mathtext_used_on_all_math_surfaces():
    """R1-012 AC2 / 方案：结果页、错题本、逐题正确率、教案都用 MathText；cleanLatex 正则已移除。"""
    assert not grep_frontend(r"cleanLatex"), grep_frontend(r"cleanLatex")
    users = {h[0] for h in grep_frontend(r"<MathText\b")}
    for page in ("WrongNotebook", "HomeworkDetail", "TaskDetail|Review|Result"):
        assert any(re.search(page, u) for u in users), f"{page} 未使用 MathText: {users}"


# ====================================================================== R1-014 三态与 404（静态）

def test_state_components_and_no_swallowed_errors():
    """R1-014 方案：Loading / Empty / ErrorState 公共组件存在；不再有 .catch(() => {}) 吞错。"""
    names = {p.stem for p in FRONTEND_SRC.rglob("*.jsx")}
    for need in (r"Loading", r"Empty", r"Error"):
        assert any(re.search(need, n) for n in names), f"缺少公共组件 {need}: {sorted(names)}"
    swallowed = grep_frontend(r"\.catch\(\s*\(\s*\w*\s*\)\s*=>\s*\{\s*\}\s*\)|catch\s*\(\w*\)\s*\{\s*\}")
    assert not swallowed, swallowed
    assert grep_frontend(r"重试"), "缺少“重试”按钮文案"


def test_not_found_route():
    """R1-014 AC3 / L-U08（静态）：未知路由有 404 页，含“页面不存在”“回到工作台”。"""
    app = _app_src()
    assert re.search(r"path=[\"']\*[\"']", app), "缺少 * 路由"
    assert grep_frontend(r"页面不存在") and grep_frontend(r"回到工作台"), "404 页文案缺失"
