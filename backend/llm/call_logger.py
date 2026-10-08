"""
模型调用日志：每次调用追加一行到 api_calls.jsonl。

目录由本模块写入，api_yibu_sumarize.py 可直接统计：
  api_runs/
    <YYYYmmdd_HHMMSS>_backend_key<后四位>_<run前8位>/
      api_calls.jsonl    # 每次调用一行（schema api_call_log_v4）
      responses.jsonl    # 精简的响应记录
      run_meta.json
      summary.json       # 本进程累计汇总，每次调用后刷新

一个后端进程对应一个 run 目录，首次调用时才创建。
"""

import asyncio
import copy
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

LOG_SCHEMA = "api_call_log_v4"
_IMAGE_PLACEHOLDER = "<image omitted: {n} chars>"


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def key_suffix(api_key: str) -> str:
    return api_key[-4:] if api_key and len(api_key) >= 4 else "none"


def zero_usage() -> Dict[str, int]:
    return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "reasoning_tokens": 0}


def _json_line(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)


def sanitize_messages(messages: List[Dict[str, Any]], keep_content: bool) -> List[Dict[str, Any]]:
    """日志里去掉 base64 图片；keep_content=False 时只保留长度。"""
    cleaned = copy.deepcopy(messages)
    for msg in cleaned:
        content = msg.get("content")
        if isinstance(content, str):
            if not keep_content:
                msg["content"] = f"<{len(content)} chars>"
        elif isinstance(content, list):
            for part in content:
                if part.get("type") == "image_url":
                    url = (part.get("image_url") or {}).get("url", "")
                    if url.startswith("data:"):
                        part["image_url"] = {"url": _IMAGE_PLACEHOLDER.format(n=len(url))}
                elif part.get("type") == "text" and not keep_content:
                    part["text"] = f"<{len(part.get('text', ''))} chars>"
    return cleaned


class CallLogger:
    def __init__(self, log_root: str, api_key: str, base_url: str, source: str = "backend"):
        self.log_root = os.path.abspath(log_root)
        self.api_key_suffix = key_suffix(api_key)
        self.base_url = base_url
        self.source = source
        self._lock = asyncio.Lock()
        self._run_meta: Optional[Dict[str, Any]] = None
        self._totals = {"total_calls": 0, "success_calls": 0, "failed_calls": 0,
                        "elapsed_seconds": 0.0, "usage": zero_usage(), "by_feature": {}}

    def _ensure_run(self) -> Dict[str, Any]:
        if self._run_meta is not None:
            return self._run_meta

        run_id = str(uuid.uuid4())
        run_ts_local = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(
            self.log_root, f"{run_ts_local}_{self.source}_key{self.api_key_suffix}_{run_id[:8]}"
        )
        os.makedirs(run_dir, exist_ok=True)

        meta = {
            "schema_version": "api_run_meta_v4",
            "run_id": run_id,
            "run_id_short": run_id[:8],
            "run_ts_local": run_ts_local,
            "run_ts_utc": now_utc_iso(),
            "run_dir": run_dir,
            "source": self.source,
            "api_key_suffix": self.api_key_suffix,
            "base_url": self.base_url,
            "pid": os.getpid(),
            "log_jsonl": os.path.join(run_dir, "api_calls.jsonl"),
            "response_jsonl": os.path.join(run_dir, "responses.jsonl"),
            "summary_json": os.path.join(run_dir, "summary.json"),
        }
        with open(os.path.join(run_dir, "run_meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        self._run_meta = meta
        return meta

    def _accumulate(self, feature: str, success: bool, elapsed: float, usage: Dict[str, int]) -> None:
        t = self._totals
        t["total_calls"] += 1
        t["success_calls" if success else "failed_calls"] += 1
        t["elapsed_seconds"] = round(t["elapsed_seconds"] + elapsed, 4)
        for k in t["usage"]:
            t["usage"][k] += int(usage.get(k) or 0)

        f = t["by_feature"].setdefault(feature, {"calls": 0, "failed": 0, "total_tokens": 0})
        f["calls"] += 1
        f["failed"] += 0 if success else 1
        f["total_tokens"] += int(usage.get("total_tokens") or 0)

    def _write_summary(self, meta: Dict[str, Any]) -> None:
        t = self._totals
        summary = {
            "schema_version": "api_run_summary_v4",
            "run_id": meta["run_id"],
            "run_dir": meta["run_dir"],
            "run_ts_local": meta["run_ts_local"],
            "run_ts_utc": meta["run_ts_utc"],
            "updated_utc": now_utc_iso(),
            "source": self.source,
            "api_key_suffix": self.api_key_suffix,
            "base_url": self.base_url,
            **t,
            "success_rate": round(t["success_calls"] / t["total_calls"] * 100, 4) if t["total_calls"] else 0,
        }
        tmp = meta["summary_json"] + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        os.replace(tmp, meta["summary_json"])

    async def log_call(
        self,
        *,
        call_id: str,
        task_id: str,
        feature: str,
        model: str,
        request: Dict[str, Any],
        task_meta: Dict[str, Any],
        success: bool,
        elapsed: float,
        usage: Dict[str, int],
        content: str,
        finish_reason: Optional[str],
        response_id: Optional[str],
        error: Optional[Dict[str, str]],
    ) -> None:
        """写日志失败只打印，不影响业务调用。"""
        try:
            async with self._lock:
                meta = self._ensure_run()
                ts = now_utc_iso()
                record = {
                    "schema_version": LOG_SCHEMA,
                    "run_id": meta["run_id"],
                    "run_dir": meta["run_dir"],
                    "run_ts_local": meta["run_ts_local"],
                    "run_ts_utc": meta["run_ts_utc"],
                    "call_id": call_id,
                    "task_id": task_id,
                    "ts_utc": ts,
                    "api_key_suffix": self.api_key_suffix,
                    "model": model,
                    "base_url": self.base_url,
                    "success": success,
                    "elapsed_seconds": round(elapsed, 4),
                    "usage": usage,
                    "request": request,
                    "task_meta": task_meta,
                    "response": {"content": content, "finish_reason": finish_reason,
                                 "raw_response_id": response_id},
                    "error": error,
                    "source": self.source,
                    "feature": feature,
                }
                with open(meta["log_jsonl"], "a", encoding="utf-8") as f:
                    f.write(_json_line(record) + "\n")
                with open(meta["response_jsonl"], "a", encoding="utf-8") as f:
                    f.write(_json_line({
                        "run_id": meta["run_id"], "task_id": task_id, "call_id": call_id,
                        "api_key_suffix": self.api_key_suffix, "model": model, "feature": feature,
                        "success": success, "elapsed_seconds": round(elapsed, 4), "usage": usage,
                        "content": content, "error": error,
                    }) + "\n")
                self._accumulate(feature, success, elapsed, usage)
                self._write_summary(meta)
        except Exception as e:  # noqa: BLE001
            print(f"[llm] 写调用日志失败：{type(e).__name__}: {e}")
