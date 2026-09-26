"""Every API call in frontend/src/utils/api.js must hit a real backend route (method + path)."""
import re

import pytest
from starlette.routing import Match

from conftest import REPO_ROOT

API_JS = REPO_ROOT / "frontend" / "src" / "utils" / "api.js"
CALL_RE = re.compile(r"api\.(get|post|put|patch|delete)\(\s*[`'\"]([^`'\"]+)[`'\"]")


def _calls():
    if not API_JS.exists():
        return []
    text = API_JS.read_text(encoding="utf-8")
    out = sorted({(m.group(1).upper(), m.group(2)) for m in CALL_RE.finditer(text)})
    return out


@pytest.mark.parametrize("method,path", _calls(), ids=lambda v: str(v))
def test_frontend_call_has_backend_route(app_module, method, path):
    concrete = re.sub(r"\$\{[^}]*\}", "1", path).split("?")[0]
    # slug-like params
    concrete = concrete.replace("/class/1", "/class/class1") if concrete.startswith("/class/1") else concrete
    scope = {"type": "http", "path": "/api" + concrete, "method": method, "root_path": ""}
    full = partial = False
    for route in app_module.app.router.routes:
        m, _ = route.matches(scope)
        if m == Match.FULL:
            full = True
            break
        if m == Match.PARTIAL:
            partial = True
    assert full, f"{method} /api{path}: " + ("method not allowed" if partial else "no such route")


def test_api_js_found():
    assert _calls(), f"no api calls parsed from {API_JS}"
