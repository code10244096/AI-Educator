# -*- coding: utf-8 -*-
"""
模型调用用量统计（纯函数模块，无 FastAPI 依赖）。

日志约定：
  <log_root>/<run_dir>/api_calls.jsonl   每行一次调用（最后可能有 run_summary 行，跳过）
  responses.jsonl 为重复内容，不统计。

安全：加载时只保留统计所需的轻量字段，request / response 正文一律丢弃，
key 只保留 4 位后缀（api_key_suffix）。
"""

import json
import os
import statistics
import threading
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

LOG_FILE_NAME = "api_calls.jsonl"
ERROR_MAX_CHARS = 300

KNOWN_FEATURES = ("ocr", "grade", "lessonplan", "variant", "seed_grade", "other")


# =========================
# 基础工具
# =========================

def default_log_root() -> str:
    """日志根目录：环境变量 API_OUTPUT_ROOT，否则 <repo>/api_runs。"""
    env = os.environ.get("API_OUTPUT_ROOT", "").strip()
    if env:
        return os.path.abspath(env)
    return str(Path(__file__).resolve().parent.parent / "api_runs")


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def parse_ts(value: Any) -> Optional[float]:
    """把 ISO 时间 / 日期字符串解析为 epoch 秒；无时区视为 UTC。失败返回 None。"""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    if s.endswith("Z") or s.endswith("z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def is_real_call_record(row: Dict[str, Any]) -> bool:
    """是否为真实的一次 API 调用记录（跳过 run_summary 行）。"""
    if row.get("type") == "run_summary":
        return False
    if "summary" in str(row.get("schema_version", "")):
        return False
    if not row.get("call_id"):
        return False
    return True


def find_api_call_logs(root: str, pattern: str = LOG_FILE_NAME) -> List[str]:
    """root 可以是单个 jsonl 文件、单个 run 目录，或 api_runs 根目录。"""
    root = os.path.abspath(root)
    if os.path.isfile(root):
        return [root]
    if not os.path.isdir(root):
        return []
    matches: List[str] = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if name == pattern:
                matches.append(os.path.join(dirpath, name))
    return sorted(matches)


def _error_message(err: Any) -> str:
    if not err:
        return ""
    if isinstance(err, dict):
        msg = err.get("message") or err.get("type") or ""
        etype = err.get("type")
        if etype and msg and msg != etype:
            msg = f"{etype}: {msg}"
    else:
        msg = str(err)
    msg = str(msg)
    return msg[:ERROR_MAX_CHARS]


def _slim_record(row: Dict[str, Any], source_file: str) -> Dict[str, Any]:
    """只保留统计字段，丢弃 request / response 正文。"""
    usage = row.get("usage") or {}
    if not isinstance(usage, dict):
        usage = {}
    response = row.get("response") or {}
    ts = str(row.get("ts_utc") or "")
    return {
        "schema_version": str(row.get("schema_version") or ""),
        "run_id": str(row.get("run_id") or ""),
        "call_id": str(row.get("call_id") or ""),
        "task_id": str(row.get("task_id") or ""),
        "ts_utc": ts,
        "_ts_epoch": parse_ts(ts),
        "api_key_suffix": str(row.get("api_key_suffix") or "unknown"),
        "model": str(row.get("model") or "unknown"),
        "success": bool(row.get("success")),
        "elapsed_seconds": safe_float(row.get("elapsed_seconds")),
        "usage": {
            "prompt_tokens": safe_int(usage.get("prompt_tokens")),
            "completion_tokens": safe_int(usage.get("completion_tokens")),
            "total_tokens": safe_int(usage.get("total_tokens")),
            "reasoning_tokens": safe_int(usage.get("reasoning_tokens")),
        },
        "finish_reason": (response.get("finish_reason") if isinstance(response, dict) else None),
        "error_message": _error_message(row.get("error")),
        "source": str(row.get("source") or "cli"),
        "feature": str(row.get("feature") or "unknown"),
        "_source_file": source_file,
    }


# =========================
# 读取（带 mtime 缓存）
# =========================

_cache_lock = threading.Lock()
# path -> (mtime_ns, size, records, counters)
_file_cache: Dict[str, Tuple[int, int, List[Dict[str, Any]], Dict[str, int]]] = {}


def _load_file(path: str) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    path = os.path.abspath(path)
    try:
        st = os.stat(path)
    except OSError:
        return [], {"summary_rows": 0, "invalid_rows": 0}

    with _cache_lock:
        cached = _file_cache.get(path)
        if cached and cached[0] == st.st_mtime_ns and cached[1] == st.st_size:
            return cached[2], cached[3]

    records: List[Dict[str, Any]] = []
    counters = {"summary_rows": 0, "invalid_rows": 0}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    counters["invalid_rows"] += 1
                    continue
                if not isinstance(obj, dict):
                    counters["invalid_rows"] += 1
                    continue
                if obj.get("type") == "run_summary" or "summary" in str(obj.get("schema_version", "")):
                    counters["summary_rows"] += 1
                    continue
                if not is_real_call_record(obj):
                    counters["invalid_rows"] += 1
                    continue
                records.append(_slim_record(obj, path))
    except OSError:
        return [], counters

    with _cache_lock:
        _file_cache[path] = (st.st_mtime_ns, st.st_size, records, counters)
    return records, counters


def clear_cache() -> None:
    with _cache_lock:
        _file_cache.clear()


def scan_logs(root: Optional[str] = None) -> Dict[str, Any]:
    """扫描全部日志，返回 {"records", "log_files", "skipped_summary_rows", "skipped_invalid_rows"}。"""
    root = root or default_log_root()
    files = find_api_call_logs(root)
    all_records: List[Dict[str, Any]] = []
    skipped_summary = 0
    skipped_invalid = 0
    for path in files:
        recs, counters = _load_file(path)
        all_records.extend(recs)
        skipped_summary += counters["summary_rows"]
        skipped_invalid += counters["invalid_rows"]
    return {
        "records": all_records,
        "log_files": files,
        "skipped_summary_rows": skipped_summary,
        "skipped_invalid_rows": skipped_invalid,
    }


def _split_filter(value: Any) -> Optional[set]:
    if value is None or value == "":
        return None
    if isinstance(value, (list, tuple, set)):
        items = [str(v).strip() for v in value]
    else:
        items = [x.strip() for x in str(value).split(",")]
    items = [x for x in items if x]
    return set(items) or None


def filter_records(
    records: Iterable[Dict[str, Any]],
    since: Any = None,
    until: Any = None,
    source: Any = None,
    feature: Any = None,
    success: Optional[bool] = None,
    model: Any = None,
) -> List[Dict[str, Any]]:
    """since/until 接受 ISO 字符串或 epoch 秒（无时区按 UTC）；source/feature/model 支持逗号分隔多值。"""
    since_ts = parse_ts(since)
    until_ts = parse_ts(until)
    sources = _split_filter(source)
    features = _split_filter(feature)
    models = _split_filter(model)

    out = []
    for r in records:
        ts = r.get("_ts_epoch")
        if since_ts is not None and (ts is None or ts < since_ts):
            continue
        if until_ts is not None and (ts is None or ts > until_ts):
            continue
        if sources and r.get("source") not in sources:
            continue
        if features and r.get("feature") not in features:
            continue
        if models and r.get("model") not in models:
            continue
        if success is not None and bool(r.get("success")) != bool(success):
            continue
        out.append(r)
    return out


def load_call_records(
    root: Optional[str] = None,
    since: Any = None,
    until: Any = None,
    source: Any = None,
    feature: Any = None,
) -> List[Dict[str, Any]]:
    """
    读取并过滤调用记录（轻量字典，已去除请求/响应正文）。
    返回的字典来自缓存，调用方请勿修改。
    """
    records = scan_logs(root)["records"]
    return filter_records(records, since=since, until=until, source=source, feature=feature)


# =========================
# 汇总
# =========================

def _new_stat() -> Dict[str, Any]:
    return {
        "calls": 0,
        "unique_call_ids": set(),
        "duplicate_call_id_count": 0,
        "success": 0,
        "failed": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "reasoning_tokens": 0,
        "elapsed_seconds": 0.0,
        "elapsed_values": [],
        "run_ids": set(),
        "task_ids": set(),
        "log_files": set(),
        "first_ts": "",
        "last_ts": "",
    }


def _update_stat(stat: Dict[str, Any], row: Dict[str, Any]) -> None:
    stat["calls"] += 1
    call_id = row.get("call_id") or ""
    if call_id:
        if call_id in stat["unique_call_ids"]:
            stat["duplicate_call_id_count"] += 1
        stat["unique_call_ids"].add(call_id)

    if row.get("success"):
        stat["success"] += 1
    else:
        stat["failed"] += 1

    usage = row.get("usage") or {}
    stat["prompt_tokens"] += safe_int(usage.get("prompt_tokens"))
    stat["completion_tokens"] += safe_int(usage.get("completion_tokens"))
    stat["total_tokens"] += safe_int(usage.get("total_tokens"))
    stat["reasoning_tokens"] += safe_int(usage.get("reasoning_tokens"))

    elapsed = safe_float(row.get("elapsed_seconds"))
    stat["elapsed_seconds"] += elapsed
    stat["elapsed_values"].append(elapsed)

    if row.get("run_id"):
        stat["run_ids"].add(row["run_id"])
    if row.get("task_id"):
        stat["task_ids"].add(row["task_id"])
    if row.get("_source_file"):
        stat["log_files"].add(row["_source_file"])

    ts = row.get("ts_utc") or ""
    if ts:
        if not stat["first_ts"] or ts < stat["first_ts"]:
            stat["first_ts"] = ts
        if not stat["last_ts"] or ts > stat["last_ts"]:
            stat["last_ts"] = ts


def _finalize_stat(stat: Dict[str, Any], include_log_files: bool = False) -> Dict[str, Any]:
    calls = stat["calls"]
    success = stat["success"]
    values = stat["elapsed_values"]
    out = {
        "calls": calls,
        "unique_call_ids": len(stat["unique_call_ids"]),
        "duplicate_call_id_count": stat["duplicate_call_id_count"],
        "success": success,
        "failed": stat["failed"],
        "success_rate": round(success / calls * 100, 4) if calls else 0,
        "prompt_tokens": stat["prompt_tokens"],
        "completion_tokens": stat["completion_tokens"],
        "total_tokens": stat["total_tokens"],
        "reasoning_tokens": stat["reasoning_tokens"],
        "avg_total_tokens_per_call": round(stat["total_tokens"] / calls, 4) if calls else 0,
        "avg_prompt_tokens_per_call": round(stat["prompt_tokens"] / calls, 4) if calls else 0,
        "avg_completion_tokens_per_call": round(stat["completion_tokens"] / calls, 4) if calls else 0,
        "elapsed_seconds": round(stat["elapsed_seconds"], 4),
        "avg_elapsed_seconds": round(stat["elapsed_seconds"] / calls, 4) if calls else 0,
        "median_elapsed_seconds": round(statistics.median(values), 4) if values else 0,
        "run_count": len(stat["run_ids"]),
        "task_count": len(stat["task_ids"]),
        "log_file_count": len(stat["log_files"]),
        "first_ts": stat["first_ts"],
        "last_ts": stat["last_ts"],
    }
    if include_log_files:
        out["log_files"] = ";".join(sorted(stat["log_files"]))
    return out


def _local_day(row: Dict[str, Any]) -> str:
    ts = row.get("_ts_epoch")
    if ts is None:
        return "unknown"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def summarize(records: List[Dict[str, Any]], include_log_files: bool = False) -> Dict[str, Any]:
    """
    返回（均可 JSON 序列化）：
      overview   总计
      by_model / by_key / by_feature / by_source   按 total_tokens 降序
      by_day     按本地日期升序（字段 day）
      key_model  key + model 明细
    """
    overall = _new_stat()
    groups: Dict[str, Dict[Any, Dict[str, Any]]] = {
        "by_model": defaultdict(_new_stat),
        "by_key": defaultdict(_new_stat),
        "by_feature": defaultdict(_new_stat),
        "by_source": defaultdict(_new_stat),
        "by_day": defaultdict(_new_stat),
        "key_model": defaultdict(_new_stat),
    }

    for row in records:
        key_suffix = row.get("api_key_suffix") or "unknown"
        model = row.get("model") or "unknown"
        _update_stat(overall, row)
        _update_stat(groups["by_model"][model], row)
        _update_stat(groups["by_key"][key_suffix], row)
        _update_stat(groups["by_feature"][row.get("feature") or "unknown"], row)
        _update_stat(groups["by_source"][row.get("source") or "cli"], row)
        _update_stat(groups["by_day"][_local_day(row)], row)
        _update_stat(groups["key_model"][(key_suffix, model)], row)

    def build(name: str, label: str) -> List[Dict[str, Any]]:
        items = []
        for k, stat in groups[name].items():
            item = {label: k}
            item.update(_finalize_stat(stat, include_log_files))
            items.append(item)
        items.sort(key=lambda x: (-x["total_tokens"], -x["calls"], str(x[label])))
        return items

    key_model = []
    for (key_suffix, model), stat in groups["key_model"].items():
        item = {"key_suffix": key_suffix, "model": model}
        item.update(_finalize_stat(stat, include_log_files))
        key_model.append(item)
    key_model.sort(key=lambda x: (x["key_suffix"], -x["total_tokens"], x["model"]))

    by_day = build("by_day", "day")
    by_day.sort(key=lambda x: x["day"])

    return {
        "overview": _finalize_stat(overall, include_log_files),
        "by_model": build("by_model", "model"),
        "by_key": build("by_key", "key_suffix"),
        "by_feature": build("by_feature", "feature"),
        "by_source": build("by_source", "source"),
        "by_day": by_day,
        "key_model": key_model,
    }


def recent_calls(records: List[Dict[str, Any]], limit: int = 50) -> List[Dict[str, Any]]:
    """最近调用（新 -> 旧），仅轻量字段，不含请求/响应内容。"""
    limit = max(0, int(limit))
    ordered = sorted(
        records,
        key=lambda r: (r.get("_ts_epoch") or 0.0, r.get("ts_utc") or ""),
        reverse=True,
    )
    out = []
    for r in ordered[:limit]:
        out.append({
            "ts_utc": r.get("ts_utc"),
            "call_id": r.get("call_id"),
            "task_id": r.get("task_id"),
            "feature": r.get("feature"),
            "source": r.get("source"),
            "model": r.get("model"),
            "api_key_suffix": r.get("api_key_suffix"),
            "success": bool(r.get("success")),
            "elapsed_seconds": r.get("elapsed_seconds"),
            "usage": dict(r.get("usage") or {}),
            "finish_reason": r.get("finish_reason"),
            "error": (r.get("error_message") or "")[:ERROR_MAX_CHARS] or None,
        })
    return out
