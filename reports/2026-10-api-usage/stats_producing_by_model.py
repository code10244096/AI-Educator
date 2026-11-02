# -*- coding: utf-8 -*-
"""10 月"真实产出内容"的 API 调用统计（按模型）。

口径：
  1. 时间：北京时间 2026-10-01 00:00 ~ 2026-10-31 24:00
  2. 只算成功且实际产出了内容的调用（success=True 且 completion_tokens>0）
  3. 双通道核算：usage_stats 模块 vs 原生 json 逐行解析，二者必须完全一致
"""
import io
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent / "backend"))

BEIJING = timezone(timedelta(hours=8))
T0 = datetime(2026, 10, 1, 0, 0, 0, tzinfo=BEIJING).timestamp()
T1 = datetime(2026, 11, 1, 0, 0, 0, tzinfo=BEIJING).timestamp()


def parse_ts(ts):
    if not ts:
        return None
    s = str(ts).strip()
    if s.endswith(("Z", "z")):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


# ---------------- 通道一：原生逐行解析（含逐文件明细，供对账） ----------------
per_model = defaultdict(lambda: {"calls": 0, "prompt": 0, "completion": 0, "files": defaultdict(int)})
excluded_fail = defaultdict(int)   # model -> 失败/无产出 次数
all_rows = 0
in_range = 0

for path in sorted(ROOT.rglob("api_calls.jsonl")):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("type") == "run_summary" or not row.get("call_id"):
                continue
            all_rows += 1
            ts = parse_ts(row.get("ts_utc"))
            if ts is None or not (T0 <= ts < T1):
                continue
            in_range += 1
            model = row.get("model") or "unknown"
            usage = row.get("usage") or {}
            comp = int(usage.get("completion_tokens") or 0)
            ok = bool(row.get("success"))
            if ok and comp > 0:
                per_model[model]["calls"] += 1
                per_model[model]["prompt"] += int(usage.get("prompt_tokens") or 0)
                per_model[model]["completion"] += comp
                per_model[model]["files"][str(path.relative_to(ROOT))] += 1
            else:
                excluded_fail[model] += 1

# ---------------- 通道二：usage_stats 模块 ----------------
from usage_stats import load_call_records  # noqa: E402
recs = load_call_records(str(ROOT), since="2026-09-30T16:00:00+00:00", until="2026-10-31T16:00:00+00:00")
check = defaultdict(lambda: {"calls": 0, "prompt": 0, "completion": 0})
for r in recs:
    u = r["usage"]
    if r["success"] and (u.get("completion_tokens") or 0) > 0:
        check[r["model"]]["calls"] += 1
        check[r["model"]]["prompt"] += u["prompt_tokens"]
        check[r["model"]]["completion"] += u["completion_tokens"]

mismatch = []
for m in set(per_model) | set(check):
    a, b = per_model.get(m), check.get(m)
    if not a or not b or (a["calls"], a["prompt"], a["completion"]) != (b["calls"], b["prompt"], b["completion"]):
        mismatch.append(m)

# ---------------- 汇总输出 ----------------
out = {
    "range_beijing": "2026-10-01 00:00 ~ 2026-10-31 24:00",
    "criteria": "success=True 且 completion_tokens>0（真实产出内容的调用）",
    "raw_rows_total": all_rows,
    "rows_in_october": in_range,
    "consistency_check": "PASS（双通道核算一致）" if not mismatch else f"FAIL: {mismatch}",
    "producing_calls": sum(v["calls"] for v in per_model.values()),
    "excluded_no_output_calls": sum(excluded_fail.values()),
    "prompt_tokens": sum(v["prompt"] for v in per_model.values()),
    "completion_tokens": sum(v["completion"] for v in per_model.values()),
    "by_model": [
        {
            "model": m,
            "calls": v["calls"],
            "prompt_tokens": v["prompt"],
            "completion_tokens": v["completion"],
            "total_tokens": v["prompt"] + v["completion"],
            "files": dict(sorted(v["files"].items())),
        }
        for m, v in sorted(per_model.items(), key=lambda kv: -(kv[1]["prompt"] + kv[1]["completion"]))
    ],
    "excluded_by_model": dict(sorted(excluded_fail.items())),
}
(ROOT / "october_stats_producing_by_model.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
print(json.dumps({k: out[k] for k in ("consistency_check", "producing_calls",
      "excluded_no_output_calls", "prompt_tokens", "completion_tokens")}, ensure_ascii=False))
print(f"{'模型':<42}{'产出调用':>6}{'输入token':>12}{'输出token':>12}{'总token':>12}")
for item in out["by_model"]:
    print(f"{item['model']:<42}{item['calls']:>6}{item['prompt_tokens']:>12,}{item['completion_tokens']:>12,}{item['total_tokens']:>12,}")
print("\n被排除（失败/无产出）按模型：", dict(sorted(excluded_fail.items())))
