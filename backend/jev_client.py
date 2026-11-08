"""Jev systemone 语义相关度客户端（题库搜索重排）。

不走 /chat/completions；POST {base_url}/systemone，按每题 noul 概率排序。
用量写入现有 CallLogger（feature=questionbank_search）。
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

import httpx

from llm.call_logger import CallLogger, zero_usage

FEATURE = "questionbank_search"
DEFAULT_MODEL = "jev-latest"
DEFAULT_CANDIDATE_LIMIT = 50
MAX_CANDIDATE_LIMIT = 100
DEFAULT_TIMEOUT = 60.0
PREVIEW_CHARS = 220
MAX_KNOWLEDGE_POINTS = 5


class JevError(Exception):
    """Jev 调用失败（网络、鉴权、超时、响应格式等），调用方可降级。"""


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def candidate_limit() -> int:
    return max(1, min(_env_int("JEV_SEARCH_CANDIDATE_LIMIT", DEFAULT_CANDIDATE_LIMIT), MAX_CANDIDATE_LIMIT))


def search_timeout() -> float:
    return max(5.0, _env_float("JEV_SEARCH_TIMEOUT", DEFAULT_TIMEOUT))


def jev_model() -> str:
    return (os.getenv("JEV_MODEL") or "").strip() or DEFAULT_MODEL


def _preview_text(text: str, limit: int = PREVIEW_CHARS) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def _parse_knowledge_points(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            items = parsed if isinstance(parsed, list) else [text]
        except json.JSONDecodeError:
            items = [part.strip() for part in text.split(",") if part.strip()]
    else:
        items = [str(raw)]
    out: List[str] = []
    for item in items:
        name = str(item or "").strip()
        if name and name not in out:
            out.append(name)
        if len(out) >= MAX_KNOWLEDGE_POINTS:
            break
    return out


def build_noul_question(
    *,
    question_id: int,
    question_text: str,
    knowledge_points: Any,
    keyword: str,
) -> Dict[str, Any]:
    kps = _parse_knowledge_points(knowledge_points)
    kp_text = "、".join(kps) if kps else "（未标注）"
    instructions = (
        f"候选ID={question_id}；"
        f"题干预览：{_preview_text(question_text)}；"
        f"知识点：{kp_text}；"
        f"搜索意图：{(keyword or '').strip()}"
    )
    return {
        "type": "noul",
        "instructions": instructions,
        "criteria": {
            "true": "题目考查的知识点、方法或问题情境与搜索意图直接相关",
            "false": "只是同学科或主题相近，但没有考查用户要搜索的内容",
        },
    }


def _map_usage(payload: Dict[str, Any]) -> Dict[str, int]:
    usage = payload.get("usage") if isinstance(payload.get("usage"), dict) else {}
    prompt = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
    completion = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
    total = int(usage.get("total_tokens") or (prompt + completion))
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
        "reasoning_tokens": 0,
    }


def _answer_noul(answers: Dict[str, Any], question_id: int) -> Optional[float]:
    key = f"q_{question_id}"
    entry = answers.get(key)
    if entry is None:
        return None
    if isinstance(entry, (int, float)):
        return float(entry)
    if isinstance(entry, dict):
        raw = entry.get("noul")
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None
    return None


@dataclass
class RankedCandidate:
    question_id: int
    relevance: float
    candidate: Dict[str, Any]


class JevClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        log_root: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        source: str = "backend",
    ):
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "").rstrip("/")
        self.model = (model or jev_model()).strip() or DEFAULT_MODEL
        self.timeout = float(timeout if timeout is not None else search_timeout())
        self._owns_client = http_client is None
        self._http = http_client
        self.logger = CallLogger(
            log_root or os.getenv("API_OUTPUT_ROOT") or "api_runs",
            self.api_key,
            self.base_url,
            source=source,
        )

    @property
    def enabled(self) -> bool:
        key = self.api_key.lower()
        return bool(self.api_key) and not key.startswith(
            ("your_", "your-", "sk-xxx", "sk-your", "<", "change", "placeholder")
        )

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/systemone"

    def _get_http(self) -> httpx.AsyncClient:
        if self._http is None:
            # trust_env=False：避免桌面代理环境变量（HTTP(S)_PROXY/NO_PROXY）干扰服务端调用
            self._http = httpx.AsyncClient(timeout=self.timeout, trust_env=False)
            self._owns_client = True
        return self._http

    async def aclose(self) -> None:
        if self._owns_client and self._http is not None:
            await self._http.aclose()
            self._http = None

    async def rank_candidates(
        self,
        *,
        keyword: str,
        candidates: Sequence[Dict[str, Any]],
        subject: Optional[str] = None,
        education_level: Optional[str] = None,
        teacher_id: Optional[int] = None,
    ) -> List[RankedCandidate]:
        if not self.enabled:
            raise JevError("未配置有效的 AI API Key")
        if not candidates:
            return []

        from trial_quota import before_call

        before_call(teacher_id)

        questions: Dict[str, Any] = {}
        ordered: List[Dict[str, Any]] = []
        for item in candidates:
            qid = int(item["id"])
            questions[f"q_{qid}"] = build_noul_question(
                question_id=qid,
                question_text=str(item.get("question_text") or ""),
                knowledge_points=item.get("knowledge_points"),
                keyword=keyword,
            )
            ordered.append(item)

        body = {
            "model": self.model,
            "state": (
                f"学科：{subject or '未指定'}；"
                f"学段：{education_level or '未指定'}；"
                f"搜索意图：{(keyword or '').strip()}"
            ),
            "questions": questions,
        }
        candidate_ids = [int(item["id"]) for item in ordered]
        task_meta = {
            "teacher_id": teacher_id,
            "subject": subject,
            "education_level": education_level,
            "keyword": (keyword or "").strip(),
            "candidate_count": len(candidate_ids),
        }
        log_request = {
            "endpoint": "systemone",
            "model": self.model,
            "keyword": (keyword or "").strip(),
            "candidate_count": len(candidate_ids),
            "candidate_ids": candidate_ids,
            "subject": subject,
            "education_level": education_level,
        }

        call_id = str(uuid.uuid4())
        task_id = call_id
        start = time.perf_counter()
        try:
            response = await self._get_http().post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
        except Exception as exc:  # noqa: BLE001
            elapsed = time.perf_counter() - start
            await self.logger.log_call(
                call_id=call_id,
                task_id=task_id,
                feature=FEATURE,
                model=self.model,
                request=log_request,
                task_meta=task_meta,
                success=False,
                elapsed=elapsed,
                usage=zero_usage(),
                content="",
                finish_reason=None,
                response_id=None,
                error={"type": type(exc).__name__, "message": str(exc)[:2000]},
            )
            raise JevError(f"Jev 请求失败：{type(exc).__name__}: {exc}") from exc

        elapsed = time.perf_counter() - start
        if response.status_code < 200 or response.status_code >= 300:
            summary = (response.text or "")[:500]
            await self.logger.log_call(
                call_id=call_id,
                task_id=task_id,
                feature=FEATURE,
                model=self.model,
                request=log_request,
                task_meta=task_meta,
                success=False,
                elapsed=elapsed,
                usage=zero_usage(),
                content="",
                finish_reason=None,
                response_id=None,
                error={
                    "type": "HTTPStatusError",
                    "message": f"HTTP {response.status_code}: {summary}",
                },
            )
            raise JevError(f"Jev HTTP {response.status_code}")

        try:
            payload = response.json()
        except Exception as exc:  # noqa: BLE001
            await self.logger.log_call(
                call_id=call_id,
                task_id=task_id,
                feature=FEATURE,
                model=self.model,
                request=log_request,
                task_meta=task_meta,
                success=False,
                elapsed=elapsed,
                usage=zero_usage(),
                content="",
                finish_reason=None,
                response_id=None,
                error={"type": type(exc).__name__, "message": str(exc)[:2000]},
            )
            raise JevError("Jev 响应不是合法 JSON") from exc

        if not isinstance(payload, dict) or not isinstance(payload.get("answers"), dict):
            await self.logger.log_call(
                call_id=call_id,
                task_id=task_id,
                feature=FEATURE,
                model=str(payload.get("model") if isinstance(payload, dict) else self.model),
                request=log_request,
                task_meta=task_meta,
                success=False,
                elapsed=elapsed,
                usage=zero_usage(),
                content="",
                finish_reason=None,
                response_id=None,
                error={"type": "ResponseFormatError", "message": "missing answers"},
            )
            raise JevError("Jev 响应缺少 answers")

        answers = payload["answers"]
        usage = _map_usage(payload)
        returned_model = str(payload.get("model") or self.model)
        ranked: List[RankedCandidate] = []
        for item in ordered:
            qid = int(item["id"])
            score = _answer_noul(answers, qid)
            if score is None:
                continue
            ranked.append(RankedCandidate(question_id=qid, relevance=score, candidate=item))
        ranked.sort(key=lambda row: (-row.relevance, -row.question_id))

        await self.logger.log_call(
            call_id=call_id,
            task_id=task_id,
            feature=FEATURE,
            model=returned_model,
            request=log_request,
            task_meta=task_meta,
            success=True,
            elapsed=elapsed,
            usage=usage,
            content=f"ranked={len(ranked)}",
            finish_reason="stop",
            response_id=str(payload.get("id") or "") or None,
            error=None,
        )
        from trial_quota import add_tokens

        add_tokens(teacher_id, usage.get("total_tokens"))
        return ranked


_default_client: Optional[JevClient] = None


def get_jev_client(*, http_client: Optional[httpx.AsyncClient] = None) -> JevClient:
    """默认单例；传入 http_client 时返回临时实例（便于测试注入 MockTransport）。"""
    if http_client is not None:
        from config import settings

        return JevClient(
            api_key=settings.LLM.api_key,
            base_url=settings.LLM.base_url,
            log_root=settings.LLM.log_root,
            http_client=http_client,
        )
    global _default_client
    if _default_client is None:
        from config import settings

        _default_client = JevClient(
            api_key=settings.LLM.api_key,
            base_url=settings.LLM.base_url,
            log_root=settings.LLM.log_root,
        )
    return _default_client


def reset_jev_client() -> None:
    global _default_client
    _default_client = None
