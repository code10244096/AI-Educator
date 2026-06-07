"""本地自检：写入 service-check.json 供 Agent 读取"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULT = ROOT / "service-check.json"


def run(cmd, cwd=None):
    try:
        p = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=30
        )
        return {"ok": p.returncode == 0, "code": p.returncode, "out": p.stdout[-2000:], "err": p.stderr[-2000:]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def check_url(url):
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=5) as r:
            return {"ok": True, "status": r.status, "body": r.read(200).decode("utf-8", errors="replace")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    report = {
        "time": datetime.now().isoformat(),
        "python": sys.version,
        "cwd": str(ROOT),
        "checks": {},
    }

    report["checks"]["import_backend"] = run(
        f'"{sys.executable}" -c "import sys; sys.path.insert(0, r\'{ROOT / "backend"}\'); from main import app; print(\'ok\')"',
        cwd=ROOT / "backend",
    )

    report["checks"]["health_8000"] = check_url("http://127.0.0.1:8000/health")
    report["checks"]["frontend_3000"] = check_url("http://127.0.0.1:3000")
    report["checks"]["frontend_5173"] = check_url("http://127.0.0.1:5173")

    netstat = run("netstat -ano | findstr \":3000 :8000 :5173\"")
    report["checks"]["netstat"] = netstat

    RESULT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {RESULT}")


if __name__ == "__main__":
    main()
