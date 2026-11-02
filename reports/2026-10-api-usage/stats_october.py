# -*- coding: utf-8 -*-
"""统计 2026-10 全月模型调用 token（北京时间区间）。

数据：从生产服务器下载的 api_runs/ + model_eval_20261015/（43 个 api_calls.jsonl）。
用法（在 backend 目录外也能跑，把 backend 加入 sys.path）：
    py reports/2026-10-api-usage/stats_october.py
"""
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent / "backend"))

from usage_stats import load_call_records, summarize  # noqa: E402

# 北京时间 2026-10-01 00:00 ~ 2026-11-01 00:00
SINCE = "2026-09-30T16:00:00+00:00"
UNTIL = "2026-10-31T16:00:00+00:00"


def main() -> None:
    recs = load_call_records(str(ROOT), since=SINCE, until=UNTIL)
    stats = summarize(recs)
    ov = stats["overview"]

    out = {
        "range_beijing": "2026-10-01 00:00 ~ 2026-10-31 24:00 (北京时间)",
        "prompt_tokens_in": ov["prompt_tokens"],
        "completion_tokens_out": ov["completion_tokens"],
        "total_tokens": ov["total_tokens"],
        "reasoning_tokens": ov["reasoning_tokens"],
        "calls": ov["calls"],
        "success": ov["success"],
        "failed": ov["failed"],
        "first_ts_utc": ov["first_ts"],
        "last_ts_utc": ov["last_ts"],
        "by_source": [
            {"source": r["source"], "calls": r["calls"], "prompt_tokens": r["prompt_tokens"],
             "completion_tokens": r["completion_tokens"], "total_tokens": r["total_tokens"]}
            for r in stats["by_source"]
        ],
        "by_key": [
            {"key_suffix": r["key_suffix"], "calls": r["calls"],
             "prompt_tokens": r["prompt_tokens"], "completion_tokens": r["completion_tokens"],
             "total_tokens": r["total_tokens"], "success": r["success"], "failed": r["failed"]}
            for r in stats["by_key"]
        ],
        "by_model": [
            {"model": r["model"], "calls": r["calls"],
             "prompt_tokens": r["prompt_tokens"], "completion_tokens": r["completion_tokens"],
             "total_tokens": r["total_tokens"]}
            for r in stats["by_model"]
        ],
        "by_module": [
            {"module": r["module"], "calls": r["calls"], "prompt_tokens": r["prompt_tokens"],
             "completion_tokens": r["completion_tokens"], "total_tokens": r["total_tokens"]}
            for r in stats["by_module"]
        ],
        "by_day": [
            {"day": r["day"], "calls": r["calls"], "total_tokens": r["total_tokens"]}
            for r in stats["by_day"]
        ],
    }
    dest = ROOT / "october_token_stats.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main()
